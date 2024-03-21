# `notionexportstatic` is a script for dowloading pages from Notion API as JSON and generating static HTML/Markdown

- can be used for backing up Notion pages (along with child pages recursively) 
- can be used as a Static Site Generator (SSG) running in GitHub Actions and deploying to GitHub Pages for publishing Notion pages as a website with a custom domain
- supports three output file formats: JSON/HTML/Markdown
- supports two output modes: single file and flat directory
- supports downloading the assets and embedding them in the output files or in output directory
- supports loading all options from a config in JSON format or as command-line arguments for overriding the config
- supports specifying HTML header/footer snippets for customizing the output (Cookie Notice, Google Analytics, KaTeX rendering)
- generates basic HTML meta og SEO tags

Functions for retrieving from Notion API are based on https://github.com/MerkulovDaniil/notion4ever

# Usage examples

```shell
NOTION_TOKEN=secret_...
NOTION_ROOT_PAGE_ID=notionrootpageid32alphanumerical
NOTION_CHILD_PAGE_ID=notionchildpageid32alphanumerica

# extract all snippets used by a theme
python ./notionexportstatic/minima.py --snippets-dir ./_snippets

# download all child pages recursively starting from a root page id
python ./notionexportstatic/notionexportstatic.py --notion-token $NOTION_TOKEN --notion-page-id $NOTION_ROOT_PAGE_ID -o test.json --download-assets --extract-mode=single.json
# download all child pages recursively starting from a child page id
python ./notionexportstatic/notionexportstatic.py --notion-token $NOTION_TOKEN --notion-page-id $NOTION_CHILD_PAGE_ID -o $NOTION_CHILD_PAGE_ID.json --download-assets --extract-mode=single.json

# render html
#python ./notionexportstatic/notionexportstatic.py -i test.json -o test.html --edit-url 'https://www.notion.so/tokot/{page_id_no_dashes}'
#python ./notionexportstatic/notionexportstatic.py -i everything.json -o everything.html --html-details-open --extract-mode single
#python ./notionexportstatic/notionexportstatic.py -i everything.json -o ./flat.html/ --extract-mode flat.html --config-json _config.json 
#python ./notionexportstatic/notionexportstatic.py -i everything.json -o ./flat/ --extract-mode flat.html --config-json _config.json
#python ./notionexportstatic/notionexportstatic.py -i everything.json -o ./flat/ --extract-mode flat/index.html --config-json _config.json --html-details-open --toc --html-link-to-page-index-html --sitemap-xml ./flat/sitemap.xml 
#python ./notionexportstatic/notionexportstatic.py -i everything.json -o ./single/index.html --sitemap-xml ./single/sitemap.xml --extract-mode single.json --config-json __config.json --html-details-open  --toc --html-columnlist-disable --extract-mode=single.html --snippets-dir _snippets
#chrome --headless --print-to-pdf=./single/index.pdf ./single/index.html

# render markdown
#python ./notionexportstatic/notionexportstatic.py -i everything.json -o ./flat.md/ --extract-mode flat.md --config-json _config.json  --extract-assets --sitemap-xml ./flat.md/sitemap.xml --base-url 'https://vadimkantorov.github.io/eriadilos-lixe/markdown/' --base-url-removesuffix .md --edit-url 'https://github.com/vadimkantorov/eriadilos-lixe/edit/gh-pages/markdown/{page_slug}.md'
#python ./notionexportstatic/notionexportstatic.py -i everything.json -o ./single/index.md --sitemap-xml ./single/sitemap.xml --extract-mode single.md --config-json _config.json --toc --edit-url 'https://github.com/vadimkantorov/eriadilos-lixe/edit/gh-pages/markdown/{page_slug}.md'
```

# TODO
- cookies notice: snippet for html and for markdown
- katex for equations
- google analytics 
- option to export html templates and use templates
- option for generating or not toc for markdown
- nanojekyll theme using stock minima templates

# License
MIT
