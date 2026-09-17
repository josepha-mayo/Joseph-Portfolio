"""Apply the narrow CV-button patch only to the inspected portfolio revision."""
from pathlib import Path
import hashlib
p=Path('src/app/page.tsx')
text=p.read_text()
before='ec209d82df60ec49a08782fb933ed61d349ed57ebcb929ec4a3ffab796895a8b'
after='f9e2cff23b7e031af9c5bcf1e21550593c3cd32713a0811173aa3c797ff345da'
current=hashlib.sha256(text.encode()).hexdigest()
if current==after:
    print('Reviewed CV links already present')
    raise SystemExit(0)
assert current==before,'Portfolio changed: reconcile rather than overwrite newer work'
hero='''                <a href="#contact" className="btn-ghost inline-flex items-center gap-2 px-5 py-3 rounded-md font-medium text-text-secondary hover:text-text-primary no-underline">'''
addition='''                <a href="/Joseph_Ayanda_CV.pdf" download="Joseph_Ayanda_CV.pdf" aria-label="Download CV (PDF, 3 pages)" className="btn-ghost inline-flex items-center gap-2 px-5 py-3 rounded-md font-medium text-text-primary border border-border-subtle hover:border-accent focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-accent no-underline">
                  <i className="fa-solid fa-download text-sm" aria-hidden="true"></i> download cv <span className="text-xs text-text-secondary">PDF</span>
                </a>
'''
nav='''            <li><a href="#contact" className="text-text-secondary hover:text-text-primary text-[15px] font-medium transition-colors">contact</a></li>'''
nav_add='''            <li><a href="/Joseph_Ayanda_CV.pdf" download="Joseph_Ayanda_CV.pdf" aria-label="Download CV (PDF, 3 pages)" className="text-accent hover:text-text-primary text-[15px] font-medium transition-colors focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-accent">cv <i className="fa-solid fa-arrow-down text-xs" aria-hidden="true"></i></a></li>'''
assert text.count(hero)==text.count(nav)==1
text=text.replace(hero,addition+hero).replace(nav,nav+'\n'+nav_add)
assert hashlib.sha256(text.encode()).hexdigest()==after
p.write_text(text)
print('Added two CV anchors; existing portfolio content preserved')
