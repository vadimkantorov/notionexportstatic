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
|`page`|`.notion-page-block`|`<h1>`|
|`page`|`.notion-page-like-icon`|`<a>`|
|`page`|`.notion-page-like-edit-icon`|`<a>`|
|`page`|`.notion-page`|`<article>`|
|`toggle`|`.notion-toggle-block`|`<details>`|
|`table_of_contents`|`.notion-table_of_contents-block`|`<ul>`|
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
||||
||`.notion-topbar`||
||`.notion-code-inline`||
||`.notion-toggle-like`||
||`.notion-heading-like-icon`||
||`.notion-heading-like`||
||`.notion-page-like-icon`||
||`.notion-page-like-edit-icon`||
||`.notion-page-cover`||
||`.notion-record-icon`||
||`.notion-page-block-datetime-published`||
||`.notion-page-content`||
||`.notion-table_of_contents-site-page-list`||
||`.notion-table_of_contents-site-page-item`||
||`.notion-table_of_contents-site`||
||`.notion-table_of_contents-site-header`||
||`.notion-table_of_contents-heading`||
||`.notion-table_of_contents-{effective_heading_type}`||
||`.language-{language}`||
||`.notion-color-{color}`||


# [Theme **minima.py**](https://github.com/jekyll/minima) CSS classes:

| Element       | CSS class     |
| ------------- | ------------- |
||`.post`|
||`.post-title`|
||`.post-content`|
||`.page-link`|
||`.post-header`|
||`.site-header`|
||`.site-nav`|
||`.nav-trigger`|
||`.menu-icon`|
||`.trigger`|
||`.wrapper`|
||`.dt-published`|

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
