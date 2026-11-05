"""Official sample diagnostic with original checkpoint values, not INT8.

This does not alter the submission, certify AMD execution, or equate FP32 CPU
arithmetic with BF16 GPU arithmetic. The stored source weights are unchanged.
"""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import time
import torch
import transformers
import official_sample_probe as probe
from cpu_fp32_storage import install, selftest


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--work',type=Path,required=True)
    a=ap.parse_args();work=a.work.resolve();out=work/'fp32-arithmetic-r24'
    out.mkdir(parents=True,exist_ok=True)
    probe.save(out/'ARITHMETIC_TESTS.json',selftest())
    probe.prepare(work)
    original=transformers.Qwen3VLForConditionalGeneration.from_pretrained
    def load(*args,**kwargs):
        began=time.monotonic()
        model=original(*args,**kwargs)
        details=install(model)
        details.update(load_and_adapt_seconds=time.monotonic()-began,
            cpu=Path('/proc/cpuinfo').read_text().split('\n\n')[0],
            torch=torch.__version__,transformers=transformers.__version__,
            source_weight_values_preserved=True,production_model_modified=False,
            numerical_equivalence_to_bf16_gpu=False)
        probe.save(out/'DIAGNOSTIC_PRECISION.json',details)
        print(json.dumps({k:v for k,v in details.items() if k!='cpu'}),flush=True)
        return model
    transformers.Qwen3VLForConditionalGeneration.from_pretrained=staticmethod(load)
    try:
        probe.model_probe(work,work/'baseline','fp32-arithmetic-r24')
        receipt=json.loads((out/'RECEIPT.json').read_text())
        receipt.update(dtype='FP32 arithmetic with original BF16 Linear/Embedding storage',
            diagnostic_backend='lossless-storage-fp32-cpu',additional_weight_quantization=False,
            production_precision_equivalence=False,source_weight_values_preserved=True,
            sample_score_not_leaderboard=True)
        probe.save(out/'RECEIPT.json',receipt)
    except BaseException as exc:
        probe.save(out/'ERROR.json',{'error':type(exc).__name__+': '+str(exc),
            'diagnostic_backend':'lossless-storage-fp32-cpu','native_gpu_qualification':False})
        raise
    finally:
        transformers.Qwen3VLForConditionalGeneration.from_pretrained=original

if __name__=='__main__':main()
