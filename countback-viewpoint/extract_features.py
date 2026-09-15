"""Offline DINOv2 dense features. No labels, depth, poses or network calls."""
from pathlib import Path
import os,sys,hashlib,json,time,argparse
import numpy as np
from PIL import Image,ImageOps
import torch
ROOT=Path(__file__).resolve().parents[1]
MODEL_DIR=ROOT/'backbone'
WEIGHT_HASH='f433177089a681826f849f194ece3bb48f4d63fb38d32fc837e3dc7a4e5641fb'

def load_model(model_dir=MODEL_DIR):
    sys.path.insert(0,str(model_dir/'dinov2-source'))
    from dinov2.hub.backbones import dinov2_vits14_reg
    weights=model_dir/'dinov2_vits14_reg4_pretrain.pth'
    if hashlib.sha256(weights.read_bytes()).hexdigest()!=WEIGHT_HASH:raise ValueError('Model weight checksum mismatch')
    torch.set_num_threads(4);torch.manual_seed(0)
    model=dinov2_vits14_reg(pretrained=False)
    model.load_state_dict(torch.load(weights,map_location='cpu',weights_only=True),strict=True)
    return model.eval()

@torch.inference_mode()
def extract(model,path,max_side):
    raw=Path(path).read_bytes();im=ImageOps.exif_transpose(Image.open(path)).convert('RGB')
    w,h=im.size;scale=max_side/max(w,h);nw=max(28,round(w*scale/14)*14);nh=max(28,round(h*scale/14)*14)
    arr=np.asarray(im.resize((nw,nh),Image.Resampling.BICUBIC)).copy()
    x=torch.from_numpy(arr).permute(2,0,1)[None].float()/255
    x=(x-torch.tensor([.485,.456,.406])[None,:,None,None])/torch.tensor([.229,.224,.225])[None,:,None,None]
    start=time.monotonic();result=model.forward_features(x);sec=time.monotonic()-start
    f=torch.nn.functional.normalize(result['x_norm_patchtokens'],dim=-1)[0].reshape(nh//14,nw//14,-1).numpy()
    return dict(features=f.astype(np.float32),original_wh=np.array([w,h]),resized_wh=np.array([nw,nh]),
                input_sha256=np.array(hashlib.sha256(raw).hexdigest()),seconds=np.array(sec),weights_sha256=np.array(WEIGHT_HASH))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--inputs',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    # Manifest contains path, key and reference/scene feature resolution only.
    entries=json.loads(a.inputs.read_text());a.output.mkdir(parents=True,exist_ok=True);model=load_model()
    for e in entries:
        dst=a.output/(e['key']+'.npz')
        if dst.exists():
            d=np.load(dst,allow_pickle=False)
            assert str(d['input_sha256'])==hashlib.sha256(Path(e['path']).read_bytes()).hexdigest()
            continue
        f=extract(model,e['path'],e['max_side']);np.savez_compressed(dst,**f)
        print(e['key'],f['features'].shape,round(float(f['seconds']),3),flush=True)
