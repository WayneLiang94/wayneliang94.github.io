# WayneLAB

个人博客与文章后台，保留 GitHub Pages 托管。后台用 GitHub 访问令牌登录，在浏览器中直接调用 GitHub API；不需要额外的服务器或数据库。页面由 Markdown 自动构建，文章链接保持 `/post/<slug>/`。

## 写文章

1. 打开 [文章后台](https://wayneliang94.github.io/admin/)。
2. 在 [GitHub 创建 fine-grained personal access token](https://github.com/settings/personal-access-tokens/new)，Resource owner 选择自己的账号，仅选择 `wayneliang94.github.io` 仓库，Repository permissions 赋予 **Contents: Read and write**（Metadata read 自动提供）。设置适当有效期。账号必须具有该仓库写入权限。
3. 把令牌粘贴到后台登录框，不要写入仓库或发送到聊天。登录凭据仅保留在当前页面内存中，不进入浏览器持久存储；刷新后需重新登录。
4. 新建或编辑文章，填写标题、分类、日期、摘要和 Markdown 正文。新文章的地址标识使用英文小写、数字与短横线；已有文章地址不可改，以保留旧链接。
5. 保存草稿或发布。后台会将 Markdown 提交至 `master`，GitHub Actions 自动构建并部署。提交成功和网站上线是两个状态，可以在 [Actions](https://github.com/WayneLiang94/wayneliang94.github.io/actions) 查看结果。

**公开仓库中的草稿不是私密内容**：它们不在博客、RSS 和搜索中展示，但任何能读取仓库的人都可以看到源码和提交历史。不要写入私密信息。后台预览用于写作，最终以发布后的 Markdown 渲染为准。

令牌过期可重新生成；注销、离开后台后清除当前登录。若仓库保护规则禁止直接写 `master`，应调整写作方案使用 PR，当前后台会显示错误，不会绕过保护规则。并发修改会提示冲突，重新加载后再修改，避免覆盖其他版本。

## 首次启用自动发布

在 [仓库 Pages 设置](https://github.com/WayneLiang94/wayneliang94.github.io/settings/pages) 将 **Build and deployment → Source** 设为 **GitHub Actions**。保留仓库的 Actions 运行权限，以及 `github-pages` 环境允许 `master` 部署。

每次提交（包括后台保存文章）触发 `.github/workflows/publish.yml`。该流程安装经哈希锁定的依赖、运行测试、构建 `_site`、验证链接、上传并部署 Pages artifact。切换来源能避免旧的分支发布流程与新的构建流程互相覆盖。不需要在仓库 Secrets 中保存写作令牌，Actions 使用 GitHub 自带的短期令牌。

如果 Pages 来源尚未切换，直接推送的根目录页面仍可供旧的分支模式发布，但后台新增文章需要新的构建部署流程，不能把一次仓库提交当作部署成功。

## 本地开发

需要 Python 3.12 或兼容版本。

```sh
python3 -m venv .venv
.venv/bin/pip install --require-hashes -r requirements.txt
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python scripts/build.py --output _site
.venv/bin/python scripts/check.py --root _site
python3 -m http.server 8000 --bind 127.0.0.1 --directory _site
```

文章唯一来源是 `content/posts/*.md`。文件使用 JSON front matter（`---` 包围的 JSON 对象）和 Markdown 正文：

```markdown
---
{
  "slug": "my-first-note",
  "title": "第一篇笔记",
  "category": "计算机",
  "date": "2026-10-23",
  "summary": "一段简短的摘要。",
  "published": true
}
---

## 从一个问题开始

在这里写正文，支持 **加粗**、列表、链接、图片、表格与代码块。
```

分类支持计算机、数学、机器人与学习方法。文件名必须与 slug 一致，`about` 为保留地址。草稿使用 `"published": false`。构建前验证必填字段、日期和文件路径，过滤正文中的脚本、事件属性与危险链接。

后台浏览器集成测试可在安装 Playwright 与 Chromium 的开发环境运行 `python tests/browser_admin.py`；测试使用模拟 API，不需要真实令牌。

`styles/main.css` 控制前台，`admin/` 为独立写作应用，`scripts/build.py` 为生成器。`posts/`、`themes/` 和旧的 Gridea 元数据是历史资料，不参与发布。请勿从旧 Gridea 客户端生成并覆盖当前站点。部署 artifact 不包含仓库源码、历史资料或草稿源文件。
