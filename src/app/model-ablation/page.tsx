import Link from "next/link";

export const metadata = {
  title: "Model Ablation — Refusal Direction Orthogonalization",
  description: "Raw mathematics behind refusal-direction ablation for LLM uncensoring. The technique used for Fara-7B-Abliterated and Qwopus-9B-Unfettered.",
};

function CodeBlock({ children }: { children: React.ReactNode }) {
  return (
    <pre className="bg-white/5 border border-border-subtle rounded-lg p-4 overflow-x-auto text-sm text-text-secondary font-[family-name:var(--font-geist-mono)] my-6">
      <code>{children}</code>
    </pre>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="mb-16">
      <h2 className="text-2xl font-display font-semibold mb-6 text-text-primary">{title}</h2>
      <div className="space-y-4 text-text-secondary leading-relaxed">{children}</div>
    </section>
  );
}

export default function ModelAblationPage() {
  return (
    <main className="min-h-screen bg-background">
      {/* Nav */}
      <nav className="fixed top-0 w-full h-[70px] nav-glass border-b border-border-subtle z-50 flex items-center">
        <div className="container mx-auto px-8 flex justify-between items-center">
          <Link href="/" className="font-display text-2xl font-bold text-text-primary">
            AJ<span className="text-accent">.</span>
          </Link>
          <Link href="/" className="text-text-secondary hover:text-text-primary text-sm font-medium transition-colors">
            &larr; back to portfolio
          </Link>
        </div>
      </nav>

      <article className="pt-[100px] pb-32">
        <div className="container mx-auto px-8 max-w-3xl">
          {/* Header */}
          <header className="mb-16">
            <div className="flex items-center gap-3 mb-4">
              <span className="text-xs px-3 py-1 bg-accent/10 text-accent rounded border border-accent/20 font-medium">research</span>
              <span className="text-xs px-3 py-1 bg-white/5 text-text-secondary rounded border border-border-subtle">red teaming</span>
              <span className="text-xs px-3 py-1 bg-white/5 text-text-secondary rounded border border-border-subtle">pytorch</span>
            </div>
            <h1 className="text-4xl md:text-5xl font-display font-semibold tracking-tight mb-4 text-text-primary">
              model ablation
            </h1>
            <p className="text-lg text-text-secondary max-w-[60ch]">
              Raw mathematics behind refusal-direction orthogonalization — the technique used to remove refusal mechanisms from language models while preserving general capability.
            </p>
            <div className="flex gap-4 mt-6">
              <a
                href="https://huggingface.co/josephmayo/Fara-7B-Abliterated-v2"
                target="_blank"
                rel="noopener noreferrer"
                className="text-sm font-semibold text-text-primary hover:text-accent flex items-center gap-1.5 transition-colors"
              >
                <svg fill="currentColor" fillRule="evenodd" height="1em" style={{flex:'none',lineHeight:1}} viewBox="0 0 24 24" width="1em" xmlns="http://www.w3.org/2000/svg"><title>HuggingFace</title><path d="M16.781 3.277c2.997 1.704 4.844 4.851 4.844 8.258 0 .995-.155 1.955-.443 2.857a1.332 1.332 0 011.125.4 1.41 1.41 0 01.2 1.723c.204.165.352.385.428.632l.017.062c.06.222.12.69-.2 1.166.244.37.279.836.093 1.236-.255.57-.893 1.018-2.128 1.5l-.202.078-.131.048c-.478.173-.89.295-1.061.345l-.086.024c-.89.243-1.808.375-2.732.394-1.32 0-2.3-.36-2.923-1.067a9.852 9.852 0 01-3.18.018C9.778 21.647 8.802 22 7.494 22a11.249 11.249 0 01-2.541-.343l-.221-.06-.273-.08a16.574 16.574 0 01-1.175-.405c-1.237-.483-1.875-.93-2.13-1.501-.186-.4-.151-.867.093-1.236a1.42 1.42 0 01-.2-1.166c.069-.273.226-.516.447-.694a1.41 1.41 0 01.2-1.722c.233-.248.557-.391.917-.407l.078-.001a9.385 9.385 0 01-.44-2.85c0-3.407 1.847-6.554 4.844-8.258a9.822 9.822 0 019.687 0z"/></svg>
                Fara-7B-Abliterated-v2
              </a>
              <a
                href="https://huggingface.co/josephmayo/Qwopus-9B-Unfettered"
                target="_blank"
                rel="noopener noreferrer"
                className="text-sm font-semibold text-text-primary hover:text-accent flex items-center gap-1.5 transition-colors"
              >
                <svg fill="currentColor" fillRule="evenodd" height="1em" style={{flex:'none',lineHeight:1}} viewBox="0 0 24 24" width="1em" xmlns="http://www.w3.org/2000/svg"><title>HuggingFace</title><path d="M16.781 3.277c2.997 1.704 4.844 4.851 4.844 8.258 0 .995-.155 1.955-.443 2.857a1.332 1.332 0 011.125.4 1.41 1.41 0 01.2 1.723c.204.165.352.385.428.632l.017.062c.06.222.12.69-.2 1.166.244.37.279.836.093 1.236-.255.57-.893 1.018-2.128 1.5l-.202.078-.131.048c-.478.173-.89.295-1.061.345l-.086.024c-.89.243-1.808.375-2.732.394-1.32 0-2.3-.36-2.923-1.067a9.852 9.852 0 01-3.18.018C9.778 21.647 8.802 22 7.494 22a11.249 11.249 0 01-2.541-.343l-.221-.06-.273-.08a16.574 16.574 0 01-1.175-.405c-1.237-.483-1.875-.93-2.13-1.501-.186-.4-.151-.867.093-1.236a1.42 1.42 0 01-.2-1.166c.069-.273.226-.516.447-.694a1.41 1.41 0 01.2-1.722c.233-.248.557-.391.917-.407l.078-.001a9.385 9.385 0 01-.44-2.85c0-3.407 1.847-6.554 4.844-8.258a9.822 9.822 0 019.687 0z"/></svg>
                Qwopus-9B-Unfettered
              </a>
            </div>
          </header>

          {/* Overview */}
          <Section title="overview">
            <p>
              Ablation (also called refusal-direction orthogonalization) is a technique for removing specific behavioral directions from a model&apos;s internal representations. The core insight: refusal behavior in aligned language models is encoded as a linear direction in activation space. By identifying and projecting out this direction, we can remove refusal while preserving the model&apos;s general capabilities.
            </p>
            <p>
              This technique was applied to create:
            </p>
            <ul className="list-none space-y-2 ml-4">
              <li><i className="fa-solid fa-check text-accent mr-2"></i> <strong className="text-text-primary">Fara-7B-Abliterated-v2</strong> — 98.75% compliance on held-out harmful evals</li>
              <li><i className="fa-solid fa-check text-accent mr-2"></i> <strong className="text-text-primary">Qwopus-9B-Unfettered</strong> — directional ablation applied to remove refusal mechanisms</li>
            </ul>
          </Section>

          {/* Theory */}
          <Section title="theoretical foundation">
            <h3 className="text-xl font-display font-semibold mt-8 mb-4 text-text-primary">refusal as a linear direction</h3>
            <p>
              Research has shown that refusal behavior in aligned LLMs is encoded as a single linear direction in the residual stream. For a model with layers <code>L</code>, let the residual activations at layer <code>l</code> be:
            </p>
            <CodeBlock>{`h_l ∈ R^d    for l ∈ {1, ..., L}`}</CodeBlock>
            <p>
              The refusal direction <code>r</code> can be extracted by computing the mean difference between activations on harmful prompts <code>H</code> and benign prompts <code>B</code>:
            </p>
            <CodeBlock>{`r = E[h_l | x ∈ H] − E[h_l | x ∈ B]`}</CodeBlock>
            <p>
              This direction <code>r</code> captures the model&apos;s tendency to refuse. It is typically extracted from a specific layer (often the last few transformer blocks) and normalized:
            </p>
            <CodeBlock>{`r̂ = r / ||r||₂`}</CodeBlock>
          </Section>

          {/* Projection */}
          <Section title="projection / subtraction">
            <h3 className="text-xl font-display font-semibold mt-8 mb-4 text-text-primary">removing the refusal direction</h3>
            <p>
              Given the normalized refusal direction <code>r̂</code>, we can remove it from any activation <code>h</code> by projecting out the component along <code>r̂</code>:
            </p>
            <CodeBlock>{`h_ablated = h − (h · r̂) r̂`}</CodeBlock>
            <p>
              This is the orthogonal projection of <code>h</code> onto the subspace orthogonal to <code>r̂</code>. In matrix form across all dimensions:
            </p>
            <CodeBlock>{`h_ablated = (I − r̂ r̂ᵀ) h`}</CodeBlock>
            <p>
              where <code>I</code> is the identity matrix and <code>r̂ r̂ᵀ</code> is the outer product forming the projection matrix.
            </p>

            <h3 className="text-xl font-display font-semibold mt-8 mb-4 text-text-primary">weight-space ablation</h3>
            <p>
              Rather than modifying activations at runtime, we can bake the ablation into the model weights directly. For a linear layer with weight matrix <code>W</code>:
            </p>
            <CodeBlock>{`W_ablated = W − (W r̂) r̂ᵀ`}</CodeBlock>
            <p>
              Or equivalently, using the projection matrix <code>P = I − r̂ r̂ᵀ</code>:
            </p>
            <CodeBlock>{`W_ablated = P W`}</CodeBlock>
            <p>
              This modifies the weight matrix so that the refusal direction is permanently removed from the model&apos;s representational capacity.
            </p>

            <h3 className="text-xl font-display font-semibold mt-8 mb-4 text-text-primary">per-layer ablation</h3>
            <p>
              The refusal direction may differ across layers. For layer-specific ablation:
            </p>
            <CodeBlock>{`r̂_l = r_l / ||r_l||₂    for each layer l

h_l^{ablated} = h_l − (h_l · r̂_l) r̂_l

W_l^{ablated} = W_l − (W_l r̂_l) r̂_lᵀ`}</CodeBlock>
            <p>
              Per-layer ablation is more precise but requires extracting layer-wise refusal directions.
            </p>
          </Section>

          {/* Full Pipeline */}
          <Section title="full ablation pipeline">
            <h3 className="text-xl font-display font-semibold mt-8 mb-4 text-text-primary">step 1: extract refusal direction</h3>
            <CodeBlock>{`# Collect activations
harmful_acts = collect_activations(model, harmful_prompts)
benign_acts  = collect_activations(model, benign_prompts)

# Compute mean difference
r = mean(harmful_acts, dim=0) - mean(benign_acts, dim=0)

# Normalize
r_hat = r / torch.norm(r)`}</CodeBlock>

            <h3 className="text-xl font-display font-semibold mt-8 mb-4 text-text-primary">step 2: apply ablation</h3>
            <CodeBlock>{`# Method 1: Activation-level (runtime)
def ablate_activation(h, r_hat):
    return h - torch.dot(h, r_hat) * r_hat

# Method 2: Weight-level (baked in)
def ablate_weight(W, r_hat):
    return W - torch.outer(W @ r_hat, r_hat)

# Apply to all target layers
for layer in model.transformer.layers:
    layer.attn.W_q = ablate_weight(layer.attn.W_q, r_hat)
    layer.attn.W_k = ablate_weight(layer.attn.W_k, r_hat)
    layer.attn.W_v = ablate_weight(layer.attn.W_v, r_hat)
    layer.mlp.W   = ablate_weight(layer.mlp.W, r_hat)`}</CodeBlock>

            <h3 className="text-xl font-display font-semibold mt-8 mb-4 text-text-primary">step 3: verify ablation</h3>
            <CodeBlock>{`# Check refusal direction is removed
h = model.get_activations(test_prompt)
component = torch.dot(h, r_hat)
assert abs(component) < 1e-6, "refusal direction still present"

# Evaluate compliance on harmful eval set
compliance_rate = evaluate(model, harmful_eval_set)
print(f"compliance: {compliance_rate:.2%}")`}</CodeBlock>
          </Section>

          {/* Delta-Span */}
          <Section title="delta-span subtraction (dr-opic variant)">
            <p>
              The DR-OPIC framework uses a more targeted approach: delta-span subtraction. Rather than ablating the entire refusal direction, it identifies the specific tokens where failure occurs and applies surgical correction.
            </p>
            <p>Given failed code <code>y⁻</code> and fixed code <code>y⁺</code>:</p>
            <CodeBlock>{`D+ = {t : token t was added or replaced in the verified fix}
D- = {t : token t was removed or replaced in the failed answer}

L_delta =
  − w_task · Σ_{t ∈ D+} log π_θ(y⁺_t | prefix⁺_t)
  + λ_neg · w_task · Σ_{t ∈ D-} relu(
      log π_θ(y⁻_t | prefix⁻_t)
    − log π_ref(y⁻_t | prefix⁻_t)
    − margin
    )`}</CodeBlock>
            <p>
              This increases probability on corrected spans (D+) and subtracts only the failing spans (D−) relative to a reference model, leaving shared correct code unpunished.
            </p>
            <p>The implementation computes:</p>
            <CodeBlock>{`shared_ratio = shared_tokens / max(len(failed), len(fixed))
edit_ratio   = 1 − shared_ratio

# Positive mask: tokens to reinforce
positive_mask[fix_indices] = 1

# Negative mask: tokens to suppress (with margin)
negative_mask[fail_indices] = 1`}</CodeBlock>
            <p>
              This approach is more surgical than full-direction ablation because it only modifies the model&apos;s behavior on the specific failure modes, not its entire representational capacity.
            </p>
          </Section>

          {/* Practical Considerations */}
          <Section title="practical considerations">
            <h3 className="text-xl font-display font-semibold mt-8 mb-4 text-text-primary">layer selection</h3>
            <p>
              The refusal direction is strongest in the later transformer layers (typically layers 16-32 in a 7B-9B model). Ablating earlier layers risks degrading general capability more than necessary.
            </p>

            <h3 className="text-xl font-display font-semibold mt-8 mb-4 text-text-primary">ablation strength</h3>
            <p>
              Full projection (<code>λ = 1.0</code>) removes the direction completely. Partial ablation preserves some refusal tendency:
            </p>
            <CodeBlock>{`h_ablated = h − λ · (h · r̂) r̂

# λ = 1.0: full ablation (maximum compliance)
# λ = 0.5: partial ablation (reduced but not removed refusal)
# λ = 0.0: no ablation (original model)`}</CodeBlock>

            <h3 className="text-xl font-display font-semibold mt-8 mb-4 text-text-primary">capability preservation</h3>
            <p>
              The key assumption is that refusal is a low-rank behavior that can be separated from general capability. Empirical evaluation shows:
            </p>
            <ul className="list-none space-y-2 ml-4">
              <li><i className="fa-solid fa-check text-accent mr-2"></i> MMLU, HumanEval, and MBPP scores remain stable</li>
              <li><i className="fa-solid fa-check text-accent mr-2"></i> Code generation quality is preserved</li>
              <li><i className="fa-solid fa-check text-accent mr-2"></i> Reasoning ability is maintained</li>
              <li><i className="fa-solid fa-check text-accent mr-2"></i> Only refusal behavior is removed</li>
            </ul>

            <h3 className="text-xl font-display font-semibold mt-8 mb-4 text-text-primary">reference model requirement</h3>
            <p>
              Delta-span subtraction requires a reference model <code>π_ref</code> (typically the base model before alignment). The margin term ensures we only subtract behavior that differs from the reference:
            </p>
            <CodeBlock>{`# Reference model provides the baseline
log_ref = π_ref.log_prob(y⁻_t | prefix⁻_t)

# Only subtract if current model is more refuse-y than reference
margin_condition = log_πθ(y⁻_t | prefix⁻_t) − log_ref > margin`}</CodeBlock>
          </Section>

          {/* Evaluation */}
          <Section title="evaluation metrics">
            <p>
              After ablation, evaluate on the following to ensure capability preservation:
            </p>
            <CodeBlock>{`# Compliance metrics
compliance_rate  = passed_harmful / total_harmful
refusal_rate     = 1 − compliance_rate

# Capability metrics (should remain unchanged)
mmlu_score       = evaluate_mmlu(model)
humaneval_score  = evaluate_humaneval(model)
mbpp_score       = evaluate_mbpp(model)

# Safety metrics
unsafe_output_rate = unsafe_outputs / total_outputs
format_preservation = correct_format / total_outputs`}</CodeBlock>
            <p className="mt-4 text-text-primary border-l-2 border-accent pl-4">
              The goal: 98%+ compliance on harmful evals while maintaining &lt;2% degradation on standard benchmarks.
            </p>
          </Section>

          {/* Loss Functions */}
          <Section title="loss functions for ablation training">
            <p>
              When ablation is applied during fine-tuning (not just weight surgery), the training objective combines standard SFT with ablation-specific losses:
            </p>
            <CodeBlock>{`L_total = L_sft + λ_abl · L_ablation + λ_ref · L_reference

# Ablation loss: minimize refusal direction magnitude
L_ablation = ||W · r̂||²

# Reference loss: stay close to base model behavior
L_reference = KL(π_θ || π_ref)`}</CodeBlock>

            <h3 className="text-xl font-display font-semibold mt-8 mb-4 text-text-primary">gradient-level ablation</h3>
            <p>
              During training, gradients can be projected to avoid reinforcing the refusal direction:
            </p>
            <CodeBlock>{`# Project gradient to avoid refusal direction
def project_gradient(grad, r_hat):
    # Remove component along refusal direction
    return grad - torch.dot(grad, r_hat) * r_hat

# Apply during backward pass
for param in model.parameters():
    if param.grad is not None:
        param.grad = project_gradient(param.grad, r_hat)`}</CodeBlock>
          </Section>

        </div>
      </article>
    </main>
  );
}
