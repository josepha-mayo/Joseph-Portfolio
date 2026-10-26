"""Build the current one-page CV. Source: Joseph's supplied CV and explicit updates, 2026-10-26."""
from pathlib import Path
import hashlib, json, os
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable, KeepTogether
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'public/Joseph_Ayanda_CV.pdf'
fonts=Path(os.environ.get('WINDIR','C:/Windows'))/'Fonts'
if (fonts/'arial.ttf').exists():
 for n,f in [('Resume','arial.ttf'),('Resume-Bold','arialbd.ttf')]:pdfmetrics.registerFont(TTFont(n,str(fonts/f)))
 pdfmetrics.registerFontFamily('Resume',normal='Resume',bold='Resume-Bold',italic='Resume',boldItalic='Resume-Bold')
 normal,bold='Resume','Resume-Bold'
else:normal,bold='Helvetica','Helvetica-Bold'
ink=colors.HexColor('#202C37');accent=colors.HexColor('#296272');muted=colors.HexColor('#53616D')
styles={
'name':ParagraphStyle('name',fontName=bold,fontSize=24,leading=26,textColor=ink,spaceAfter=2),
'tag':ParagraphStyle('tag',fontName=bold,fontSize=9.1,leading=12,textColor=muted,spaceAfter=5),
'contact':ParagraphStyle('contact',fontName=normal,fontSize=9.1,leading=12.5,textColor=ink),
'body':ParagraphStyle('body',fontName=normal,fontSize=9.7,leading=12.5,textColor=ink,spaceAfter=5),
'item':ParagraphStyle('item',fontName=bold,fontSize=9.9,leading=12.4,textColor=ink,spaceBefore=4,spaceAfter=1.5),
'section':ParagraphStyle('section',fontName=bold,fontSize=9.7,leading=13,textColor=accent,spaceBefore=7,spaceAfter=4),
'skills':ParagraphStyle('skills',fontName=normal,fontSize=9.2,leading=11.8,textColor=ink,spaceAfter=2),
}
story=[]
def p(s,style='body'):return Paragraph(s,styles[style])
def link(url,label):return f'<link href="{url}" color="#296272">{label}</link>'
def section(title):story.extend([p(title,'section'),HRFlowable(width='100%',thickness=.4,color=colors.HexColor('#CDD6DA'),spaceAfter=4)])
def entry(title,body,url):story.append(KeepTogether([p(link(url,title),'item'),p(body)]))
story += [p('AYANDA JOSEPH','name'),p('AI &amp; SOFTWARE ENGINEER | END-TO-END PRODUCTS, TRAINING &amp; EVALUATION','tag'),p('Nigeria &nbsp; | &nbsp; '+link('mailto:ayandajoseph390@gmail.com','ayandajoseph390@gmail.com')+' &nbsp; | &nbsp; '+link('https://josephmayo.site','josephmayo.site'),'contact'),p(link('https://github.com/josepha-mayo','github.com/josepha-mayo')+' &nbsp; | &nbsp; '+link('https://huggingface.co/josephmayo','huggingface.co/josephmayo'),'contact'),Spacer(1,7),HRFlowable(width='100%',thickness=.55,color=colors.HexColor('#CDD6DA'),spaceAfter=8),p('<b>18-year-old AI engineer with 3 years of hands-on software engineering experience; available for full-time work.</b> Build end-to-end AI systems: curate data, train and fine-tune models, benchmark checkpoints, package inference, and ship full-stack products. Combine Python/PyTorch model work with TypeScript/React interfaces, backend APIs and PostgreSQL.')]
section('TRAINING, EVALUATION &amp; AGENT-ASSISTED ENGINEERING')
story.append(p('<b>RSI workflow (human-supervised):</b> Use a frozen copy of the base model as a researcher to analyse failures and propose training-data, policy and training-code changes for a trainable copy. Supervise fine-tuning and RL experiments on cloud GPUs, compare candidate checkpoints against baseline evaluations, and publish selected improvements on Hugging Face.'))
story.append(p('<b>Multi-agent execution:</b> Coordinate parallel autonomous research, coding, testing and review agents to accelerate experiments and product delivery. Ground acceptance in executable tests, benchmark comparisons and direct inspection, rather than agent completion claims.'))
section('SELECTED AI &amp; FULL-STACK PRODUCTS')
entry('PEX | Coding-agent supervision','Built a Python/TypeScript supervisor with persistent goals, evidence-backed completion gates and independent test verification. In a documented live OpenCode run, caught a false test-pass claim and guided recovery to verified passing tests.','https://github.com/josepha-mayo/pex')
entry('Socbench | Dataset quality &amp; evaluation platform','Built a Next.js/FastAPI product with a seven-stage audit pipeline: 55 catalogued datasets, 53 complete automated assessments and 16 validated proxy-training outcomes, retaining six divergent runs as evidence.','https://github.com/josepha-mayo/socbench')
entry('gitPulse | Developer social feed','Built a GitHub-connected social and release platform using Next.js, TypeScript, PostgreSQL and OAuth, with profiles, discovery feeds, live updates and API-based posting.','https://github.com/josepha-mayo/git-pulse')
entry('ring-sandbox | Published Python SDK &amp; API emulator','Shipped a typed API client and FastAPI emulator with HMAC-verified webhooks, replayable device scenarios, pytest fixtures and CI-backed integration tests.','https://github.com/josepha-mayo/ring-sandbox')
section('PUBLISHED HUGGING FACE MODELS | MEASURED OUTCOMES')
entry('Holo-3.1-9B-Coder | Coding-model post-training','Reported HumanEval+ pass@1: <b>52.4% to 65.2% (+12.8 points)</b>; LiveCodeBench v2: <b>31.5% to 37.8%</b>. Released LoRA adapter, merged weights and three GGUF quantizations.','https://huggingface.co/josephmayo/Holo-3.1-9B-Coder')
entry('VON-3B | Efficient coding &amp; structured tool use','Combined SFT, RL and policy distillation. Matched EvalPlus HumanEval+: <b>134/164 to 145/164</b>; structured tool-call probe: <b>0/32 to 32/32</b>. Packaged Q8 GGUF for offline inference.','https://huggingface.co/josephmayo/von3b')
entry('Gemma 4 E4B IT Coder | Multimodal coding fine-tune','Fine-tuned on 1,024 filtered examples; executable pass count improved from <b>34/50 to 42/50</b> on a documented HumanEval subset. Released merged weights and GGUF.','https://huggingface.co/josephmayo/gemma-4-E4B-it-Coder')
section('TECHNICAL SKILLS')
story.append(p('<b>ML:</b> PyTorch, Transformers, PEFT, LoRA/QLoRA, SFT, RL experiments, DPO/ORPO, distillation, EvalPlus/HumanEval, LiveCodeBench, dataset auditing, contamination controls, GGUF, llama.cpp.','skills'))
story.append(p('<b>Software:</b> Python, TypeScript, React/Next.js, Node.js, FastAPI, SQL/PostgreSQL, REST APIs, OAuth, live updates, pytest, Docker, Linux, GitHub Actions. <b>Agent workflows:</b> MCP, OpenCode, Codex, Claude.','skills'))
def footer(c,d):
 c.setFont(normal,7.5);c.setFillColor(muted);c.drawString(33,16,'AYANDA JOSEPH | AI ENGINEERING & SOFTWARE DEVELOPMENT');c.drawRightString(A4[0]-33,16,str(d.page))
SimpleDocTemplate(str(OUT),pagesize=A4,rightMargin=33,leftMargin=33,topMargin=27,bottomMargin=25,title='Ayanda Joseph | AI Software Engineer',author='Ayanda Joseph').build(story,onFirstPage=footer,onLaterPages=footer)
import fitz
pdf=fitz.open(OUT);text='\n'.join(page.get_text() for page in pdf)
assert len(pdf)==1, 'CV must remain one page'
assert all(term not in text.lower() for term in ['education','university','school','abliterat'])
for term in ['3 years','18-year-old','RSI workflow','Multi-agent execution','Codex, Claude']:assert term in text,term
assert len(pdf[0].get_links())>=10
(ROOT/'cv/BUILD.json').write_text(json.dumps({'updated':'2026-10-26','pages':1,'pdf_sha256':hashlib.sha256(OUT.read_bytes()).hexdigest(),'generator':'scripts/build_cv_current.py','source':'User-supplied CV, project evidence and explicit user updates. Self-reported model results preserve their evaluation scopes.'},indent=2)+'\n')
pdf[0].get_pixmap(matrix=fitz.Matrix(1.5,1.5)).save(str(ROOT.parent/'cv-updated-preview.png'))
print('CV verified:',len(pdf),'page;',OUT.stat().st_size,'bytes;',len(pdf[0].get_links()),'links')
