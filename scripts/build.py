"""Build the public blog: python3 scripts/build.py [--output DIR]."""
from argparse import ArgumentParser
from html import escape as esc
from pathlib import Path
import json
import re
import shutil
from xml.etree import ElementTree as ET

from content import load_articles

ROOT = Path(__file__).resolve().parents[1]
BASE = 'https://wayneliang94.github.io'
CATEGORIES = {'计算机': 'CS', '数学': 'Math', '机器人': 'Robot', '学习方法': 'Notes'}
TOPICS = {
    '计算机': ('01', 'Computer science', '从一行代码，走向系统背后的原理。', '⌘'),
    '数学': ('02', 'Mathematics', '在抽象的符号里，寻找清晰的直觉。', '∑'),
    '机器人': ('03', 'Robotics', '让感知、思考与行动连接起来。', '◎'),
    '学习方法': ('04', 'Learning in public', '记录理解的过程，也记录新的问题。', '↗'),
}
ABOUT = '''<p>欢迎来到 WayneLAB。这里是一个持续生长的个人知识空间，整理计算机、数学与机器人的学习笔记，也记录把知识转化为实践的方法。</p><h2>温故而知新</h2><p>学习不只是收集答案。更有意思的部分，是用自己的语言重新解释一个概念，用一个小例子检验理解，再把零散的知识连接起来。这个小站就是这一过程的记录。</p><h2>你会在这里读到什么</h2><ul><li><a href="/tag/CS/">计算机</a>：从数据结构到操作系统，理解程序背后的原理。</li><li><a href="/tag/Math/">数学</a>：连接几何直觉、公式推导与具体问题。</li><li><a href="/tag/Robot/">机器人</a>：探索感知、规划与控制的闭环。</li><li><a href="/tag/Notes/">学习方法</a>：把读过的内容，变成可以再次使用的理解。</li></ul><h2>保持联系</h2><p>欢迎通过 <a href="https://github.com/WayneLiang94">GitHub</a> 交流。如果你喜欢安静地阅读，也可以通过 <a href="/atom.xml">RSS</a> 订阅更新。内容会随学习持续修订，愿这些笔记也能成为你的思考起点。</p>'''


def write(output, path, text):
    target = output / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding='utf-8')


def category_url(name):
    return '/tag/' + CATEGORIES[name] + '/'


def page(title, body, active='', description=None, path='/'):
    links = [('/', '首页'), ('/archives/', '文章'), ('/tags/', '探索'), ('/post/about/', '关于')]
    nav = ''.join(f'<a href="{url}"' + (' aria-current="page"' if active == url else '') + f'>{name}</a>' for url, name in links)
    description = description or 'WayneLAB · 关于计算机、数学、机器人与学习的思考。温故而知新，保持好奇，持续记录。'
    return f'''<!doctype html>
<html lang="zh-CN">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><meta name="color-scheme" content="light"><meta name="generator" content="WayneLAB"><title>{esc(title)} · WayneLAB</title><meta name="description" content="{esc(description, quote=True)}"><meta property="og:title" content="{esc(title, quote=True)} · WayneLAB"><meta property="og:description" content="{esc(description, quote=True)}"><meta property="og:type" content="website"><meta property="og:url" content="{BASE}{esc(path, quote=True)}"><link rel="canonical" href="{BASE}{esc(path, quote=True)}"><link rel="icon" href="/favicon.ico"><link rel="stylesheet" href="/styles/main.css"><link rel="alternate" type="application/atom+xml" title="WayneLAB RSS" href="/atom.xml"></head>
<body><a class="skip" href="#main">跳至内容</a>
<header class="site-header"><a class="brand" href="/" aria-label="WayneLAB 首页"><span class="brand-icon" aria-hidden="true">w<span>.</span></span><span>Wayne<span class="brand-light">LAB</span><small>一个人的数字花园</small></span></a><nav aria-label="主导航">{nav}<a class="nav-rss" href="/atom.xml" aria-label="RSS 订阅">RSS <span aria-hidden="true">↗</span></a></nav></header>
<main id="main">{body}</main>
<footer class="site-footer"><div><a class="footer-name" href="/">WayneLAB<span aria-hidden="true">.</span></a><p>温故而知新。让思考留下痕迹。</p></div><div class="footer-links"><a href="/post/about/">关于本站</a><a href="https://github.com/WayneLiang94">GitHub ↗</a><a href="/atom.xml">RSS 订阅 ↗</a><a href="/admin/">写作后台 ↗</a></div><p class="footer-note">保持好奇，持续记录。<span>Made with care &amp; curiosity.</span></p></footer>
</body></html>'''


def reading_minutes(article):
    text = re.sub(r'<[^>]+>', '', article['body'])
    return max(1, (len(text) + 399) // 400)


def meta(article):
    return f'<div class="article-meta"><a href="{category_url(article["category"])}">{esc(article["category"])}</a><span class="meta-dot" aria-hidden="true">·</span><time datetime="{article["date"]}">{article["date"]}</time><span class="meta-dot" aria-hidden="true">·</span><span>{reading_minutes(article)} 分钟阅读</span></div>'


def article_row(article, index=1):
    url = f'/post/{article["slug"]}/'
    return f'''<article class="article-row"><span class="row-number" aria-hidden="true">{index:02d}</span><div class="row-content">{meta(article)}<h3><a href="{url}">{esc(article['title'])}</a></h3><p>{esc(article['summary'])}</p></div><a class="row-arrow" href="{url}" aria-label="阅读：{esc(article['title'], quote=True)}">↗</a></article>'''


def topic_cards(articles):
    result = ''
    for name, slug in CATEGORIES.items():
        number, english, description, symbol = TOPICS[name]
        count = sum(a['category'] == name for a in articles)
        result += f'<a class="topic-card" href="/tag/{slug}/"><div class="topic-top"><span>{number} / {english}</span><b aria-hidden="true">{symbol}</b></div><h3>{name}<span aria-hidden="true">↗</span></h3><p>{description}</p><small>{count} 篇笔记</small></a>'
    return result


def page_heading(label, title, text):
    return f'<section class="page-heading"><p class="eyebrow">{esc(label)}</p><h1>{esc(title)}</h1><p>{esc(text)}</p></section>'


def build(output=ROOT):
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    articles = sorted(load_articles(ROOT), key=lambda a: (a['date'], a['slug']), reverse=True)
    if output != ROOT:
        for name in ('styles', 'images', 'media', 'admin'):
            if (ROOT / name).is_dir():
                shutil.copytree(ROOT / name, output / name, dirs_exist_ok=True)
        for name in ('favicon.ico', 'site.js'):
            if (ROOT / name).is_file():
                shutil.copy2(ROOT / name, output / name)
    # Only remove article HTML generated by this builder; never touch content sources.
    current_slugs = {a['slug'] for a in articles}
    for old_page in (output / 'post').glob('*/index.html'):
        if old_page.parent.name not in current_slugs and old_page.parent.name != 'about':
            previous = old_page.read_text(encoding='utf-8')
            if '<meta name="generator" content="WayneLAB">' in previous:
                old_page.unlink()
                if not any(old_page.parent.iterdir()):
                    old_page.parent.rmdir()
    paths = ['/', '/archives/', '/tags/', '/post/about/']
    hero = '''<section class="hero"><div class="hero-copy"><p class="eyebrow"><span class="status-dot" aria-hidden="true"></span> WAYNE'S PERSONAL SPACE</p><h1>认真思考，<br>让知识<span class="title-green">慢慢生长<span class="title-period">。</span></span></h1><p class="hero-description">你好，我是 Wayne。<br>在这里记录计算机、数学与机器人的学习之旅，<br class="desktop-break">以及那些值得反复琢磨的小小发现。</p><div class="hero-actions"><a class="button" href="#latest">翻开我的笔记 <span aria-hidden="true">↗</span></a><a class="quiet-link" href="/post/about/">关于我 <span aria-hidden="true">→</span></a></div></div><div class="hero-art" aria-hidden="true"><div class="art-grid"></div><span class="art-label art-label-top">IDEAS TAKE ROOT HERE.</span><svg class="garden-art" viewBox="0 0 400 360" fill="none"><path d="M200 300V154M200 239C151 240 128 203 131 166C174 164 197 195 200 239ZM200 205C244 203 270 172 266 133C227 135 200 161 200 205ZM200 166C170 154 159 128 167 98C195 108 207 135 200 166Z" stroke="currentColor" stroke-width="2"/><circle cx="200" cy="194" r="113" stroke="currentColor" stroke-opacity=".2"/><circle cx="200" cy="194" r="143" stroke="currentColor" stroke-opacity=".16" stroke-dasharray="3 8"/><path d="M110 302H290M137 317H263M158 331H242" stroke="currentColor" stroke-opacity=".45"/><path d="M75 95H105M90 80V110M310 228H328M319 219V237" stroke="currentColor" stroke-opacity=".5"/><circle cx="289" cy="82" r="5" stroke="currentColor"/><circle cx="82" cy="247" r="3" fill="currentColor"/></svg><span class="art-tag tag-top">⌘ 代码与逻辑</span><span class="art-tag tag-bottom">∑ 思考与探索</span><span class="art-label art-label-bottom">LEARN. CONNECT. GROW.</span><span class="art-coordinate">31° N / A CURIOUS MIND</span></div></section>'''
    metrics = f'<div class="home-divider"><span>持续生长的数字花园</span><span>{len(articles):02d} 篇笔记 <i aria-hidden="true">/</i> {len(CATEGORIES):02d} 个探索方向</span></div>'
    topics = '<section class="topics-section"><div class="section-heading"><div><p class="eyebrow">FIELDS OF CURIOSITY</p><h2>沿着兴趣，探索。</h2></div><a class="quiet-link" href="/tags/">所有主题 ↗</a></div><div class="topic-grid">'+topic_cards(articles)+'</div></section>'
    featured = ''
    if articles:
        first = articles[0]
        featured = f'<a class="featured-note" href="/post/{first["slug"]}/"><div class="featured-symbol" aria-hidden="true">✳</div><div><span class="eyebrow">A NOTE TO BEGIN WITH / 从这篇开始</span><h2>{esc(first["title"])}</h2><p>{esc(first["summary"])}</p></div><span class="featured-arrow" aria-hidden="true">↗</span></a>'
    latest = '<section class="latest-section" id="latest"><div class="section-heading"><div><p class="eyebrow">THE NOTEBOOK</p><h2>最近的笔记</h2></div><a class="quiet-link" href="/archives/">文章归档 ↗</a></div><div class="notebook-layout"><div class="article-list">'+(''.join(article_row(a, i) for i, a in enumerate(articles, 1)) or '<p class="empty-state">新的笔记正在酝酿，欢迎稍后再来。</p>')+'</div><aside class="author-card"><span class="eyebrow">BEHIND THE NOTES</span><div class="author-avatar" aria-hidden="true">W<span>.</span></div><h3>你好，我是 Wayne。</h3><p>把复杂的事情想清楚，<br>把学到的东西写下来。<br>在记录中，遇见新的可能。</p><a href="/post/about/">多认识我一点 ↗</a><div class="author-bottom"><span class="status-dot" aria-hidden="true"></span> 保持好奇，慢慢来。</div></aside></div></section>'
    subscribe = '<section class="subscribe-strip"><div><span class="eyebrow">STAY IN THE LOOP</span><h2>下次更新，再见。</h2><p>通过 RSS 订阅，在你喜欢的阅读器里继续这段探索。</p></div><a class="button button-outline" href="/atom.xml">订阅我的笔记 ↗</a></section>'
    write(output, 'index.html', page('首页', hero+metrics+topics+featured+latest+subscribe, '/'))
    for a in articles:
        url = f'/post/{a["slug"]}/'
        content = '<div class="reading-layout"><article class="prose"><a class="back-link" href="'+category_url(a['category'])+'">← '+esc(a['category'])+'</a>'+meta(a)+f'<h1>{esc(a["title"])}</h1><p class="article-lead">{esc(a["summary"])}</p><div class="article-body">{a["body"]}</div><div class="article-end"><span>— 感谢阅读 —</span><a href="/archives/">继续探索其他笔记 →</a></div></article></div>'
        write(output, f'post/{a["slug"]}/index.html', page(a['title'], content, '/archives/', a['summary'], url))
        paths.append(url)
    write(output, 'post/about/index.html', page('关于', '<article class="prose about-page"><p class="eyebrow">A LITTLE ABOUT THIS SPACE</p><h1>你好，欢迎来到<br><span class="title-green">我的数字花园。</span></h1><div class="article-body">'+ABOUT+'</div></article>', '/post/about/', path='/post/about/'))
    aliases = {'Ho7S3eSMW': '计算机', 'Xw4oj60xyM': '计算机', 'bl_isxESH': '机器人', 'lWxM1hi8c': '数学'}
    aliases.update({slug: name for name, slug in CATEGORIES.items()})
    for slug, name in aliases.items():
        matches = [a for a in articles if a['category'] == name]
        body = page_heading(TOPICS[name][1].upper(), name, TOPICS[name][2])+f'<div class="listing-caption">{len(matches):02d} 篇笔记 · 持续更新</div><div class="article-list standalone-list">'+(''.join(article_row(a, i) for i, a in enumerate(matches, 1)) or '<p class="empty-state">这个方向的新笔记正在准备中。</p>')+'</div>'
        write(output, f'tag/{slug}/index.html', page(name, body, '/tags/', path=f'/tag/{slug}/'))
        paths.append(f'/tag/{slug}/')
    write(output, 'tags/index.html', page('探索方向', page_heading('FIELDS OF CURIOSITY', '世界很大，慢慢探索。', '从一个感兴趣的问题出发，建立属于自己的知识连接。')+'<div class="topic-grid all-topics">'+topic_cards(articles)+'</div>', '/tags/', path='/tags/'))
    archive = page_heading('THE ARCHIVE', '所有思考，都有来处。', '沿着时间回看，一篇笔记，一次新的理解。')
    years = sorted({a['date'][:4] for a in articles}, reverse=True)
    for year in years:
        archive += f'<section class="archive-year"><h2>{year}<span> / </span></h2><div class="archive-list">'
        for a in articles:
            if a['date'].startswith(year):
                archive += f'<a href="/post/{a["slug"]}/"><time datetime="{a["date"]}">{a["date"][5:]}</time><strong>{esc(a["title"])}</strong><span>{esc(a["category"])}</span><b aria-hidden="true">↗</b></a>'
        archive += '</div></section>'
    write(output, 'archives/index.html', page('文章归档', archive, '/archives/', path='/archives/'))
    error = page('页面未找到', page_heading('404 / AN UNWRITTEN PAGE', '这页，还是空白。', '页面可能已移除，不妨换一个方向，继续探索。')+'<a class="button" href="/">回到首页 ↗</a>', path='/404.html')
    write(output, '404.html', error)
    write(output, 'static/404.html', error)
    write(output, 'search.json', json.dumps([dict(slug=a['slug'], title=a['title'], category=a['category'], date=a['date'], summary=a['summary'], url=f'/post/{a["slug"]}/') for a in articles], ensure_ascii=False, indent=2)+'\n')
    write(output, '.nojekyll', '')
    write(output, 'robots.txt', 'User-agent: *\nAllow: /\nDisallow: /admin/\nSitemap: '+BASE+'/sitemap.xml\n')
    namespace = 'http://www.w3.org/2005/Atom'
    ET.register_namespace('', namespace)
    def el(parent, name, text=None, **attrs):
        node = ET.SubElement(parent, '{'+namespace+'}'+name, attrs)
        node.text = text
        return node
    feed = ET.Element('{'+namespace+'}feed')
    el(feed, 'id', BASE+'/'); el(feed, 'title', 'WayneLAB'); el(feed, 'updated', (articles[0]['date'] if articles else '2026-01-01')+'T00:00:00Z')
    el(feed, 'subtitle', '温故而知新。关于计算机、数学、机器人与学习的思考。')
    el(feed, 'link', href=BASE+'/atom.xml', rel='self'); el(feed, 'link', href=BASE+'/')
    el(el(feed, 'author'), 'name', 'WayneLAB')
    for a in articles:
        entry = el(feed, 'entry'); el(entry, 'title', a['title']); el(entry, 'id', BASE+'/post/'+a['slug']+'/')
        el(entry, 'link', href=BASE+'/post/'+a['slug']+'/'); el(entry, 'updated', a['date']+'T00:00:00Z'); el(entry, 'summary', a['summary'])
    write(output, 'atom.xml', '<?xml version="1.0" encoding="utf-8"?>\n'+ET.tostring(feed, encoding='unicode')+'\n')
    sitemap = ET.Element('urlset', xmlns='http://www.sitemaps.org/schemas/sitemap/0.9')
    for path in paths:
        node = ET.SubElement(sitemap, 'url'); ET.SubElement(node, 'loc').text = BASE+path
    write(output, 'sitemap.xml', '<?xml version="1.0" encoding="utf-8"?>\n'+ET.tostring(sitemap, encoding='unicode')+'\n')
    return articles


if __name__ == '__main__':
    parser = ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT, help='Public output directory (defaults to repository root).')
    args = parser.parse_args()
    articles = build(args.output)
    print(f'Built {len(articles)} published articles, public pages, RSS and sitemap in {args.output.resolve()}.')
