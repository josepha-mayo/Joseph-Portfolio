"""Official public-sample diagnostic, never a native AMD acceptance result.

The earlier CPU host has AVX2 but no native BF16 instruction flag. This driver
keeps original BF16 linear storage and computes in FP32, avoiding integer
quantization and the full-model FP32 memory peak. Native BF16 rounding and
performance are not reproduced. Model files and submitted images stay intact.
"""
from __future__ import annotations
import argparse
import copy
import json
from pathlib import Path
import time
import torch
import transformers
import official_sample_probe as probe
from streamed_cpu import install_streamed_float32, self_test


def tiny_qwen_test():
    torch.manual_seed(330929)
    config=transformers.Qwen3VLConfig(
        text_config={'vocab_size':256,'hidden_size':256,'intermediate_size':512,
            'num_hidden_layers':2,'num_attention_heads':4,'num_key_value_heads':2,
            'head_dim':64,'max_position_embeddings':512,'attention_dropout':0.0},
        vision_config={'depth':2,'hidden_size':128,'intermediate_size':256,
            'num_heads':4,'patch_size':14,'spatial_merge_size':2,'temporal_patch_size':2,
            'out_hidden_size':256,'deepstack_visual_indexes':[0,1]},
        image_token_id=250,video_token_id=251,vision_start_token_id=252,
        vision_end_token_id=253)
    reference=transformers.Qwen3VLForConditionalGeneration(config).bfloat16().eval()
    candidate=copy.deepcopy(reference)
    reference.float().eval()
    report=install_streamed_float32(candidate)
    ids=torch.tensor([[1,20,15,27,30,18]])
    mask=torch.ones_like(ids)
    with torch.inference_mode():
        a=reference(input_ids=ids,attention_mask=mask,use_cache=False).logits
        b=candidate(input_ids=ids,attention_mask=mask,use_cache=False).logits
    torch.testing.assert_close(a,b,rtol=0,atol=0)
    assert report['original_linear_storage_retained']
    return {'passed':True,'max_abs_logit_error':float((a-b).abs().max()),
        'tiny_random_architecture':True,'pretrained_accuracy_measured':False}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work',type=Path,required=True)
    parser.add_argument('--checks-only',action='store_true')
    args=parser.parse_args()
    work=args.work.resolve();out=work/'cpu-float32-r24';out.mkdir(parents=True,exist_ok=True)
    torch.set_num_threads(4)
    checks={'operator_tests':self_test(),'qwen_architecture_test':tiny_qwen_test()}
    probe.save(out/'NUMERICAL_CHECKS.json',checks)
    print(json.dumps(checks),flush=True)
    if args.checks_only:return
    probe.prepare(work)
    original_loader=transformers.Qwen3VLForConditionalGeneration.from_pretrained
    def load(*a,**kw):
        started=time.monotonic()
        model=original_loader(*a,**kw)
        report=install_streamed_float32(model)
        assert report['original_linear_storage_retained']
        assert model.get_input_embeddings().weight.dtype==torch.float32
        report.update(diagnostic_only=True,load_and_prepare_seconds=time.monotonic()-started,
            checkpoint_values_losslessly_widened=True,
            production_precision_equivalence=False,
            cpu_info=Path('/proc/cpuinfo').read_text().split('\n\n')[0])
        probe.save(out/'DIAGNOSTIC_PRECISION.json',report)
        print(json.dumps({k:v for k,v in report.items() if k!='cpu_info'}),flush=True)
        return model
    transformers.Qwen3VLForConditionalGeneration.from_pretrained=staticmethod(load)
    try:
        probe.model_probe(work,work/'baseline','cpu-float32-r24')
        receipt=json.loads((out/'RECEIPT.json').read_text())
        receipt.update(dtype='FP32 arithmetic, original BF16 linear storage',
            diagnostic_backend='lossless-widening-cpu',integer_quantization=False,
            checkpoint_values_changed=False,production_precision_equivalence=False,
            official_selfcheck_run=False,native_gpu_qualification=False,
            sample_score_not_leaderboard=True)
        probe.save(out/'RECEIPT.json',receipt)
    except Exception as exc:
        probe.save(out/'ERROR.json',{'error':type(exc).__name__+': '+str(exc),
            'diagnostic_backend':'lossless-widening-cpu','native_gpu_qualification':False})
        raise
    finally:
        transformers.Qwen3VLForConditionalGeneration.from_pretrained=original_loader

if __name__=='__main__':main()
