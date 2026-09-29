"""Test-only CPU execution of saved BF16 weights using FP32 arithmetic.

No quantization, answer correction or change to saved weight values. Large
linear weights stay in BF16 storage and are widened losslessly just for each
matmul. This is not production BF16/GPU numerical or timing equivalence.
"""
from __future__ import annotations
import gc
import torch
from torch import nn
from torch.nn import functional as F

class StreamedFloatLinear(nn.Module):
    def __init__(self, original: nn.Linear):
        super().__init__()
        if original.weight.device.type != 'cpu':
            raise ValueError('CPU diagnostic only')
        if original.weight.dtype != torch.bfloat16:
            raise ValueError('Expected exact saved BF16 weight storage')
        self.in_features = original.in_features
        self.out_features = original.out_features
        self.register_buffer('weight', original.weight.detach())
        self.register_buffer('bias', original.bias.detach() if original.bias is not None else None)
        self.calls = 0
    def forward(self, value):
        if value.device.type != 'cpu':
            raise ValueError('CPU diagnostic only')
        self.calls += 1
        return F.linear(value.float(), self.weight.float(), self.bias.float() if self.bias is not None else None)

def install_streamed_float32(model):
    names = [n for n,m in model.named_modules() if isinstance(m, nn.Linear)]
    if not names:
        raise ValueError('No linear modules found')
    count = 0
    identities = []
    for name in names:
        parent_name, _, leaf = name.rpartition('.')
        parent = model.get_submodule(parent_name) if parent_name else model
        old = getattr(parent, leaf)
        pointer = old.weight.data_ptr()
        replacement = StreamedFloatLinear(old)
        assert pointer == replacement.weight.data_ptr()
        count += replacement.weight.numel()
        identities.append((name, pointer, tuple(replacement.weight.shape)))
        setattr(parent, leaf, replacement)
    for module in model.modules():
        if isinstance(module, StreamedFloatLinear):
            continue
        for parameter in module.parameters(recurse=False):
            if parameter.is_floating_point():
                parameter.data = parameter.data.float()
                parameter.requires_grad_(False)
        for name, buffer in tuple(module.named_buffers(recurse=False)):
            if buffer.is_floating_point():
                setattr(module, name, buffer.float())
    model.eval()
    gc.collect()
    return {'linear_modules': len(names), 'linear_weight_values': count,
            'original_linear_storage_retained': all(model.get_submodule(n).weight.data_ptr()==p for n,p,s in identities),
            'linear_storage_dtype': 'bfloat16', 'arithmetic_dtype': 'float32',
            'integer_quantization': False, 'gpu_qualification': False}

def self_test():
    import copy
    torch.manual_seed(330929)
    errors = []
    cases = 0
    with torch.inference_mode():
        for batch in ((1,64),(2,17,64)):
            for bias in (False,True):
                layer=nn.Linear(64,96,bias=bias).bfloat16().eval()
                x=torch.randn(batch)
                reference=F.linear(x,layer.weight.float(),layer.bias.float() if bias else None)
                observed=StreamedFloatLinear(layer)(x)
                assert torch.equal(reference,observed)
                cases+=1;errors.append(float((reference-observed).abs().max()))
    class Mini(nn.Module):
        def __init__(self):
            super().__init__();self.embedding=nn.Embedding(97,64);self.norm=nn.LayerNorm(64)
            self.layers=nn.Sequential(nn.Linear(64,96),nn.SiLU(),nn.Linear(96,64))
            self.output=nn.Linear(64,97,bias=False)
        def forward(self,ids):
            x=self.norm(self.embedding(ids));return self.output(x+self.layers(x))
    original=Mini().bfloat16().eval()
    reference=copy.deepcopy(original).float().eval()
    report=install_streamed_float32(original)
    with torch.inference_mode():
        for length in (1,8,31):
            ids=torch.randint(0,97,(2,length))
            observed=original(ids);expected=reference(ids)
            torch.testing.assert_close(observed,expected,rtol=0,atol=0)
            errors.append(float((observed-expected).abs().max()));cases+=1
    assert report['original_linear_storage_retained']
    return {'passed':True,'cases':cases,'max_abs_error':max(errors),
            'comparison':'Fully FP32 arithmetic on the same saved BF16 weights; small authored modules only'}

if __name__=='__main__':
    import json
    print(json.dumps(self_test(),indent=2))
