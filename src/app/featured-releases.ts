export interface FeaturedRelease {
  name: string;
  kind: string;
  type: 'model' | 'dataset';
  description: string;
  repo: string;
  downloads: number;
  downloadLabel: string;
  result: string;
  scope: string;
  evidenceUrl: string;
  links: { label: string; url: string }[];
}

const hf = 'https://huggingface.co/josephmayo/';
const datasets = 'https://huggingface.co/datasets/josephmayo/';

// Download snapshots: Hugging Face API, 5 November 2026. Refreshed in the browser.
// Each count belongs to the named release, never a sum across model formats.
export const featuredReleases: FeaturedRelease[] = [
  {
    name: 'Holo-3.1-9B-Coder', kind: 'coding · 9B', type: 'model',
    description: 'A coding adaptation of Hcompany Holo, with merged weights and local GGUF builds.',
    repo: 'josephmayo/Holo-3.1-9B-Coder', downloads: 5405, downloadLabel: 'model downloads',
    result: '52.4% → 65.2%', scope: 'HumanEval+ pass@1 · +12.8 percentage points vs base',
    evidenceUrl: hf + 'Holo-3.1-9B-Coder#evaluation',
    links: [{ label: 'weights & GGUF', url: hf + 'Holo-3.1-9B-Coder' }],
  },
  {
    name: 'ZAYA1-8B-Coder', kind: 'coding · 8B', type: 'model',
    description: 'Python-focused LoRA tuning of Zyphra ZAYA, released as merged weights and GGUF.',
    repo: 'josephmayo/ZAYA1-8B-Coder-GGUF', downloads: 4498, downloadLabel: 'GGUF downloads',
    result: '2.36 → 4.76 / 10', scope: '50 Python prompts · heuristic score, not an execution benchmark',
    evidenceUrl: hf + 'ZAYA1-8B-Coder#evaluation-gate',
    links: [{ label: 'weights', url: hf + 'ZAYA1-8B-Coder' }, { label: 'GGUF', url: hf + 'ZAYA1-8B-Coder-GGUF' }],
  },
  {
    name: 'Gemma-4-E4B-it-Coder', kind: 'coding · E4B', type: 'model',
    description: 'A merged coding LoRA for Gemma 4, with generated before/after code published.',
    repo: 'josephmayo/gemma-4-E4B-it-Coder-GGUF', downloads: 1989, downloadLabel: 'GGUF downloads',
    result: '34 / 50 → 42 / 50', scope: 'HumanEval 50-task subset · +16 percentage points vs base',
    evidenceUrl: hf + 'gemma-4-E4B-it-Coder#humaneval-results-50-problem-subset',
    links: [{ label: 'weights', url: hf + 'gemma-4-E4B-it-Coder' }, { label: 'GGUF', url: hf + 'gemma-4-E4B-it-Coder-GGUF' }],
  },
  {
    name: 'LFM2.5-8B-A1B-Coder', kind: 'coding · mixture of experts', type: 'model',
    description: 'LiquidAI LFM tuned on real-world and multilingual coding data.',
    repo: 'josephmayo/LFM2.5-8B-A1B-Coder-GGUF', downloads: 1475, downloadLabel: 'GGUF downloads',
    result: '3.390 → 1.875 NLL', scope: 'Held-out loss · 44.71% lower vs base; no pass-rate claim',
    evidenceUrl: hf + 'LFM2.5-8B-A1B-Coder#validation',
    links: [{ label: 'weights', url: hf + 'LFM2.5-8B-A1B-Coder' }, { label: 'GGUF', url: hf + 'LFM2.5-8B-A1B-Coder-GGUF' }],
  },
  {
    name: 'Mellum2 Thinking Abliterated', kind: 'refusal research · 12B / 2.5B active', type: 'model',
    description: 'Per-layer and per-expert refusal-direction work on JetBrains Mellum2.',
    repo: 'josephmayo/Mellum2-12B-A2.5B-Thinking-Abliterated-GGUF', downloads: 1386, downloadLabel: 'GGUF downloads',
    result: '16 / 16 → 2 / 16', scope: 'Refusals on 16 harmful prompts · 87.5% drop; small internal evaluation',
    evidenceUrl: hf + 'Mellum2-12B-A2.5B-Thinking-Abliterated#results',
    links: [{ label: 'weights', url: hf + 'Mellum2-12B-A2.5B-Thinking-Abliterated' }, { label: 'GGUF', url: hf + 'Mellum2-12B-A2.5B-Thinking-Abliterated-GGUF' }],
  },
  {
    name: 'Qwopus 9B Unfettered', kind: 'refusal research · 9B', type: 'model',
    description: 'Weight-space refusal ablation, with local inference builds for red-team experiments.',
    repo: 'josephmayo/Qwopus-9B-Unfettered-GGUF', downloads: 2919, downloadLabel: 'GGUF downloads',
    result: '100% reported compliance', scope: 'Internal suite · no base comparison or sample count published',
    evidenceUrl: hf + 'Qwopus-9B-Unfettered',
    links: [{ label: 'weights', url: hf + 'Qwopus-9B-Unfettered' }, { label: 'GGUF', url: hf + 'Qwopus-9B-Unfettered-GGUF' }],
  },
  {
    name: 'Qwen2.5-0.5B-Unfettered', kind: 'refusal research · 0.5B', type: 'model',
    description: 'A small Qwen refusal-ablation experiment for CPU and low-memory inference.',
    repo: 'josephmayo/Qwen2.5-0.5B-Unfettered', downloads: 1906, downloadLabel: 'model downloads',
    result: 'Low-memory experiment', scope: 'No comparative evaluation published; no measured gain claimed',
    evidenceUrl: hf + 'Qwen2.5-0.5B-Unfettered',
    links: [{ label: 'model & GGUF', url: hf + 'Qwen2.5-0.5B-Unfettered' }],
  },
  {
    name: 'Refusal Compliance Pairs', kind: 'dataset · adversarial evaluation', type: 'dataset',
    description: 'Contrasting refusal and compliance prompts for refusal-direction and red-team research.',
    repo: 'josephmayo/refusal-compliance-pairs', downloads: 430, downloadLabel: 'dataset downloads',
    result: '201 prompts', scope: '101 refusal + 100 compliance prompts · research data',
    evidenceUrl: datasets + 'refusal-compliance-pairs',
    links: [{ label: 'dataset', url: datasets + 'refusal-compliance-pairs' }],
  },
  {
    name: 'Curated OpenBMB Code/Math', kind: 'dataset · post-training', type: 'dataset',
    description: 'Code and math data curated from OpenBMB UltraData, with SFT and thinking splits.',
    repo: 'josephmayo/curated-openbmb-code-math', downloads: 254, downloadLabel: 'dataset downloads',
    result: '31,909 rows', scope: 'Curated training data · no isolated downstream gain claimed',
    evidenceUrl: datasets + 'curated-openbmb-code-math',
    links: [{ label: 'dataset', url: datasets + 'curated-openbmb-code-math' }],
  },
];
