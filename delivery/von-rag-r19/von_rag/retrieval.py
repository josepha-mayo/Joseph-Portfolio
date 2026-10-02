"""Disk-backed lexical retrieval and identifier joins with source provenance."""
from __future__ import annotations
import collections
import hashlib
import json
import math
import os
from pathlib import Path
import re
import sqlite3
import subprocess
import sys
import tempfile
import time
from .parsers import Chunk, SUPPORTED, MAX_FILE_BYTES, kv_fields

STOP = set('a an the of for to in on at by what which is are was were does do did be been being and or that this it its as from with when where how has have had can should would could enter enters per please tell me give many much all then shown according reported shows says set'.split())
ALIASES = {'maximum':'max','junction':'junction','temperature':'temperature','thermal':'thermal',
 'sampling':'sampling','samples':'sampling','sample':'sampling','quarter':'quarter',
 'release':'firmware','released':'firmware','releases':'firmware','version':'version',
 'fixed':'fixed','fixes':'fixed','fix':'fixed','resolved':'fixed','resolution':'fixed',
 'assembly':'assembly','replaceable':'replaceable','replacement':'replaceable',
 'seconds':'seconds','second':'seconds','secs':'seconds','s':'seconds',
 'incidents':'incident','engages':'engage','triggered':'engage','throttling':'throttle'}


def tokens(text):
    words = re.findall(r'[a-z0-9]+', str(text).casefold())
    return [ALIASES.get(w,w) for w in words if w not in STOP]


def identifiers(text):
    raw = re.findall(r'(?<![\w])(?:[A-Za-z]{1,32}[-_][A-Za-z0-9][A-Za-z0-9_-]*|[A-Za-z]{1,24}\d{2,}[A-Za-z0-9_-]*)(?![\w])', text)
    return {re.sub(r'[-_]', '', x).upper() for x in raw
            if any(c.isdigit() for c in x) and not re.fullmatch(r'FY\d+',x,re.I)}


def retired(source, text=''):
    return bool(
        re.search(r'(?:^|[/_.-])(withdrawn|superseded|obsolete|deprecated|archived)(?:[/_.-]|$)', source, re.I)
        or re.search(r'(?im)^\s*status\s*:\s*(withdrawn|superseded|obsolete|deprecated|archived)\b', text)
        or re.search(r'(?im)^\s*(?:withdrawn|superseded|obsolete|deprecated|archived|do\s+not\s+use)\b\s*(?:[-:\u2014]|$)', text)
    )



def document_retirement_marker(chunk):
    """True only for a document-level retirement marker, not a retired record."""
    text = str(chunk.text)
    if chunk.kind == 'row' or not retired('', text):
        return False
    fields = kv_fields(text)
    if not fields:
        return True
    keys = {re.sub(r'[^a-z0-9]', '', str(k).casefold()) for k in fields}
    # A status block is document-wide unless it also declares an entity record.
    # This preserves a withdrawn status plus arbitrary document metadata while
    # preventing a retired Part/SKU/Asset record from poisoning live siblings.
    entity_keys = {
        'product', 'model', 'device', 'partnumber', 'partno', 'pn', 'sku',
        'asset', 'component', 'serialnumber', 'item', 'assembly', 'module'
    }
    return not bool(keys & entity_keys)


_REVISION_SUFFIX = re.compile(
    r'(?i)(?:^|[_ .-])(?:rev(?:ision)?|r|v|version)[_ .-]?([0-9]+(?:\.[0-9]+)*)([a-z]?)([0-9]*)$')


def revision_family(source: str):
    path = Path(source)
    match = _REVISION_SUFFIX.search(path.stem)
    if match is None:
        return None
    prefix = path.stem[:match.start()].rstrip('_ .-').casefold()
    if not prefix:
        return None
    letter = ord(match.group(2).casefold()) - 96 if match.group(2) else 0
    tail = int(match.group(3)) if match.group(3) else 0
    family = (path.parent / (prefix + path.suffix.casefold())).as_posix()
    parts=tuple(int(n) for n in match.group(1).split('.'))
    while len(parts)>1 and parts[-1]==0: parts=parts[:-1]
    return family, (parts, letter, tail)


def pdf_render_scale(width, height, *, pixel_limit=4_000_000, edge_limit=4096):
    """Bound dimensions before rasterization, including extreme page geometry."""
    width,height=float(width),float(height)
    if not all(math.isfinite(v) and v > 0 for v in (width,height)):
        raise ValueError('invalid PDF page geometry')
    scale=min(1.5, math.sqrt(pixel_limit/width/height), edge_limit/width, edge_limit/height)
    if not math.isfinite(scale) or scale <= 0:
        raise ValueError('unrenderable PDF geometry')
    # Ceil rounding may otherwise cross the target by one row or column.
    while math.ceil(width*scale)*math.ceil(height*scale) > pixel_limit:
        scale *= .999
    return scale


def build_index(root: Path, output: Path, *, vision=None, deadline_seconds=540, file_timeout=60) -> dict:
    root, output = root.resolve(strict=True), output.absolute()
    if not root.is_dir(): raise ValueError('corpus must be a directory')
    if output.is_relative_to(root): raise ValueError('index must be outside corpus')
    output.parent.mkdir(parents=True, exist_ok=True)
    start = time.monotonic()
    fd, tmp = tempfile.mkstemp(prefix='.von-index-', suffix='.sqlite', dir=output.parent)
    os.close(fd)
    con = sqlite3.connect(tmp)
    skipped, files, nchunks = [], [], 0
    document_status = {}
    try:
        con.executescript('''
        CREATE TABLE meta(key TEXT PRIMARY KEY,value TEXT NOT NULL);
        CREATE TABLE chunks(cid TEXT PRIMARY KEY,source TEXT,locator TEXT,text TEXT,fields TEXT,context TEXT,kind TEXT,retired INTEGER);
        CREATE VIRTUAL TABLE lex USING fts5(cid UNINDEXED,body,tokenize='unicode61');
        CREATE TABLE entities(entity TEXT,cid TEXT,PRIMARY KEY(entity,cid));
        CREATE INDEX entity_lookup ON entities(entity);
        ''')
        for directory, dirs, names in os.walk(root, followlinks=False):
            dirs[:] = sorted(d for d in dirs if not (Path(directory)/d).is_symlink())
            for name in sorted(names):
                p = Path(directory)/name
                rel = p.relative_to(root).as_posix()
                if time.monotonic()-start >= deadline_seconds:
                    raise TimeoutError('index startup budget exceeded')
                try:
                    info = p.lstat()
                    if p.is_symlink() or not p.is_file() or not info.st_mode & 0o444:
                        raise PermissionError('not an authorized readable regular file')
                    if info.st_size > MAX_FILE_BYTES: raise ValueError('oversized file')
                    file_deadline=min(start+deadline_seconds, time.monotonic()+file_timeout)
                    ext = p.suffix.lower()
                    if ext not in SUPPORTED: raise ValueError('unknown format')
                    if ext in {'.png','.jpg','.jpeg'}:
                        if vision is None: raise RuntimeError('image requires vision backend; not silently treated as read')
                        from von_read.views import load_image
                        with load_image(p) as im:
                            text = vision(im, deadline=file_deadline)
                        if time.monotonic() >= file_deadline: raise TimeoutError('late image transcription')
                        chunks = [Chunk(rel, 'vision', text, kv_fields(text), '', 'vision')]
                    else:
                        env = dict(os.environ, OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1')
                        run = subprocess.run([sys.executable,'-m','von_rag.parsers',str(p),str(root)],
                            text=True, capture_output=True, timeout=max(.001, file_deadline-time.monotonic()), env=env)
                        data = json.loads(run.stdout)
                        if run.returncode: raise ValueError(data.get('error','parse failed')+': '+data.get('detail',''))
                        chunks = [Chunk(**x) for x in data['chunks']]
                        # Sparse/image-only PDF pages need the same local vision
                        # backend used for standalone images. Text-rich pages stay
                        # on the ordinary parser path to avoid extra model calls.
                        if ext == '.pdf' and vision is not None:
                            import fitz
                            from PIL import Image
                            page_chars = {}
                            for c in chunks:
                                match = re.match(r'^page(\d+)', c.locator)
                                if match:
                                    page_no = int(match.group(1))
                                    page_chars[page_no] = page_chars.get(page_no, 0) + len(c.text.strip())
                            vision_pages = 0
                            with fitz.open(p) as pdf:
                                if pdf.needs_pass:
                                    raise ValueError('encrypted PDF')
                                if len(pdf) > 1000:
                                    raise ValueError('PDF page budget exceeded')
                                for page_no, page in enumerate(pdf, 1):
                                    if page_chars.get(page_no, 0) >= 40:
                                        continue
                                    if not page.get_images(full=True):
                                        continue
                                    if vision_pages >= 64:
                                        raise ValueError('PDF vision page budget exceeded')
                                    if time.monotonic() >= file_deadline:
                                        raise TimeoutError('PDF file budget exceeded')
                                    scale=pdf_render_scale(page.rect.width,page.rect.height)
                                    pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
                                    image = Image.frombytes('RGB', (pix.width, pix.height), pix.samples)
                                    try:
                                        if time.monotonic() >= file_deadline:
                                            raise TimeoutError('PDF render exhausted file budget')
                                        visual = vision(image, deadline=file_deadline)
                                        if time.monotonic() >= file_deadline:
                                            raise TimeoutError('late PDF transcription')
                                    finally:
                                        image.close()
                                    vision_pages += 1
                                    if visual and str(visual).strip():
                                        value = str(visual)
                                        chunks.append(Chunk(rel, f'page{page_no}:vision', value,
                                                            kv_fields(value), '', 'vision'))
                    # Source naming can retire a complete historical document,
                    # while an inline Status applies only to that literal record.
                    # Do not let one withdrawn row hide current rows in the same file.
                    # A retirement marker in the source name always applies to
                    # the whole document. A standalone document-status chunk
                    # (e.g. `Status: withdrawn` before the first record) also
                    # applies globally. Status attached to an explicit
                    # Product/Model/Device record remains record-local.
                    source_retired = retired(rel, '') or any(
                        document_retirement_marker(c) for c in chunks)
                    document_status[rel] = bool(source_retired)
                    file_hash = hashlib.sha256(p.read_bytes()).hexdigest()
                    files.append({'source':rel,'sha256':file_hash,'bytes':info.st_size,'chunks':len(chunks)})
                    for c in chunks:
                        if not c.text: continue
                        chunk_retired = source_retired or retired('', c.text)
                        con.execute('INSERT INTO chunks VALUES(?,?,?,?,?,?,?,?)',
                            (c.cid,c.source,c.locator,c.text,json.dumps(c.fields),c.context,c.kind,int(chunk_retired)))
                        body = ' '.join(tokens(c.source+' '+c.context+' '+c.text))
                        con.execute('INSERT INTO lex VALUES(?,?)',(c.cid,body))
                        for entity in identifiers(c.text+' '+c.context):
                            con.execute('INSERT OR IGNORE INTO entities VALUES(?,?)',(entity,c.cid))
                        nchunks += 1
                except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as e:
                    skipped.append({'source':rel,'reason':str(e)[:260]})
        # Explicit filename revision families prefer the newest eligible sibling
        # for ordinary queries while preserving old revisions for historical mode.
        families = collections.defaultdict(list)
        for item in files:
            parsed = revision_family(item['source'])
            if parsed is not None:
                family, revision = parsed
                families[family].append((revision, item['source']))
        for members in families.values():
            # A newer sibling is eligible only if it actually retained at
            # least one live chunk. A scoped `Status: withdrawn` record in a
            # single-record r2 file must not suppress a valid r1 sibling.
            eligible = [(revision, source) for revision, source in members
                        if con.execute('SELECT 1 FROM chunks WHERE source=? AND retired=0 LIMIT 1',
                                       (source,)).fetchone() is not None]
            if len(eligible) < 2:
                continue
            newest = max(revision for revision, _ in eligible)
            for revision, source in eligible:
                if revision < newest:
                    con.execute('UPDATE chunks SET retired=1 WHERE source=?', (source,))

        if time.monotonic() >= start+deadline_seconds:
            raise TimeoutError('index startup budget exceeded before commit')
        manifest = {'schema':1,'corpus':str(root),'files':files,'skipped':skipped,'chunks':nchunks,
                    'index_seconds':time.monotonic()-start,'images_read':sum(1 for f in files if Path(f['source']).suffix.lower() in {'.png','.jpg','.jpeg'})}
        con.execute('INSERT INTO meta VALUES(?,?)',('manifest',json.dumps(manifest)))
        con.commit(); con.close()
        os.replace(tmp, output)
        return manifest
    except BaseException:
        con.close()
        Path(tmp).unlink(missing_ok=True)
        raise


class Index:
    def __init__(self, path: Path, root: Path | None = None):
        self.con = sqlite3.connect(path.resolve().as_uri()+'?mode=ro', uri=True)
        self.con.row_factory = sqlite3.Row
        m = self.con.execute('SELECT value FROM meta WHERE key=?',('manifest',)).fetchone()
        if not m: raise ValueError('index has no manifest')
        self.manifest = json.loads(m[0])
        if root is not None and str(root.resolve()) != self.manifest['corpus']:
            self.con.close(); raise ValueError('index belongs to a different corpus')

    def close(self): self.con.close()

    def chunk(self, cid):
        r = self.con.execute('SELECT * FROM chunks WHERE cid=?',(cid,)).fetchone()
        if not r: raise KeyError(cid)
        d = dict(r);d['fields']=json.loads(d['fields']);return d

    def search(self, query: str, k=16, *, historical=False):
        ts = list(dict.fromkeys(tokens(query)))[:80]
        if not ts: return []
        expression = ' OR '.join('"'+x.replace('"','""')+'"' for x in ts)
        # Apply retirement eligibility before LIMIT. Otherwise many retired
        # revisions can occupy the entire shortlist and hide every current fact.
        rows = self.con.execute('SELECT c.*,bm25(lex) AS score FROM lex JOIN chunks c ON c.cid=lex.cid WHERE lex MATCH ? AND (? OR c.retired=0) ORDER BY score LIMIT ?', (expression,int(historical),k*4)).fetchall()
        result=[]
        for r in rows:
            d=dict(r);d['fields']=json.loads(d['fields'])
            if not historical and d['retired']: continue
            result.append(d)
            if len(result)>=k: break
        return result

    def expand(self, seeds: list[dict], *, hops=2, max_chunks=48, historical=False, query=None):
        result={c['cid']:c for c in seeds}; frontier=list(result)
        expanded=set()
        qtokens=set(tokens(query or ''))
        qwords=set(re.findall(r'[a-z0-9]+', str(query or '').casefold()))
        wants_log=bool({'log','logs','production','incident'} & qwords)
        hints=set()
        if 'firmware' in qtokens:
            hints |= {'fixedin','fixedversion','firmware','firmwareversion','fixversion','resolvedin'}
        if 'temperature' in qtokens:
            hints |= {'tjmax','tjmin','maxjunctiontemperature','maximumjunctiontemperature',
                      'minjunctiontemperature','minimumjunctiontemperature'}
        if 'price' in qtokens:
            hints |= {'unitprice','price','cost'}
        if 'timeout' in qtokens:
            hints |= {'batchtimeout','defaultbatchtimeout','timeout','batchtimeoutseconds'}
        if 'revision' in qtokens:
            hints |= {'boardrevision','revision','rev'}
        if 'quarter' in qtokens or 'sampling' in qtokens:
            hints |= {'customersamplingquarter','samplingquarter','quarter'}
        if 'part' in qtokens:
            hints |= {'partnumber','replacementpart','partno','pn','sku'}
        if 'error' in qtokens:
            hints |= {'errorcode','error','code'}

        def ref_rank(cid):
            c=self.chunk(cid)
            fields=c.get('fields') or kv_fields(c.get('text',''))
            keys={re.sub(r'[^a-z0-9]','',str(k).casefold()) for k in fields}
            text_tokens=set(tokens(c.get('source','')+' '+c.get('context','')+' '+c.get('text','')))
            score=60*bool(keys & hints) + 3*len(qtokens & text_tokens)
            if wants_log and c.get('source','').lower().endswith('.log'):
                score += 45
            score += 12*bool(identifiers(query or '') & identifiers(c.get('text','')+' '+c.get('context','')))
            return (-score, len(c.get('text','')), c.get('source',''), cid)

        for _ in range(hops):
            next_frontier=[]
            for cid in frontier:
                ids=[r[0] for r in self.con.execute('SELECT entity FROM entities WHERE cid=?',(cid,))]
                for entity in ids:
                    if entity in expanded: continue
                    expanded.add(entity)
                    refs=[r[0] for r in self.con.execute(
                        'SELECT cid FROM entities WHERE entity=? LIMIT 129',(entity,)).fetchall()]
                    if len(refs)>32:
                        if query is None:
                            continue
                        refs=sorted(refs,key=ref_rank)[:32]
                    for other in refs:
                        if other in result: continue
                        c=self.chunk(other)
                        if not historical and c['retired']: continue
                        result[other]=c; next_frontier.append(other)
                        if len(result)>=max_chunks: return list(result.values())
            frontier=next_frontier
        return list(result.values())

    def all(self):
        return [self.chunk(r[0]) for r in self.con.execute('SELECT cid FROM chunks')]
