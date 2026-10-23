"""Validated, sanitized Markdown content shared by local and Pages builds."""
from datetime import date
from pathlib import Path
import json
import re
import bleach
import markdown

CATEGORIES = {'计算机', '数学', '机器人', '学习方法'}
SLUG = re.compile(r'[a-z0-9]+(?:-[a-z0-9]+)*\Z')
TAGS = {'p', 'br', 'hr', 'h2', 'h3', 'h4', 'h5', 'h6', 'strong', 'em', 'del', 'blockquote', 'pre', 'code', 'ul', 'ol', 'li', 'a', 'img', 'table', 'thead', 'tbody', 'tr', 'th', 'td'}
ATTRIBUTES = {'a': ['href', 'title'], 'img': ['src', 'alt', 'title'], 'code': ['class'], 'ol': ['start']}

def render_markdown(text):
    raw = markdown.markdown(text, extensions=['fenced_code', 'tables', 'sane_lists'])
    return bleach.clean(raw, tags=TAGS, attributes=ATTRIBUTES, protocols={'http', 'https', 'mailto'}, strip=True, strip_comments=True)

def parse_post(path):
    text = path.read_text(encoding='utf-8')
    match = re.fullmatch(r'---\r?\n(.*?)\r?\n---\r?\n(.*)', text, flags=re.S)
    if not match:
        raise ValueError(f'{path.name}: expected JSON front matter between --- lines')
    metadata = json.loads(match[1])
    if not isinstance(metadata, dict):
        raise ValueError(f'{path.name}: metadata must be an object')
    for key in ['title', 'slug', 'category', 'date', 'summary']:
        if not isinstance(metadata.get(key), str) or not metadata[key].strip():
            raise ValueError(f'{path.name}: missing {key}')
    if not SLUG.fullmatch(metadata['slug']) or metadata['slug'] == 'about' or path.stem != metadata['slug']:
        raise ValueError(f'{path.name}: invalid or reserved slug')
    if metadata['category'] not in CATEGORIES:
        raise ValueError(f'{path.name}: unsupported category')
    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', metadata['date']):
        raise ValueError(f'{path.name}: expected YYYY-MM-DD date')
    date.fromisoformat(metadata['date'])
    if type(metadata.get('published')) is not bool:
        raise ValueError(f'{path.name}: published must be boolean')
    if len(metadata['title']) > 120 or len(metadata['summary']) > 300 or len(metadata['slug']) > 100:
        raise ValueError(f'{path.name}: metadata too long')
    content = match[2].strip()
    if not content:
        raise ValueError(f'{path.name}: empty article')
    return {**metadata, 'content': content, 'body': render_markdown(content)}

def load_articles(root, include_drafts=False):
    articles = [parse_post(path) for path in sorted((Path(root) / 'content/posts').glob('*.md'))]
    if len({a['slug'] for a in articles}) != len(articles):
        raise ValueError('Duplicate article slug')
    return sorted((a for a in articles if include_drafts or a['published']), key=lambda a: (a['date'], a['slug']), reverse=True)
