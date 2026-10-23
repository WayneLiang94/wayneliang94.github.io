# WayneLAB

以计算机、数学、机器人与学习方法为主题的静态博客。

## 本地开发

需要 Python 3，无第三方依赖。

```sh
python3 scripts/build.py
python3 -m http.server 8000 --bind 127.0.0.1
```

在 `config/articles.json` 中编辑文章的标题、分类、日期、摘要与 HTML 正文，再运行构建命令。构建会同步生成首页、文章、分类、归档、RSS、Markdown 写作文件与 Gridea 元数据。全站样式位于 `styles/main.css`。当前页面由此脚本维护，旧 Gridea 主题仅作历史素材保留，直接从客户端重新生成会覆盖当前设计。

发布前运行 `python3 scripts/check.py` 检查内部链接、HTML 基本结构与 RSS。将生成后的仓库发布到 GitHub Pages 才会更新线上网站。
