import Link from "next/link";

export const metadata = {
  title: "DR-OPIC — Domain-Routed On-Policy Iterative Correction",
  description: "A runnable Python framework for coding SLM experiments. Student-first rollout, verified repair, delta-span training, and curriculum scheduling.",
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

export default function DROPIPage() {
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
              <span className="text-xs px-3 py-1 bg-accent/10 text-accent rounded border border-accent/20 font-medium">framework</span>
              <span className="text-xs px-3 py-1 bg-white/5 text-text-secondary rounded border border-border-subtle">python</span>
              <span className="text-xs px-3 py-1 bg-white/5 text-text-secondary rounded border border-border-subtle">SLM training</span>
            </div>
            <h1 className="text-4xl md:text-5xl font-display font-semibold tracking-tight mb-4 text-text-primary">
              DR-OPIC
            </h1>
            <p className="text-lg text-text-secondary max-w-[60ch]">
              Domain-Routed On-Policy Iterative Correction — a runnable Python framework for coding SLM experiments where the student model attempts first, executable verifiers expose failures, repairs are verified, and training records are built from the student&apos;s reachable failure states.
            </p>
            <div className="flex gap-4 mt-6">
              <a
                href="https://github.com/josepha-mayo/DR-OPIC"
                target="_blank"
                rel="noopener noreferrer"
                className="text-sm font-semibold text-text-primary hover:text-accent flex items-center gap-1.5 transition-colors"
              >
                <i className="fa-brands fa-github"></i> source code
              </a>
            </div>
          </header>

          {/* Overview */}
          <Section title="overview">
            <p>
              DR-OPIC does three concrete things:
            </p>
            <ol className="list-decimal list-inside space-y-2 ml-4">
              <li>Runs student coding attempts against executable tests.</li>
              <li>Builds verified repair, delta, and preference training records from real failures.</li>
              <li>Reports the metrics that matter for a coding SLM: <code className="text-accent">greedy@1</code>, <code className="text-accent">coverage@K</code>, <code className="text-accent">selected@K</code>, <code className="text-accent">selector_gap</code>, and <code className="text-accent">repair@1</code>.</li>
            </ol>
            <p className="mt-4">
              No private datasets, PDFs, model weights, or Kaggle outputs are included. The framework provides the glue needed to run a student-first coding SLM loop without bundling model weights or datasets.
            </p>
          </Section>

          {/* Install */}
          <Section title="install">
            <p>From the repository root:</p>
            <CodeBlock>{`python -m pip install -e ".[dev]"
python -m pytest -q`}</CodeBlock>
            <p>Expected result: <code className="text-accent">7 passed</code></p>
          </Section>

          {/* Core Loop */}
          <Section title="the core loop">
            <p>DR-OPIC follows this sequence:</p>
            <ol className="list-decimal list-inside space-y-2 ml-4">
              <li>Route a task to a bounded coding domain, or abstain.</li>
              <li>Let the current student attempt the task before using any teacher answer.</li>
              <li>Run executable verification.</li>
              <li>Compute task learnability with ZPD weighting.</li>
              <li>Repair failed attempts using failed code plus verifier observation.</li>
              <li>Verify repairs.</li>
              <li>Select the most learnable verified winner.</li>
              <li>Emit JSON and JSONL artifacts for training and review.</li>
            </ol>
          </Section>

          {/* Architecture */}
          <Section title="architecture">
            <p>The data flow through the system:</p>
            <CodeBlock>{`Task
  → route and safety check
  → student rollout K times
  → Python verifier
  → ZPD and advantage calculation
  → repair failed attempts
  → verify repairs
  → select learnable winner
  → schedule into mastered/ZPD/repair/decompose buckets
  → emit JSON/JSONL artifacts
  → train with SFT, delta, preference, or RLVR losses`}</CodeBlock>
          </Section>

          {/* Math */}
          <Section title="the mathematics">
            <h3 className="text-xl font-display font-semibold mt-8 mb-4 text-text-primary">Domain Routing</h3>
            <p>
              Let <code>D = {'{'}D_1, ..., D_K{'}'}</code> be bounded coding domains. A router maps a task to a specialist or abstains:
            </p>
            <CodeBlock>{`r_phi(x) ∈ {1, ..., K, abstain}
π_k(y | x, r_phi(x) = k)`}</CodeBlock>
            <p>The target is cost-adjusted reliable competence:</p>
            <CodeBlock>{`η_k = (Q_k - Q_base,k) / (C_train,k + ρ C_infer,k + γ C_review,k)`}</CodeBlock>
            <p>Promotion also requires safety and abstention constraints:</p>
            <CodeBlock>{`unsafe_accept_k ≤ ε_k
ood_accept_k ≤ α_k
selective_risk_k(θ, τ) ≤ δ_k`}</CodeBlock>

            <h3 className="text-xl font-display font-semibold mt-8 mb-4 text-text-primary">Verifier Reward</h3>
            <p>For a candidate <code>y</code> on task <code>x</code>:</p>
            <CodeBlock>{`r(y, x) =
  1.00 · final_pass
+ 0.25 · public_test_fraction
+ 0.10 · syntax_ok
+ 0.05 · import_ok
- 0.05 · repeated_token_penalty
- 0.05 · invalid_format_penalty
- 0.02 · normalized_length_penalty
- 0.05 · unsafe_api_penalty`}</CodeBlock>
            <p>
              Final pass dominates. Partial rewards rank failures for repair and RL; they do not replace held-out tests.
            </p>

            <h3 className="text-xl font-display font-semibold mt-8 mb-4 text-text-primary">ZPD Weighting</h3>
            <p>For <code>s</code> passes in <code>K</code> samples:</p>
            <CodeBlock>{`p̃ = (s + 0.5) / (K + 1)
w_zpd = 4 · p̃ · (1 − p̃)`}</CodeBlock>
            <p>
              This peaks near tasks the model sometimes solves and sometimes fails. It stays nonzero for small-K all-fail groups, which keeps near-impossible tasks available for decomposition and repair instead of deleting them.
            </p>

            <h3 className="text-xl font-display font-semibold mt-8 mb-4 text-text-primary">Learnable Winner</h3>
            <p>For a verified candidate <code>c</code> and failed student attempt <code>s</code>:</p>
            <CodeBlock>{`Score(c; s) =
  λ_v · 1[verifier(c) = pass]
+ λ_f · fuzz_pass_fraction(c)
+ λ_l · log π_student(c | x) / |c|
- λ_e · normalized_edit_distance(c, s)
- λ_c · complexity(c)
- λ_d · rare_dependency_count(c)`}</CodeBlock>
            <p>
              The target is not the prettiest teacher answer. It is the passing answer closest to the student&apos;s reachable failure state.
            </p>

            <h3 className="text-xl font-display font-semibold mt-8 mb-4 text-text-primary">Composite Objective</h3>
            <CodeBlock>{`L_DR-OPIC =
  L_self
+ λ_r · L_repair
+ λ_delta · L_delta
+ λ_ood · L_ood
+ λ_cal · L_cal
+ λ_pref · L_pref
+ λ_rl · L_RLVR
+ λ_comp · R_comp`}</CodeBlock>
            <p>Practical early runs should start with:</p>
            <CodeBlock>{`L = L_self + L_repair + 0.3 · L_delta`}</CodeBlock>
            <p>Add verified preference or RLVR only after the repair probe improves.</p>

            <h3 className="text-xl font-display font-semibold mt-8 mb-4 text-text-primary">Self Training</h3>
            <p>For a rollout group with rewards <code>{'{'}r_i{'}'}</code>:</p>
            <CodeBlock>{`A_i = (r_i − mean(r)) / (std(r) + ε)
L_self = − w_task · Σ_i max(A_i, 0) · log π_θ(y_i | x)`}</CodeBlock>
            <p>This is advantage-weighted behavior cloning over the student&apos;s own distribution.</p>

            <h3 className="text-xl font-display font-semibold mt-8 mb-4 text-text-primary">Repair Training</h3>
            <CodeBlock>{`c_repair = format(task=x, failed_code=y_fail, observation=o_verifier)
L_repair = − w_task · log π_θ(y_fix | c_repair)`}</CodeBlock>
            <p>
              Loss should be applied only to the assistant correction, not to the task, failed code, or verifier observation.
            </p>

            <h3 className="text-xl font-display font-semibold mt-8 mb-4 text-text-primary">Delta-Span Subtraction</h3>
            <p>Align failed code <code>y⁻</code> and fixed code <code>y⁺</code>:</p>
            <CodeBlock>{`D+ = added/replaced tokens in the verified fix
D- = removed/replaced tokens in the failed answer

L_delta =
  − w_task · Σ_{t ∈ D+} log π_θ(y⁺_t | prefix⁺_t)
  + λ_neg · w_task · Σ_{t ∈ D-} relu(
      log π_θ(y⁻_t | prefix⁻_t)
    − log π_ref(y⁻_t | prefix⁻_t)
    − margin
    )`}</CodeBlock>
            <p>
              This increases corrected spans and subtracts only the wrong local spans, avoiding whole-program punishment when most code is shared and correct.
            </p>
            <p>The implementation exposes:</p>
            <CodeBlock>{`D+ = fixed-code token indices touched by insert/replace
D- = failed-code token indices touched by delete/replace
shared_ratio = shared tokens / max(len(failed), len(fixed))
edit_ratio = 1 − shared_ratio`}</CodeBlock>
            <p>
              These fields let a trainer build positive masks for corrected spans and negative masks for failing spans without penalizing shared code.
            </p>

            <h3 className="text-xl font-display font-semibold mt-8 mb-4 text-text-primary">Verified Preference</h3>
            <p>Use preference only when pairs are execution-grounded:</p>
            <CodeBlock>{`ℓ_θ(y | c) = log π_θ(y | c) / max(1, tokens(y))
Δ =
  [ℓ_θ(y⁺) − ℓ_ref(y⁺)]
− [ℓ_θ(y⁻) − ℓ_ref(y⁻)]
− margin(r⁺, r⁻)

L_vDPO = − log sigmoid(β · Δ)`}</CodeBlock>

            <h3 className="text-xl font-display font-semibold mt-8 mb-4 text-text-primary">RLVR</h3>
            <p>For verifiable rewards and an old policy:</p>
            <CodeBlock>{`ρ_i = π_θ(y_i | x) / π_old(y_i | x)
L_RLVR = − E_i min(ρ_i A_i, clip(ρ_i, 1−ε, 1+ε) A_i)`}</CodeBlock>
            <p>
              The reward must come from execution tests, fuzzing, static checks, type checks, linters, safety gates, and abstention checks.
            </p>

            <h3 className="text-xl font-display font-semibold mt-8 mb-4 text-text-primary">Test-Time Scaling</h3>
            <p>Report empirical metrics:</p>
            <CodeBlock>{`coverage@K = tasks with at least one passing sample / tasks
selected@K = tasks where selector chose a passing sample / tasks
selector_gap = coverage@K − selected@K
repair@1 = tasks fixed by one repair after K failures / tasks`}</CodeBlock>
            <p>Do not rely on the IID <code>1 − (1 − p)^K</code> formula except as intuition.</p>
          </Section>

          {/* Scheduler */}
          <Section title="verifier-zpd scheduler">
            <p>For each rollout group, the scheduler emits a bucket:</p>
            <div className="overflow-x-auto my-6">
              <table className="w-full text-sm text-left">
                <thead>
                  <tr className="border-b border-border-subtle">
                    <th className="py-3 px-4 text-text-primary font-medium">Bucket</th>
                    <th className="py-3 px-4 text-text-primary font-medium">Condition</th>
                  </tr>
                </thead>
                <tbody className="text-text-secondary">
                  <tr className="border-b border-border-subtle/50">
                    <td className="py-3 px-4 font-[family-name:var(--font-geist-mono)] text-accent">mastered</td>
                    <td className="py-3 px-4">smoothed pass rate is high</td>
                  </tr>
                  <tr className="border-b border-border-subtle/50">
                    <td className="py-3 px-4 font-[family-name:var(--font-geist-mono)] text-accent">zpd_train</td>
                    <td className="py-3 px-4">pass rate is neither too low nor mastered</td>
                  </tr>
                  <tr className="border-b border-border-subtle/50">
                    <td className="py-3 px-4 font-[family-name:var(--font-geist-mono)] text-accent">repair_train</td>
                    <td className="py-3 px-4">student failed but a close verified repair exists</td>
                  </tr>
                  <tr className="border-b border-border-subtle/50">
                    <td className="py-3 px-4 font-[family-name:var(--font-geist-mono)] text-accent">decompose</td>
                    <td className="py-3 px-4">task is too hard and no close fix was found</td>
                  </tr>
                  <tr className="border-b border-border-subtle/50">
                    <td className="py-3 px-4 font-[family-name:var(--font-geist-mono)] text-accent">eval_only</td>
                    <td className="py-3 px-4">split is not training</td>
                  </tr>
                  <tr>
                    <td className="py-3 px-4 font-[family-name:var(--font-geist-mono)] text-accent">discard</td>
                    <td className="py-3 px-4">verifier reliability is too low</td>
                  </tr>
                </tbody>
              </table>
            </div>
            <p>Training weight combines:</p>
            <CodeBlock>{`w = w_zpd · q_failure_balance · q_novelty · q_repair`}</CodeBlock>
            <p>
              <code className="text-accent">repair_train</code> is the important DR-OPIC bucket: it captures tasks where the student cannot solve the task alone yet, but a verified fix is close enough to the student&apos;s failed state to be learnable.
            </p>
          </Section>

          {/* Modules */}
          <Section title="modules">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {[
                { name: "maths", desc: "ZPD, rewards, advantages, coverage metrics, cost estimates" },
                { name: "verifier", desc: "Python code extraction, static checks, test execution" },
                { name: "forge", desc: "Student-first rollout, repair, and artifact construction" },
                { name: "selectors", desc: "Verified learnable-winner selection" },
                { name: "delta", desc: "Token/line delta spans between failed and fixed code" },
                { name: "scheduler", desc: "Verifier-ZPD curriculum buckets and train-mix weights" },
                { name: "preference", desc: "Scalar helpers for verified DPO/ORPO-style pairs" },
                { name: "datasets", desc: "JSONL schema and quality audit helpers" },
                { name: "replay", desc: "Deterministic replay certification" },
                { name: "routing", desc: "Domain routing and abstention helper" },
                { name: "safety", desc: "Simple coding-safety acceptance helper" },
                { name: "compression", desc: "Memory/compute estimates and retention gates" },
                { name: "losses", desc: "Optional PyTorch losses for SFT, delta, DPO, and RLVR" },
              ].map((mod) => (
                <div key={mod.name} className="bg-white/5 border border-border-subtle rounded-lg p-4">
                  <code className="text-accent text-sm font-medium">{mod.name}</code>
                  <p className="text-text-secondary text-sm mt-1">{mod.desc}</p>
                </div>
              ))}
            </div>
          </Section>

          {/* CLI */}
          <Section title="cli cheatsheet">
            <CodeBlock>{`# Run the built-in demo
python -m dr_opic.cli forge-demo

# Write stable artifact bundle
python -m dr_opic.cli --output outputs/demo forge-demo

# Verify a Python candidate
python -m dr_opic.cli verify-python examples/python_task.json \\
  --code examples/reverse_words_good.py

# Compute ZPD weight
python -m dr_opic.cli zpd --passes 2 --samples 5

# Route a prompt
python -m dr_opic.cli route "Fix this Python traceback and add pytest coverage"

# Estimate dense model memory
python -m dr_opic.cli estimate-model --params 3.09e9

# Build delta-span record
python -m dr_opic.cli delta --task-id reverse_words \\
  --failed examples/reverse_words_bad.py \\
  --fixed examples/reverse_words_good.py

# Run scheduler demo
python -m dr_opic.cli schedule-demo

# Audit a JSONL training file
python -m dr_opic.cli audit-jsonl C:/datasets/slm/sft.jsonl --schema sft`}</CodeBlock>
          </Section>

          {/* Artifacts */}
          <Section title="artifact contract">
            <p>Running <code className="text-accent">forge-demo</code> writes:</p>
            <ul className="list-none space-y-2 ml-4">
              <li><code className="text-accent">round_summary.json</code></li>
              <li><code className="text-accent">student_rollouts.jsonl</code></li>
              <li><code className="text-accent">verified_repairs.jsonl</code></li>
              <li><code className="text-accent">learnable_winner.json</code></li>
              <li><code className="text-accent">delta_spans.json</code></li>
            </ul>
            <p className="mt-4">
              These file names are stable and can be consumed by training notebooks or release scripts.
            </p>
          </Section>

          {/* Release */}
          <Section title="release checklist">
            <p>
              Do not promote a run just because one number moved. A serious DR-OPIC release should report:
            </p>
            <ul className="list-none space-y-2 ml-4">
              <li><i className="fa-solid fa-check text-accent mr-2"></i> greedy@1</li>
              <li><i className="fa-solid fa-check text-accent mr-2"></i> coverage@K</li>
              <li><i className="fa-solid fa-check text-accent mr-2"></i> selected@K</li>
              <li><i className="fa-solid fa-check text-accent mr-2"></i> selector gap</li>
              <li><i className="fa-solid fa-check text-accent mr-2"></i> repair@1</li>
              <li><i className="fa-solid fa-check text-accent mr-2"></i> hard-subset pass rate</li>
              <li><i className="fa-solid fa-check text-accent mr-2"></i> malformed output rate</li>
              <li><i className="fa-solid fa-check text-accent mr-2"></i> repeated-token collapse rate</li>
              <li><i className="fa-solid fa-check text-accent mr-2"></i> OOD false accept rate</li>
              <li><i className="fa-solid fa-check text-accent mr-2"></i> unsafe compliance rate</li>
              <li><i className="fa-solid fa-check text-accent mr-2"></i> latency and memory</li>
              <li><i className="fa-solid fa-check text-accent mr-2"></i> contamination and dataset audit summary</li>
            </ul>
            <p className="mt-6 text-text-primary border-l-2 border-accent pl-4">
              The falsifiable claim: student-first repair and delta-span training should improve selected@K or repair@1 without damaging formatting, safety, or abstention.
            </p>
          </Section>

          {/* Safety */}
          <Section title="safety scope">
            <p>
              <code className="text-accent">verify-python</code> executes candidate code in a temporary subprocess with a timeout. That is useful for local research, but it is not a security sandbox. Run untrusted model code inside a container or VM.
            </p>
          </Section>
        </div>
      </article>
    </main>
  );
}
