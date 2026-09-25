"""Small transport fixture only. No model, GPU, image rebuild or public credentials.
AWS writes use the branch-scoped OIDC role; Docker pulls use an empty auth config.
The endpoint stays out of public output and artifacts.
"""
from __future__ import annotations
import gzip, hashlib, io, json, os, pathlib, subprocess, tarfile, tempfile, time
import boto3
import requests

REGION = 'us-east-1'
STACK = 'von-registry-r5-20260925'
OCI = 'application/vnd.oci.image.manifest.v1+json'
CONFIG = 'application/vnd.oci.image.config.v1+json'
LAYER = 'application/vnd.oci.image.layer.v1.tar+gzip'

def digest(data: bytes) -> str:
    return 'sha256:' + hashlib.sha256(data).hexdigest()

def encoded(obj: dict) -> bytes:
    return json.dumps(obj, separators=(',', ':'), sort_keys=True).encode()

def main() -> None:
    started = time.monotonic()
    cfn = boto3.client('cloudformation', region_name=REGION)
    state = cfn.describe_stacks(StackName=STACK)['Stacks'][0]
    assert state['StackStatus'] == 'CREATE_COMPLETE', 'Registry stack is not ready'
    out = {v['OutputKey']:v['OutputValue'] for v in state['Outputs']}
    base, repo, bucket = out['RegistryUrl'].rstrip('/'), out['Repository'], out['Bucket']
    host = base.removeprefix('https://')
    assert host.endswith('.lambda-url.us-east-1.on.aws')
    print('::add-mask::' + base)
    print('::add-mask::' + host + '/' + repo)
    s3 = boto3.client('s3', region_name=REGION)
    proof = b'von-read isolated registry transport test\nNot an OCR evaluation.\n'
    stream = io.BytesIO()
    with tarfile.open(fileobj=stream, mode='w', format=tarfile.USTAR_FORMAT) as tar:
        info = tarfile.TarInfo('proof.txt'); info.size = len(proof); info.mode = 0o644; info.mtime = 0
        tar.addfile(info, io.BytesIO(proof))
    raw = stream.getvalue()
    layer = gzip.compress(raw, mtime=0)
    config = encoded({'architecture':'amd64','os':'linux','config':{'Labels':{'purpose':'authored registry transport fixture; not OCR'}},'rootfs':{'type':'layers','diff_ids':[digest(raw)]},'history':[{'created_by':'von-read transport probe'}]})
    manifest = encoded({'schemaVersion':2,'mediaType':OCI,'config':{'mediaType':CONFIG,'size':len(config),'digest':digest(config)},'layers':[{'mediaType':LAYER,'size':len(layer),'digest':digest(layer)}]})
    for payload,kind,reference,media in [(layer,'blobs',digest(layer),LAYER),(config,'blobs',digest(config),CONFIG),(manifest,'manifests',digest(manifest),OCI),(manifest,'manifests','smoke',OCI)]:
        assert len(payload) < 16384
        s3.put_object(Bucket=bucket,Key=f'v2/{repo}/{kind}/{reference}',Body=payload,ContentType=media,Metadata={'digest':digest(payload)})
    session = requests.Session()
    assert not session.auth
    results = {'scope':'small authored transport fixture; no real OCR image','anonymous':True,'credential_free_docker_config':True,'checks':{},'uploaded_objects':4,'uploaded_bytes':len(layer)+len(config)+2*len(manifest),'full_weighted_image_uploaded':False}
    def check(name: str, condition: bool) -> None:
        results['checks'][name] = bool(condition)
        if not condition: raise AssertionError(name)
    check('v2_ping', session.get(base+'/v2/',timeout=10).status_code == 200)
    url = f'{base}/v2/{repo}/manifests/smoke'
    head = session.head(url,timeout=10)
    check('manifest_head', head.status_code == 200 and head.headers.get('Docker-Content-Digest') == digest(manifest) and int(head.headers['Content-Length']) == len(manifest))
    got = session.get(url,timeout=10)
    check('manifest_exact_bytes', got.status_code == 200 and got.content == manifest)
    check('digest_addressing', session.get(f'{base}/v2/{repo}/manifests/{digest(manifest)}',timeout=10).content == manifest)
    blob = f'{base}/v2/{repo}/blobs/{digest(layer)}'
    redirect = session.get(blob,allow_redirects=False,timeout=10)
    check('private_s3_redirect', redirect.status_code == 307 and redirect.headers.get('Location','').startswith('https://'))
    actual = session.get(blob,timeout=10)
    check('anonymous_blob_hash', actual.status_code == 200 and digest(actual.content) == digest(layer))
    ranged = session.get(blob,headers={'Range':'bytes=0-15'},timeout=10)
    check('blob_range', ranged.status_code == 206 and ranged.content == layer[:16])
    for method in ('PUT','POST','DELETE','PATCH'):
        check('deny_'+method.lower(), session.request(method,url,data=b'no-write',timeout=10).status_code == 405)
    check('unknown_repository', session.get(base+'/v2/not-our-repository/manifests/smoke',timeout=10).status_code == 404)
    direct = f'https://{bucket}.s3.{REGION}.amazonaws.com/v2/{repo}/blobs/{digest(layer)}'
    check('direct_bucket_denied', session.get(direct,timeout=10).status_code == 403)
    with tempfile.TemporaryDirectory(prefix='von-registry-probe-') as temp:
        auth = pathlib.Path(temp)/'auth'; auth.mkdir(); (auth/'config.json').write_text('{}')
        ref = host+'/'+repo+':smoke'
        pulled = subprocess.run(['docker','--config',str(auth),'pull',ref],capture_output=True,text=True,timeout=120)
        check('real_docker_anonymous_pull', pulled.returncode == 0)
        inspected = subprocess.run(['docker','image','inspect',ref],capture_output=True,text=True,check=True,timeout=10)
        data = json.loads(inspected.stdout)[0]
        check('docker_layer_identity', data['RootFS']['Layers'] == [digest(raw)])
        archive = pathlib.Path(temp)/'image.tar'
        with archive.open('wb') as f: subprocess.run(['docker','image','save',ref],stdout=f,stderr=subprocess.DEVNULL,check=True,timeout=30)
        with tarfile.open(archive) as image:
            exported = json.load(image.extractfile('manifest.json'))[0]
            layer_content = image.extractfile(exported['Layers'][0]).read()
            check('docker_export_layer_hash', digest(layer_content) == digest(raw))
            with tarfile.open(fileobj=io.BytesIO(layer_content)) as files:
                check('docker_export_payload', files.extractfile('proof.txt').read() == proof)
        subprocess.run(['docker','image','rm',ref],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=15)
    results['elapsed_seconds'] = time.monotonic()-started
    results['status'] = 'passed'
    pathlib.Path('/tmp/von-registry-receipt').mkdir(exist_ok=True)
    pathlib.Path('/tmp/von-registry-receipt/PROBE.json').write_text(json.dumps(results,indent=2))
    print(json.dumps(results))

if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        # Do not expose URLs, signed redirects or AWS credentials through errors.
        print(json.dumps({'status':'failed','error_type':type(error).__name__,'message':str(error) if isinstance(error,AssertionError) else 'Inspect private AWS state; request details redacted'}))
        raise SystemExit(1)
