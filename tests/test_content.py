import json
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from content import load_articles, parse_post, render_markdown

class ContentTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root/'content/posts').mkdir(parents=True)
    def tearDown(self): self.temp.cleanup()
    def save(self, slug='example', **overrides):
        meta=dict(title='中文标题',slug=slug,category='计算机',date='2026-10-23',summary='摘要',published=True)
        meta.update(overrides)
        p=self.root/'content/posts'/f'{slug}.md'
        p.write_text('---\n'+json.dumps(meta,ensure_ascii=False)+'\n---\n\n## Heading\n\n**中文** and `code`.\n')
        return p
    def test_roundtrip_utf8_markdown(self):
        article=parse_post(self.save())
        self.assertEqual(article['title'],'中文标题')
        self.assertIn('<strong>中文</strong>',article['body'])
        self.assertIn('<code>code</code>',article['body'])
    def test_drafts_are_excluded_and_dates_sorted(self):
        self.save('older',date='2020-01-01'); self.save('newer'); self.save('private-draft',published=False)
        self.assertEqual([a['slug'] for a in load_articles(self.root)],['newer','older'])
        self.assertEqual(len(load_articles(self.root,include_drafts=True)),3)
    def test_reject_invalid_dates_categories_status_and_slug(self):
        for overrides in [dict(date='2026-02-30'),dict(category='unexpected'),dict(published='false'),dict(slug='../escape'),dict(slug='about')]:
            with self.subTest(overrides=overrides):
                with self.assertRaises(ValueError): parse_post(self.save(**overrides))
    def test_drop_scripts_events_and_unsafe_links(self):
        result=render_markdown('<script>alert(1)</script><img src="x" onerror="alert(1)"><a href="javascript:alert(1)">bad</a>\n\n[also](javascript:alert(1))')
        for dangerous in ['<script','onerror','href="javascript:']:
            self.assertNotIn(dangerous,result)
    def test_tables_and_code_fences(self):
        result=render_markdown('| A | B |\n|---|---|\n| 1 | 2 |\n\n```python\nprint("test")\n```')
        self.assertIn('<table>',result);self.assertIn('language-python',result)

if __name__ == '__main__': unittest.main()
