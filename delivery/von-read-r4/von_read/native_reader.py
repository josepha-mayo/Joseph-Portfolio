"""Native Qwen3-VL candidate with completion checks.

The 512-token policy was measured on AMD. This extracted deployment adapter is
source-tested only; the final container and warm-worker wiring need a GPU test.
No recognition dictionaries, answer tables, network downloads or CPU fallback.
"""
from __future__ import annotations

import hashlib
import json
import math
import time
from pathlib import Path
from typing import Any

REPO = 'Qwen/Qwen3-VL-4B-Instruct'
REVISION = 'ebb281ec70b05090aa6165b016eac8ec08e71b17'
MAX_TOKENS = 512
MAX_PIXELS = 1_048_576
PROMPT = (
    'Read only the identifier on the main vehicle license plate, or all printed text on the main road sign, in reading order. '
    'For a plate, exclude state names, slogans, stickers and frame text; keep its Chinese province character. '
    'Ignore unrelated background text and camera overlays. Output only the observed text, without explanation.'
)


def sha256(path: Path) -> str:
    value = hashlib.sha256()
    with path.open('rb') as source:
        for block in iter(lambda: source.read(8 * 1024 * 1024), b''):
            value.update(block)
    return value.hexdigest()


def verify_snapshot(directory: Path) -> dict[str, Any]:
    root = directory.resolve(strict=True)
    lock = json.loads((root / 'MODEL_LOCK.json').read_text())
    if lock.get('repo') != REPO or lock.get('revision') != REVISION:
        raise ValueError('The measured model snapshot is required')
    files = lock.get('files', [])
    if not files or len({item['file'] for item in files}) != len(files):
        raise ValueError('Missing or duplicate snapshot entries')
    names = {item['file'] for item in files}
    if not {'config.json', 'tokenizer_config.json', 'preprocessor_config.json'} <= names:
        raise ValueError('Missing required model configuration')
    if not any(name.endswith('.safetensors') for name in names):
        raise ValueError('Missing model weights')
    for item in files:
        path = (root / item['file']).resolve(strict=True)
        if not path.is_relative_to(root) or not path.is_file():
            raise ValueError('Snapshot path is outside the model directory')
        if path.stat().st_size != item['bytes'] or sha256(path) != item['sha256']:
            raise ValueError('Snapshot bytes do not match the recorded lock')
    return lock


def finish(suffix: list[int], text: str, eos_ids: set[int], *,
           deadline: float | None = None, now: float | None = None) -> dict[str, Any]:
    """Reject partial output, including token-cap exhaustion without EOS.

    Reaching the token cap is not itself a failure when its final token is EOS.
    This gate must precede the runtime's atomic JSON output commit.
    """
    if not suffix or len(suffix) > MAX_TOKENS:
        raise ValueError('Invalid generated suffix length')
    if not eos_ids or any(type(i) is not int for i in (*suffix, *eos_ids)):
        raise ValueError('Invalid token identifiers')
    if suffix[-1] not in eos_ids:
        raise TimeoutError('Transcription ended without an end-of-sequence token')
    if deadline is not None:
        if not math.isfinite(deadline):
            raise ValueError('Invalid deadline')
        current = time.monotonic() if now is None else now
        if current >= deadline:
            raise TimeoutError('Transcription completed after its deadline')
    if not isinstance(text, str) or not text.strip() or len(text) > 4096:
        raise ValueError('Invalid transcription text')
    return {'text': text, 'generated_tokens': len(suffix), 'ended_eos': True}


class NativeReader:
    """Instantiate once in the private worker; call generate once per image."""

    def __init__(self, model_dir: Path) -> None:
        self.lock = verify_snapshot(model_dir)
        import torch
        import transformers
        if not torch.version.hip or not torch.cuda.is_available():
            raise RuntimeError('Allocated AMD ROCm hardware required')
        if transformers.__version__ != '5.3.0':
            raise RuntimeError('Dependency differs from the measured stack')
        self.torch = torch
        torch.set_num_threads(4)
        torch.manual_seed(0)
        self.model = transformers.Qwen3VLForConditionalGeneration.from_pretrained(
            model_dir, local_files_only=True, trust_remote_code=False,
            dtype=torch.bfloat16, device_map={'': 0}, attn_implementation='sdpa').eval()
        self.processor = transformers.AutoProcessor.from_pretrained(
            model_dir, local_files_only=True, trust_remote_code=False,
            min_pixels=4096, max_pixels=MAX_PIXELS, use_fast=False)
        eos = self.model.generation_config.eos_token_id
        self.eos_ids = set(eos if isinstance(eos, list) else [eos])
        if not self.eos_ids or any(type(i) is not int for i in self.eos_ids):
            raise ValueError('Model has no valid end-of-sequence configuration')
        torch.cuda.synchronize()

    def generate(self, image: Any, *, max_pixels: int = MAX_PIXELS,
                 deadline: float | None = None) -> dict[str, Any]:
        if max_pixels != MAX_PIXELS:
            raise ValueError('Changing the measured image budget needs a separate experiment')
        torch = self.torch
        begin = time.monotonic()
        image = image.convert('RGB')
        if image.width * image.height > MAX_PIXELS:
            ratio = (MAX_PIXELS / (image.width * image.height)) ** .5
            image = image.resize((max(1, int(image.width * ratio)), max(1, int(image.height * ratio))))
        message = [{'role': 'user', 'content': [
            {'type': 'image', 'image': image}, {'type': 'text', 'text': PROMPT}]}]
        batch = self.processor.apply_chat_template(
            message, tokenize=True, add_generation_prompt=True,
            return_dict=True, return_tensors='pt').to(self.model.device)
        remaining = 23.0 if deadline is None else min(23.0, deadline - time.monotonic())
        if not math.isfinite(remaining) or remaining <= 0:
            raise TimeoutError('No inference time remains')
        torch.cuda.synchronize()
        with torch.inference_mode():
            ids = self.model.generate(**batch, max_new_tokens=MAX_TOKENS,
                                      do_sample=False, max_time=remaining)
        torch.cuda.synchronize()
        suffix = ids[:, batch.input_ids.shape[1]:]
        text = self.processor.batch_decode(
            suffix, skip_special_tokens=True, clean_up_tokenization_spaces=False)[0]
        result = finish(suffix[0].tolist(), text, self.eos_ids, deadline=deadline)
        result['generation_ms'] = (time.monotonic() - begin) * 1000
        return result
