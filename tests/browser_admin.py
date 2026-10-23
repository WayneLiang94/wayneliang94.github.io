"""Optional CMS integration checks using Playwright and mocked GitHub responses.

Run: python3 tests/browser_admin.py
Install Playwright separately for development. Chromium is detected from PATH,
or set PLAYWRIGHT_CHROMIUM_EXECUTABLE; otherwise Playwright's browser is used.
No real credential or network access to GitHub is used.
"""
import json,base64,threading,os,shutil,tempfile
from pathlib import Path
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
ARTIFACTS=Path(tempfile.gettempdir())/'waynelab-admin-tests'
ARTIFACTS.mkdir(exist_ok=True)
class Handler(SimpleHTTPRequestHandler):
 def __init__(self,*args,**kwargs): super().__init__(*args,directory=str(ROOT),**kwargs)
 def log_message(self,*args): pass
server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
threading.Thread(target=server.serve_forever,daemon=True).start()
BASE=f'http://127.0.0.1:{server.server_port}'
fixture={'title':'测试文章','slug':'existing','category':'计算机','date':'2026-10-23','summary':'摘要','published':True}
def document(meta,body='## 章节\n\n正文内容。',sha='initial-sha'):
 raw='---\n'+json.dumps(meta,ensure_ascii=False,indent=2)+'\n---\n\n'+body+'\n'
 return {'name':meta['slug']+'.md','path':'content/posts/'+meta['slug']+'.md','sha':sha,'content':base64.b64encode(raw.encode()).decode(),'encoding':'base64'}
files={'existing':document(fixture)}
puts=[]; fail=False; unauthorized=False
with sync_playwright() as p:
 executable=os.environ.get('PLAYWRIGHT_CHROMIUM_EXECUTABLE') or shutil.which('chromium') or shutil.which('chromium-browser')
 browser=p.chromium.launch(**({'executable_path':executable} if executable else {}),headless=True,args=['--no-sandbox'])
 page=browser.new_page(viewport={'width':1360,'height':900})
 errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
 def api(route):
  global fail,unauthorized
  req=route.request
  assert req.headers.get('authorization')=='Bearer fake-test-token'
  path=req.url.split('wayneliang94.github.io',1)[1]
  if unauthorized:
   route.fulfill(status=401,json={'message':'Bad credentials'});return
  if req.method=='GET' and path=='':
   route.fulfill(json={'permissions':{'push':True}});return
  if req.method=='GET' and path.startswith('/contents/content/posts?'):
   route.fulfill(json=[{'name':f['name'],'path':f['path'],'type':'file'} for f in files.values()]);return
  if '/contents/content/posts/' in path:
   slug=path.split('/contents/content/posts/',1)[1].split('.md',1)[0]
   if req.method=='GET':
    route.fulfill(json=files[slug]);return
   if req.method=='PUT':
    data=req.post_data_json;puts.append((slug,data))
    if fail:
     route.fulfill(status=409,json={'message':'conflict'});return
    raw=base64.b64decode(data['content']).decode();meta=json.loads(raw.split('---\n',2)[1].strip())
    assert data['branch']=='master';assert 'fake-test-token' not in raw
    files[slug]=document(meta,raw.split('\n---\n',1)[1].strip(),f'sha-{len(puts)}')
    route.fulfill(status=201,json={'content':{'sha':files[slug]['sha']}});return
  raise AssertionError((req.method,path))
 page.route('https://api.github.com/**',api)
 page.goto(BASE+'/admin/')
 unauthorized=True
 page.locator('#token').fill('fake-test-token');page.locator('#login-button').click()
 page.locator('#login-status.error').wait_for();assert '令牌无效' in page.locator('#login-status').inner_text()
 unauthorized=False
 page.locator('#token').fill('fake-test-token');page.locator('#login-button').click()
 page.locator('#app-view').wait_for(state='visible');assert page.locator('.post-row').count()==1
 assert page.locator('#token').input_value()==''
 assert page.evaluate('JSON.stringify([localStorage,sessionStorage])')=='[{},{}]'
 page.locator('#create-post').click()
 page.locator('#post-title').fill('一个新的中文标题')
 page.locator('#post-slug').fill('new-post')
 page.locator('#post-summary').fill('支持中文的摘要')
 page.locator('#post-body').fill('## 标题\n\n**加粗**\n\n<script>window.hacked=true</script>\n\n[恶意](javascript:alert(1))\n\n![图片](https://example.com/test.png)')
 page.locator('#preview-tab').click()
 assert page.locator('#preview-pane script').count()==0
 assert page.locator('#preview-pane a[href^="javascript:"]').count()==0
 assert page.evaluate('window.hacked') is None
 assert page.locator('#preview-pane strong').inner_text()=='加粗'
 page.locator('#save-draft').click()
 page.locator('#save-result.success').wait_for()
 assert files['new-post']['sha']=='sha-1'
 assert json.loads(base64.b64decode(puts[-1][1]['content']).decode().split('---\n',2)[1])['published'] is False
 assert page.locator('#post-slug').is_disabled()
 assert 'sha' not in puts[0][1]
 page.locator('#publish-post').click();page.locator('#save-result.success').wait_for()
 page.wait_for_function("() => document.querySelector('#publish-post').disabled === false")
 assert puts[-1][1]['sha']=='sha-1'
 assert json.loads(base64.b64decode(puts[-1][1]['content']).decode().split('---\n',2)[1])['published'] is True
 page.locator('#write-tab').click();page.locator('#post-body').fill('正文更新，冲突时不能丢失。')
 fail=True;page.locator('#publish-post').click();page.locator('#reload-conflict').wait_for(state='visible')
 assert page.locator('#post-body').input_value()=='正文更新，冲突时不能丢失。'
 assert '其他页面更新' in page.locator('#save-result').inner_text()
 fail=False
 page.once('dialog',lambda dialog:dialog.accept())
 page.locator('#reload-conflict').click();page.wait_for_function("() => document.querySelector('#save-result').textContent.includes('最新版本')")
 assert '<script>' in page.locator('#post-body').input_value()
 page.locator('#back-list').click();assert page.locator('.post-row').count()==2
 page.locator('#search').fill('一个新的');assert page.locator('.post-row').count()==1
 page.locator('#logout').click();page.locator('#login-view').wait_for(state='visible')
 assert page.evaluate('JSON.stringify([localStorage,sessionStorage])')=='[{},{}]'
 assert page.locator('#post-body').input_value()==''
 page.set_viewport_size({'width':390,'height':844});page.screenshot(path=str(ARTIFACTS/'login-mobile.png'),full_page=True)
 assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
 page.locator('#token').fill('fake-test-token');page.locator('#login-button').click();page.locator('#app-view').wait_for(state='visible')
 page.screenshot(path=str(ARTIFACTS/'list-mobile.png'),full_page=True)
 assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
 page.evaluate("window.dispatchEvent(new PageTransitionEvent('pagehide',{persisted:true}))")
 page.locator('#login-view').wait_for(state='visible')
 assert page.locator('#post-body').input_value()==''
 assert page.locator('#token').input_value()==''
 assert not errors,errors
 print('PASS: authentication success/failure, UTF-8 draft/create/update with SHA, publish, safe preview, conflict recovery, search, logout credential clearance, BFCache credential clearance, mobile overflow and no runtime errors.')
 browser.close()
server.shutdown();server.server_close()
