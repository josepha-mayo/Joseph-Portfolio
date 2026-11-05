"""One normal browser form attempt. Never solve or bypass human verification."""
from pathlib import Path
from datetime import datetime,timezone
from urllib.request import urlopen
import os,json,re,time,hashlib
from playwright.sync_api import sync_playwright
R=Path('public/geodrift');E=R/'evidence';E.mkdir(exist_ok=True)
record=E/'contest-form.json'
if record.exists():
 old=json.loads(record.read_text())
 if old.get('submit_clicked') or old.get('post_responses'): raise SystemExit('A prior attempt exists; inspect it manually rather than risk a duplicate.')
verified=json.loads((E/'public-verification.json').read_text());assert verified['status']=='passed'
base=verified['base_url'];repo='https://github.com/josepha-mayo/Joseph-Portfolio/tree/geodrift-entry-preview-20260907/public/geodrift'
name='Joseph Ayanda';email='ayandajoseph390@gmail.com'
report={'status':'not_submitted','form_url':'https://contest.ip2location.com/submission','started_at':datetime.now(timezone.utc).isoformat(),'submit_clicked':False,'submission_confirmed':False,'post_responses':[],'human_verification_interacted_with':False,'public_source':repo,'public_app':base+'/index.html'}
def redacted(text):
 return text.replace(email,'[entrant email]').replace(name,'[entrant name]')
try:
 # Read only the contact address the organizer publicly publishes.
 html=urlopen('https://contest.ip2location.com/',timeout=30).read().decode()
 contacts=[]
 for value in re.findall(r'data-cfemail=[\"\']([0-9a-fA-F]+)',html):
  data=bytes.fromhex(value)
  decoded=bytes(x^data[0] for x in data[1:]).decode('utf-8')
  if decoded.endswith('@ip2location.com'):contacts.append(decoded)
 contacts += re.findall(r'mailto:([^\"\'>\s]+@ip2location\.com)',html)
 report['published_contact_addresses']=sorted(set(contacts))
 with sync_playwright() as p:
  browser=p.chromium.launch(headless=True)
  context=browser.new_context(viewport={'width':1280,'height':900})
  page=context.new_page()
  def response(r):
   if r.request.method=='POST' and r.url.startswith('https://contest.ip2location.com/'):
    report['post_responses'].append({'url':r.url.split('?')[0],'status':r.status})
  page.on('response',response)
  page.goto(report['form_url'],wait_until='domcontentloaded',timeout=45000)
  fields={
   'name':name,'email':email,'project_title':'GeoDrift: Rehearse Geolocation Database Updates',
   'short_desc':'An offline IP2Location CSV release-rehearsal tool. It compares country snapshots and access policies, finds exact IPv4/IPv6 decision changes and lost coverage, and replays aggregate request counts before rollout. Includes a browser worker app and streaming Python CLI. No firewall changes or network probes.',
   'github_link':repo,
   'message':'Working app: '+base+'/index.html\nOriginal MIT-licensed code developed with substantial AI assistance on September 7, 2026. The native IP2Location CSV layout is a core runtime input. Official reference samples retain their MIT notice; the example update and request counts are explicitly synthetic. Source includes setup instructions and executed test evidence. No vendor error, customer incident or social-media engagement is claimed. The surrounding portfolio is not part of this entry. Please advise whether following all three social accounts is mandatory for eligibility; those follows have not been completed through this assistant.',
   'other':'AI-assisted web research of programming contests'
  }
  for key,value in fields.items():
   target=page.locator('[name="'+key+'"]')
   if key=='other':continue
   target.fill(value)
  page.locator('[name="source"]').select_option('Others')
  page.locator('[name="other"]').fill(fields['other'])
  page.locator('[name="agreed"]').check()
  report['fields_filled']=list(fields)+['source','agreed']
  # A normal submit click may initiate the site's automatic verification.
  # Do not click, solve, suppress or inject a response into any challenge.
  page.get_by_role('button',name='Submit',exact=True).click(timeout=15000)
  report['submit_clicked']=True
  messages=[]
  for _ in range(15):
   page.wait_for_timeout(3000)
   text=page.locator('body').inner_text()
   matched=re.search(r'[^\n]*(?:successfully submitted|submission (?:has been |was )?(?:received|successful)|thank you for (?:your )?submission|project (?:has been |was )?submitted)[^\n]*',text,re.I)
   if matched and report['post_responses']:
    report.update(status='server_confirmation_visible',submission_confirmed=True,confirmation=redacted(matched.group(0)));break
   messages=page.locator('.alert, .modal-body, [role="alert"]').all_text_contents()
  if not report['submission_confirmed']:
   report['messages']=[redacted(x[:2000]) for x in messages if x.strip()]
   report['challenge_frames_present']=any('challenges.cloudflare.com' in f.url for f in page.frames)
   report['status']='confirmation_not_observed' if report['post_responses'] else 'no_submission_post_observed'
  report['final_url']=page.url.split('?')[0]
  browser.close()
except Exception as exc:
 report.update(status='attempt_incomplete',error=redacted(str(exc)[:2000]))
finally:
 report['finished_at']=datetime.now(timezone.utc).isoformat();record.write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
