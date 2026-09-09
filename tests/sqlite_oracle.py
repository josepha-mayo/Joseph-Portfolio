"""Read actual Node-created databases with Python's independent SQLite client."""
import sqlite3,json,hashlib
from pathlib import Path
root=Path(json.loads(Path('evidence/outbox-record.json').read_text())['databaseRoot']);checks=[]
for case in ['before-send','lost-ack']:
 with sqlite3.connect(f'file:{root/case/"receiver.sqlite"}?mode=ro',uri=True)as sink:
  sink.row_factory=sqlite3.Row;tickets={r['key']:dict(r)for r in sink.execute('select * from tickets')}
  assert sink.execute('pragma integrity_check').fetchone()[0]=='ok';checks.append(case+': receiver integrity')
  for lane in ['guard','enqueue-only']:
   with sqlite3.connect(f'file:{root/case/(lane+".sqlite")}?mode=ro',uri=True)as worker:
    worker.row_factory=sqlite3.Row;assert worker.execute('pragma integrity_check').fetchone()[0]=='ok'
    jobs=[dict(r)for r in worker.execute('select * from outbox')];receipts=[dict(r)for r in worker.execute('select * from receipts')]
    for job in jobs:assert hashlib.sha256(job['payload'].encode()).hexdigest()==job['payload_hash']
    for row in receipts:
     assert row['key']in tickets and row['receipt']==tickets[row['key']]['receipt']
    checks.append(case+': '+lane+' payload hashes and receipts bind to receiver rows')
    if lane=='guard':
     if case=='before-send':assert len(jobs)==1 and jobs[0]['state']=='blocked'and len(receipts)==0 and jobs[0]['key']not in tickets
     else:assert len(jobs)==1 and jobs[0]['state']=='acknowledged'and jobs[0]['attempts']==1 and len(receipts)==1 and worker.execute('select count(*) from incidents').fetchone()[0]==1
     checks.append(case+': expected guard effect and latched state')
report={'status':'passed','checks':checks,'count':len(checks),'scope':'Independent Python read-only SQLite integrity, payload hash, receipt join and outcome checks of Node-created local test files.'}
Path('evidence/sqlite-oracle.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
