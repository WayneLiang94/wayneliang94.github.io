import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
import build as site

class BuildTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)/'repo';self.out=Path(self.temp.name)/'site'
        (self.root/'content/posts').mkdir(parents=True)
        (self.root/'styles').mkdir();(self.root/'styles/main.css').write_text('body{}')
        (self.root/'admin').mkdir();(self.root/'admin/index.html').write_text('<h1>Admin</h1>')
    def tearDown(self):self.temp.cleanup()
    def save(self,slug,published=True):
        meta=dict(title=slug,slug=slug,category='计算机',date='2026-10-23',summary='summary',published=published)
        (self.root/f'content/posts/{slug}.md').write_text('---\n'+json.dumps(meta)+'\n---\n\n## Note\n\nContent')
    def test_draft_never_enters_site_and_unpublish_removes_page(self):
        self.save('live');self.save('draft',False)
        with patch.object(site,'ROOT',self.root):
            site.build(self.out)
            self.assertTrue((self.out/'post/live/index.html').exists())
            self.assertFalse((self.out/'post/draft/index.html').exists())
            self.assertNotIn('draft',(self.out/'search.json').read_text())
            self.assertNotIn('/post/draft/',(self.out/'atom.xml').read_text())
            self.assertNotIn('/post/draft/',(self.out/'sitemap.xml').read_text())
            self.assertFalse((self.out/'content').exists())
            self.assertTrue((self.out/'admin/index.html').exists())
            self.save('live',False);site.build(self.out)
            self.assertFalse((self.out/'post/live/index.html').exists())
            self.assertEqual(json.loads((self.out/'search.json').read_text()),[])
            self.assertTrue((self.out/'post/about/index.html').exists())
    def test_repeatable_build(self):
        self.save('live')
        with patch.object(site,'ROOT',self.root):
            site.build(self.out)
            before={str(p.relative_to(self.out)):p.read_bytes() for p in self.out.rglob('*') if p.is_file()}
            site.build(self.out)
            after={str(p.relative_to(self.out)):p.read_bytes() for p in self.out.rglob('*') if p.is_file()}
            self.assertEqual(before,after)

if __name__=='__main__':unittest.main()
