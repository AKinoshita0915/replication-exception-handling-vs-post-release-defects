#!/usr/bin/env python3
"""Independent check of detect.py (no tree-sitter) and audit of unflagged catch blocks.

Usage: python3 crosscheck.py SRC_DIR COUNTS_DIR RESULTS_DIR
Writes RESULTS_DIR/crosscheck.txt. Uses only the standard library.
"""
import csv, re, sys, collections

SRC, COUNTS, RES = sys.argv[1:4]
LIBS = {'Lang': ('commons-lang', 'lang'), 'Codec': ('commons-codec', 'codec'),
        'Compress': ('commons-compress', 'compress'), 'Gson': ('gson', 'gson')}

def clean(s):
    """Blank out comments and string/char literals, keeping offsets and newlines."""
    out, i, n = [], 0, len(s)
    while i < n:
        c = s[i]
        if s.startswith('//', i):
            j = s.find('\n', i); j = n if j < 0 else j
            out.append(' ' * (j - i)); i = j
        elif s.startswith('/*', i):
            j = s.find('*/', i + 2); j = n if j < 0 else j + 2
            out.append(re.sub(r'[^\n]', ' ', s[i:j])); i = j
        elif s.startswith('"""', i):
            j = s.find('"""', i + 3); j = n if j < 0 else j + 3
            seg = s[i:j]; out.append('"' + re.sub(r'[^\n]', ' ', seg[1:-1]) + '"'); i = j
        elif c in '"\'':
            j = i + 1
            while j < n and s[j] != c:
                j += 2 if s[j] == '\\' else 1
            j = min(j + 1, n); seg = s[i:j]
            out.append(c + ' ' * (len(seg) - 2) + c if len(seg) >= 2 else seg); i = j
        else:
            out.append(c); i += 1
    return ''.join(out)

def match(s, i, o, c):
    d = 0
    for j in range(i, len(s)):
        if s[j] == o: d += 1
        elif s[j] == c:
            d -= 1
            if d == 0: return j
    return -1

LOG = re.compile(r'^(?:[\w$.]*\.)?(?:log|logger|logging)\w*\.\w+\s*\(|^[\w$.]*(?:LOG|LOGGER)\w*\.\w+\s*\('
                 r'|^System\.(?:out|err)\.(?:print|println|printf|format)\s*\(|^[\w$]+\.printStackTrace\s*\(\s*\)$', re.I)
blocks = {}
for lib, (folder, pre) in LIBS.items():
    for rel in [l.strip() for l in open(f'{COUNTS}/{pre}_catch_files.txt') if l.strip()]:
        raw = open(f'{SRC}/{folder}/{rel}', encoding='utf8', errors='replace').read()
        s = clean(raw)
        for m in re.finditer(r'\bcatch\s*\(', s):
            p0 = m.end() - 1; p1 = match(s, p0, '(', ')')
            if p1 < 0: continue
            b0 = s.find('{', p1); b1 = match(s, b0, '{', '}')
            param = re.sub(r'\bfinal\b', '', re.sub(r'@\w+(\([^)]*\))?', '', s[p0 + 1:p1]))
            tp = param.rsplit(None, 1)[0] if param.split() else ''
            types = [t.strip().split('.')[-1] for t in tp.split('|')]
            body = s[b0 + 1:b1]
            stmts = [x.strip() for x in body.split(';') if x.strip()]
            thr = bool(re.search(r'\bthrow\b', body))
            logs = [bool(LOG.match(re.sub(r'\s+', ' ', x))) for x in stmts]
            blocks[(lib, rel, str(raw[:m.start()].count('\n') + 1))] = dict(
                generic=any(t in ('Exception', 'Throwable') for t in types),
                dummy=(not body.strip()) or (bool(stmts) and all(logs)),
                lt=thr and any(logs),
                intr=('InterruptedException' in types) and not thr and 'interrupt(' not in body,
                thr=thr, body=re.sub(r'\s+', ' ', body.strip()))

det = {(r['library'], r['file'], r['line']): r for r in csv.DictReader(open(f'{RES}/blocks.csv'))}
out = []
out.append(f'independent parser: {len(blocks)} catch blocks; detect.py: {len(det)}')
out.append(f'blocks only in one list: {len(set(blocks) - set(det))} / {len(set(det) - set(blocks))}')
flags = [('generic', 'generic_catch'), ('dummy', 'dummy_handler'), ('lt', 'log_and_throw'), ('intr', 'ignoring_interrupted')]
dis = collections.Counter()
for k, r in blocks.items():
    d = det.get(k)
    if d:
        for a, b in flags:
            if r[a] != (d[b] == '1'): dis[b] += 1
out.append('disagreements per flag: ' + (str(dict(dis)) if dis else 'none'))
cls = collections.Counter()
for k, r in blocks.items():
    d = det.get(k)
    if not d or any(d[b] == '1' for _, b in flags): continue
    b = r['body']
    if r['thr']: c = 'throws or rethrows'
    elif re.fullmatch(r'(continue|break) ?;?', b): c = 'only continue/break'
    elif re.fullmatch(r'return(?: [^;]{0,40})?;?', b): c = 'only a return (null/false/default)'
    else: c = 'other real statements'
    cls[c] += 1
out.append(f'unflagged blocks: {sum(cls.values())}')
out += [f'  {k}: {v}' for k, v in sorted(cls.items(), key=lambda x: -x[1])]
open(f'{RES}/crosscheck.txt', 'w').write('\n'.join(out) + '\n')
print('\n'.join(out))
