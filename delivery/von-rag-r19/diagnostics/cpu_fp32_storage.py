"""CPU diagnostic arithmetic without extra weight quantization.

Keep checkpoint Linear/Embedding storage unchanged; expand one Linear weight
at a time for FP32 arithmetic. This avoids a full FP32 resident model and does
not claim numerically identical computation to BF16 GPU inference. Never enable
this diagnostic adapter in the submitted native AMD runtime.
"""
from __future__ import annotations
import copy
import gc
import time
import torch
from torch import nn
from torch.nn import functional as F


class ExpandedLinear(nn.Linear):
    def forward(self, value):
        return F.linear(value.float(), self.weight.float(),
                        None if self.bias is None else self.bias.float())


class ExpandedEmbedding(nn.Embedding):
    def forward(self, value):
        if self.max_norm is not None:
            raise ValueError('In-place embedding renormalization is not supported')
        return F.embedding(value, self.weight, self.padding_idx, self.max_norm,
                           self.norm_type, self.scale_grad_by_freq, self.sparse).float()


def install(model):
    """Preserve every stored low-precision weight value; no INT8 quantization."""
    params=list(model.parameters())
    if any(p.device.type!='cpu' for p in params):
        raise ValueError('This adapter is CPU diagnostic only')
    if any(p.is_floating_point() and p.dtype not in (torch.bfloat16,torch.float32) for p in params):
        raise ValueError('Expected BF16 checkpoint or FP32 parameters')
    model.eval().requires_grad_(False)
    samples={name:p.detach().reshape(-1)[:128].float().clone()
             for name,p in model.named_parameters()}
    linear=embedding=expanded_values=0
    protected=set()
    for module in model.modules():
        if type(module) is nn.Linear:
            module.__class__=ExpandedLinear
            linear+=1
            protected.add(id(module.weight))
            if module.bias is not None:protected.add(id(module.bias))
        elif type(module) is nn.Embedding:
            if module.max_norm is not None:raise ValueError('Unsupported embedding max_norm')
            module.__class__=ExpandedEmbedding
            embedding+=1;protected.add(id(module.weight))
    for param in model.parameters():
        if id(param) not in protected and param.is_floating_point():
            expanded_values+=param.numel()
            param.data=param.data.float()
    for module in model.modules():
        for key,buffer in list(module._buffers.items()):
            if buffer is not None and buffer.is_floating_point():
                module._buffers[key]=buffer.float()
    for name,param in model.named_parameters():
        if not torch.equal(samples[name],param.detach().reshape(-1)[:128].float()):
            raise AssertionError('Parameter sample changed: '+name)
    gc.collect()
    return {'linear_wrappers':linear,'embedding_wrappers':embedding,
            'other_parameters_expanded':expanded_values,
            'resident_parameter_bytes':sum(p.numel()*p.element_size() for p in model.parameters()),
            'parameter_samples_verified':len(samples),'additional_weight_quantization':False,
            'activation_dtype':'float32','native_amd_adapter':False}


def selftest():
    torch.manual_seed(90127)
    records=[]
    for bias in (True,False):
        original=nn.Linear(64,37,bias=bias).to(torch.bfloat16).eval()
        exact=copy.deepcopy(original).float()
        patched=copy.deepcopy(original)
        original_bits=patched.weight.detach().clone()
        install(patched)
        value=torch.randn(2,17,64)
        with torch.inference_mode():
            expected=exact(value);actual=patched(value)
        assert torch.equal(actual,expected)
        assert torch.equal(patched.weight,original_bits)
        records.append({'test':'linear_bias_'+str(bias),'max_abs_error':0.0,'weight_bits_preserved':True})
    embed=nn.Embedding(100,64,padding_idx=0).to(torch.bfloat16)
    original=embed.weight.detach().clone();install(embed)
    ids=torch.tensor([[0,9,4],[13,70,10]])
    assert torch.equal(embed(ids),F.embedding(ids,original,padding_idx=0).float())
    assert torch.equal(embed.weight,original)
    records.append({'test':'embedding','max_abs_error':0.0,'weight_bits_preserved':True})
    composed=nn.Sequential(nn.Linear(64,128),nn.LayerNorm(128),nn.GELU(),nn.Linear(128,32)).to(torch.bfloat16)
    exact=copy.deepcopy(composed).float();install(composed)
    value=torch.randn(7,64)
    with torch.inference_mode():
        expected=exact(value);actual=composed(value)
    assert torch.equal(actual,expected)
    records.append({'test':'normalization_network','max_abs_error':0.0})
    speed={}
    torch.set_num_threads(4)
    for dtype in (torch.float32,torch.bfloat16):
        x=torch.randn(128,512).to(dtype);w=torch.randn(512,512).to(dtype)
        torch.mm(x,w)
        start=time.perf_counter()
        for _ in range(3):torch.mm(x,w)
        speed[str(dtype)]=(time.perf_counter()-start)/3
    return {'arithmetic_checks':records,'gemm_seconds':speed,
            'scope':'Small exact FP32 arithmetic checks; not full-model equivalence or AMD performance'}
