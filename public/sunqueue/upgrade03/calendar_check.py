#!/usr/bin/env python3
"""Independent Python time calculation and strict reading of exported basic ICS events."""
from pathlib import Path
from datetime import datetime,timezone,timedelta
import json,subprocess,re
R=Path(__file__).resolve().parents[1];E=R/'v03/evidence'
js="""const Q=require('./src/core.js'),S=require('./upgrade03/shift.js'),f=require('./examples/scenario.json');let out=[];for(const offset of [-720,-210,0,60,345,840]){for(const hour of [0,6,23]){const sheet=S.makeSheet(Q.solve(f),{date:'2026-12-31',hour,offsetMinutes:offset});out.push({sheet,ics:S.calendar(sheet,'2026-09-08T12:00:00Z')});}}process.stdout.write(JSON.stringify(out));"""
cases=json.loads(subprocess.check_output(['node','-e',js],cwd=R));count=0
for case in cases:
 text=case['ics'];assert '\n'not in text.replace('\r\n','')
 assert all(len(line.encode('utf-8'))<=75 for line in text.split('\r\n'))
 unfolded=text.replace('\r\n ','');events=unfolded.split('BEGIN:VEVENT\r\n')[1:];sheet=case['sheet'];a=sheet['anchor'];s=sheet['plan']['scenario'];assert len(events)==len(s['jobs'])
 ordered=sorted(s['jobs'],key=lambda j:sheet['plan']['starts'][j['id']])
 start=datetime.fromisoformat(a['date']).replace(tzinfo=timezone(timedelta(minutes=a['offsetMinutes'])))+timedelta(hours=a['hour'])
 for item,j in zip(events,ordered):
  event=item.split('END:VEVENT')[0];values=dict(line.split(':',1)for line in event.strip().split('\r\n'))
  assert values['STATUS']=='TENTATIVE' and values['TRANSP']=='TRANSPARENT'
  t=start+timedelta(hours=sheet['plan']['starts'][j['id']]);u=t+timedelta(hours=j['duration'])
  assert datetime.strptime(values['DTSTART'],'%Y%m%dT%H%M%SZ').replace(tzinfo=timezone.utc)==t.astimezone(timezone.utc)
  assert datetime.strptime(values['DTEND'],'%Y%m%dT%H%M%SZ').replace(tzinfo=timezone.utc)==u.astimezone(timezone.utc)
  assert len(values['UID'])==79 and len(set(values))==len(values)
  count+=1
assert 'VALARM'not in unfolded and 'ATTENDEE'not in unfolded
report={'status':'passed','date_offset_combinations':len(cases),'events_checked':count,'method':'Independent Python datetime mapping and strict basic ICS content reader. Not a general standards validator or a real calendar-client import.'};E.mkdir(exist_ok=True);(E/'calendar-check.json').write_text(json.dumps(report,indent=2));print(report)
