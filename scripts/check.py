"""Validate a built site's navigation, public data and publishing tools."""
import argparse
from html.parser import HTMLParser
import json
from pathlib import Path
from urllib.parse import unquote, urlsplit
import xml.etree.ElementTree as ET

class Page(HTMLParser):
    def __init__(self):
        super().__init__(); self.links=[]; self.ids=set(); self.h1=0
    def handle_starttag(self, tag, attrs):
        attrs=dict(attrs)
        if tag=='h1': self.h1+=1
        if attrs.get('id'): self.ids.add(attrs['id'])
        for key in ('href','src'):
            if attrs.get(key): self.links.append(attrs[key])

def check(root):
    root=root.resolve()
    pages=[p for p in root.rglob('*.html') if not {'themes','.git','_site','tests'}.intersection(p.relative_to(root).parts)]
    count=0
    for p in pages:
        text=p.read_text(); parsed=Page(); parsed.feed(text)
        assert '<html lang="zh-CN"' in text,(p,'Chinese language declaration missing')
        assert parsed.h1 >= 1 if 'admin' in p.relative_to(root).parts else parsed.h1 == 1, (p,'expected page heading',parsed.h1)
        assert '政治' not in text and '/tag/Phil' not in text and '/post/phi' not in text,p
        for link in parsed.links:
            url=urlsplit(link)
            if url.scheme or url.netloc: continue
            if not url.path:
                if url.fragment: assert unquote(url.fragment) in parsed.ids,(p,link)
                continue
            target=root/unquote(url.path).lstrip('/') if url.path.startswith('/') else p.parent/unquote(url.path)
            assert target.resolve().is_relative_to(root),(p,link,'path escapes site')
            if target.is_dir(): target=target/'index.html'
            assert target.is_file(),(p,link)
            count+=1
    feed=ET.parse(root/'atom.xml'); entries=feed.findall('{http://www.w3.org/2005/Atom}entry')
    search=json.loads((root/'search.json').read_text())
    assert len(entries)==len(search),'RSS and search article counts differ'
    assert (root/'admin/index.html').is_file(),'Author dashboard absent'
    assert (root/'sitemap.xml').is_file(),'Sitemap absent'
    assert not (root/'post/phi/index.html').exists()
    assert not (root/'tag/Phil/index.html').exists()
    print(f'PASS: {len(pages)} pages, {count} local links/assets, {len(entries)} published RSS/search entries, author dashboard.')

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);args=parser.parse_args();check(args.root)
