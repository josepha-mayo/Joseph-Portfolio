import csv, io, json, subprocess, sys, tempfile, unittest
from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R))
import geodrift as G

def doc(rows):
 s=io.StringIO();w=csv.writer(s);w.writerows([a,b,c,'Name, quoted'] for a,b,c in rows);return s.getvalue()

def audit(a,b,db='',da='',family=4,traffic='',limit=1000):return G.audit_text(doc(a),doc(b),db,da,family,traffic,limit)

class Engine(unittest.TestCase):
 def test_identical(self):
  r=audit([(0,9,'US')],[(0,9,'US')]);self.assertEqual(r['status'],'no_decision_change');self.assertEqual(r['summary']['union_addresses'],'10')
 def test_singleton(self):self.assertEqual(audit([(0,0,'US')],[(0,0,'CN')],'','CN')['summary']['decision_changed_addresses'],'1')
 def test_policy_only(self):self.assertEqual(audit([(0,3,'CN')],[(0,3,'CN')],'','CN')['summary']['decision_changed_addresses'],'4')
 def test_country_without_decision(self):
  r=audit([(0,3,'US')],[(0,3,'NG')]);self.assertEqual(r['status'],'no_decision_change');self.assertEqual(r['summary']['country_changed_addresses'],'4')
 def test_removed(self):
  r=audit([(0,3,'US')],[]);self.assertEqual(r['transitions'],{'allow -> review':'4'});self.assertEqual(r['summary']['coverage_lost_addresses'],'4')
 def test_added(self):self.assertEqual(audit([],[(0,3,'US')])['transitions'],{'review -> allow':'4'})
 def test_gaps_excluded(self):self.assertEqual(audit([(1,1,'US'),(9,9,'US')],[])['summary']['union_addresses'],'2')
 def test_crossing(self):self.assertEqual(audit([(0,5,'US')],[(4,9,'CN')],'','CN')['transitions'],{'allow -> deny':'2','allow -> review':'4','review -> deny':'4'})
 def test_touching(self):
  r=audit([(0,4,'US'),(5,9,'CN')],[(0,9,'US')],'CN','CN');self.assertEqual(r['summary']['decision_changed_addresses'],'5');self.assertEqual(r['summary']['coverage_lost_addresses'],'0')
 def test_segmentation_only(self):self.assertEqual(audit([(0,9,'US')],[(0,4,'US'),(5,9,'US')])['details'],[])
 def test_both_empty(self):self.assertEqual(audit([],[])['summary']['union_addresses'],'0')
 def test_unlocated(self):self.assertEqual(audit([(0,9,'-')],[(0,9,'US')])['transitions'],{'review -> allow':'10'})
 def test_unlocated_removed(self):self.assertEqual(audit([(0,9,'-')],[])['status'],'review_required')
 def test_full_ipv6(self):
  m=2**128-1;r=audit([(0,m,'US')],[(0,m,'CN')],'','CN',6);self.assertEqual(r['summary']['decision_changed_addresses'],str(2**128))
 def test_last_ipv6(self):
  m=2**128-1;r=audit([(0,m,'US')],[(0,m-1,'US'),(m,m,'CN')],'','CN',6);self.assertEqual(r['summary']['decision_changed_addresses'],'1')
 def test_overlap(self):
  with self.assertRaises(G.InputError):audit([(0,4,'US'),(4,8,'CN')],[])
 def test_unsorted(self):
  with self.assertRaises(G.InputError):audit([(4,8,'CN'),(0,3,'US')],[])
 def test_reversed(self):
  with self.assertRaises(G.InputError):audit([(4,3,'US')],[])
 def test_wrong_family(self):
  with self.assertRaises(G.InputError):audit([(0,2**32,'US')],[])
 def test_bad_family(self):
  with self.assertRaises(G.InputError):audit([],[],family=5)
 def test_bad_country(self):
  with self.assertRaises(G.InputError):audit([(0,9,'USA')],[])
 def test_header_rejected(self):
  with self.assertRaises(G.InputError):list(G.read_ranges(io.StringIO('ip_from,ip_to,code,name\n')))
 def test_bad_decimal(self):
  with self.assertRaises(G.InputError):list(G.read_ranges(io.StringIO('1e3,5000,US,Name')))
 def test_missing_columns(self):
  with self.assertRaises(G.InputError):list(G.read_ranges(io.StringIO('0,5,US')))
 def test_unclosed_quote(self):
  with self.assertRaises(G.InputError):list(G.read_ranges(io.StringIO('"0,5,US,Name')))
 def test_bom_and_newline_name(self):self.assertEqual(list(G.read_ranges(io.StringIO('\ufeff"0","5","us","A\nB"\r\n'))),[(0,5,'US')])
 def test_extra_columns(self):self.assertEqual(list(G.read_ranges(io.StringIO('0,5,US,Name,Region,City'))),[(0,5,'US')])
 def test_deny_codes(self):self.assertEqual(G.policy(' us,cn; NG us '),frozenset(['US','CN','NG']))
 def test_bad_policy(self):
  with self.assertRaises(G.InputError):audit([],[],'unknown','')
 def test_traffic_inside_outside(self):
  r=audit([(0,4,'US')],[(0,4,'CN')],'','CN',traffic='ip,requests\n0.0.0.0,10\n0.0.0.8,20\n');self.assertEqual(r['traffic']['transitions'],{'allow -> deny':'10','review -> review':'20'})
 def test_traffic_duplicates(self):self.assertEqual(audit([],[],traffic='ip,requests\n1.1.1.1,10\n1.1.1.1,20')['traffic']['requests'],'30')
 def test_traffic_not_exported(self):self.assertNotIn('1.1.1.1',json.dumps(audit([],[],traffic='ip,requests\n1.1.1.1,10')))
 def test_traffic_zero(self):self.assertEqual(audit([],[],traffic='ip,requests\n1.1.1.1,0')['traffic']['requests'],'0')
 def test_ipv6_traffic(self):self.assertEqual(audit([(0,0,'US')],[(0,0,'CN')],'','CN',6,'ip,requests\n::,2')['traffic']['transitions'],{'allow -> deny':'2'})
 def test_bad_traffic(self):
  with self.assertRaises(G.InputError):audit([],[],traffic='ip,requests\n1.1.1.1,-2')
 def test_wrong_traffic_family(self):
  with self.assertRaises(G.InputError):audit([],[],traffic='ip,requests\n::1,2')
 def test_mapped_traffic(self):
  with self.assertRaises(G.InputError):audit([],[],family=6,traffic='ip,requests\n::ffff:1.1.1.1,2')
 def test_scoped_traffic(self):
  with self.assertRaises(G.InputError):audit([],[],family=6,traffic='ip,requests\nfe80::1%eth0,2')
 def test_detail_truncation(self):
  r=audit([(0,4,'US'),(9,12,'NG')],[],limit=1);self.assertTrue(r['details_truncated']);self.assertEqual(r['summary']['changed_addresses'],'9')
 def test_zero_details_totals_complete(self):self.assertEqual(audit([(0,9,'US')],[],limit=0)['summary']['changed_addresses'],'10')
 def test_hash_records(self):self.assertEqual(len(audit([],[])['source_sha256']['before_csv']),64)
 def test_cli_success(self):
  p=subprocess.run([sys.executable,str(R/'geodrift.py'),str(R/'examples/vendor-ipv4.csv'),str(R/'examples/vendor-ipv4.csv'),'--fail-on-risk'],capture_output=True,text=True);self.assertEqual(p.returncode,0);self.assertEqual(json.loads(p.stdout)['status'],'no_decision_change')
 def test_cli_risk(self):
  p=subprocess.run([sys.executable,str(R/'geodrift.py'),str(R/'examples/vendor-ipv4.csv'),str(R/'examples/synthetic-candidate.csv'),'--deny-after','CN','--fail-on-risk'],capture_output=True,text=True);self.assertEqual(p.returncode,3)
 def test_cli_invalid(self):
  p=subprocess.run([sys.executable,str(R/'geodrift.py'),'/nonexistent','/nonexistent'],capture_output=True,text=True);self.assertEqual(p.returncode,2);self.assertEqual(p.stdout,'')
 def test_cli_prevents_overwrite(self):
  p=subprocess.run([sys.executable,str(R/'geodrift.py'),str(R/'examples/vendor-ipv4.csv'),str(R/'examples/vendor-ipv4.csv'),'--json',str(R/'examples/vendor-ipv4.csv')],capture_output=True,text=True);self.assertEqual(p.returncode,2)
 def test_cli_atomic_reports(self):
  with tempfile.TemporaryDirectory() as d:
   j=Path(d)/'r.json';h=Path(d)/'r.html';p=subprocess.run([sys.executable,str(R/'geodrift.py'),str(R/'examples/vendor-ipv4.csv'),str(R/'examples/synthetic-candidate.csv'),'--json',str(j),'--html',str(h)],capture_output=True,text=True);self.assertEqual(p.returncode,0);self.assertEqual(json.loads(j.read_text())['schema'],'geodrift/v1');self.assertIn('GeoDrift',h.read_text())

if __name__=='__main__':unittest.main(verbosity=2)
