"""CPU-only diagnostic for the official public sample. Not an AMD backend.

R30's BF16 CPU experiment timed out during prompt processing. This script
uses real Qwen weights but quantizes text Linear layers to qint8 in memory;
all other computation stays float32. Neither the submitted model nor its
weights are modified. Scores from this diagnostic do not certify BF16/GPU
accuracy, the official self-check, timing limits, or a hidden grade.
"""
from __future__ import annotations
import argparse
import gc
import hashlib
import json
import os
from pathlib import Path
import time
import torch
from torch import nn
import transformers
import official_sample_probe as probe


class DiagnosticLinear(nn.Module):
    """Stock PyTorch dynamic INT8 CPU operator with one-layer conversion peak."""
    def __init__(self, original):
        super().__init__()
        self.in_features=original.in_features
        self.out_features=original.out_features
        weight=original.weight.detach().float()
        scale=max(float(weight.abs().max())/127,1e-10)
        quantized=torch.quantize_per_tensor(weight,scale,0,torch.qint8)
        bias=original.bias.detach().float() if original.bias is not None else None
        self.packed=torch.ops.quantized.linear_prepack(quantized,bias)
    def forward(self, value):
        return torch.ops.quantized.linear_dynamic(value.float(),self.packed,True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work',type=Path,required=True)
    args=parser.parse_args()
    work=args.work.resolve()
    out=work/'cpu-int8-r24'
    out.mkdir(parents=True,exist_ok=True)
    torch.set_num_threads(4)
    torch.backends.quantized.engine='fbgemm'
    torch.manual_seed(0)
    # Check the stock operator before downloading or loading any model.
    linear=nn.Linear(64,32).eval()
    values=torch.randn(2,20,64)
    approx=DiagnosticLinear(linear)(values)
    error=float((linear(values)-approx).abs().max())
    assert error<0.1 and torch.isfinite(approx).all()
    probe.prepare(work)
    original_loader=transformers.Qwen3VLForConditionalGeneration.from_pretrained
    def load(*a,**kw):
        began=time.monotonic()
        model=original_loader(*a,**kw)
        names=[name for name,module in model.named_modules()
               if isinstance(module,nn.Linear) and ('language_model' in name or name=='lm_head')]
        if not names:raise RuntimeError('Expected Qwen text modules were not found')
        parameter_count=0
        for name in names:
            parent_name,_,leaf=name.rpartition('.')
            parent=model.get_submodule(parent_name) if parent_name else model
            old=getattr(parent,leaf)
            parameter_count+=old.weight.numel()
            replacement=DiagnosticLinear(old)
            setattr(parent,leaf,replacement)
            del old,replacement
        gc.collect()
        model.float().eval()
        receipt={'diagnostic_only':True,'text_weight_dtype':'qint8','other_dtype':'float32',
                 'operator':'torch.ops.quantized.linear_dynamic','cpu_engine':torch.backends.quantized.engine,
                 'linear_layers':len(names),'quantized_weight_values':parameter_count,
                 'smoke_max_abs_error':error,'load_and_convert_seconds':time.monotonic()-began,
                 'cpu_info':Path('/proc/cpuinfo').read_text().split('\n\n')[0],
                 'production_model_modified':False,'native_gpu_qualification':False}
        probe.save(out/'DIAGNOSTIC_PRECISION.json',receipt)
        print(json.dumps({k:v for k,v in receipt.items() if k!='cpu_info'}),flush=True)
        return model
    transformers.Qwen3VLForConditionalGeneration.from_pretrained=staticmethod(load)
    try:
        probe.model_probe(work,work/'baseline','cpu-int8-r24')
        receipt=json.loads((out/'RECEIPT.json').read_text())
        receipt.update(dtype='qint8 text Linear weights with float32 activations and remaining modules',
                       diagnostic_backend='dynamic-int8-cpu',production_precision_equivalence=False,
                       sample_score_not_leaderboard=True)
        probe.save(out/'RECEIPT.json',receipt)
    except Exception as exc:
        probe.save(out/'ERROR.json',{'error':type(exc).__name__+': '+str(exc),
             'diagnostic_backend':'dynamic-int8-cpu','native_gpu_qualification':False})
        raise
    finally:
        transformers.Qwen3VLForConditionalGeneration.from_pretrained=original_loader

if __name__=='__main__':main()
