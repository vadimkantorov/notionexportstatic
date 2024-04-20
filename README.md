# Python script for dowloading pages from Notion API as JSON and generating static HTML / Markdown

- can be used for backing up Notion pages (along with child pages recursively) 
- can be used as a Static Site Generator (SSG) running in GitHub Actions and deploying to GitHub Pages for publishing Notion pages as a website with a custom domain
- can be used for importing / syncing Notion page content into an existing Markdown-based website or for content migration
- can be used as a module / function, not just from command line
- supports three output file formats: JSON / HTML / Markdown
- supports two output modes: single file and flat directory
- supports downloading the assets and embedding them in the output files or in output directory
- supports loading all options from a config in JSON format or as command-line arguments for overriding the config
- supports custom HTML header / footer snippets for customizing the output (Cookie Notice, Google Analytics, KaTeX rendering)
- supports custom CSS styling of the HTML output (basic CSS is based on https://github.com/jekyll/minima theme)
- supports custom page slugs / page urls
- generates sitemap.xml and basic HTML meta og SEO tags
- single-file HTML output mode can be used for rendering a PDF with all content from Notion workspace in a single PDF file for backup purposes

Functions for retrieving from Notion API are based on https://github.com/MerkulovDaniil/notion4ever

For full understanding of supported features, please ask questions in [issues](../../issues/) or read the code.

# Usage

```shell
# prepare Notion token from a created integration and a Notion page ID (no dashes)
NOTION_TOKEN=secret_...
NOTION_ROOT_PAGE_ID=notionrootpageid32alphanumeric00
NOTION_CHILD_PAGE_ID=notionchildpageid32alphanumeric0

# prepare ./notionexportstatic/
git clone https://github.com/vadimkantorov/notionexportstatic

# show full command line option help manual
python ./notionexportstatic/notionexportstatic.py --help

# extract all snippets used by a theme
python ./notionexportstatic/minima.py --snippets-dir ./_snippets

# download all child pages recursively starting from a root page id, downloading images, pdfs and files by default; you can also just use the NOTION_TOKEN environment variable for passing the token (useful for passing it in as GitHub Actions secret)
python ./notionexportstatic/notionexportstatic.py --notion-token $NOTION_TOKEN --notion-page-id $NOTION_ROOT_PAGE_ID -o ./everything.json --extract-mode=single.json
# download all child pages recursively starting from a child page id
python ./notionexportstatic/notionexportstatic.py --notion-token $NOTION_TOKEN --notion-page-id $NOTION_CHILD_PAGE_ID -o $NOTION_CHILD_PAGE_ID.json --extract-mode=single.json

# generate single.html: all pages in one single HTML for simple search and backup purposes
python ./notionexportstatic/notionexportstatic.py -i ./everything.json -o ./single.html --extract-mode single.html --html-details-open --html-columnlist-disable --toc
# convert HTML to PDF using headless Chrome / Chromium
chrome --headless --print-to-pdf=./single.html.pdf ./single.html

# generate HTML in ./flat/my_page_slug/index.html file structure, suitable for publishing to GitHub Pages site (urls will be ./flat/my_page_slug/), page slugs are specified in _config.json (see example of _config.json below)
python ./notionexportstatic/notionexportstatic.py -i ./everything.json -o ./flat/  --sitemap-xml ./flat/sitemap.xml --config-json _config.json --extract-mode flat/index.html  --html-details-open --html-link-to-page-index-html --toc 
# generates ./flat/my_page_slug.html file structure, suitable for browsing locally without a web server
python ./notionexportstatic/notionexportstatic.py -i ./everything.json -o ./flat.html/ --config-json _config.json --extract-mode flat.html

# generate Markdown in ./flat.md/my_page_slug.md file structure, suitable for using with Markdown-based Static Site Generators like Jekyll (see example of _config.yml below for Jekyll configuration) and running it on GitHub Pages / Actions
python ./notionexportstatic/notionexportstatic.py -i ./everything.json -o ./flat.md/ --sitemap-xml ./flat.md/sitemap.xml --config-json _config.json  --extract-mode flat.md  --extract-assets  --base-url-removesuffix .md --base-url 'https://vadimkantorov.github.io/notionexportstatic/markdown/' --edit-url 'https://github.com/vadimkantorov/notionexportstatic/edit/gh-pages/markdown/{page_slug}.md'
# generate Markdown in ./flat.md/my_page_slug.md for a single page, useful for re-importing some Notion pages into an existing Markdown-based website structure
python ./notionexportstatic/notionexportstatic.py -i $NOTION_CHILD_PAGE_ID.json -o ./flat.md/my_page_slug.md --sitemap-xml ./flat.md/sitemap.xml --config-json _config.json --extract-mode single.md --edit-url 'https://github.com/vadimkantorov/notionexportstatic/edit/gh-pages/markdown/{page_slug}.md' 
```

- Example [`_config.json`](../gh-pages/_config.json) file for page slugs and other options
- Example [`_config.yml`](../gh-pages/_config.yml) file for https://github.com/jekyll/minima theme
- Example [`.github/workflows/render_notion_pages.yml`](../gh-pages/.github/workflows/render_notion_pages.yml)
- Example [`.github/workflows/import_notion_page_as_markdown.yml`](../gh-pages/.github/workflows/import_notion_page_as_markdown.yml)

# Supported [Notion blocks](https://developers.notion.com/reference/block) and used HTML tags / CSS classes

| Notion block  | CSS class     | HTML tag      |
| ------------- | ------------- | ------------- |
||`.notion-block`||
||`.notion-topbar`||
|`page`|`.notion-page-block`|`<h1>`|
|`page`|`.notion-page-like-icon`|`<a>`|
|`page`|`.notion-page-like-edit-icon`|`<a>`|
|`page`|`.notion-page`|`<article>`|
|`page`|`.notion-record-icon`||
|`page`|`.notion-page-like-edit-icon`||
|`page`|`.notion-page-cover`||
|`page`|`.notion-page-block-datetime-published`||
|`page`|`.notion-page-content`||
|`toggle`|`.notion-toggle-like`||
|`toggle`|`.notion-toggle-block`|`<details>`|
|`table_of_contents`|`.notion-table_of_contents-block`|`<ul>`|
|`table_of_contents`|`.notion-table_of_contents-site-page-list`||
|`table_of_contents`|`.notion-table_of_contents-site-page-item`||
|`table_of_contents`|`.notion-table_of_contents-site`||
|`table_of_contents`|`.notion-table_of_contents-site-header`||
|`table_of_contents`|`.notion-table_of_contents-heading`||
|`table_of_contents`|`.notion-table_of_contents-{effective_heading_type}`||
|`table`|`.notion-table-block`|`<table>`|
|`video`|`.notion-video-block`|`<video>`, `<iframe>`|
|`image`|`.notion-image-block`|`<img>`|
|`embed`|`.notion-embed-block`|`<figure><iframe>`|
|`bookmark`|`.notion-bookmark-block`|`<a><figure>`|
|`paragraph`|`.notion-text-block`|`<p>`, `<br>`|
|`mention`|`.notion-page-mention-token`|`<a>`|
|`mention`|`.notion-database-mention-token`|`<a>`|
|`mention`|`.notion-link-mention-token`|`<a>`|
|`mention`|`.notion-user-mention-token`|`<strong>`|
|`mention`|`.notion-date-mention-token`|`<strong>`|
|`link_to_page`|`.notion-alias-block`|`<a>`|
|`unsupported`|`.notion-unsupported-block`|`<!-- -->`, `<br>`|
|`divider`|`.notion-divider-block`|`<hr>`|
||`.notion-heading-like`||
||`.notion-heading-like-icon`||
|`heading_1`|`.notion-header-block`|`<h1>`|
|`heading_2`|`.notion-sub_header-block`|`<h2>`|
|`heading_3`|`.notion-sub_sub_header-block`|`<h3>`|
|`column_list`|`.notion-column_list-block`|`<div>`|
|`column_list`|`.notion_column_list-block-vertical`|`<div>`|
|`column`|`.notion-column-block`|`<div>`|
|`bulleted_list_item`|`.notion-bulleted_list-block`|`<ul>`|
|`numbered_list_item`|`.notion-numbered_list-block`|`<ol>`|
|`quote`|`.notion-quote-block`|`<blockquote>`|
|`code`|`.notion-code-block`|`<pre><code>`|
|`code`|`.notion-code-inline`||
|`code`|`.language-{language}`||
|`to_do`|`.notion-to_do-block`|`<div><input type="checkbox">`|
|`equation`|`.notion-equation-block`|`<code>`|
|`callout`|`.notion-callout-block`|`<div>`|
|`pdf`|`.notion-pdf-block`|`<figure><a>`|
|`file`|`.notion-file-block`|`<figure><a>`|
|`link_preview`|`.notion-link_preview-block`|`<a>`|
|`breacrumb`|`.notion-breadcrumb-block`|`<div>`|
|`template`|`.notion-template-block`|`<figure>`|
|`child_database`|`.notion-child_database-block`|`<figure>`|
|`synced_block`|`.notion-synced_block-block`|`<figure>`|
| **Notion colors light theme** | | | 
| \$\color{#37352F}{\texttt{37352F}}$ | `.notion-color-default`| `#37352F` |
| \$\color{#FFFFFF}{\texttt{FFFFFF}}$ | `.notion-color-default_background`| `#FFFFFF` |
| \$\color{#9B9A97}{\texttt{9B9A97}}$ | `.notion-color-gray`   | `#9B9A97` | 
| \$\color{#EBECED}{\texttt{EBECED}}$ | `.notion-color-gray_background`   | `#EBECED` |
| \$\color{#64473A}{\texttt{64473A}}$ | `.notion-color-brown`  | `#64473A` | 
| \$\color{#E9E5E3}{\texttt{E9E5E3}}$ | `.notion-color-brown_background`  | `#E9E5E3` |
| \$\color{#D9730D}{\texttt{D9730D}}$ | `.notion-color-orange` | `#D9730D` |  
| \$\color{#FAEBDD}{\texttt{FAEBDD}}$ | `.notion-color-orange_background` | `#FAEBDD` |
| \$\color{#DFAB01}{\texttt{DFAB01}}$ | `.notion-color-yellow` | `#DFAB01` | 
| \$\color{#FBF3DB}{\texttt{FBF3DB}}$ | `.notion-color-yellow_background` | `#FBF3DB` |
| \$\color{#0F7B6C}{\texttt{0F7B6C}}$ | `.notion-color-green`  | `#0F7B6C` | 
| \$\color{#DDEDEA}{\texttt{DDEDEA}}$ | `.notion-color-green_background`  | `#DDEDEA` |
| \$\color{#0B6E99}{\texttt{0B6E99}}$ | `.notion-color-blue`   | `#0B6E99` | 
| \$\color{#DDEBF1}{\texttt{DDEBF1}}$ | `.notion-color-blue_background`   | `#DDEBF1` |
| \$\color{#6940A5}{\texttt{6940A5}}$ | `.notion-color-purple` | `#6940A5` | 
| \$\color{#EAE4F2}{\texttt{EAE4F2}}$ | `.notion-color-purple_background` | `#EAE4F2` |
| \$\color{#AD1A72}{\texttt{AD1A72}}$ | `.notion-color-pink`   | `#AD1A72` | 
| \$\color{#F4DFEB}{\texttt{F4DFEB}}$ | `.notion-color-pink_background`   | `#F4DFEB` |
| \$\color{#E03E3E}{\texttt{E03E3E}}$ | `.notion-color-red`    | `#E03E3E` | 
| \$\color{#FBE4E4}{\texttt{FBE4E4}}$ | `.notion-color-red_background`    | `#FBE4E4` |

# [Theme **minima.py**](https://github.com/jekyll/minima) CSS classes:

| Element       | CSS class     |
| ------------- | ------------- |
||`.wrapper`|
||`.post-list-heading`|
||`.post-list`|
||`.post-meta`|
||`.post-link`|
||`.post-header`|
||`.post-title`|
||`.post-content`|
|||
|||
|||
||`.page-content`|
||`.page-heading`|
||`.page-link`|
|||
|||
|||
||`.site-header`|
||`.site-title`|
||`.site-footer`|
||`.site-nav`|
||`.nav-trigger`|
||`.menu-icon `|
||`.trigger`|
|||
|||
|||
||`.feed-subscribe`|
||`.contact-list`|
||`.social-links`|
||`.social-media-list`|
||`.svg-icon`|
||`.pagination`|
||`.pager-edge`|
||`.highlight`|
||`.highlighter-rouge`|
||`.orange`|
||`.grey`|
|||
|||
|||
||`.footer-heading`|
||`.footer-col-wrapper`|
||`.footer-col`|
||`.footer-col-1`|
||`.footer-col-2`|
||`.footer-col-3`|

# References
- https://github.com/jekyll/minima
- https://github.com/vadimkantorov/minimacss 
- https://developer.twitter.com/en/docs/twitter-for-websites/cards/overview/markup
- https://katex.org/docs/browser

# Notes
For markdown2html conversion in Python:
```python
# pip install markdown   markdown-captions markdown-checklist pymdown-extensions mdx_truly_sane_lists
html_content = markdown.markdown(md_content, extensions = ["meta", "tables", "mdx_truly_sane_lists", "markdown_captions", "pymdownx.tilde", "pymdownx.tasklist", "pymdownx.superfences"], extension_configs = {'mdx_truly_sane_lists': { 'nested_indent': 4, 'truly_sane': True, }, "pymdownx.tasklist":{"clickable_checkbox": True, } })
```

# License
MIT
