"""Test the registry's oversized-layer blocker without a paid full-image download.
The pinned upstream layer is streamed unchanged to private S3 with bounded memory.
Only signed, byte-range-bound anonymous reads are allowed by the large-blob pilot.
"""
from __future__ import annotations
import concurrent.futures,hashlib,json,pathlib,time
import boto3,requests
from botocore.config import Config
STACK='von-registry-r5b-20260925'
BASE='sha256:3174cb7061d94c427da96c0edef4adea28046fa3f3b2ff3948dc4e995665ff8c'
EXPECTED_BYTES=19956931520
PART=64*1024*1024
SAMPLE=65536

def main():
 start=time.monotonic();aws=boto3.client('cloudformation',region_name='us-east-1')
 stack=aws.describe_stacks(StackName=STACK)['Stacks'][0]
 assert stack['StackStatus']=='UPDATE_COMPLETE'
 out={r['OutputKey']:r['OutputValue'] for r in stack['Outputs']}
 endpoint,repo,bucket=out['RegistryUrl'].rstrip('/'),out['Repository'],out['Bucket']
 assert endpoint.startswith('https://') and endpoint.endswith('.cloudfront.net')
 print('::add-mask::'+endpoint);print('::add-mask::'+endpoint.removeprefix('https://')+'/'+repo)
 http=requests.Session()
 token_reply=http.get('https://auth.docker.io/token',params={'service':'registry.docker.io','scope':'repository:rocm/pytorch:pull'},timeout=30)
 token_reply.raise_for_status();token=token_reply.json()['token']
 headers={'Authorization':'Bearer '+token,'Accept':'application/vnd.oci.image.index.v1+json,application/vnd.docker.distribution.manifest.list.v2+json,application/vnd.oci.image.manifest.v1+json,application/vnd.docker.distribution.manifest.v2+json'}
 def manifest(ref):
  response=http.get('https://registry-1.docker.io/v2/rocm/pytorch/manifests/'+ref,headers=headers,timeout=30)
  response.raise_for_status();assert 'sha256:'+hashlib.sha256(response.content).hexdigest()==ref
  return response.json()
 top=manifest(BASE)
 if 'manifests' in top:
  candidates=[r for r in top['manifests'] if r.get('platform',{}).get('os')=='linux' and r.get('platform',{}).get('architecture')=='amd64']
  assert len(candidates)==1;top=manifest(candidates[0]['digest'])
 layer=max(top['layers'],key=lambda r:r['size']);assert layer['size']==EXPECTED_BYTES
 key='v2/'+repo+'/blobs/'+layer['digest']
 s3=boto3.client('s3',region_name='us-east-1',config=Config(connect_timeout=10,read_timeout=120,retries={'max_attempts':2}))
 response=http.get('https://registry-1.docker.io/v2/rocm/pytorch/blobs/'+layer['digest'],headers={'Authorization':'Bearer '+token},stream=True,timeout=(15,120))
 response.raise_for_status();assert int(response.headers['Content-Length'])==EXPECTED_BYTES
 upload=s3.create_multipart_upload(Bucket=bucket,Key=key,ContentType=layer['mediaType'],Metadata={'digest':layer['digest']})['UploadId']
 parts=[];pending=[];sha=hashlib.sha256();total=0;first=b'';last=b''
 def send(number,body):
  reply=s3.upload_part(Bucket=bucket,Key=key,UploadId=upload,PartNumber=number,Body=body)
  return {'PartNumber':number,'ETag':reply['ETag']}
 try:
  with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
   for number,body in enumerate(response.iter_content(chunk_size=PART),1):
    if time.monotonic()-start>1000:raise TimeoutError('Bounded large-layer upload')
    total+=len(body);assert total<=EXPECTED_BYTES
    sha.update(body)
    if not first:first=body[:SAMPLE]
    last=(last+body)[-SAMPLE:]
    pending.append(pool.submit(send,number,body))
    if len(pending)>=2:parts.append(pending.pop(0).result())
    if number%32==0:print(json.dumps({'phase':'private_upload','bytes_read':total,'parts_submitted':number}),flush=True)
   parts.extend(f.result() for f in pending)
  assert total==EXPECTED_BYTES and 'sha256:'+sha.hexdigest()==layer['digest']
  s3.complete_multipart_upload(Bucket=bucket,Key=key,UploadId=upload,MultipartUpload={'Parts':sorted(parts,key=lambda p:p['PartNumber'])})
 except BaseException:
  s3.abort_multipart_upload(Bucket=bucket,Key=key,UploadId=upload)
  raise
 finally:response.close()
 private=s3.head_object(Bucket=bucket,Key=key);assert private['ContentLength']==EXPECTED_BYTES
 url=endpoint+'/v2/'+repo+'/blobs/'+layer['digest']
 public_head=requests.head(url,timeout=15)
 assert public_head.status_code==200 and int(public_head.headers['Content-Length'])==EXPECTED_BYTES
 assert public_head.headers['Docker-Content-Digest']==layer['digest']
 assert requests.get(url,allow_redirects=False,timeout=15).status_code==413,'Large full download must remain disabled in the pilot'
 checks=[]
 for begin,end,expected in [(0,SAMPLE-1,first),(EXPECTED_BYTES-SAMPLE,EXPECTED_BYTES-1,last)]:
  result=requests.get(url,headers={'Range':f'bytes={begin}-{end}'},timeout=30)
  assert result.status_code==206 and result.content==expected
  checks.append({'range_start':begin,'range_end':end,'bytes':len(result.content),'sha256':hashlib.sha256(result.content).hexdigest()})
 report={'status':'passed','upstream_base_manifest':BASE,'layer_digest':layer['digest'],'layer_bytes':total,'multipart_parts':len(parts),'full_stream_sha256_verified':True,'layer_reencoded':False,'layer_split_in_image_manifest':False,'anonymous_head':True,'anonymous_ranges':checks,'full_large_download_disabled':True,'full_candidate_image_published':False,'gpu_test':False,'elapsed_seconds':time.monotonic()-start}
 folder=pathlib.Path('/tmp/von-registry-receipt');folder.mkdir(exist_ok=True)
 (folder/'LARGE_LAYER.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
if __name__=='__main__':
 try:main()
 except Exception as error:
  print(json.dumps({'status':'failed','error_type':type(error).__name__,'private_request_details':'suppressed'}));raise SystemExit(1)
