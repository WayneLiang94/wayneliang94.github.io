"""Build the static blog with Python's standard library: python3 scripts/build.py."""
from pathlib import Path
import json
from html import escape as esc
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
ARTICLES = json.loads((ROOT / 'config/articles.json').read_text())
CATEGORIES = {'计算机': 'CS', '数学': 'Math', '机器人': 'Robot', '学习方法': 'Notes'}
ABOUT = '<p>欢迎来到 WayneLAB。这里整理计算机、数学与机器人的学习笔记，也记录把知识转化为实践的方法。</p><h2>温故而知新</h2><p>本站希望让零散的知识形成联系：用具体问题理解概念，用例子检验推导，再用复盘发现遗漏。内容会随着学习持续修订。</p><h2>从这里开始</h2><ul><li><a href="/tag/CS/">计算机：数据结构与系统基础</a></li><li><a href="/tag/Math/">数学：直觉、推导与练习</a></li><li><a href="/tag/Robot/">机器人：感知、规划与控制</a></li></ul><h2>交流与订阅</h2><p>欢迎通过 <a href="https://github.com/WayneLiang94">GitHub</a> 交流，也可以通过 <a href="/atom.xml">RSS</a> 订阅更新。</p>'

def write(path, content):
    target = ROOT / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding='utf-8')

def page(title, body, active=''):
    links = [('/', '首页'), ('/tag/CS/', '计算机'), ('/tag/Math/', '数学'), ('/tag/Robot/', '机器人'), ('/archives/', '归档'), ('/post/about/', '关于')]
    nav = ''.join(f'<a href="{url}"'+(' aria-current="page"' if active == url else '')+f'>{name}</a>' for url, name in links)
    return f'''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{esc(title)} · WayneLAB</title><meta name="description" content="WayneLAB · 计算机、数学与机器人的学习笔记。温故而知新。"><link rel="icon" href="/favicon.ico"><link rel="stylesheet" href="/styles/main.css"><link rel="alternate" type="application/atom+xml" title="WayneLAB RSS" href="/atom.xml"></head>
<body><a class="skip" href="#main">跳至内容</a><header><a class="brand" href="/">Wayne<span>LAB</span><small>温故而知新</small></a><nav aria-label="主导航">{nav}</nav></header><main id="main">{body}</main><footer><span>WayneLAB · 保持好奇，持续记录。</span><div><a href="/tags/">全部标签</a><a href="/atom.xml">RSS 订阅 ↗</a><a href="https://github.com/WayneLiang94">GitHub ↗</a></div></footer></body></html>'''

def card(a):
    return f'''<article class="card"><div class="meta"><a href="/tag/{CATEGORIES[a['category']]}/">{esc(a['category'])}</a><time datetime="{a['date']}">{a['date']}</time></div><h3><a href="/post/{a['slug']}/">{esc(a['title'])}</a></h3><p>{esc(a['summary'])}</p><a class="read" href="/post/{a['slug']}/">阅读全文 <span aria-hidden="true">↗</span></a></article>'''

def build():
    categories = ''.join(f'<a class="topic" href="/tag/{slug}/"><span>0{i}</span><h3>{name} ↗</h3><p>{desc}</p></a>' for i, ((name, slug), desc) in enumerate(zip(CATEGORIES.items(), ['从数据结构到系统原理', '连接直觉、公式与推导', '探索感知与行动的闭环', '让知识沉淀为自己的方法']), 1))
    hero = '<section class="hero"><div><p class="eyebrow">WAYNELAB / DIGITAL GARDEN</p><h1>把好奇心，<br>写成<span>不断生长的笔记。</span></h1><p class="intro">在计算机、数学与机器人之间探索。记录思考的过程，也分享从理解到实践的每一步。</p><div class="actions"><a class="button" href="#latest">开始阅读 ↓</a><a href="/post/about/">认识这个小站 ↗</a></div></div><aside class="diagram" aria-label="本站的学习循环"><span class="orbit o1"></span><span class="orbit o2"></span><b>学 · 思 · 行</b><small>LEARN / THINK / BUILD</small><span class="node n1">计算机</span><span class="node n2">数学</span><span class="node n3">机器人</span></aside></section>'
    write('index.html', page('首页', hero+'<section><div class="section-head"><h2>探索方向</h2><span>循着兴趣，建立连接</span></div><div class="topics">'+categories+'</div></section><section id="latest"><div class="section-head"><h2>笔记与思考</h2><a href="/archives/">查看归档 ↗</a></div><div class="cards">'+''.join(map(card, ARTICLES))+'</div></section>', '/'))
    for a in ARTICLES:
        content = f'<article class="prose"><a class="back" href="/tag/{CATEGORIES[a["category"]]}/">← {a["category"]}</a><div class="meta"><time datetime="{a["date"]}">{a["date"]}</time><span>学习笔记</span></div><h1>{esc(a["title"])}</h1><p class="lead">{esc(a["summary"])}</p>{a["body"]}<hr><a href="/archives/">继续探索其他笔记 →</a></article>'
        write(f'post/{a["slug"]}/index.html', page(a['title'], content))
    write('post/about/index.html', page('关于', '<article class="prose"><p class="eyebrow">ABOUT THIS GARDEN</p><h1>关于 WayneLAB</h1>'+ABOUT+'</article>', '/post/about/'))
    aliases = {'Ho7S3eSMW': '计算机', 'Xw4oj60xyM': '计算机', 'bl_isxESH': '机器人', 'lWxM1hi8c': '数学'}
    for name, slug in CATEGORIES.items():
        aliases[slug] = name
    for slug, name in aliases.items():
        write(f'tag/{slug}/index.html', page(name, f'<section class="page-title"><p class="eyebrow">TOPIC / {esc(slug)}</p><h1>{name}</h1><p>围绕一个方向，积累可复用的理解。</p></section><div class="cards">'+''.join(card(a) for a in ARTICLES if a['category'] == name)+'</div>', f'/tag/{slug}/'))
    write('tags/index.html', page('全部标签', '<section class="page-title"><h1>探索方向</h1><p>找到感兴趣的主题，从一篇笔记开始。</p></section><div class="topics">'+categories+'</div>'))
    archive = '<section class="page-title"><p class="eyebrow">THE ARCHIVE</p><h1>文章归档</h1><p>沿着时间，回看学习的足迹。</p></section><div class="archive">'
    for a in ARTICLES:
        archive += f'<a href="/post/{a["slug"]}/"><time>{a["date"]}</time><strong>{esc(a["title"])}</strong><span>{a["category"]} ↗</span></a>'
    write('archives/index.html', page('文章归档', archive+'</div>', '/archives/'))
    error = page('页面未找到', '<section class="page-title"><p class="eyebrow">404 / LOST IN THE GARDEN</p><h1>这条小径还没有笔记。</h1><p>页面可能已移除，换一个方向继续探索吧。</p><a class="button" href="/">返回首页 →</a></section>')
    write('404.html', error)
    write('static/404.html', error)
    ET.register_namespace('', 'http://www.w3.org/2005/Atom')
    def el(parent, name, text=None, **attrs):
        node = ET.SubElement(parent, '{http://www.w3.org/2005/Atom}'+name, attrs)
        node.text = text
        return node
    feed = ET.Element('{http://www.w3.org/2005/Atom}feed')
    base = 'https://wayneliang94.github.io'
    el(feed, 'id', base+'/'); el(feed, 'title', 'WayneLAB'); el(feed, 'updated', ARTICLES[0]['date']+'T00:00:00Z')
    el(feed, 'link', href=base+'/atom.xml', rel='self'); el(feed, 'link', href=base+'/')
    el(el(feed, 'author'), 'name', 'WayneLAB')
    for a in ARTICLES:
        entry = el(feed, 'entry'); el(entry, 'title', a['title']); el(entry, 'id', base+'/post/'+a['slug']+'/')
        el(entry, 'link', href=base+'/post/'+a['slug']+'/'); el(entry, 'updated', a['date']+'T00:00:00Z'); el(entry, 'summary', a['summary'])
    write('atom.xml', '<?xml version="1.0" encoding="utf-8"?>\n'+ET.tostring(feed, encoding='unicode')+'\n')
    config = json.loads((ROOT/'config/posts.json').read_text())
    config['menus'] = [{'link': url, 'name': name, 'openType': 'Internal'} for url, name in [('/', '首页'), ('/tag/CS/', '计算机'), ('/tag/Math/', '数学'), ('/tag/Robot/', '机器人'), ('/archives/', '归档'), ('/post/about/', '关于')]]
    # Keep the writing client's metadata in sync with the generated site.
    config['posts'] = [dict(content=a['body'], data=dict(title=a['title'], date=a['date']+' 00:00:00', tags=[a['category']], published=True, hideInList=False, feature=None, isTop=False), isEmpty=False, excerpt=a['summary'], abstract=a['summary'], fileName=a['slug']) for a in ARTICLES]
    config['posts'].append(dict(content=ABOUT, data=dict(title='关于', date='2019-01-25 19:09:48', tags=[], published=True, hideInList=True, feature=None, isTop=False), isEmpty=False, excerpt='', abstract='', fileName='about'))
    config['tags'] = [dict(name=k, slug=v, used=True) for k,v in CATEGORIES.items()]
    write('config/posts.json', json.dumps(config, ensure_ascii=False, indent=2)+'\n')
    for a in ARTICLES:
        write(f'posts/{a["slug"]}.md', '---\n'+f'title: {a["title"]}\ndate: {a["date"]}\ntags: [{a["category"]}]\npublished: true\nhideInList: false\n'+'---\n\n'+a['body']+'\n')
    write('posts/about.md', '---\ntitle: 关于\ndate: 2019-01-25 19:09:48\npublished: true\nhideInList: true\n---\n\n'+ABOUT+'\n')

if __name__ == '__main__':
    build()
    print('Built WayneLAB static pages, writing metadata and RSS.')
