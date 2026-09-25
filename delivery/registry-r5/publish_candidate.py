"""Publish an already-built candidate to the scoped S3 pull registry.

The eleven upstream base descriptors and bytes are preserved. Docker save is
streamed twice instead of creating another full-size image tar on disk.
No registry address, credentials or signed URL is written to public receipts.
"""
from __future__ import annotations
import contextlib, gzip, hashlib, json, os, pathlib, subprocess, tarfile, tempfile, time
import boto3, requests
from boto3.s3.transfer import TransferConfig
from botocore.exceptions import ClientError

STACK = 'von-registry-r5b-20260925'
BASE_DIGEST = 'sha256:3174cb7061d94c427da96c0edef4adea28046fa3f3b2ff3948dc4e995665ff8c'
BASE_NAME = 'rocm/pytorch:rocm10.0_ubuntu26.04_py3.14_pytorch_release_2.13.0'
IMAGE = 'von-read-candidate:local'
MAX_COMPRESSED = 31 * 2**30
CHUNK = 8 * 2**20
OUT = pathlib.Path('receipts')


def digest(data):
    return 'sha256:' + hashlib.sha256(data).hexdigest()


def inspect_image(name):
    return json.loads(subprocess.check_output(['docker', 'image', 'inspect', name], timeout=30))[0]


def check_base(candidate, base, upstream_config):
    layers = base['RootFS']['Layers']
    if len(layers) != 11 or upstream_config['rootfs']['diff_ids'] != layers:
        raise ValueError('Mandatory base layer identity differs')
    if candidate['RootFS']['Layers'][:len(layers)] != layers:
        raise ValueError('Candidate lost mandatory base layers')
    if candidate['Architecture'] != 'amd64' or candidate['Os'] != 'linux':
        raise ValueError('Unexpected candidate platform')
    if not 0 < candidate['Size'] < 60 * 2**30:
        raise ValueError('Uncompressed image exceeds the gate')
    if candidate['Config']['Entrypoint'] != ['python3','-m','von_read.warm_runtime','supervise']:
        raise ValueError('Unexpected entrypoint')


@contextlib.contextmanager
def saved_image():
    with tempfile.TemporaryFile() as err:
        proc = subprocess.Popen(['docker', 'image', 'save', IMAGE], stdout=subprocess.PIPE, stderr=err)
        try:
            with tarfile.open(fileobj=proc.stdout, mode='r|') as archive:
                yield archive
            while proc.stdout.read(CHUNK):
                pass
            if proc.wait(timeout=30):
                raise RuntimeError('Docker image export failed')
        finally:
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    proc.kill(); proc.wait()
            proc.stdout.close()


def read_manifest(archive):
    result = None
    for member in archive:
        if member.name.lstrip('./') == 'manifest.json':
            if result is not None or member.size > 262144:
                raise ValueError('Invalid Docker save manifest')
            result = json.load(archive.extractfile(member))
    if not isinstance(result, list) or len(result) != 1:
        raise ValueError('Expected one saved image')
    row = result[0]
    if not isinstance(row.get('Config'), str) or not isinstance(row.get('Layers'), list):
        raise ValueError('Unsupported Docker export structure')
    if len(set(row['Layers'])) != len(row['Layers']):
        raise ValueError('Repeated archive layer path')
    return row


def compress_new_layer(source, size, expected_diffid, dest):
    sha = hashlib.sha256(); total = 0
    with dest.open('xb') as f, gzip.GzipFile(fileobj=f, mode='wb', filename='', mtime=0, compresslevel=1) as gz:
        while True:
            block = source.read(CHUNK)
            if not block:
                break
            total += len(block)
            if total > size:
                raise ValueError('Layer bytes exceeded archive header')
            sha.update(block); gz.write(block)
    if total != size or 'sha256:' + sha.hexdigest() != expected_diffid:
        raise ValueError('Uncompressed layer differs from Docker rootfs identity')
    sha = hashlib.sha256()
    with dest.open('rb') as f:
        for block in iter(lambda: f.read(CHUNK), b''):
            sha.update(block)
    return {'digest':'sha256:'+sha.hexdigest(), 'size':dest.stat().st_size,
            'mediaType':'application/vnd.oci.image.layer.v1.tar+gzip'}


def main():
    OUT.mkdir(exist_ok=True)
    t = time.monotonic()
    stack = boto3.client('cloudformation', region_name='us-east-1').describe_stacks(StackName=STACK)['Stacks'][0]
    if stack['StackStatus'] != 'UPDATE_COMPLETE':
        raise ValueError('Registry is not ready')
    out = {v['OutputKey']:v['OutputValue'] for v in stack['Outputs']}
    bucket, repo = out['Bucket'], out['Repository']
    for value in (out['RegistryUrl'], out['RegistryUrl'].removeprefix('https://').rstrip('/')+'/'+repo):
        print('::add-mask::'+value, flush=True)
    s3 = boto3.client('s3', region_name='us-east-1')
    prefix = 'v2/'+repo+'/'
    http = requests.Session()
    auth = http.get('https://auth.docker.io/token', params={'service':'registry.docker.io','scope':'repository:rocm/pytorch:pull'}, timeout=30)
    auth.raise_for_status()
    bearer = {'Authorization':'Bearer '+auth.json()['token']}
    accept = ','.join(['application/vnd.oci.image.index.v1+json','application/vnd.docker.distribution.manifest.list.v2+json','application/vnd.oci.image.manifest.v1+json','application/vnd.docker.distribution.manifest.v2+json'])
    def get_manifest(ref):
        r = http.get('https://registry-1.docker.io/v2/rocm/pytorch/manifests/'+ref, headers={**bearer,'Accept':accept}, timeout=30)
        r.raise_for_status()
        if digest(r.content) != ref:
            raise ValueError('Base manifest digest differs')
        return r.json()
    upstream = get_manifest(BASE_DIGEST)
    if 'manifests' in upstream:
        options = [r for r in upstream['manifests'] if r.get('platform',{}).get('os')=='linux' and r.get('platform',{}).get('architecture')=='amd64']
        if len(options) != 1: raise ValueError('Ambiguous base platform')
        upstream = get_manifest(options[0]['digest'])
    cfg = http.get('https://registry-1.docker.io/v2/rocm/pytorch/blobs/'+upstream['config']['digest'], headers=bearer, timeout=30)
    cfg.raise_for_status()
    if digest(cfg.content) != upstream['config']['digest']: raise ValueError('Base config digest differs')
    base = inspect_image(BASE_NAME); candidate = inspect_image(IMAGE)
    if base['Id'] != upstream['config']['digest']: raise ValueError('Base tag no longer matches the reviewed digest')
    check_base(candidate, base, cfg.json())
    layers = list(upstream['layers']); base_n = len(layers)
    transfer = TransferConfig(multipart_threshold=64*2**20, multipart_chunksize=64*2**20, max_concurrency=2)
    published = []; reused = []
    def exists(descriptor, kind='blobs'):
        try:
            h = s3.head_object(Bucket=bucket, Key=prefix+kind+'/'+descriptor['digest'])
        except ClientError as e:
            if str(e.response['Error']['Code']) in ('404','403','NoSuchKey','AccessDenied','NotFound'): return False
            raise
        if h['ContentLength'] != descriptor['size'] or h.get('Metadata',{}).get('digest') != descriptor['digest']:
            raise ValueError('Stored object conflicts with content-addressed descriptor')
        return True
    for layer in layers:
        if exists(layer):
            reused.append(layer['digest']); continue
        resp = http.get('https://registry-1.docker.io/v2/rocm/pytorch/blobs/'+layer['digest'], headers=bearer, stream=True, timeout=(15,120))
        resp.raise_for_status()
        upload = s3.create_multipart_upload(Bucket=bucket, Key=prefix+'blobs/'+layer['digest'], ContentType=layer['mediaType'], Metadata={'digest':layer['digest']})['UploadId']
        parts=[]; h=hashlib.sha256(); count=0
        try:
            for number, block in enumerate(resp.iter_content(chunk_size=64*2**20),1):
                h.update(block); count += len(block)
                if count > layer['size']: raise ValueError('Oversized base stream')
                p=s3.upload_part(Bucket=bucket,Key=prefix+'blobs/'+layer['digest'],UploadId=upload,PartNumber=number,Body=block)
                parts.append({'PartNumber':number,'ETag':p['ETag']})
            if count != layer['size'] or 'sha256:'+h.hexdigest() != layer['digest']:
                raise ValueError('Base bytes changed during transfer')
            s3.complete_multipart_upload(Bucket=bucket,Key=prefix+'blobs/'+layer['digest'],UploadId=upload,MultipartUpload={'Parts':parts})
        except BaseException:
            s3.abort_multipart_upload(Bucket=bucket,Key=prefix+'blobs/'+layer['digest'],UploadId=upload); raise
        finally: resp.close()
        published.append(layer['digest'])
    print(json.dumps({'phase':'base_preserved','layers':base_n,'reused':len(reused)}),flush=True)
    with saved_image() as archive:
        manifest = read_manifest(archive)
    diffs = candidate['RootFS']['Layers']
    if len(manifest['Layers']) != len(diffs): raise ValueError('Save layer count differs')
    appended = dict(zip(manifest['Layers'][base_n:],diffs[base_n:]))
    encoded = {}; config_bytes = None
    with tempfile.TemporaryDirectory(prefix='von-new-layers-') as temp:
        with saved_image() as archive:
            for member in archive:
                if member.name == manifest['Config']:
                    if member.size > 2**20: raise ValueError('Oversized config')
                    config_bytes = archive.extractfile(member).read()
                    if digest(config_bytes) != candidate['Id']: raise ValueError('Candidate config differs')
                elif member.name in appended:
                    if not member.isfile() or member.size > 12*2**30: raise ValueError('Unexpected application layer')
                    path=pathlib.Path(temp)/('layer-'+str(len(encoded))+'.tar.gz')
                    d=compress_new_layer(archive.extractfile(member),member.size,appended[member.name],path)
                    if sum(x['size'] for x in layers)+sum(x['size'] for x in encoded.values())+d['size']>MAX_COMPRESSED:
                        raise ValueError('Compressed transfer budget exceeded')
                    if exists(d): reused.append(d['digest'])
                    else:
                        s3.upload_file(str(path),bucket,prefix+'blobs/'+d['digest'],ExtraArgs={'ContentType':d['mediaType'],'Metadata':{'digest':d['digest']}},Config=transfer)
                        published.append(d['digest'])
                    encoded[member.name]=d;path.unlink()
                    print(json.dumps({'phase':'application_layer','count':len(encoded),'compressed_bytes':d['size']}),flush=True)
    if config_bytes is None or set(encoded) != set(appended): raise ValueError('Incomplete candidate export')
    config = {'mediaType':'application/vnd.oci.image.config.v1+json','digest':digest(config_bytes),'size':len(config_bytes)}
    if json.loads(config_bytes)['rootfs']['diff_ids'] != diffs: raise ValueError('Rootfs differs after export')
    s3.put_object(Bucket=bucket,Key=prefix+'blobs/'+config['digest'],Body=config_bytes,ContentType=config['mediaType'],Metadata={'digest':config['digest']})
    final_layers = layers+[encoded[name] for name in manifest['Layers'][base_n:]]
    body=json.dumps({'schemaVersion':2,'mediaType':'application/vnd.oci.image.manifest.v1+json','config':config,'layers':final_layers},separators=(',',':')).encode()
    md=digest(body)
    for ref in (md,'candidate-r4'):
        s3.put_object(Bucket=bucket,Key=prefix+'manifests/'+ref,Body=body,ContentType='application/vnd.oci.image.manifest.v1+json',Metadata={'digest':md})
    report={'status':'published','candidate_config_digest':config['digest'],'candidate_manifest_digest':md,'base_manifest_digest':BASE_DIGEST,'base_descriptors_preserved':len(layers),'base_bytes_reencoded':False,'rootfs_diff_ids':diffs,'uncompressed_bytes':candidate['Size'],'compressed_blob_bytes':sum(r['size'] for r in final_layers)+len(config_bytes),'new_blobs_uploaded':len(published),'previous_blobs_reused':len(reused),'gpu_image_verified':False,'anonymous_full_pull_verified':False,'elapsed_seconds':time.monotonic()-t}
    (OUT/'S3_PUBLICATION.json').write_text(json.dumps(report,indent=2))
    print(json.dumps({k:v for k,v in report.items() if k!='rootfs_diff_ids'}),flush=True)

if __name__=='__main__':
    try: main()
    except Exception as error:
        print(json.dumps({'status':'failed','error_type':type(error).__name__,'message':str(error)[:300] if not isinstance(error,(requests.RequestException,ClientError)) else 'Request details suppressed'}),flush=True)
        raise SystemExit(1)
