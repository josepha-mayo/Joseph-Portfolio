"""Bounded document parsing. Corpus Python is read, never imported or executed.

Office files are read as OOXML; formulas need an existing cached value. The
image reader is dependency injected and must use genuine vision in deployment.
"""
from __future__ import annotations
import ast
import csv
import hashlib
import io
import json
import os
import re
import stat
import zipfile
from dataclasses import asdict, dataclass, field
from pathlib import Path, PurePosixPath
from typing import Callable
import xml.etree.ElementTree as ET

MAX_FILE_BYTES = 64 * 1024 * 1024
MAX_XML_BYTES = 32 * 1024 * 1024
MAX_ARCHIVE_BYTES = 192 * 1024 * 1024
MAX_ROWS = 100_000
MAX_TEXT = 12_000_000
SUPPORTED = {'.pdf', '.docx', '.xlsx', '.csv', '.txt', '.log', '.py', '.md', '.png', '.jpg', '.jpeg'}
W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
S = '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'
R = '{http://schemas.openxmlformats.org/officeDocument/2006/relationships}'

@dataclass
class Chunk:
    source: str
    locator: str
    text: str
    fields: dict[str, str] = field(default_factory=dict)
    context: str = ''
    kind: str = 'text'
    cid: str = ''

    def __post_init__(self):
        self.text = self.text.strip()
        if not self.cid:
            self.cid = hashlib.sha256((self.source+'\0'+self.locator+'\0'+self.text).encode()).hexdigest()[:24]

    def dict(self):
        return asdict(self)


def clean(value) -> str:
    return re.sub(r'\s+', ' ', str('' if value is None else value)).strip()


def xml(z: zipfile.ZipFile, name: str) -> ET.Element:
    info = z.getinfo(name)
    if info.file_size > MAX_XML_BYTES:
        raise ValueError('oversized XML part')
    data = z.read(name)
    if b'<!DOCTYPE' in data.upper() or b'<!ENTITY' in data.upper():
        raise ValueError('document type declarations are not supported')
    return ET.fromstring(data)


def archive(path: Path):
    z = zipfile.ZipFile(path)
    if len(z.infolist()) > 10_000 or sum(x.file_size for x in z.infolist()) > MAX_ARCHIVE_BYTES:
        z.close()
        raise ValueError('oversized archive')
    return z


def row_chunks(rows, source: str, locator: str, context: str = '') -> list[Chunk]:
    """Carry column headers into every row; blank rows delimit table sections."""
    out, headers = [], None
    for i, row in enumerate(rows, 1):
        if i > MAX_ROWS:
            raise ValueError('table exceeds row budget')
        cells = [clean(x) for x in row]
        if not any(cells):
            headers = None
            continue
        if headers is None:
            # A title row does not become a one-column schema for the next table.
            if sum(bool(x) for x in cells) < 2:
                context = clean(context + ' ' + ' '.join(cells))[-2000:]
                if any(cells): out.append(Chunk(source, f'{locator}:row{i}', ' '.join(cells), context=context))
                continue
            headers = [x or f'column{j+1}' for j, x in enumerate(cells)]
            continue
        if cells == headers:
            continue
        fields = {}
        for j, v in enumerate(cells):
            h = headers[j] if j < len(headers) else f'column{j+1}'
            # Keep duplicate column names distinct rather than silently overwrite.
            if h in fields: h = f'{h} [{j+1}]'
            fields[h] = v
        text = '\n'.join(f'{k}: {v}' for k, v in fields.items() if v)
        if text:
            out.append(Chunk(source, f'{locator}:row{i}', text, fields, context, 'row'))
    return out


def kv_fields(text: str) -> dict[str, str]:
    result = {}
    for line in text.splitlines():
        m = re.match(r'^\s*([A-Za-z][A-Za-z0-9 _#()/.-]{0,75})\s*:\s*(.{1,300})$', line)
        if m: result[m[1].strip()] = m[2].strip()
    # Log-style k=v including quoted values with spaces.
    for m in re.finditer(r'\b([A-Za-z][A-Za-z0-9_]*)=("[^"\n]*"|\'[^\'\n]*\'|[^\s;]+)', text):
        result[m[1]] = m[2].strip('"\'')
    return result


def text_chunks(text: str, source: str, locator: str = 'text', context: str = '') -> list[Chunk]:
    if len(text) > MAX_TEXT: raise ValueError('text budget exceeded')
    out = []
    # Logs must not merge unrelated incidents into a single citation proof.
    blocks = text.splitlines() if Path(source).suffix == '.log' else re.split(r'\n\s*\n', text)
    for i, block in enumerate(blocks):
        if not block.strip(): continue
        pieces = [block]
        if Path(source).suffix != '.log':
            # A plain-text/PDF paragraph can contain several literal product
            # records without blank lines. Keeping them in one chunk makes
            # scope ambiguous and also lets duplicate key/value fields
            # overwrite each other. Split only at the second and later explicit
            # Product/Model/Device header; preserve any heading/prefix with the
            # first record and never synthesize or summarize source text.
            lines = block.splitlines()
            starts = [n for n,line in enumerate(lines)
                      if re.match(r'^\s*(?:product|model|device)\s*:\s*\S', line, re.I)]
            if len(starts) > 1:
                cuts = starts[1:]
                pieces=[]; begin=0
                for end in cuts:
                    part='\n'.join(lines[begin:end])
                    if part.strip(): pieces.append(part)
                    begin=end
                part='\n'.join(lines[begin:])
                if part.strip(): pieces.append(part)
        for piece_no, piece in enumerate(pieces):
            for j in range(0, len(piece), 3500):
                part = piece[max(0, j-180):j+3500]
                suffix = f'{i+1}.{piece_no+1}.{j}' if len(pieces)>1 else f'{i+1}.{j}'
                out.append(Chunk(source, f'{locator}:{suffix}', part, kv_fields(part), context))
    return out


def docx_table_rows(table) -> list[list[str]]:
    """Expand OOXML grid spans and carry only genuine vertical-merge scope.

    Word stores a vertically merged continuation as an empty cell with vMerge,
    so flattening text naively loses the entity/key on later rows. Horizontal
    grid spans also need placeholder columns or every later field shifts left.
    """
    rows=[]; vertical={}
    for row in table.findall(W+'tr'):
        cells=[]; col=0
        for cell in row.findall(W+'tc'):
            props=cell.find(W+'tcPr')
            span=1
            merge=None
            if props is not None:
                grid=props.find(W+'gridSpan')
                if grid is not None:
                    raw=grid.attrib.get(W+'val','1')
                    if not raw.isdigit(): raise ValueError('invalid Word table grid span')
                    span=int(raw)
                    if not 1 <= span <= 512: raise ValueError('Word table grid span out of bounds')
                merge=props.find(W+'vMerge')
            if col+span>512: raise ValueError('Word table too wide')
            text=' '.join(x.text or '' for x in cell.iter(W+'t')).strip()
            if merge is not None:
                state=merge.attrib.get(W+'val','continue').casefold()
                if state=='restart':
                    for c in range(col,col+span): vertical[c]=text
                elif state in {'continue',''}:
                    if not text:
                        inherited={vertical.get(c,'') for c in range(col,col+span)}
                        inherited.discard('')
                        if len(inherited)==1:text=next(iter(inherited))
                else:
                    raise ValueError('unsupported Word vertical merge state')
            else:
                for c in range(col,col+span): vertical.pop(c,None)
            cells.append(text)
            cells.extend(['']*(span-1))
            col += span
        rows.append(cells)
    return rows


def parse_docx(path: Path, source: str) -> list[Chunk]:
    out, context = [], ''
    with archive(path) as z:
        root = xml(z, 'word/document.xml')
        body = root.find(W+'body')
        if body is None: return []
        for i, item in enumerate(body):
            if item.tag == W+'p':
                t = ''.join(x.text or '' for x in item.iter(W+'t'))
                if t.strip():
                    out += text_chunks(t, source, f'paragraph{i+1}', context)
                    # Preserve nearby document/section headings, not arbitrary prior rows.
                    if len(t) < 220: context = (context + '\n' + t)[-1400:]
            elif item.tag == W+'tbl':
                out += row_chunks(docx_table_rows(item), source, f'table{i+1}', context)
    return out


def column_index(ref: str) -> int:
    letters = re.match(r'[A-Za-z]+', ref)
    if not letters: raise ValueError('invalid cell reference')
    n = 0
    for c in letters[0].upper(): n = n*26 + ord(c)-64
    if n > 16384: raise ValueError('invalid column')
    return n-1


def parse_xlsx(path: Path, source: str) -> list[Chunk]:
    out = []
    with archive(path) as z:
        strings = []
        if 'xl/sharedStrings.xml' in z.namelist():
            strings = [''.join(x.text or '' for x in e.iter(S+'t'))
                       for e in xml(z, 'xl/sharedStrings.xml').findall(S+'si')]
        rels = {x.attrib.get('Id'): x.attrib.get('Target','')
                for x in xml(z, 'xl/_rels/workbook.xml.rels')
                if x.attrib.get('TargetMode') != 'External'}
        styles=[]; custom_formats={}
        if 'xl/styles.xml' in z.namelist():
            st=xml(z,'xl/styles.xml')
            custom_formats={int(x.attrib['numFmtId']):x.attrib.get('formatCode','') for x in st.iter(S+'numFmt')}
            xfs=st.find(S+'cellXfs')
            if xfs is not None: styles=[int(x.attrib.get('numFmtId','0')) for x in xfs]
        workbook = xml(z, 'xl/workbook.xml')
        for sh in workbook.iter(S+'sheet'):
            target = rels.get(sh.attrib.get(R+'id'), '')
            if not target: continue
            name = target.lstrip('/') if target.startswith('/') else 'xl/' + target
            import posixpath
            name = posixpath.normpath(name)
            if not name.startswith('xl/'): continue
            tree = xml(z, name)
            rows = []
            for r in tree.iter(S+'row'):
                rownum = int(r.attrib.get('r',len(rows)+1))
                if rownum > MAX_ROWS or rownum <= len(rows): raise ValueError('invalid or oversized sparse row index')
                while len(rows)<rownum-1: rows.append([])
                row = []
                for cell in r.findall(S+'c'):
                    idx = column_index(cell.attrib.get('r','A1'))
                    if idx >= 512: raise ValueError('table too wide')
                    while len(row) <= idx: row.append('')
                    v = cell.find(S+'v')
                    raw = v.text if v is not None and v.text is not None else ''
                    if cell.attrib.get('t') == 's':
                        raw = strings[int(raw)] if raw else ''
                    elif cell.attrib.get('t') == 'inlineStr':
                        raw = ''.join(t.text or '' for t in cell.iter(S+'t'))
                    # Never execute formulas or pretend a missing formula cache is zero.
                    if cell.find(S+'f') is not None and v is None: raw = ''
                    if cell.attrib.get('t')=='e': raw=''
                    style=int(cell.attrib.get('s','0'))
                    fmt=custom_formats.get(styles[style],'') if style<len(styles) else ''
                    if raw and re.fullmatch(r'0{2,32}',fmt) and re.fullmatch(r'\d+',raw): raw=raw.zfill(len(fmt))
                    row[idx] = raw
                rows.append(row)
            # Fill genuine vertically merged scope cells only. Blank ordinary cells stay blank.
            for merged in tree.iter(S+'mergeCell'):
                a, _, b = merged.attrib.get('ref','').partition(':')
                if not a or not b: continue
                ac, bc = column_index(a), column_index(b)
                ar, br = int(re.search(r'\d+', a)[0])-1, int(re.search(r'\d+', b)[0])-1
                if ac == bc and 0 <= ar < len(rows) and br < len(rows) and ac < len(rows[ar]):
                    value = rows[ar][ac]
                    for rr in range(ar+1, br+1):
                        while len(rows[rr]) <= ac: rows[rr].append('')
                        rows[rr][ac] = value
            out += row_chunks(rows, source, 'sheet:'+sh.attrib.get('name',''), sh.attrib.get('name',''))
    return out


def literal_default(n: ast.AST):
    """Accept only scalar literals and a documented getenv fallback, never eval."""
    if isinstance(n, ast.Constant) and type(n.value) in (str, int, float, bool):
        return str(n.value)
    if isinstance(n, ast.UnaryOp) and isinstance(n.op, ast.USub) and isinstance(n.operand, ast.Constant) and type(n.operand.value) in (int,float):
        return str(-n.operand.value)
    if isinstance(n, ast.Call):
        if isinstance(n.func, ast.Name) and n.func.id in {'int','float','str'} and len(n.args) == 1:
            return literal_default(n.args[0])
        if isinstance(n.func, ast.Attribute) and isinstance(n.func.value, ast.Name) and n.func.value.id == 'os' and n.func.attr == 'getenv' and len(n.args) == 2:
            return literal_default(n.args[1])
    return None


def parse_python(path: Path, source: str) -> list[Chunk]:
    text = path.read_text(encoding='utf-8-sig')
    if len(text) > 1_000_000: raise ValueError('code parsing budget exceeded')
    tree = ast.parse(text)
    out = text_chunks(text, source)
    nodes = list(ast.walk(tree))
    if len(nodes) > 50_000: raise ValueError('AST budget exceeded')
    for node in nodes:
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            value = literal_default(node.value) if node.value else None
            for t in targets:
                if isinstance(t, ast.Name) and value is not None:
                    snippet = ast.get_source_segment(text, node) or ''
                    out.append(Chunk(source, f'constant:{t.id}:{node.lineno}', snippet,
                                     {'parameter': t.id, 'value': value}, 'Static literal/default, not runtime state', 'code'))
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            positional = node.args.posonlyargs + node.args.args
            defaults = list(zip(positional[-len(node.args.defaults):], node.args.defaults)) if node.args.defaults else []
            defaults += list(zip(node.args.kwonlyargs, node.args.kw_defaults))
            for arg, default in defaults:
                value = literal_default(default) if default is not None else None
                if value is not None:
                    out.append(Chunk(source, f'argument:{node.name}.{arg.arg}:{node.lineno}',
                                     ast.get_source_segment(text, node)[:2500],
                                     {'parameter': arg.arg, 'value': value, 'function': node.name}, '', 'code'))
    return out


def parse_pdf(path: Path, source: str) -> list[Chunk]:
    import fitz
    out = []
    with fitz.open(path) as doc:
        if doc.needs_pass: raise PermissionError('encrypted PDF')
        if len(doc) > 1000: raise ValueError('PDF page budget exceeded')
        for i, page in enumerate(doc):
            text = page.get_text(sort=True)
            out += text_chunks(text, source, f'page{i+1}', '')
            # Preserve genuine drawn table structure rather than flattening columns.
            try:
                tables = page.find_tables().tables
                for j, table in enumerate(tables):
                    out += row_chunks(table.extract(), source, f'page{i+1}:table{j+1}', text[:400])
            except (ValueError, RuntimeError, AttributeError):
                pass
    return out


def parse_file(path: Path, root: Path) -> list[Chunk]:
    root, path = root.resolve(), path.absolute()
    if path.is_symlink() or not path.resolve().is_relative_to(root):
        raise PermissionError('outside corpus or symbolic link')
    info = path.stat()
    if not stat.S_ISREG(info.st_mode): raise ValueError('not a regular file')
    if not info.st_mode & 0o444: raise PermissionError('no readable mode bits')
    if info.st_size > MAX_FILE_BYTES: raise ValueError('file size budget exceeded')
    source = path.relative_to(root).as_posix()
    ext = path.suffix.lower()
    if ext not in SUPPORTED: raise ValueError('unsupported format')
    if ext in {'.png','.jpg','.jpeg'}: raise RuntimeError('vision parser required')
    if ext == '.pdf': return parse_pdf(path, source)
    if ext == '.docx': return parse_docx(path, source)
    if ext == '.xlsx': return parse_xlsx(path, source)
    if ext == '.py': return parse_python(path, source)
    text = path.read_text(encoding='utf-8-sig', errors='replace')
    if ext == '.csv':
        try: dialect = csv.Sniffer().sniff(text[:8192], delimiters=',;\t|')
        except csv.Error: dialect = csv.excel
        return row_chunks(csv.reader(io.StringIO(text), dialect), source, 'csv')
    return text_chunks(text, source)

if __name__ == '__main__':
    import sys
    try:
        import contextlib
        with contextlib.redirect_stdout(sys.stderr):
            chunks = parse_file(Path(sys.argv[1]), Path(sys.argv[2]))
        print(json.dumps({'chunks': [x.dict() for x in chunks]}))
    except Exception as e:
        print(json.dumps({'error': type(e).__name__, 'detail': str(e)[:240]}))
        sys.exit(2)