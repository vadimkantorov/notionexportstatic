# Python script for dowloading pages from Notion API as JSON and generating static HTML / Markdown

- can be used for backing up Notion pages (along with child pages recursively) 
- can be used as a Static Site Generator (SSG) running in GitHub Actions and deploying to GitHub Pages for publishing Notion pages as a website with a custom domain
- can be used for importing / syncing Notion page content into an existing Markdown-based website or for content migration
- can be used as a module / function, not just from command line
- supports three output file formats: JSON / HTML / Markdown
- supports two output modes: single file and flat directory
- supports downloading the assets and embedding them in the output files or in output directory
- supports loading all options from a config in JSON format or as command-line arguments for overriding the config
- supports specifying HTML header / footer snippets for customizing the output (Cookie Notice, Google Analytics, KaTeX rendering)
- supports simple and versatile CSS-based customization of the HTML output
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

# Example `_config.json` file
```json
{
    "slugs": {
        "some_page_id" : "index",
        "some_other_page_id" : "my_page_slug"
    }
}
```

# Example `_config.yml` file for https://github.com/jekyll/minima theme
```yaml
title: notionexportstatic
author:
  name: Vadim Kantorov
  email: vadimkantorov@gmail.com
description: "notionexportstatic example website"

optional_front_matter:
  remove_originals: true
  collections: true

markdown: CommonMarkGhPages
commonmark:
  options: ["UNSAFE", "SMART", "FOOTNOTES"]

include: ['markdown'] #, '_assets']
defaults:
  - scope:
      path: "markdown"
    values:
      layout: "page"
      permalink: /markdown/:basename/
  - scope:
      path: "markdown/index.md"
    values:
      layout: "page"
      permalink: /markdown/

remote_theme: jekyll/minima
#minima:
#  skin: classic
```

# Example `.github/workflows/render_notion_pages.yml`
```yaml
name: render_notion_pages
on: workflow_dispatch
# https://github.blog/changelog/2021-04-20-github-actions-control-permissions-for-github_token/
permissions: write-all

jobs:
  render_notion_pages:
    runs-on: ubuntu-22.04
    steps:
      - uses: browser-actions/setup-chrome@v1

      - uses: actions/checkout@v4
      - name: Clone notionexportstatic
        run: git clone https://github.com/vadimkantorov/notionexportstatic

      - name: Generate HTML and PDF
        run: |
          # generate an everything HTML and PDF
          mkdir -p ./single/ ./flat/ ./markdown/
          python ./notionexportstatic/notionexportstatic.py -i everything.json -o ./single/index.html --config-json _config.json --extract-mode single.html  --html-details-open --html-columnlist-disable --toc
          chrome --headless --print-to-pdf=./single/index.pdf ./single/index.html

          # generate flat HTML
          python ./notionexportstatic/notionexportstatic.py -i everything.json -o ./flat/ --config-json _config.json --extract-mode flat.html  --html-details-open --html-columnlist-disable

          # generate flat Markdown
          python ./notionexportstatic/notionexportstatic.py -i everything.json -o ./markdown/ --config-json _config.json --extract-mode flat.md --html-details-open  --extract-assets  --sitemap-xml ./markdown/sitemap.xml --base-url https://vadimkantorov.github.io/notionexportstatic/markdown/ --base-url-removesuffix=.md
          python ./notionexportstatic/notionexportstatic.py -i everything.json -o ./markdown/single.md --config-json _config.json --extract-mode single.md --html-details-open --html-columnlist-disable  --toc

      - name: Push HTML and Markdown and PDF
        run: |
          git config user.name 'Vadim Kantorov'
          git config user.email 'vadimkantorov@gmail.com'
          git add -f -A ./single/ ./flat/ ./markdown/
          git commit -a -m ...
          git push
```

# Example `.github/workflows/import_notion_page_as_markdown.yml`
```yaml
name: import_notion_page_as_markdown
on:
  workflow_dispatch:
    inputs:
      commaseparatednotionpageids:
        description: 'comma separated notion page ids'
        required: false
        default: ''

# https://github.blog/changelog/2021-04-20-github-actions-control-permissions-for-github_token/
permissions: write-all

jobs:
  import_notion_page_as_markdown:
    runs-on: ubuntu-22.04
    steps:
      - uses: actions/checkout@v4

      - name: Clone notionexportstatic
        run: git clone https://github.com/vadimkantorov/notionexportstatic

      - name: Import Markdown
        run: |
          python ./notionexportstatic/notionexportstatic.py --notion-page-id ${{ github.event.inputs.commaseparatednotionpageids }} -o ./markdown/ --config-json _config.json --extract-mode flat.md
        env:
          NOTION_TOKEN: ${{ secrets.NOTION_TOKEN }}

      - name: Push HTML and Markdown and PDF
        run: |
          git config user.name 'Vadim Kantorov'
          git config user.email 'vadimkantorov@gmail.com'
          git add -f -A ./markdown/
          git commit -a -m ...
          git push
```

# License
MIT
