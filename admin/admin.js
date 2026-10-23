'use strict';
(() => {
  const OWNER = 'WayneLiang94';
  const REPO = 'wayneliang94.github.io';
  const BRANCH = 'master';
  const API = `https://api.github.com/repos/${OWNER}/${REPO}`;
  const CATEGORIES = ['计算机', '数学', '机器人', '学习方法'];
  const $ = (id) => document.getElementById(id);
  const fields = ['post-title', 'post-category', 'post-date', 'post-slug', 'post-summary', 'post-body'];
  let token = '';
  let posts = [];
  let editing = null;
  let dirty = false;
  let busy = false;
  let filter = 'all';
  let generation = 0;
  let controller = new AbortController();

  function status(message, kind = '', target = 'app-status') {
    const node = $(target);
    node.textContent = message;
    node.classList.remove('error', 'success');
    if (kind) node.classList.add(kind);
  }
  function errorMessage(error) {
    if (error.name === 'AbortError') return '操作已取消，请重新登录。';
    if (error.status === 401) return '令牌无效或已过期，请退出后使用新的令牌登录。';
    if (error.status === 403) return 'GitHub 拒绝了请求。请确认令牌仅授权此仓库，并具有 Contents 读写权限；也请检查是否触发访问频率限制。';
    if (error.status === 409 || error.status === 422) return '文章可能已在其他页面更新，或路径已被占用。请保留当前文字，重新载入远端版本后再编辑。';
    if (error instanceof TypeError) return '无法连接 GitHub，请检查网络后重试。当前文字仍在编辑器中。';
    return error.message || '操作失败，请稍后重试。';
  }
  async function api(path, options = {}) {
    const response = await fetch(API + path, {
      ...options,
      signal: controller.signal,
      headers: {
        Accept: 'application/vnd.github+json',
        Authorization: `Bearer ${token}`,
        'X-GitHub-Api-Version': '2022-11-28',
        ...(options.body ? { 'Content-Type': 'application/json' } : {}),
      },
      cache: 'no-store',
    });
    if (!response.ok) {
      const error = new Error(`GitHub 请求失败（${response.status}）。`);
      error.status = response.status;
      throw error;
    }
    return response.status === 204 ? null : response.json();
  }
  function decode64(content) {
    return new TextDecoder('utf-8', { fatal: true }).decode(Uint8Array.from(atob(content.replace(/\s/g, '')), c => c.charCodeAt(0)));
  }
  function encode64(content) {
    const bytes = new TextEncoder().encode(content);
    let binary = '';
    for (let i = 0; i < bytes.length; i += 8192) binary += String.fromCharCode(...bytes.subarray(i, i + 8192));
    return btoa(binary);
  }
  function parsePost(file) {
    const text = decode64(file.content).replace(/^\uFEFF/, '').replace(/\r\n/g, '\n');
    const match = text.match(/^---\n([\s\S]*?)\n---\n([\s\S]*)$/);
    if (!match) throw new Error(`无法读取 ${file.name}：文章头部格式不正确。`);
    let meta;
    try { meta = JSON.parse(match[1]); }
    catch { throw new Error(`无法读取 ${file.name}：文章元数据不是有效 JSON。`); }
    if (!meta || typeof meta !== 'object' || !/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(meta.slug || '') || `${meta.slug}.md` !== file.name) {
      throw new Error(`无法读取 ${file.name}：文章地址与文件名不一致。`);
    }
    if (typeof meta.title !== 'string' || !CATEGORIES.includes(meta.category) || typeof meta.date !== 'string' || typeof meta.summary !== 'string' || typeof meta.published !== 'boolean') {
      throw new Error(`无法读取 ${file.name}：文章信息不完整。`);
    }
    return { ...meta, body: match[2].replace(/^\n/, ''), sha: file.sha, path: file.path };
  }
  async function loadPosts() {
    let files;
    try { files = await api(`/contents/content/posts?ref=${BRANCH}`); }
    catch (error) { if (error.status === 404) return []; throw error; }
    if (!Array.isArray(files)) throw new Error('文章目录格式不正确。');
    // Read through the authenticated Contents endpoint; never follow a response-provided URL with a token.
    const documents = files.filter(f => f.type === 'file' && /^[a-z0-9]+(?:-[a-z0-9]+)*\.md$/.test(f.name));
    const result = [];
    for (let i = 0; i < documents.length; i += 5) {
      const batch = await Promise.all(documents.slice(i, i + 5).map(f => api(`/contents/content/posts/${encodeURIComponent(f.name)}?ref=${BRANCH}`).then(parsePost)));
      result.push(...batch);
    }
    return result.sort((a, b) => b.date.localeCompare(a.date) || a.title.localeCompare(b.title, 'zh-CN'));
  }
  function setBusy(value) {
    busy = value;
    ['save-draft', 'publish-post', 'image-file', 'reload-conflict', 'refresh-posts'].forEach(id => { $(id).disabled = value; });
  }
  function confirmLeave() {
    return !dirty || window.confirm('当前内容尚未保存到 GitHub，确定离开吗？');
  }
  function renderList() {
    const total = posts.length;
    const published = posts.filter(p => p.published).length;
    $('total-count').textContent = total;
    $('sidebar-count').textContent = total;
    $('published-count').textContent = published;
    $('draft-count').textContent = total - published;
    const term = $('search').value.trim().toLowerCase();
    const visible = posts.filter(p => (filter === 'all' || (filter === 'published' ? p.published : !p.published)) && `${p.title} ${p.category} ${p.summary}`.toLowerCase().includes(term));
    const container = $('post-list');
    container.replaceChildren();
    for (const post of visible) {
      const row = document.createElement('button');
      row.type = 'button'; row.className = 'post-row';
      const info = document.createElement('div');
      const heading = document.createElement('h3'); heading.textContent = post.title;
      const description = document.createElement('p'); description.textContent = `${post.category} · /post/${post.slug}/`;
      info.append(heading, description);
      const badge = document.createElement('span'); badge.className = `badge${post.published ? '' : ' draft'}`; badge.textContent = post.published ? '已发布' : '草稿';
      const date = document.createElement('time'); date.dateTime = post.date; date.textContent = post.date;
      const arrow = document.createElement('span'); arrow.className = 'arrow'; arrow.textContent = '↗'; arrow.setAttribute('aria-hidden', 'true');
      row.append(info, badge, date, arrow);
      row.addEventListener('click', () => openEditor(post));
      container.append(row);
    }
    if (!visible.length) {
      const empty = document.createElement('p'); empty.className = 'empty-state';
      empty.textContent = term ? '没有匹配的文章，换个关键词试试。' : filter === 'draft' ? '还没有草稿。给下一个想法留一点空间。' : '还没有文章，开始写第一篇笔记吧。';
      container.append(empty);
    }
  }
  function showList() {
    if (!confirmLeave()) return;
    dirty = false;
    $('list-view').hidden = false; $('editor-view').hidden = true;
    $('view-name').textContent = '全部文章';
    renderList();
  }
  function today() {
    const date = new Date();
    return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;
  }
  function openEditor(post = null) {
    if (busy || !confirmLeave()) return;
    editing = post ? { ...post } : null;
    $('editor-form').reset();
    $('post-title').value = post?.title || '';
    $('post-category').value = post?.category || CATEGORIES[0];
    $('post-date').value = post?.date || today();
    $('post-slug').value = post?.slug || '';
    $('post-slug').disabled = !!post;
    $('post-summary').value = post?.summary || '';
    $('post-body').value = post?.body || '';
    $('reload-conflict').hidden = true;
    $('save-result').replaceChildren();
    $('list-view').hidden = true; $('editor-view').hidden = false;
    $('view-name').textContent = post ? '编辑文章' : '新建文章';
    $('publish-post').textContent = post?.published ? '更新文章 ↗' : '发布文章 ↗';
    dirty = false; togglePreview(false); updateCount();
    $('post-title').focus();
  }
  function updateCount() {
    $('word-count').textContent = `${$('post-body').value.replace(/\s/g, '').length.toLocaleString('zh-CN')} 字`;
  }
  function readForm(published) {
    if (!$('editor-form').reportValidity()) return null;
    const value = {
      title: $('post-title').value.trim(),
      slug: $('post-slug').value.trim(),
      category: $('post-category').value,
      date: $('post-date').value,
      summary: $('post-summary').value.trim(),
      published,
      body: $('post-body').value.trim(),
    };
    if (!value.title || !value.summary || !value.body) throw new Error('请填写标题、摘要和正文，内容不能只有空白。');
    if (!/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(value.slug) || value.slug.length > 90 || value.slug === 'about') throw new Error('文章地址需使用小写字母、数字和短横线，且不能使用保留地址 about。');
    if (!CATEGORIES.includes(value.category)) throw new Error('请选择一个有效分类。');
    const date = new Date(`${value.date}T00:00:00Z`);
    if (!/^\d{4}-\d{2}-\d{2}$/.test(value.date) || Number.isNaN(date.getTime()) || date.toISOString().slice(0, 10) !== value.date) throw new Error('请输入有效的文章日期。');
    if (!editing && posts.some(p => p.slug === value.slug)) throw new Error('此文章地址已存在，请换一个地址。');
    return value;
  }
  function serialize(post) {
    const { title, slug, category, date, summary, published, body } = post;
    return `---\n${JSON.stringify({ title, slug, category, date, summary, published }, null, 2)}\n---\n\n${body}\n`;
  }
  async function save(published) {
    if (busy) return;
    const authGeneration = generation;
    let post;
    try { post = readForm(published); if (!post) return; }
    catch (error) { status(errorMessage(error), 'error', 'save-result'); return; }
    if (!published && editing?.published && !window.confirm('保存为草稿会在下一次成功发布后将这篇文章从博客撤下。确定继续吗？')) return;
    setBusy(true);
    fields.forEach(id => { $(id).readOnly = true; });
    $('post-category').disabled = true;
    status(published ? '正在将文章提交到 GitHub…' : '正在保存草稿到 GitHub…', '', 'save-result');
    try {
      const body = { message: `${published ? 'Publish' : 'Save draft'}: ${post.title}`, branch: BRANCH, content: encode64(serialize(post)) };
      if (editing?.sha) body.sha = editing.sha;
      const result = await api(`/contents/content/posts/${post.slug}.md`, { method: 'PUT', body: JSON.stringify(body) });
      if (authGeneration !== generation) return;
      editing = { ...post, sha: result.content.sha, path: `content/posts/${post.slug}.md` };
      const existing = posts.findIndex(p => p.slug === post.slug);
      if (existing === -1) posts.push({ ...editing }); else posts[existing] = { ...editing };
      posts.sort((a, b) => b.date.localeCompare(a.date));
      dirty = false; $('post-slug').disabled = true;
      $('publish-post').textContent = published ? '更新文章 ↗' : '发布文章 ↗';
      $('reload-conflict').hidden = true;
      const message = document.createElement('span');
      message.textContent = published ? '文章已提交。网站正在等待 GitHub 发布流程更新。' : '草稿已保存到 GitHub，不会显示在博客列表中。';
      const link = document.createElement('a');
      link.href = `https://github.com/${OWNER}/${REPO}/actions`;
      link.target = '_blank'; link.rel = 'noopener'; link.textContent = ' 查看发布记录 ↗';
      $('save-result').className = 'save-result success';
      $('save-result').replaceChildren(message, link);
      renderList();
    } catch (error) {
      if (authGeneration !== generation) return;
      status(errorMessage(error), 'error', 'save-result');
      if (error.status === 409 || error.status === 422) $('reload-conflict').hidden = false;
    } finally {
      if (authGeneration === generation) {
        setBusy(false);
        fields.forEach(id => { $(id).readOnly = false; });
        $('post-category').disabled = false;
      }
    }
  }
  function safeURL(value, image = false) {
    if (/^[\s\u0000-\u001f]/.test(value)) return null;
    try {
      const url = new URL(value, window.location.origin);
      if (url.protocol !== 'https:' && url.protocol !== 'http:' && (image || url.protocol !== 'mailto:')) return null;
      if (image && url.protocol !== 'https:' && url.origin !== window.location.origin) return null;
      return url.href;
    } catch { return null; }
  }
  function appendInline(parent, value) {
    // All text is appended as Text nodes. Never interpret raw HTML from an article.
    const matcher = /(!?\[([^\]\n]*)\]\(([^\s)]+)\)|\*\*([^*\n]+)\*\*|`([^`\n]+)`|\*([^*\n]+)\*)/g;
    let last = 0;
    for (const match of value.matchAll(matcher)) {
      parent.append(document.createTextNode(value.slice(last, match.index)));
      let node;
      if (match[2] !== undefined) {
        const image = match[1].startsWith('!');
        const url = safeURL(match[3], image);
        if (url) {
          node = document.createElement(image ? 'img' : 'a');
          if (image) { node.src = url; node.alt = match[2]; node.loading = 'lazy'; }
          else { node.href = url; node.textContent = match[2]; node.target = '_blank'; node.rel = 'noopener noreferrer'; }
        }
      } else {
        node = document.createElement(match[4] ? 'strong' : match[5] ? 'code' : 'em');
        node.textContent = match[4] || match[5] || match[6];
      }
      parent.append(node || document.createTextNode(match[0]));
      last = match.index + match[0].length;
    }
    parent.append(document.createTextNode(value.slice(last)));
  }
  function renderPreview() {
    const output = $('preview-pane'); output.replaceChildren();
    const title = document.createElement('h1'); title.textContent = $('post-title').value || '未命名文章'; output.append(title);
    const lines = $('post-body').value.replace(/\r/g, '').split('\n');
    let list = null, paragraph = null, code = null;
    for (const line of lines) {
      if (/^```/.test(line)) {
        paragraph = null; list = null;
        if (code) code = null;
        else { const pre = document.createElement('pre'); code = document.createElement('code'); pre.append(code); output.append(pre); }
        continue;
      }
      if (code) { code.append(document.createTextNode(line + '\n')); continue; }
      if (!line.trim()) { paragraph = null; list = null; continue; }
      const heading = line.match(/^(#{1,6})\s+(.+)$/);
      const item = line.match(/^\s*(?:([-*+])|\d+\.)\s+(.+)$/);
      if (heading) {
        paragraph = null; list = null;
        const node = document.createElement(`h${heading[1].length}`); appendInline(node, heading[2]); output.append(node);
      } else if (item) {
        paragraph = null;
        const tag = item[1] ? 'UL' : 'OL';
        if (!list || list.tagName !== tag) { list = document.createElement(tag); output.append(list); }
        const li = document.createElement('li'); appendInline(li, item[2]); list.append(li);
      } else if (/^>\s?/.test(line)) {
        paragraph = null; list = null;
        const node = document.createElement('blockquote'); appendInline(node, line.replace(/^>\s?/, '')); output.append(node);
      } else if (/^(?:---+|\*\*\*+)\s*$/.test(line)) {
        paragraph = null; list = null; output.append(document.createElement('hr'));
      } else {
        list = null;
        if (!paragraph) { paragraph = document.createElement('p'); output.append(paragraph); }
        else paragraph.append(document.createTextNode('\n'));
        appendInline(paragraph, line);
      }
    }
    if (!lines.join('').trim()) { const hint = document.createElement('p'); hint.textContent = '写下正文后，这里会展示预览。'; output.append(hint); }
  }
  function togglePreview(preview) {
    $('writing-pane').hidden = preview; $('preview-pane').hidden = !preview;
    $('write-tab').classList.toggle('selected', !preview); $('preview-tab').classList.toggle('selected', preview);
    $('write-tab').setAttribute('aria-pressed', String(!preview)); $('preview-tab').setAttribute('aria-pressed', String(preview));
    if (preview) renderPreview();
  }
  function insertFormat(kind) {
    const input = $('post-body');
    const text = input.value.slice(input.selectionStart, input.selectionEnd);
    const formats = {
      heading: ['## ', text || '小标题', ''],
      bold: ['**', text || '重点文字', '**'],
      italic: ['*', text || '强调文字', '*'],
      link: ['[', text || '链接文字', '](https://example.com)'],
      code: ['\n```\n', text || '代码', '\n```\n'],
    };
    const parts = formats[kind];
    if (!parts) return;
    const start = input.selectionStart;
    input.setRangeText(parts.join(''), input.selectionStart, input.selectionEnd, 'end');
    input.focus(); input.setSelectionRange(start + parts[0].length, start + parts[0].length + parts[1].length);
    dirty = true; updateCount();
  }
  async function uploadImage(file) {
    if (!file || busy) return;
    const types = { 'image/png': 'png', 'image/jpeg': 'jpg', 'image/webp': 'webp', 'image/gif': 'gif' };
    if (!types[file.type]) { status('请上传 PNG、JPEG、WebP 或 GIF 图片。', 'error', 'save-result'); return; }
    if (file.size > 5 * 1024 * 1024) { status('图片最大支持 5 MB，请压缩后重试。', 'error', 'save-result'); return; }
    const authGeneration = generation;
    setBusy(true); status('正在上传图片到 GitHub…', '', 'save-result');
    try {
      const path = `images/uploads/${Date.now()}-${crypto.randomUUID().slice(0, 8)}.${types[file.type]}`;
      const bytes = new Uint8Array(await file.arrayBuffer());
      let binary = '';
      for (let i = 0; i < bytes.length; i += 8192) binary += String.fromCharCode(...bytes.subarray(i, i + 8192));
      await api(`/contents/${path}`, { method: 'PUT', body: JSON.stringify({ message: 'Upload article image', branch: BRANCH, content: btoa(binary) }) });
      if (authGeneration !== generation) return;
      const input = $('post-body');
      input.setRangeText(`\n![图片说明](/${path})\n`, input.selectionStart, input.selectionEnd, 'end');
      dirty = true; updateCount(); status('图片已上传，链接已插入正文。图片将在发布流程完成后显示。', 'success', 'save-result');
    } catch (error) { if (authGeneration === generation) status(errorMessage(error), 'error', 'save-result'); }
    finally { if (authGeneration === generation) { setBusy(false); $('image-file').value = ''; } }
  }
  $('login-form').addEventListener('submit', async (event) => {
    event.preventDefault();
    if ($('login-button').disabled) return;
    token = $('token').value.trim(); $('token').value = '';
    if (!token) return;
    controller.abort(); controller = new AbortController();
    const authGeneration = ++generation;
    $('login-button').disabled = true; status('正在验证仓库访问权限…', '', 'login-status');
    try {
      const repository = await api('');
      if (repository.permissions && repository.permissions.push === false) throw new Error('当前账号没有此仓库的写入权限，无法使用写作后台。');
      posts = await loadPosts();
      if (authGeneration !== generation) return;
      $('login-view').hidden = true; $('app-view').hidden = false;
      status(''); status('', '', 'login-status'); dirty = false;
      $('list-view').hidden = false; $('editor-view').hidden = true;
      renderList();
    } catch (error) {
      if (authGeneration !== generation) return;
      token = ''; status(errorMessage(error), 'error', 'login-status');
    } finally { if (authGeneration === generation) $('login-button').disabled = false; }
  });
  function resetSession(message = '') {
    ++generation; controller.abort(); controller = new AbortController(); token = ''; posts = []; editing = null; dirty = false;
    setBusy(false); $('editor-form').reset(); $('post-slug').disabled = false;
    fields.forEach(id => { $(id).readOnly = false; }); $('post-category').disabled = false;
    $('app-view').hidden = true; $('login-view').hidden = false; $('login-button').disabled = false;
    $('token').value = '';
    $('preview-pane').replaceChildren(); $('post-list').replaceChildren(); $('save-result').replaceChildren();
    status(''); status(message, message ? 'success' : '', 'login-status');
  }
  $('logout').addEventListener('click', () => {
    if (!confirmLeave()) return;
    resetSession('已退出登录。'); $('token').focus();
  });
  // A browser may preserve JavaScript memory in its back/forward cache. Clear
  // authentication when leaving, so returning to a cached page requires login.
  window.addEventListener('pagehide', () => resetSession());
  ['new-post', 'create-post'].forEach(id => $(id).addEventListener('click', () => openEditor()));
  ['all-posts', 'back-list'].forEach(id => $(id).addEventListener('click', () => { if (!busy) showList(); }));
  $('search').addEventListener('input', renderList);
  document.querySelectorAll('[data-filter]').forEach(button => button.addEventListener('click', () => {
    filter = button.dataset.filter;
    document.querySelectorAll('[data-filter]').forEach(b => b.classList.toggle('selected', b === button));
    renderList();
  }));
  $('refresh-posts').addEventListener('click', async () => {
    if (busy) return;
    const authGeneration = generation;
    setBusy(true); status('正在刷新文章…');
    try {
      const result = await loadPosts();
      if (authGeneration !== generation) return;
      posts = result; renderList(); status('文章列表已更新。', 'success');
    } catch (error) { if (authGeneration === generation) status(errorMessage(error), 'error'); }
    finally { if (authGeneration === generation) setBusy(false); }
  });
  $('editor-form').addEventListener('submit', event => event.preventDefault());
  fields.forEach(id => $(id).addEventListener('input', () => { dirty = true; updateCount(); }));
  $('write-tab').addEventListener('click', () => togglePreview(false));
  $('preview-tab').addEventListener('click', () => togglePreview(true));
  document.querySelectorAll('[data-format]').forEach(button => button.addEventListener('click', () => { if (!busy) insertFormat(button.dataset.format); }));
  $('save-draft').addEventListener('click', () => save(false));
  $('publish-post').addEventListener('click', () => save(true));
  $('image-file').addEventListener('change', () => uploadImage($('image-file').files[0]));
  $('reload-conflict').addEventListener('click', async () => {
    if (busy || !window.confirm('重新载入会替换编辑器中的文字。请先复制需要保留的内容，确定继续吗？')) return;
    const slug = editing?.slug || $('post-slug').value;
    const authGeneration = generation;
    setBusy(true);
    try {
      const post = parsePost(await api(`/contents/content/posts/${encodeURIComponent(slug)}.md?ref=${BRANCH}`));
      if (authGeneration !== generation) return;
      setBusy(false); dirty = false; openEditor(post); status('已载入 GitHub 上的最新版本。', 'success', 'save-result');
    } catch (error) { if (authGeneration === generation) status(errorMessage(error), 'error', 'save-result'); }
    finally { if (authGeneration === generation) setBusy(false); }
  });
  window.addEventListener('beforeunload', event => { if (dirty || busy) { event.preventDefault(); event.returnValue = ''; } });
})();
