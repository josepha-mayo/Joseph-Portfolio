"""Build Joseph Ayanda's expanded technical CV from a dated public-source snapshot."""
from pathlib import Path
import json, hashlib
from xml.sax.saxutils import escape
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether

DATE = "17 September 2026"
INK = colors.HexColor("#152D43")
ACCENT = colors.HexColor("#176B72")
MUTED = colors.HexColor("#536371")
RULE = colors.HexColor("#D7E0E6")
PALE = colors.HexColor("#F1F5F7")
BASE = "https://huggingface.co/josephmayo/"
GH = "https://github.com/josepha-mayo/"
SITE = "https://josephmayo.site"

FAMILIES = [
 ("Holo-3.1-9B-Coder", "Coding fine-tune; adapter, merged weights and GGUF in one repository.",
  [("All artifacts","Holo-3.1-9B-Coder")]),
 ("ZAYA1-8B-Coder", "Custom-architecture coding adaptation and local inference releases.",
  [("Merged","ZAYA1-8B-Coder"),("GGUF","ZAYA1-8B-Coder-GGUF"),("LoRA","ZAYA1-8B-Coder-LoRA")]),
 ("Gemma 4 E4B IT Coder", "Coding SFT, full-weight merge and quantized distribution.",
  [("Merged","gemma-4-E4B-it-Coder"),("GGUF","gemma-4-E4B-it-Coder-GGUF"),("LoRA","gemma-4-E4B-it-coding-lora")]),
 ("Holo-3.1-4B-Coder", "Compact coding model with an 80-task reported evaluation probe.",
  [("Merged","Holo-3.1-4B-Coder"),("GGUF","Holo-3.1-4B-Coder-GGUF"),("LoRA","Holo-3.1-4B-Coder-LoRA")]),
 ("LFM2.5-8B-A1B-Coder", "Mixture-of-experts adaptation for multilingual coding tasks.",
  [("Merged","LFM2.5-8B-A1B-Coder"),("GGUF","LFM2.5-8B-A1B-Coder-GGUF"),("LoRA","LFM2.5-8B-A1B-Coder-LoRA")]),
 ("Qwopus-9B-Unfettered", "Directional-ablation research release and local GGUF builds.",
  [("Model","Qwopus-9B-Unfettered"),("GGUF","Qwopus-9B-Unfettered-GGUF")]),
 ("Fara-7B-Abliterated-v2", "Refusal-direction orthogonalization with a quantized companion.",
  [("Model","Fara-7B-Abliterated-v2"),("GGUF","Fara-7B-Abliterated-v2-GGUF")]),
 ("Mellum2-12B-A2.5B-Thinking-Abliterated", "MoE reasoning-model research with per-expert and per-layer ablation.",
  [("Model","Mellum2-12B-A2.5B-Thinking-Abliterated"),("GGUF","Mellum2-12B-A2.5B-Thinking-Abliterated-GGUF")]),
 ("Qwen2.5-0.5B-Unfettered", "Small-model ablation research for resource-constrained inference.",
  [("Model","Qwen2.5-0.5B-Unfettered")]),
 ("HRM-Text-1B-sft-code", "Code-generation SFT experiment with a companion LoRA adapter.",
  [("Model","HRM-Text-1B-sft-code"),("LoRA","HRM-Text-1B-sft-code-LoRA")]),
 ("Qwen2.5-agentic-7B-SLM-LoRA", "Adapter release targeting agentic and tool-use workflows.",
  [("LoRA","Qwen2.5-agentic-7B-SLM-LoRA")])
]

PROJECTS = [
 ("ModelFang", "Graph-based adversarial evaluation", GH+"ModelFang",
  "Built a multi-turn LLM testing framework with conditional attack flows, finite-state response evaluation, provider adapters, execution budgets and audit logs; paired it with a Next.js analyst dashboard."),
 ("IntellectSafe", "AI safety and security prototype", GH+"IntellectSafe",
  "Developed a FastAPI/Next.js platform combining a multi-provider proxy, prompt and output review, privacy modules, multi-model validation and agent permission controls."),
 ("Mayo", "Multi-agent repository maintenance", GH+"mayo",
  "Implemented scanner, executor and reviewer agents that propose and review code changes, create GitHub pull requests and retain cross-repository lessons for subsequent runs."),
 ("SWARMs Debate Primitive", "Multi-agent coordination", GH+"Swarms",
  "Built persona-based debate and voting workflows with transcript hashing and Solana-linked records, making the discussion and voting process inspectable."),
 ("Countback", "OpenCV 5 and AWS inspection workflow", "https://devpost.com/software/countback-inspect-the-evidence",
  "Built photo enrollment, viewpoint-aware review, evidence-linked notes and export. Evaluated 18 photos from nine fresh clips; validated the original analysis handler on private AWS Lambda with four valid analyses and five expected input rejections."),
 ("Counterstep and Pocket", "Algebra repair and native Android practice", GH+"Counterstep-Relay",
  "Developed typed repair and transfer-practice workflows that retain first attempts, hints and unfinished drafts. Shipped a Kotlin Android prototype with 98 JVM and 19 emulator UI tests in its recorded build."),
 ("SunQueue", "Solar-aware work scheduling", "https://devpost.com/software/sunqueue-same-work-less-grid",
  "Built a local JavaScript planner, dated shift sheets and a reported-run ledger. Enforced equivalent completed work and terminal battery accounting before displaying modeled grid-energy savings."),
 ("Forkline", "Rollback and delivery-recovery lab", "https://devpost.com/software/forkline-rehearse-the-rollback",
  "Integrated blockchain reorganization checks with a SQLite outbox and HTTP receiver. Demonstrated guarded dispatch, lost-acknowledgement reconciliation and restart recovery using an isolated local EVM."),
 ("ReturnReady", "Merged open-source contribution", "https://github.com/CALLE-AI/awesome-phone-call-agents/pull/408",
  "Built conservative comparison of written return terms and finished call results, with source-linked uncertainty and human review. Contribution PR #408 was merged into CALL-E's upstream repository."),
 ("DOOMFLY", "Experimental vision and connectome interfaces", SITE+"/doomfly",
  "Built a physical fly-tracking setup and documented Doom/control experiments alongside a reproducible connectome-driven chess replay. Preserved protocol hashes, game records and measurement failures; did not label the chess run a live-fly result.")
]

def make_cv(snapshot_path, output_path):
    snapshot=json.loads(Path(snapshot_path).read_text())
    repo_rows={r["repo"].split("/",1)[1]:r for r in snapshot["rows"] if r["type"]=="model" and "metadata" in r}
    selected=[repo for _,_,variants in FAMILIES for _,repo in variants]
    assert len(selected)==len(set(selected))==23
    assert all(type(repo_rows[n]["metadata"]["downloadsAllTime"]) is int for n in selected)
    total=sum(repo_rows[n]["metadata"]["downloadsAllTime"] for n in selected)
    assert total==21033, "This CV's reviewed summary is pinned to the September 17 snapshot."
    body=ParagraphStyle("Body",fontName="Helvetica",fontSize=10,leading=13.8,textColor=INK,spaceAfter=6)
    small=ParagraphStyle("Small",parent=body,fontSize=8.5,leading=11.2,textColor=MUTED,spaceAfter=5)
    title=ParagraphStyle("Title",parent=body,fontName="Helvetica-Bold",fontSize=28,leading=31,spaceAfter=6)
    sub=ParagraphStyle("Subtitle",parent=body,fontName="Helvetica-Bold",fontSize=10.5,leading=14,textColor=ACCENT,spaceAfter=7)
    section=ParagraphStyle("Section",parent=body,fontName="Helvetica-Bold",fontSize=11.5,leading=15,textColor=ACCENT,spaceBefore=12,spaceAfter=8)
    blocktitle=ParagraphStyle("BlockTitle",parent=body,fontName="Helvetica-Bold",fontSize=10.4,leading=14,spaceAfter=3)
    cell=ParagraphStyle("Cell",parent=body,fontSize=9,leading=12,spaceAfter=0)
    cellsmall=ParagraphStyle("CellSmall",parent=small,fontSize=8.3,leading=11,spaceAfter=0)
    def P(t,sty=body):return Paragraph(t,sty)
    def A(label,url):return '<a href="'+escape(url, {'"':'&quot;'})+'" color="#176B72">'+escape(label)+'</a>'
    def block(name,subtitle,url,content):
        return KeepTogether([P(A(name,url)+" | "+escape(subtitle),blocktitle),P(content)])
    page_labels=["PROFILE & SELECTED RESEARCH","OPEN MODELS & DATASETS","SELECTED ENGINEERING PROJECTS"]
    def footer(c,d):
        c.saveState()
        c.setStrokeColor(RULE);c.setLineWidth(.5);c.line(42,39,A4[0]-42,39)
        c.setFont("Helvetica",8);c.setFillColor(MUTED)
        c.drawString(42,26,"JOSEPH AYANDA  /  "+page_labels[min(d.page-1,2)])
        c.drawRightString(A4[0]-42,26,f"{d.page} / 3")
        c.restoreState()
    story=[
      P("JOSEPH AYANDA",title),
      P("AI/ML ENGINEER  |  CODING MODELS, EVALUATION & AGENTIC SYSTEMS",sub),
      P("Ilorin, Nigeria  |  "+A("ayandajoseph390@gmail.com","mailto:ayandajoseph390@gmail.com")+"  |  "+A("josephmayo.site",SITE),small),
      P(A("github.com/josepha-mayo",GH.rstrip("/"))+"  |  "+A("huggingface.co/josephmayo",BASE.rstrip("/")),small),
      Spacer(1,6),
      P("Independent AI/ML engineer building coding-model adaptations, verifier-driven post-training tools and practical AI applications. Work spans data curation, LoRA/QLoRA training, model merging, GGUF delivery, adversarial evaluation and multi-agent systems."),
    ]
    banner=Table([[P("<b>23</b> public model repositories",cell),P("<b>21,033</b> all-time model downloads",cell),P("<b>3</b> published datasets",cell)]],colWidths=[164,188,159])
    banner.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,-1),PALE),("BOX",(0,0),(-1,-1),.5,RULE),("TOPPADDING",(0,0),(-1,-1),11),("BOTTOMPADDING",(0,0),(-1,-1),11)]))
    story += [banner,P("Hugging Face public counters, "+DATE+". Includes adapters and quantized releases; not unique users. Full breakdown on page 2.",small),P("SELECTED MODEL & RESEARCH WORK",section)]
    story += [
      block("Holo-3.1-9B-Coder","Coding-model adaptation",BASE+"Holo-3.1-9B-Coder",
        "Fine-tuned Hcompany's Holo backbone and published the adapter, merged weights and Q4_K_M/Q5_K_M/Q6_K GGUF builds. Published evaluation reports HumanEval+ pass@1 of <b>65.2%</b> versus 52.4% base, and LiveCodeBench v2 of <b>37.8%</b> versus 31.5% base."),
      block("Gemma 4 E4B IT Coder","Training, evaluation and merge",BASE+"gemma-4-E4B-it-Coder",
        "Published a coding-tuned Gemma release with LoRA training and merge records from two Tesla T4 GPUs. Reported executable 50-task HumanEval-subset results improved from <b>34/50 to 42/50</b>; distributed merged weights, adapter and GGUF builds."),
      block("Holo 4B and LFM2.5 Coder","Compact and MoE adaptations",BASE+"Holo-3.1-4B-Coder",
        "Released coding adaptations for a compact Holo model and LiquidAI's MoE model. Holo's published 80-task probe improved from <b>24 to 31 passes</b>; LFM's reported held-out mean negative log-likelihood decreased from <b>3.390 to 1.875</b>."),
      block("DR-OPIC","Verifier-driven post-training framework",GH+"DR-OPIC",
        "Built a runnable Python framework that turns student coding failures into verified repair, preference and changed-span training records. Implemented curriculum weighting, rollout selection, deterministic replay, dataset auditing and optional PyTorch loss helpers for SFT, DPO and RLVR."),
      block("Model Unfetter","Directional-ablation research tooling",GH+"model-unfetter",
        "Implemented refusal-vector extraction, directional and norm-preserving ablation, per-layer/component controls and post-ablation evaluation. Added CPU/GPU, streaming and GGUF-oriented research backends.")
    ]
    story += [P("TECHNICAL SKILLS",section),
      P("<b>Models & data:</b> PyTorch, Transformers, Hugging Face, PEFT, LoRA/QLoRA, SFT, DPO, ORPO, distillation, RLVR, GGUF, executable evaluation, synthetic data, filtering and deduplication."),
      P("<b>Engineering:</b> Python, TypeScript/JavaScript, C, Kotlin, FastAPI, Next.js, Node.js, PostgreSQL, SQLite, Redis, OpenCV, Docker, AWS Lambda, GitHub Actions and REST APIs."),
      P("EDUCATION",section),
      P("<b>Al-Hikmah University, Ilorin</b> | Cybersecurity undergraduate, in progress."),
      P("Model performance figures above are reported in the linked release cards. Subset evaluations and negative log-likelihood are not full-benchmark or independent replication claims.",small),
      PageBreak(),P("OPEN MODELS & DATASETS",title),
      P("Release catalogue  /  cumulative downloads as of "+DATE,sub),
      P("All model links below resolve to public repositories under <b>josephmayo</b>. Each format has its own count; family variants are grouped to distinguish full models, adapters and quantizations.",body)]
    table=[[P("<b>MODEL FAMILY / CONTRIBUTION</b>",cell),P("<b>ARTIFACT DOWNLOAD COUNTS</b>",cell)]]
    for name,desc,variants in FAMILIES:
        links="  |  ".join(A(label+" "+format(repo_rows[repo]["metadata"]["downloadsAllTime"],","),BASE+repo) for label,repo in variants)
        table.append([P("<b>"+escape(name)+"</b><br/>"+escape(desc),cellsmall),P(links,cell)])
    tbl=Table(table,colWidths=[285,226],repeatRows=1,hAlign="LEFT")
    tbl.setStyle(TableStyle([
      ("BACKGROUND",(0,0),(-1,0),PALE),("VALIGN",(0,0),(-1,-1),"TOP"),
      ("TOPPADDING",(0,0),(-1,-1),7),("BOTTOMPADDING",(0,0),(-1,-1),7),
      ("LEFTPADDING",(0,0),(-1,-1),8),("RIGHTPADDING",(0,0),(-1,-1),8),
      ("LINEBELOW",(0,0),(-1,0),.7,RULE),("LINEBELOW",(0,1),(-1,-1),.35,RULE)]))
    story += [tbl,P("TOTAL: <b>21,033 model downloads</b> across 23 accessible repositories and 11 model families.",small),
       P("PUBLISHED DATASETS",section)]
    datasets=[
      ("Curated OpenBMB Code/Math","curated-openbmb-code-math","<b>31,909 records</b>: 25,891 direct-answer and 6,018 reasoning examples for code/math post-training."),
      ("Public Curated Coding Data","public-curated-coding-data","<b>2,703 prompt/response rows</b> across GitHub code, technical discussions and coding examples; source-specific licensing retained."),
      ("Refusal Compliance Pairs","refusal-compliance-pairs","<b>201 labelled prompts</b>: 101 refusal and 100 compliance prompts for activation contrast and directional-ablation research.")
    ]
    dr={r["repo"].split("/",1)[1]:r for r in snapshot["rows"] if r["type"]=="dataset" and "metadata" in r}
    for name,repo,desc in datasets:
        count=dr[repo]["metadata"]["downloadsAllTime"]
        story.append(block(name,f"{count:,} all-time downloads","https://huggingface.co/datasets/josephmayo/"+repo,desc))
    story += [P("Download figures are dated Hub counters, not endorsements, paying users or de-duplicated installations. Model and dataset counts use different Hub counting rules. Research-ablation releases are listed as research artifacts, not safety-certified deployments.",small),
       PageBreak(),P("SELECTED ENGINEERING PROJECTS",title),
       P("Open-source tools, application prototypes and reproducible experiments",sub)]
    for name,subtitle,url,desc in PROJECTS:
        story.append(block(name,subtitle,url,escape(desc)))
        story.append(Spacer(1,4))
    story += [P("ADDITIONAL WORK",section),
       P(A("CutProof","https://devpost.com/software/cutproof-context-first-clip-studio")+" | Local-first clip review and source-context workflows. More code, model cards, demonstrations and technical notes are linked from "+A("the portfolio",SITE)+".",body),
       Spacer(1,0)]
    out=Path(output_path);out.parent.mkdir(parents=True,exist_ok=True)
    doc=SimpleDocTemplate(str(out),pagesize=A4,rightMargin=42,leftMargin=42,topMargin=38,bottomMargin=51,
       title="Joseph Ayanda | AI/ML Engineer | CV",author="Joseph Ayanda",
       subject="Technical CV: models, research, open-source projects and software engineering")
    class DeterministicCanvas(canvas.Canvas):
        def __init__(self,*a,**k):k["invariant"]=1;super().__init__(*a,**k)
    doc.build(story,onFirstPage=footer,onLaterPages=footer,canvasmaker=DeterministicCanvas)
    return out

if __name__=="__main__":
    import argparse
    p=argparse.ArgumentParser();p.add_argument("--snapshot",required=True);p.add_argument("--out",required=True)
    args=p.parse_args();make_cv(args.snapshot,args.out)
