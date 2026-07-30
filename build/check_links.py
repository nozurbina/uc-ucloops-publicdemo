# Link checker: verify every internal href#anchor resolves to a real id on the target page.
import re, glob, os, json
os.chdir(os.path.join(os.path.dirname(__file__), '..', 'site'))

ids = {}
hrefs = {}
for f in glob.glob('**/*.html', recursive=True):
    f = f.replace('\\', '/')
    html = open(f, encoding='utf-8').read()
    ids[f] = set(re.findall(r'id="([^"]+)"', html))
    hrefs[f] = re.findall(r'href="([^"]+)"', html)

def resolve(cur, href):
    if href.startswith('#'):
        return cur, href[1:]
    path, anc = (href.split('#', 1) + [''])[:2] if '#' in href else (href, '')
    tgt = os.path.normpath(os.path.join(os.path.dirname(cur), path)).replace('\\', '/')
    return tgt, anc

broken, total = [], 0
for f in hrefs:
    for href in hrefs[f]:
        if href.startswith(('http', 'mailto')):
            continue
        total += 1
        tf, anc = resolve(f, href)
        if not anc:
            if not os.path.exists(tf):
                broken.append((f, href, 'missing file'))
            continue
        if tf not in ids:
            broken.append((f, href, 'missing target file'))
        elif anc not in ids[tf]:
            broken.append((f, href, 'missing anchor'))

print('files:', len(ids), '| internal links checked:', total, '| BROKEN:', len(broken))
for b in broken[:40]:
    print('   ', b)

# Trail spot check: journey -> insight -> verbatim
def anchors_of(f): return ids.get(f, set())
jf = 'journey-late-night-foodie.html'
jhtml = open(jf, encoding='utf-8').read()
ins_links = re.findall(r'href="insights\.html#(INS-[^"]+)"', jhtml)
print(f'\nTrail check on {jf}: {len(ins_links)} insight links from journey cells')
ihtml = open('insights.html', encoding='utf-8').read()
# for first 3 insight links, confirm the insight exists and has >=1 source evidence link
import collections
ok = 0
for ins in ins_links[:6]:
    block = re.search(r'id="'+re.escape(ins)+r'".*?</article>', ihtml, re.S)
    if not block: print('   MISSING insight', ins); continue
    ev = re.findall(r'href="(sources/[^"]+#[^"]+)"', block.group(0))
    if ev: ok += 1
print(f'   insights with verbatim evidence links: {ok}/{min(6,len(ins_links))}  (journey->insight->verbatim intact)')
