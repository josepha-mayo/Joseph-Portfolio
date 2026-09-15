"""Bounded Countback AWS trial using an existing scoped assumed role.

No IAM writes, public endpoint, event sources, private photographs or retrying
invocations. Records actual AWS receipts separately from the unchanged handler.
"""
from __future__ import annotations
import argparse, base64, copy, hashlib, io, json, os, re, subprocess, sys, time, zipfile
from pathlib import Path
from datetime import datetime, timezone
import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
from PIL import Image

REGION='us-east-1'
FUNCTION='countback-validation-v1'
REPOSITORY='countback-validation'
LOG_GROUP='/aws/lambda/'+FUNCTION
IMAGE_ZIP_SHA='a298a354afeef4dfc3108602f056d9f3b1a53501c0925f58f15350d785ff7ed6'
IMAGE_TAR_SHA='5600736960ba040892b756cd76d74c81db529ed7373f53fdde6448bdf77b76e0'
IMAGE_ID='sha256:8182323674be852b8f2ee782a275e61c4b5d992c4e99ecb3e709f2420d17f66a'
OLD_SHA='6ff6c03f5c473bc8b04c29bd0033bb75e298208ee762b057a0b28806740f96bb'
FRESH_SHA='8198234666f1159c0b587fbcece4c22a2dca5db55d5cc30a52b041926ef902e5'
MAX_INVOKES=20

def sha(data): return hashlib.sha256(data).hexdigest()
def stamp(): return datetime.now(timezone.utc).isoformat()
def hash_file(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for part in iter(lambda:f.read(1024*1024),b''): h.update(part)
    return h.hexdigest()
def checked_zip(path, expected):
    assert hash_file(path)==expected,'Pinned archive checksum mismatch'
    z=zipfile.ZipFile(path);assert z.testzip() is None,'Corrupt archive';return z

def public_event(old_path,fresh_path):
    with checked_zip(old_path,OLD_SHA) as old,checked_zip(fresh_path,FRESH_SHA) as fresh:
        reference=Image.open(io.BytesIO(old.read('files/167/167/0094_rgb.png'))).convert('RGB')
        crops={'chips_can':[261,321,458,406],'mustard_bottle':[826,328,925,488],'hot_sauce':[981,462,1090,595]}
        raw={};refs={}
        for label,box in crops.items():
            b=io.BytesIO();reference.crop(box).save(b,format='PNG');raw[label+'.png']=b.getvalue()
            refs[label]={'filename':label+'.png','roi_fraction':[0,0,1,1]}
        views=[]
        for f in ['0064','0128']:
            n='group-'+f+'.png';raw[n]=fresh.read('files/171/171/'+f+'_rgb.png');views.append(n)
    assert sum(map(len,raw.values()))<=3600000
    return {'schema':'countback-inline-analysis-1','photo_processing_authorized':True,
      'manifest':{'schema':'countback-reference-rois-1','references':refs,'views':views},
      'images':{n:{'sha256':sha(b),'base64':base64.b64encode(b).decode()} for n,b in raw.items()}}

def main(a):
    a.out.mkdir(parents=True,exist_ok=False)
    config=Config(region_name=REGION,retries={'total_max_attempts':1},connect_timeout=10,read_timeout=110)
    session=boto3.Session(region_name=REGION)
    sts=session.client('sts',config=config);ecr=session.client('ecr',config=config)
    lam=session.client('lambda',config=config);logs=session.client('logs',config=config)
    identity=sts.get_caller_identity();account=identity['Account']
    assert ':assumed-role/countback-github-trial/' in identity['Arn'],'Non-root dedicated trial role required'
    def safe(obj): return json.loads(json.dumps(obj,default=str).replace(account,'ACCOUNT_ID_REDACTED'))
    def save(name,value): (a.out/name).write_text(json.dumps(safe(value),indent=2,allow_nan=False)+'\n')
    report={'schema':'countback-actual-aws-trial-1','status':'running','started_at':stamp(),'region':REGION,
      'deployment_identity':'assumed-role/countback-github-trial','budget_ceiling_usd':5,
      'max_invocations':MAX_INVOKES,'invocations':[],'created_resources':[],'cleanup':[],
      'private_photos_used':False,'public_endpoint_created':False,'pose_refinement_executed_in_aws':False,
      'source_commit':os.environ.get('GITHUB_SHA'),'github_run':os.environ.get('GITHUB_RUN_ID'),
      'tested_image_id':IMAGE_ID,'iam_created_by_this_script':False}
    created=set();failed=False;image_tar=Path('/tmp/countback-lambda.tar')
    def checkpoint(): save('AWS_TRIAL.json',report)
    def missing_call(client,method,kwargs,missing_codes):
        try: getattr(client,method)(**kwargs)
        except ClientError as err:
            if err.response['Error']['Code'] in missing_codes:return
            raise
        raise ValueError('Existing resource found; refusing replacement')
    try:
        missing_call(ecr,'describe_repositories',{'repositoryNames':[REPOSITORY]},['RepositoryNotFoundException'])
        missing_call(lam,'get_function',{'FunctionName':FUNCTION},['ResourceNotFoundException'])
        # Create the named log group first. Existing groups are never overwritten.
        logs.create_log_group(logGroupName=LOG_GROUP,tags={'Project':'Countback','Purpose':'ApprovedFiveDollarTrial'})
        created.add('logs');report['created_resources'].append(LOG_GROUP);checkpoint()
        logs.put_retention_policy(logGroupName=LOG_GROUP,retentionInDays=7)
        with checked_zip(a.image,IMAGE_ZIP_SHA) as z:
            assert z.namelist()==['countback-lambda.tar']
            with z.open('countback-lambda.tar') as src,image_tar.open('xb') as dst:
                for part in iter(lambda:src.read(1024*1024),b''):dst.write(part)
        assert hash_file(image_tar)==IMAGE_TAR_SHA,'Tested image bytes changed'
        subprocess.run(['docker','load','--input',str(image_tar)],check=True,capture_output=True)
        loaded=json.loads(subprocess.check_output(['docker','image','inspect',IMAGE_ID]))[0]
        assert loaded['Id']==IMAGE_ID and loaded['Architecture']=='amd64'
        repo=ecr.create_repository(repositoryName=REPOSITORY,imageTagMutability='IMMUTABLE',
          imageScanningConfiguration={'scanOnPush':False},tags=[{'Key':'Project','Value':'Countback'}])['repository']
        created.add('ecr');report['created_resources'].append(REPOSITORY);checkpoint()
        repository_uri=repo['repositoryUri'];image_tag=repository_uri+':validated-image'
        policy={'Version':'2012-10-17','Statement':[{'Sid':'ExactCountbackLambdaImageRead','Effect':'Allow',
          'Principal':{'Service':'lambda.amazonaws.com'},'Action':['ecr:BatchGetImage','ecr:GetDownloadUrlForLayer'],
          'Condition':{'StringEquals':{'aws:SourceAccount':account},
            'ArnLike':{'aws:SourceArn':'arn:aws:lambda:'+REGION+':'+account+':function:'+FUNCTION}}}]}
        ecr.set_repository_policy(repositoryName=REPOSITORY,policyText=json.dumps(policy))
        auth=ecr.get_authorization_token()['authorizationData'][0]
        username,password=base64.b64decode(auth['authorizationToken']).decode().split(':',1)
        subprocess.run(['docker','login','--username',username,'--password-stdin',auth['proxyEndpoint']],
                       input=password+'\n',text=True,capture_output=True,check=True)
        del password,auth
        subprocess.run(['docker','tag',IMAGE_ID,image_tag],check=True,capture_output=True)
        subprocess.run(['docker','push',image_tag],check=True,capture_output=True,timeout=180)
        descriptor=ecr.describe_images(repositoryName=REPOSITORY,imageIds=[{'imageTag':'validated-image'}])['imageDetails'][0]
        digest=descriptor['imageDigest'];report['ecr_image_digest']=digest;report['ecr_image_size_bytes']=descriptor['imageSizeInBytes']
        role='arn:aws:iam::'+account+':role/countback-lambda-execution'
        fn=lam.create_function(FunctionName=FUNCTION,Description='Private bounded Countback image-analysis trial',
          Role=role,PackageType='Image',Code={'ImageUri':repository_uri+'@'+digest},Architectures=['x86_64'],
          MemorySize=2048,Timeout=90,EphemeralStorage={'Size':512},Publish=True,
          LoggingConfig={'LogFormat':'Text','LogGroup':LOG_GROUP},Tags={'Project':'Countback','Purpose':'ApprovedFiveDollarTrial'})
        created.add('lambda');report['created_resources'].append(FUNCTION);checkpoint()
        deadline=time.monotonic()+150
        while True:
            cfg=lam.get_function_configuration(FunctionName=FUNCTION)
            if cfg['State']=='Active':break
            if cfg['State']=='Failed' or time.monotonic()>deadline:raise RuntimeError('Lambda did not become active: '+cfg.get('StateReason',''))
            time.sleep(3)
        version=fn['Version'];assert version!='\u0024LATEST','Published version required'
        described=lam.get_function(FunctionName=FUNCTION,Qualifier=version)
        assert described['Code']['ResolvedImageUri'].endswith('@'+digest)
        report.update(function_version=version,memory_mb=cfg['MemorySize'],timeout_seconds=cfg['Timeout'],
          ephemeral_storage_mb=cfg['EphemeralStorage']['Size'],state=cfg['State'],aws_executed=False)
        save('FUNCTION_PROVENANCE.json',{'configuration':described['Configuration'],
          'resolved_image_uri':described['Code']['ResolvedImageUri'],'api_request_id':described['ResponseMetadata']['RequestId'],
          'observed_at':stamp(),'account_arn_redacted':True})
        root=Path(__file__).resolve().parents[1]
        sys.path.insert(0,str(root/'countback-workbench/cloud'))
        from smoke_rie import make_event
        generated=make_event()
        def invoke(name,event,expected_error=None):
            assert len(report['invocations'])<MAX_INVOKES,'Approved call count exceeded'
            payload=json.dumps(event,separators=(',',':'),allow_nan=False).encode();assert len(payload)<=5000000
            item={'case':name,'expected_error':expected_error,'started_at':stamp(),'status':'invoking',
              'input_sha256':sha(payload),'input_image_sha256':{n:r['sha256'] for n,r in event['images'].items()}}
            report['invocations'].append(item);checkpoint();start=time.monotonic()
            r=lam.invoke(FunctionName=FUNCTION,Qualifier=version,InvocationType='RequestResponse',LogType='Tail',Payload=payload)
            raw=r['Payload'].read(5000001);assert len(raw)<=5000000;value=json.loads(raw)
            tail=base64.b64decode(r.get('LogResult','')).decode(errors='replace')
            item.update(wall_seconds=round(time.monotonic()-start,3),request_id=r['ResponseMetadata']['RequestId'],
              executed_version=r.get('ExecutedVersion'),http_status=r['StatusCode'],
              function_error=r.get('FunctionError'),response_sha256=sha(raw),log_tail=tail)
            if expected_error:
                assert r.get('FunctionError') and value.get('errorType')=='ValueError',value
                assert expected_error in value.get('errorMessage',''),value
            else:
                assert not r.get('FunctionError'),value
                engine=value['engine_report'];assert engine['opencv5_executed'] and engine['opencv_version']=='5.0.0'
                assert engine['identity_verified'] is False and engine['kit_complete'] is None
                assert value['aws_execution_verified'] is False,'Do not change handler claims using an environment hint'
                for label,spec in event['manifest']['references'].items():
                    assert engine['input_provenance'][label]['sha256']==event['images'][spec['filename']]['sha256']
                for index,name_in in enumerate(event['manifest']['views'],1):
                    key='view-'+str(index)
                    if key in engine['input_provenance']:assert engine['input_provenance'][key]['sha256']==event['images'][name_in]['sha256']
                item['evidence_tiers']={n:p['evidence_level'] for n,p in engine['parts'].items()}
                item['views_processed']=engine['distinct_views'];item['engine_seconds']=engine['elapsed_seconds']
                report['aws_executed']=True
            assert all(row['base64'] not in raw.decode() for row in event['images'].values()),'Image bytes returned'
            save('response-'+name+'.json',value);item['status']='passed';checkpoint();return value
        invoke('generated-cold',generated);invoke('generated-warm',generated)
        cases=[]
        wrong=copy.deepcopy(generated);wrong['photo_processing_authorized']=False;cases.append(('permission-refused',wrong,'Explicit authorization'))
        wrong=copy.deepcopy(generated);wrong['images']['a.png']['sha256']='0'*64;cases.append(('changed-bytes',wrong,'Changed, empty or oversized'))
        wrong=copy.deepcopy(generated);wrong['manifest']['views'].append('b.png');cases.append(('duplicate-views',wrong,'Repeated group'))
        wrong=copy.deepcopy(generated);wrong['manifest']['references']['item']['roi_fraction']=[0,0,2,1];cases.append(('invalid-crop',wrong,'outside'))
        wrong=copy.deepcopy(generated);wrong['manifest']['references']['view-1']=wrong['manifest']['references'].pop('item');cases.append(('reserved-label',wrong,'reserved'))
        for name,event,error in cases:invoke(name,event,error)
        invoke('generated-recovery',generated)
        public=public_event(a.original,a.fresh);save('PUBLIC_INPUTS.json',{
          'dataset':'UW-IS Occluded v1, Figshare 20506506, CC BY 4.0',
          'authors':['Ekta U. Samani','Xingjian Yang','Srivatsa Grama Satyanarayana','Ashis G. Banerjee'],
          'reference_frame':'167/0094','observations':['171/0064','171/0128'],
          'input_image_sha256':{n:r['sha256'] for n,r in public['images'].items()},
          'scope':'Three cropped public references, two unchanged public observations. No observation masks or poses transmitted. Previously evaluated scene; not fresh accuracy evidence.'})
        invoke('public-photo-analysis',public)
        report['status']='passed';report['invocation_count']=len(report['invocations'])
        report['compute_finished_at']=stamp()
    except BaseException as error:
        failed=True;report.update(status='failed',error_type=type(error).__name__,error=str(error))
    finally:
        # Delete only resources whose successful creation this process recorded.
        for name,client,method,kwargs in [
          ('lambda',lam,'delete_function',{'FunctionName':FUNCTION}),
          ('ecr',ecr,'delete_repository',{'repositoryName':REPOSITORY,'force':True}),
          ('logs',logs,'delete_log_group',{'logGroupName':LOG_GROUP})]:
            if name not in created:continue
            try:
                getattr(client,method)(**kwargs);report['cleanup'].append({'resource':name,'status':'delete_api_succeeded','at':stamp()})
            except BaseException as error:
                report['cleanup'].append({'resource':name,'status':'failed','error':str(error)});failed=True
        report['finished_at']=stamp();report['cleanup_requests_succeeded']=all(c['status']=='delete_api_succeeded' for c in report['cleanup'])
        if not report['cleanup_requests_succeeded']:report['status']='cleanup_failed'
        report['billing_invoice_checked']=False
        report['scope']='Actual private AWS original-engine trial. Local pose refinement is separate. Nine requested tests reuse generated fixtures and a public scene; no general accuracy, kit completeness or operator-benefit claim. Compute resources deleted; separate bootstrap IAM cleanup follows.'
        checkpoint()
        subprocess.run(['docker','logout'],capture_output=True)
    print(json.dumps({'status':report['status'],'aws_executed':report.get('aws_executed',False),
      'invocations':len(report['invocations']),'cleanup_requests_succeeded':report['cleanup_requests_succeeded']}))
    return 1 if failed else 0

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--image',type=Path,required=True);p.add_argument('--original',type=Path,required=True)
    p.add_argument('--fresh',type=Path,required=True);p.add_argument('--out',type=Path,required=True);raise SystemExit(main(p.parse_args()))
