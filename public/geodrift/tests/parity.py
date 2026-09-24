"""Seeded exhaustive-address oracle AND independently implemented JS/Python parity."""
from pathlib import Path
import sys,random,json,subprocess,collections
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R));import geodrift as G
rng=random.Random(20260907)
def sample():
 a=[];pos=0
 while pos<64:
  pos+=rng.randrange(0,5)
  if pos>=64:break
  end=min(63,pos+rng.randrange(0,9));a.append((pos,end,rng.choice(['US','CN','NG','-'])));pos=end+1
 return a

def text(a):return '\n'.join(f'"{s}","{e}","{c}","Name"'for s,e,c in a)

def brute(a,b,db,da):
 def at(r,x):return next((c for s,e,c in r if s<=x<=e),None)
 def dec(c,p):return 'review'if c is None or c=='-'else'deny'if c in p else'allow'
 out=collections.Counter();summary={k:0 for k in ['union_addresses','changed_addresses','decision_changed_addresses','coverage_lost_addresses','coverage_gained_addresses','country_changed_addresses']}
 for x in range(64):
  o,n=at(a,x),at(b,x)
  if o is None and n is None:continue
  od,nd=dec(o,db),dec(n,da);out[od+' -> '+nd]+=1
  summary['union_addresses']+=1;summary['changed_addresses']+=o!=n or od!=nd;summary['decision_changed_addresses']+=od!=nd;summary['coverage_lost_addresses']+=o is not None and n is None;summary['coverage_gained_addresses']+=o is None and n is not None;summary['country_changed_addresses']+=o is not None and n is not None and o!=n
 return {k:str(v)for k,v in summary.items()},{k:str(v)for k,v in out.items()}
rows=[]; expected=[]
for i in range(500):
 a,b=sample(),sample();db=','.join(rng.sample(['CN','US','NG'],rng.randrange(4)));da=','.join(rng.sample(['CN','US','NG'],rng.randrange(4)))
 rows.append({'old':text(a),'new':text(b),'deny_before':db,'deny_after':da})
 py=G.audit_text(text(a),text(b),db,da);s,t=brute(a,b,db.split(','),da.split(','));assert py['summary']==s and py['transitions']==t,(i,py,s,t);expected.append(py)
# Extreme integers cannot be checked by enumerating the address space.
for family, m in [(4,2**32-1),(6,2**128-1)]:
 a,b=[(0,m,'US')],[(0,m-1,'US'),(m,m,'CN')];rows.append({'old':text(a),'new':text(b),'deny_after':'CN','family':family});expected.append(G.audit_text(text(a),text(b),'','CN',family))
for family in [4,6]:
 p=R/f'examples/vendor-ipv{family}.csv'
 if p.exists():
  s=p.read_text();rows.append({'old':s,'new':s,'family':family});expected.append(G.audit_text(s,s,family=family))
p=subprocess.run(['node',str(R/'tools/node_audit.cjs')],input='\n'.join(json.dumps(r)for r in rows)+'\n',text=True,capture_output=True,check=True)
actual=[json.loads(line)for line in p.stdout.splitlines()];assert len(actual)==len(expected)
for i,(a,b)in enumerate(zip(actual,expected)):
 for k in ['summary','transitions','status','policy','details','changed_intervals','traffic','details_truncated']:assert a[k]==b[k],(i,k,a,b)
report={'status':'passed','seed':20260907,'enumerated_small_domain_cases':500,'cross_language_cases':len(rows),'boundary_cases':2,'method':'Separate brute-force 64-address oracle, Python streaming engine, JS BigInt engine. Synthetic cases except unchanged official vendor samples.','vendor_sample_self_comparisons':len(rows)-502}
(R/'evidence/parity.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
