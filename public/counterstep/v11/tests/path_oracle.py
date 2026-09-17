"""Independent AST/Fraction checks for tasks and requested-form rejection."""
from pathlib import Path
from fractions import Fraction as F
import ast,re,json,subprocess
R=Path(__file__).resolve().parents[1]
def affine(text):
 text=re.sub(r'(?<=\d)(?=[x(])','*',text.strip())
 def walk(n):
  if isinstance(n,ast.Constant) and isinstance(n.value,int):return F(0),F(n.value)
  if isinstance(n,ast.Name) and n.id=='x':return F(1),F(0)
  if isinstance(n,ast.UnaryOp):
   a,b=walk(n.operand)
   if isinstance(n.op,ast.USub):return -a,-b
   if isinstance(n.op,ast.UAdd):return a,b
  if isinstance(n,ast.BinOp):
   a,b=walk(n.left);c,d=walk(n.right)
   if isinstance(n.op,ast.Add):return a+c,b+d
   if isinstance(n.op,ast.Sub):return a-c,b-d
   if isinstance(n.op,ast.Mult) and (not a or not c):return a*d+c*b,b*d
   if isinstance(n.op,ast.Div) and not c and d:return a/d,b/d
  raise ValueError('Outside independent linear grammar')
 return walk(ast.parse(text,mode='eval').body)
def parts(eq):
 l,r=eq.split('=');return (*affine(l),*affine(r))
def solution(eq):
 a,b,c,d=parts(eq);assert a!=c;return (d-b)/(a-c)
script="const P=require('./src/path.js');let rows=[];for(const skill of ['spread','balance','divide','negative','arithmetic'])for(const stage of ['warmup','transfer'])for(const seed of [0,1,2,3,7,11,37,99,321,711,2026,5301,19031,123456,999999]){let t=P.makeTask(skill,seed,stage);const [l,r]=t.good.split('=');const answers=[t.good,t.good.split('=').reverse().join('='),t.before,`${l}=(${r})+1`,`2*(${l})=2*(${r})`];rows.push({task:t,answers,results:answers.map(a=>P.checkTask(t,a))});}console.log(JSON.stringify(rows))"
rows=json.loads(subprocess.check_output(['node','-e',script],cwd=R));checks=0
for row in rows:
 t=row['task'];assert solution(t['before'])==solution(t['good']);assert list(map(str,parts(t['good'])))==t['target']
 for i,(a,out) in enumerate(zip(row['answers'],row['results'])):
  assert out['correct']==(i in (0,1)),(t,a,out)
  if i in (0,1,2,4):assert solution(a)==solution(t['before'])
  if i==3:assert solution(a)!=solution(t['before'])
  checks+=1
report={'status':'passed','generated_tasks':len(rows),'response_checks':checks,'independent_parser':'Python AST plus Fraction affine algebra; no eval and no JavaScript parser reuse','scope':'Synthetic authored task families, not learner results, new-model evaluation or formal proof'}
(R/'evidence/path-oracle.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
