"""Check generated pages and local asset/navigation targets."""
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlsplit, unquote
import xml.etree.ElementTree as ET
ROOT = Path(__file__).resolve().parents[1]
class Links(HTMLParser):
    def __init__(self):
        super().__init__(); self.links=[]; self.ids=set(); self.h1=0
    def handle_starttag(self, tag, attrs):
        attrs=dict(attrs)
        if tag=='h1': self.h1+=1
        if 'id' in attrs: self.ids.add(attrs['id'])
        for key in ('href','src'):
            if key in attrs: self.links.append(attrs[key])
pages=[p for p in ROOT.rglob('*.html') if 'themes' not in p.parts and '.git' not in p.parts]
count=0
for p in pages:
    text=p.read_text(); parsed=Links(); parsed.feed(text)
    assert '<html lang="zh-CN">' in text, p
    assert parsed.h1==1, (p,'expected one h1')
    assert '政治' not in text and '/tag/Phil' not in text and '/post/phi' not in text, p
    for link in parsed.links:
        url=urlsplit(link)
        if url.scheme or url.netloc: continue
        if not url.path:
            if url.fragment: assert unquote(url.fragment) in parsed.ids,(p,link)
            continue
        target=ROOT/unquote(url.path).lstrip('/') if url.path.startswith('/') else p.parent/unquote(url.path)
        if target.is_dir(): target=target/'index.html'
        assert target.is_file(),(p,link)
        count+=1
feed=ET.parse(ROOT/'atom.xml')
assert len(feed.findall('{http://www.w3.org/2005/Atom}entry'))==5
assert not (ROOT/'post/phi/index.html').exists()
assert not (ROOT/'tag/Phil/index.html').exists()
print(f'PASS: {len(pages)} pages, {count} local links/assets, 5 RSS entries, removed category absent.')
