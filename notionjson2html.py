# TODO: embed resources by default or follow extracted nested/flat resources if extracted?
# TODO: fix links in flat/nested mode: need to have some page link and resource resolver, maybe discovered if pages.json is not helpful: in-tree, out-tree? (typically with json-s, it would be in-tree)
# TODO: for a single or nested mode, what to do with unresolved link_to_pages? extend slug.json info? or scan the current directory?
# TODO: support recursive conversion of all json to html? or maybe example with find -exec?
# TODO: prepare_and_extract_assets: first load in memory? or copy directly to target dir?

# TODO: link_to_page: find the page path in relation to the current path, need to know flat or flat.html; allow passing url-style explicitly, if not set, detect if slug.html or if /slug/ exists already and maybe have some url-style as default
# TODO: link_to_page: use plain_text for page title
# TODO: link_like: basename -> urlparse + format link to page if link url/href starts from '/' in richtext2html/text_link: 
# TODO: htmlescape for captions
# TODO: bookmark: generate social media card: title, maybe description, favicon
# TODO: image: fixup url from assets; when to embed image, html.escape for caption

# TODO: main: nested: update only a single page on disk? or all nested dirs as well? in general, can there be a nested page with multi-page? add extra switch? fix page_ids = to include all child_pages recursively?
# TODO: heading_like: use header slugs as valid anchor targets
# TODO: dump to stderr all URLs, allow verification for 404?

# TODO: child_database: and child_page -> mentions
# TODO: add cmdline option for pages/headings links to notion ✏️

# https://jeroensormani.com/automatically-add-ids-to-your-headings/
# https://github.com/themightymo/auto-anchor-header-links/blob/master/auto-header-anchor-links.php
# https://docs.super.so/super-css-classes

import os
import sys
import json
import html
import time
import datetime
import copy
import base64
import argparse
import functools
import urllib.parse
import importlib

def richtext2html(richtext, ctx = {}, title_mode=False) -> str:
    # https://www.notion.so/help/customize-and-style-your-content#markdown
    # https://developers.notion.com/reference/rich-text

    if isinstance(richtext, list):
        return ''.join(richtext2html(r, ctx, title_mode = title_mode) for r in richtext).strip()
    
    plain_text = richtext['plain_text']
    
    if richtext['type'] == 'mention':
        return mention(richtext, ctx)

    if richtext['type'] == 'equation':
        return f'<code class="notion-equation-inline">{plain_text}</code>'
    
    assert richtext['type'] == 'text'
    
    color     = lambda content, color: f'<span style="color:{color}">{content}</span>'
    text_link = lambda kwargs: '<a href="{url}">{caption}</a>'.format(caption = kwargs['content'], url = kwargs['link']['url'])
    
    bold = lambda content: content if ((not content) or content.isspace()) else  (content[0] * (bool(content) and content[0].isspace())) + f' <b>{content.strip()}</b> '
    italic = lambda content: f'<i>{content}</i>'
    strikethrough = lambda content: f'<s>{content}</s>'
    underline = lambda content: f'<u>{content}</u>'
    code = lambda content: f'<code class="notion-code-inline">{content}</code>'

    if title_mode:
        return plain_text
    
    html = text_link(richtext['text']) if 'href' in richtext and richtext['href'] else plain_text
    for k, fn in dict(bold = bold, italic = italic, strikethrough = strikethrough, underline = underline, code = code).items():
        if richtext['annotations'][k]:
            html = fn(html)
    if richtext['annotations']['color'] != 'default':
        html = color(html, richtext['annotations']['color'])
    return html

def notionattrs2html(block, ctx = {}, used_keys = [], class_name = '', attrs = {}):
    used_keys_ = used_keys
    used_keys, used_keys_nested1, used_keys_nested2 = [k for k in used_keys if k.count('-') == 0], [tuple(k.split('-')) for k in used_keys if k.count('-') == 1], [tuple(k.split('-')) for k in used_keys if k.count('-') == 2]

    default_annotations = dict(bold = False, italic = False, strikethrough = False, underline = False, code = False, color = "default")

    keys = ['object', 'id', 'created_time', 'last_edited_time', 'archived', 'type', 'has_children', 'url', 'public_url', 'request_id'] 
    keys_nested1 = [('created_by', 'object'), ('created_by', 'id'), ('last_edited_by', 'object'), ('last_edited_by', 'id'), ('parent', 'type'), ('parent', 'workspace'), ('parent', 'page_id'), ('parent', 'block_id')] 

    keys_extra = [k for k in block.keys() if k not in keys and k not in used_keys if not isinstance(block[k], dict)] + [f'{k1}-{k2}' for k1 in block.keys() if isinstance(block[k1], dict) for k2 in block[k1].keys() if (k1, k2) not in keys_nested1 and (k1, k2) not in used_keys_nested1]
    html_attrs = ' ' + ' '.join(f'{k}="{v}"' for k, v in attrs.items()) + ' '
    if keys_extra:
        print(block.get('type') or block.get('object'), ';'.join(keys_extra), block.get('id'))
        #breakpoint()
        
    res = ' data-block-id="{id}" '.format(id = block.get('id', '')) + (f' class="{class_name}" ' if class_name else '') + html_attrs
    keys.remove('id')
    if ctx['notion_attrs_verbose'] is True:
        res += ' '.join('{kk}="{v}"'.format(kk = keys_alias.get(k, 'data-notion-' + k), v = block[k]) for k in keys if k in block) + ' ' + ' '.join('data-notion-{k1}-{k2}="{v}"'.format(k1 = k1, k2 = k2, v = block[k1][k2]) for k1, k2 in keys_nested1 if k1 in block and k2 in block[k1]) + (' data-notion-extrakeys="{}"'.format(';'.join(keys_extra)) if keys_extra else '') + ' '
    return res

def open_block(block = None, ctx = {}, class_name = '', tag = '', extra_attrstr = '', selfclose = False, set_html_contents_and_close = '', **kwargs):
    return (f'<{tag} {extra_attrstr} ' + (notionattrs2html(block, ctx, class_name = 'notion-block ' + class_name, **kwargs) if block else '') + '/' * selfclose + '>\n' + (set_html_contents_and_close + f'\n</{tag}>' if set_html_contents_and_close else '')) if tag else ''

def close_block(tag = ''):
    return f'</{tag}>\n' if tag else ''

def children_like(block, ctx, key = 'children', tag = ''):
    html = ''
    subblocks = block.get(key, []) or block.get(block.get('type'), {}).get(key, [])
    for i, subblock in enumerate(subblocks):
        same_block_type_as_prev = i > 0 and subblock.get('type') == subblocks[i - 1].get('type')
        same_block_type_as_next = i + 1 < len(subblocks) and subblock.get('type') == subblocks[i + 1].get('type')
        html += ((f'<{tag}>') if tag else '') + block2html(subblock, ctx, begin = not same_block_type_as_prev, end = not same_block_type_as_next) + (f'</{tag}>\n' if tag else '')
    return html

def text_like(block, ctx, block_type, tag = 'span', used_keys = [], attrs = {}, class_name = '', html_icon = '', checked = None):
    color = block[block_type].get('color', '')
    html_checked = '<input type="checkbox" disabled {} />'.format('checked' * checked) if checked is not None else ''
    return open_block(block, ctx, tag = tag, class_name = class_name + f' notion-color-{color}', attrs = attrs, used_keys = ['children', block_type + '-text', block_type + '-rich_text', block_type + '-color'] + used_keys, set_html_contents_and_close = html_checked + richtext2html(block[block_type].get('text') or block[block_type].get('rich_text') or [], ctx) + children_like(block, ctx) + html_icon)

def toggle_like(block, ctx, block_type, tag = 'span', used_keys = [], attrs = {}, class_name = '', html_icon = ''):
    html_text = richtext2html(block[block_type].get('text') or block[block_type].get('rich_text') or [], ctx)
    color = block[block_type].get('color', '')
    html_details_open = 'open' * ctx['html_details_open']
    return open_block(block, ctx, tag = 'details', extra_attrstr = html_details_open, class_name = f'notion-color-{color} notion-toggle-like ' + class_name, attrs = attrs, used_keys = ['children', block_type + '-text', block_type + '-rich_text', block_type + '-color', block_type + '-is_toggleable'] + used_keys, set_html_contents_and_close = f'<summary><{tag}>{html_text}{html_icon}</{tag}></summary>\n' + children_like(block, ctx))

def heading_like(block, ctx, block_type, tag, class_name = ''):
    block_id_no_dashes = block['id'].replace('-', '')
    slugs = ['{block_id_no_dashes}', '{page_slug}-{block_slug}', '{page_slug}-{block_id_no_dashes}']
    html_anchor = f'<a href="#{block_id_no_dashes}" class="notion-heading-like-icon"></a>'
    
    if block.get(block_type, {}).get('is_toggleable') is not True: 
        return text_like(block, ctx, block_type, tag = tag, attrs = dict(id = block_id_no_dashes), class_name = 'notion-heading-like ' + class_name, html_icon = html_anchor, used_keys = [block_type + '-is_toggleable'])
    else:
        return toggle_like(block, ctx, block_type, tag = tag, attrs = dict(id = block_id_no_dashes), class_name = 'notion-heading-like ' + class_name, html_icon = html_anchor, used_keys = [block_type + '-is_toggleable'])

def link_like(block, ctx, tag = 'a', class_name = '', full_url_as_caption = False, html_icon = '', line_break = False, used_keys = []):
    block_type = block.get('type', '')
    src = block[block_type].get('url') or block[block_type].get('file', {}).get('url') or block[block_type].get('external', {}).get('url') or block[block_type].get('url') or block.get('href') or ''
    html_text = richtext2html(block[block_type].get('caption', []), ctx) or block[block_type].get('name') or block.get('plain_text') or (src if full_url_as_caption else os.path.basename(src))
    return open_block(block, ctx, tag = tag, extra_attrstr = f'href="{src}"', class_name = class_name, used_keys = [block_type + '-name', block_type + '-url', block_type + '-caption', block_type + '-type', block_type + '-file', block_type + '-external', 'href', 'plain_text'] + used_keys, set_html_contents_and_close = html_icon + html_text) + '<br/>' * line_break

def get_page_url(block):
    return block.get('url', 'https://www.notion.so/' + block.get('id', '').replace('-', ''))

def get_page_title(block, untitled = 'Untitled'):
    page_title = ' '.join(t['plain_text'] for t in block.get('properties', {}).get('title', {}).get('title', [])).strip() or block.get('child_page', {}).get('title', '').strip() or block.get('title', '').strip() or ' '.join(t['plain_text'] for t in block.get('properties', {}).get('Name', {}).get('title', [])).strip() or untitled
    #if page_title == untitled:
    #    breakpoint()
    return page_title
   
def get_page_emoji(block):
    payload_icon = block.get('icon') or {}
    icon_emoji = payload_icon.get(payload_icon.get('type'), '')
    children = block.get('children', []) or block.get('blocks', [])
    if not icon_emoji and children:
        for subblock in children:
            if subblock.get('type') == 'callout':
                payload_icon = subblock.get('callout', {}).get('icon') or {}
                icon_emoji = payload_icon.get(payload_icon.get('type'), '')
                if icon_emoji:
                    break
    return icon_emoji

def get_page_current(block, ctx):
    id2block = {}
    stack = list(ctx['pages'].values())
    while stack:
        top = stack.pop()
        id2block[top.get('id')] = top
        stack.extend(top.get('blocks', []) + top.get('children', []))
    parent_block = block
    while (parent_block.get('type') or parent_block.get('object')) not in ['page', 'child_page']:
        parent_id = parent_block.get('parent', {}).get(parent_block.get('parent', {}).get('type'))
        if not parent_id or parent_id not in id2block:
            break
        parent_block = id2block[parent_id]
    return id2block, parent_block

def get_page_slug(link_to_page_page_id, ctx):
    return ctx['slugs'].get(link_to_page_page_id) or ctx['slugs'].get(link_to_page_page_id.replace('-', '')) or link_to_page_page_id.replace('-', '')

def get_heading_slug(block, ctx):
    pass

def page_like(block, ctx, tag = 'article', class_name = 'notion-page-block', strftime = '%Y/%m/%d %H:%M:%S', html_prefix = '', html_suffix = ''):
    unix_seconds_downloaded = ctx.get('unix_seconds_end', 0)
    unix_seconds_generated = ctx.get('unix_seconds_generated', 0)
    src = (block.get('cover') or {}).get((block.get('cover') or {}).get('type'), {}).get('url', '')
    src = ctx['assets'].get(src, {}).get('uri', src)

    page_title = html.escape(get_page_title(block))
    page_emoji = get_page_emoji(block)
    page_url = get_page_url(block)

    link_to_page_page_id = block.get('id', '')
    slug = get_page_slug(link_to_page_page_id, ctx) 
    block_id_no_dashes = link_to_page_page_id.replace('-', '')
    
    dt_published = datetime.datetime.fromtimestamp(unix_seconds_generated).strftime(strftime) if unix_seconds_generated else ''
    dt_modified = datetime.datetime.fromtimestamp(unix_seconds_downloaded).strftime(strftime) if unix_seconds_downloaded else ''
    return open_block(block, ctx, tag = tag, extra_attrstr = f'id="{slug}" data-notion-url="{page_url}"', class_name = 'notion-page', used_keys = ['id', 'blocks', 'icon', 'cover', 'icon-type', 'icon-emoji', 'cover-type', 'cover-file', 'properties-title', 'children', 'title', 'child_page-title']) + f'{html_prefix}<header id="{block_id_no_dashes}"><img src="{src}"></img><h1 class="notion-record-icon">{page_emoji}</h1><h1 class="{class_name}">{page_title}</h1><p><sub><time class="notion-page-block-datetime-published dt-published" datetime="{dt_published}" title="downloaded @{dt_modified}">@{dt_published}</time></sub></p></header><div class="notion-page-content">\n' + children_like(block, ctx, key = 'blocks' if 'blocks' in block else 'children') + f'\n</div>{html_suffix}' + close_block(tag)


def table_of_contents(block, ctx, tag = 'ul', class_name = 'notion-table_of_contents-block'):
    # https://www.notion.so/help/columns-headings-and-dividers#how-it-works
    if block.get('site_table_of_contents_page_ids'):
        table_of_contents_page_tree = lambda page_ids: '' if not page_ids else '<ul class="notion-table_of_contents-site-page-list">\n' + '\n'.join('<li class="notion-table_of_contents-site-page-item">\n{html_link_to_page}\n{html_child_pages}\n</li>'.format(html_link_to_page = link_to_page(dict(type = 'link_to_page', link_to_page = dict(type = 'page_id', page_id = page_id)), ctx), html_child_pages = table_of_contents_page_tree(page['id'] for page in ctx['child_pages_by_parent_id'].get(page_id, []))) for page_id in page_ids) + '\n</ul>'
        page_ids = block.get('site_table_of_contents_page_ids', [])
        child_page_ids = set(child_page['id'] for child_pages in ctx['child_pages_by_parent_id'].values() for child_page in child_pages)
        root_page_ids = [page_id for page_id in page_ids if page_id not in child_page_ids]
        return '<div class="notion-table_of_contents-site"><h1 class="notion-table_of_contents-site-header"></h1>\n' + table_of_contents_page_tree(root_page_ids) + '<hr /></div>\n'

    id2block, parent_block = get_page_current(block, ctx)
    
    headings = []
    stack = [parent_block]
    while stack:
        top = stack.pop()
        is_heading = top.get('type', '') in [heading_1.__name__, heading_2.__name__, heading_3.__name__]
        if is_heading:
            headings.append(top)
        if not is_heading or top.get(top.get('type'), {}).get('is_toggleable') is not True:
            stack.extend(reversed(top.get('blocks', []) + top.get('children', [])))
    
    color = block[table_of_contents.__name__].get('color', '')
    html = open_block(block, ctx, tag = tag, class_name = class_name + f' notion-color-{color}', used_keys = ['table_of_contents-color'])
    
    inc_heading_type = dict(heading_0 = 'heading_1', heading_1 = 'heading_2', heading_2 = 'heading_3', heading_3 = 'heading_3').get
    nominal_heading_type, effective_heading_type = 'heading_0', 'heading_0'
    for block in headings:
        block_id_no_dashes = block.get('id', '').replace('-', '')
        heading_type = block.get('type', '')
        nominal_heading_type, effective_heading_type = heading_type, min(heading_type, inc_heading_type(effective_heading_type) if heading_type > nominal_heading_type else effective_heading_type)
        html_text = richtext2html(block[block.get('type')].get('text') or block[block.get('type')].get('rich_text') or [], ctx, title_mode = True)
        html += f'<li class="notion-table_of_contents-heading notion-table_of_contents-{effective_heading_type}"><a href="#{block_id_no_dashes}">' + html_text + '</a></li>\n'
    html += close_block(tag)
    return html

def link_to_page(block, ctx, tag = 'a', html_suffix = '<br/>', class_name = 'notion-alias-block', html_icon = '', used_keys = []):
    link_to_page_page_id = block[link_to_page.__name__].get(block[link_to_page.__name__].get('type'), '')
    
    id2block, parent_block = get_page_current(block, ctx)
    
    is_index_page = 'index' == get_page_slug(parent_block.get('id', ''), ctx)
    slug = get_page_slug(link_to_page_page_id, ctx) 

    href = '#404'
    url_suffix = '/index.html'.lstrip('/' if slug == 'index' else '') if args.html_link_to_page_index_html else ''
    if ctx['extract_html'] == 'single' or not parent_block.get('id'):
        if link_to_page_page_id in ctx['page_ids']:
            href = '#' + slug 
        else:
            href = './' + slug + url_suffix
    elif ctx['extract_html'] == 'flat':
        href = ('./' if is_index_page else '../') + ('' if slug == 'index' else slug) + url_suffix

    subblock = id2block.get(link_to_page_page_id) 
    if subblock:
        page_title = html.escape(get_page_title(subblock))
        page_emoji = get_page_emoji(subblock)
        html_caption = f'{html_icon}{page_emoji} {page_title}'
    else:
        html_caption = f'{html_icon}title of linked page [{link_to_page_page_id}] not found'

    return open_block(block, ctx, tag = tag, extra_attrstr = f'href="{href}"', class_name = class_name, used_keys = [link_to_page.__name__ + '-type', link_to_page.__name__ + '-page_id'] + used_keys, set_html_contents_and_close = html_caption) + html_suffix + '\n'

def table(block, ctx, tag = 'table', class_name = 'notion-table-block'):
    table_width = block[table.__name__].get('table_width', 0)
    has_row_header = block[table.__name__].get('has_row_header', False)
    has_column_header = block[table.__name__].get('has_column_header', False)
    html = open_block(block, ctx, tag = tag, class_name = class_name, used_keys = ['children', 'table-table_width', 'table-has_column_header', 'table-has_row_header'])
    rows = block.get('children', [])
    for i, subblock in enumerate(rows):
        if i == 0:
            html += '\n<thead>\n' if has_row_header else '\n<tbody>\n'
        html += '<tr>\n'
        cells = subblock.get('table_row', {}).get('cells', [])
        for j, cell in enumerate(cells):
            tag_cell = 'th' if (has_row_header and i == 0) or (has_column_header and j == 0) else 'td'
            html += f'<{tag_cell}>' + (''.join('<div>{html_text}</div>'.format(html_text = richtext2html(subcell, ctx)) for subcell in cell) if isinstance(cell, list) else richtext2html(cell, ctx)) + f'</{tag_cell}>\n'
        if len(cells) < table_width:
            html += '<td></td>' * (table_width - len(cells))
        html += '</tr>\n'
        if i == 0:
            html += '\n</thead>\n<tbody>\n' if has_row_header else ''
    html += '\n</tbody>\n'
    html += close_block(tag)
    return html

def page(block, ctx, tag = 'article', class_name = 'notion-page-block', **kwargs):
    return page_like(block, ctx, tag = tag, class_name = class_name, **kwargs)

def child_page(block, ctx, tag = 'article', class_name = 'notion-page-block', **kwargs):
    return page_like(block, ctx, tag = tag, class_name = class_name, **kwargs)

def column_list(block, ctx, tag = 'div', class_name = 'notion-column_list-block'):
    return open_block(block, ctx, tag = tag, class_name = class_name + ' notion_column_list-block-vertical' * ctx['html_columnlist_disable'], used_keys = ['children'], set_html_contents_and_close = children_like(block, ctx))

def column(block, ctx, tag = 'div', class_name = 'notion-column-block'):
    return open_block(block, ctx, tag = tag, class_name = class_name, used_keys = ['children'], set_html_contents_and_close = children_like(block, ctx, tag = tag)) 

def video(block, ctx, tag = 'p', class_name = 'notion-video-block'):
    caption = richtext2html(block[video.__name__].get('caption', []), ctx)
    src = block[video.__name__].get(block[video.__name__]['type'], {}).get('url', '')
    is_youtube = 'youtube.com' in src
    src = src.replace("http://", "https://").replace('/watch?v=', '/embed/').split('&')[0] if is_youtube else src
    html_contents = f'<div><iframe width="640" height="480" src="{src}" frameborder="0" allowfullscreen></iframe></div>' if is_youtube else f'<video playsinline autoplay muted loop controls src="{src}"></video>'
    return open_block(block, ctx, tag = tag, class_name = class_name, used_keys = [video.__name__ + '-caption', video.__name__ + '-type', video.__name__ + '-external', video.__name__ + '-external-url'], set_html_contents_and_close = html_contents)

def image(block, ctx, tag = 'img', class_name = 'notion-image-block'):
    assert block['image']['type'] in ['file', 'external']
    src = block['image'].get('file', {}).get('url') or block['image'].get('external', {}).get('url') or ''
    src = ctx['assets'].get(src, {}).get('uri', src)
    if src.startswith('file:///'):
        src = src.split('file:///', maxsplit = 1)[-1]
    html_text = richtext2html(block['image']['caption'], ctx, title_mode = False)
    html_text_alt = richtext2html(block['image']['caption'], ctx, title_mode = True)
    return open_block(block, ctx, tag = 'figure', class_name = class_name, used_keys = ['image-caption', 'image-type', 'image-file', 'image-external'], set_html_contents_and_close = f'<{tag} src="{src}" alt="{html_text_alt}"></{tag}><figcaption>{html_text}</figcaption>')

def callout(block, ctx, tag = 'p', class_name = 'notion-callout-block'):
    icon_type = block[callout.__name__].get('icon', {}).get('type')
    icon_emoji = block[callout.__name__].get('icon', {}).get('emoji', '')
    color = block[callout.__name__].get('color', '')
    return open_block(block, ctx, tag = 'div', class_name = class_name + f' notion-color-{color}', used_keys = [callout.__name__ + '-icon', callout.__name__ + '-color', callout.__name__ + '-rich_text', 'children'], set_html_contents_and_close = f'<div>{icon_emoji}</div><div>\n' + text_like(block, ctx, block_type = callout.__name__, tag = tag, used_keys = [callout.__name__ + '-icon'])) + '</div>\n'

def embed(block, ctx, tag = 'iframe', class_name = 'notion-embed-block', html_text = ''):
    block_type = block.get('type', '')
    link_type = block[block_type].get('type', '')
    src = block[block_type].get('url') or block[block_type].get(link_type, {}).get('url') or ''
    html_text = html_text or richtext2html(block.get(block_type, {}).get('caption', []), ctx) 
    return open_block(block, ctx, tag = 'figure', class_name = class_name, used_keys = [block_type + '-caption', block_type + '-url', block_type + '-type', block_type + '-' + link_type], set_html_contents_and_close = f'<figcaption>{html_text}</figcaption><{tag} src="{src}"></{tag}>')

def pdf(block, ctx, tag = 'a', class_name = 'notion-pdf-block', html_icon = '📄 '):
    return embed(block, ctx, class_name = class_name, html_text = link_like({k : v for k, v in block.items() if k != 'id'}, ctx, tag = tag, html_icon = html_icon))

def file(block, ctx, tag = 'a', class_name = 'notion-file-block', html_icon = '📎 '):
    return link_like(block, ctx, tag = tag, class_name = class_name, html_icon = html_icon, line_break = True)

def bookmark(block, ctx, tag = 'a', class_name = 'notion-bookmark-block', html_icon = '🔖 '):
    return link_like(block, ctx, tag = tag, class_name = class_name, full_url_as_caption = True, html_icon = html_icon, line_break = True)

def link_preview(block, ctx, tag = 'a', class_name = 'notion-link_preview-block', html_prefix = '🌐 '):
    return link_like(block, ctx, tag = tag, class_name = class_name, html_prefix = html_prefix, line_break = True)

def paragraph(block, ctx, tag = 'p', class_name = 'notion-text-block'):
    if block.get('has_children') is False and not (block[block['type']].get('text') or block[block['type']].get('rich_text')):
        return open_block(block, ctx, tag = 'br', class_name = class_name, used_keys = ['children', paragraph.__name__ + '-text', paragraph.__name__ + '-rich_text', paragraph.__name__ + '-color'], selfclose = True)
    return text_like(block, ctx, block_type = paragraph.__name__, tag = tag, class_name = class_name)

def heading_1(block, ctx, tag = 'h1', class_name = 'notion-header-block'):
    return heading_like(block, ctx, block_type = heading_1.__name__, tag = tag, class_name = class_name)

def heading_2(block, ctx, tag = 'h2', class_name = 'notion-sub_header-block'):
    return heading_like(block, ctx, block_type = heading_2.__name__, tag = tag, class_name = class_name)
    
def heading_3(block, ctx, tag = 'h3', class_name = 'notion-sub_sub_header-block'):
    return heading_like(block, ctx, block_type = heading_3.__name__, tag = tag, class_name = class_name)

def quote(block, ctx, tag = 'blockquote', class_name = 'notion-quote-block'):
    return text_like(block, ctx, block_type = quote.__name__, tag = tag, class_name = class_name)

def toggle(block, ctx, tag = 'span', class_name = 'notion-toggle-block'):
    return toggle_like(block, ctx, block_type = toggle.__name__, tag = tag, class_name = class_name)

def divider(block, ctx, tag = 'hr', class_name = 'notion-divider-block'):
    return open_block(block, ctx, tag = tag, class_name = class_name, selfclose = True)

def bulleted_list_item(block, ctx, tag = 'ul', begin = False, end = False, class_name = 'notion-bulleted_list-block'):
    return (f'<{tag} class="{class_name}">\n' if begin else '') + text_like(block, ctx, block_type = bulleted_list_item.__name__, tag = 'li') + ('\n' + f'</{tag}>\n' if end else '')

def numbered_list_item(block, ctx, tag = 'ol', begin = False, end = False, class_name = 'notion-numbered_list-block'):
    return (f'<{tag} class="{class_name}">\n' if begin else '') + text_like(block, ctx, block_type = numbered_list_item.__name__, tag = 'li') + ('\n' + f'</{tag}>\n' if end else '')

def code(block, ctx, tag = 'code', class_name = 'notion-code-block'):
    html_caption = richtext2html(block[code.__name__].get('caption', []), ctx)
    language = block[code.__name__].get('language', '')
    return open_block(block, ctx, tag = 'figure', extra_attrstr = f'data-language="{language}"', class_name = class_name, used_keys = [code.__name__ + '-caption', code.__name__ + '-rich_text', code.__name__ + '-language'], set_html_contents_and_close = f'<figcaption>{html_caption}</figcaption>\n<pre><{tag}>' + richtext2html(block[code.__name__].get('rich_text', []), ctx) + f'</{tag}></pre>')

def equation(block, ctx, tag = 'code', class_name = 'notion-equation-block'):
    html_expression = block[equation.__name__].get('expression', '')
    return open_block(block, ctx, tag = tag, class_name = class_name, used_keys = [equation.__name__ + '-expression'], set_html_contents_and_close = html_expression)

def child_database(block, ctx, tag = 'figure', class_name = 'notion-child_database-block', html_icon = '📚', untitled = '???'):
    html_child_database_title = block[child_database.__name__].get('title') or untitled
    return open_block(block, ctx, tag = tag, class_name = class_name, used_keys = [child_database.__name__ + '-title'], set_html_contents_and_close = f'<figcaption>{html_icon}<strong>{html_child_database_title}</strong>{html_icon}</figcaption>')

def breadcrumb(block, ctx, tag = 'div', class_name = 'notion-breadcrumb-block'):
    id2block, parent_block = get_page_current(block, ctx)
    page_id = parent_block['id']
    return open_block(block, ctx, tag = tag, class_name = class_name, set_html_contents_and_close = '&nbsp;/&nbsp;'.join(block2html(subblock, ctx).replace('<br/>', '') for subblock in reversed(ctx['pages_parent_path'][page_id])))

def mention(block, ctx, tag = 'div', class_name = 'notion-mention-block', untitled = 'Untitled'):
    mention_type = block[mention.__name__].get('type')
    mention_payload = block[mention.__name__][mention_type]
  
    used_keys = [mention.__name__ + '-type', mention.__name__ + '-page', mention.__name__ + '-database', 'annotations-bold', 'annotations-italic', 'annotations-strikethrough', 'annotations-underline', 'annotations-code', 'annotations-color', 'plain_text', 'href']
    if mention_type == 'page':
        page_id = mention_payload.get('id', '')
        return link_to_page(dict(block, type = 'link_to_page', link_to_page = dict(type = 'page_id', page_id = page_id)), ctx, html_icon = '📄⤷', used_keys = used_keys)

    if mention_type == 'link_preview':
        return link_preview(block, ctx)

    if mention_type == 'user':
        user_id = mention_payload.get('id', '')
        user_name = block['plain_text'].lstrip('@')
        return f'<strong title="notion mention of user">@{user_name}#{user_id}</strong>'

    if mention_type == 'date':
        date_text = block.get('plain_text', '')
        return f'<strong title="notion mention of date">@{date_text}⏰</strong>'

    if mention_type == 'database':
        return link_like(block, ctx, html_icon = '🗃️⤷', used_keys = used_keys)
    
    return unsupported(block, ctx)

def template(block, ctx, tag = 'figure', class_name = 'notion-template-block'):
    html_text = richtext2html(block[block_type].get('text') or block[block_type].get('rich_text') or [], ctx)
    html_children = children_like(block, ctx)
    return open_block(block, ctx, tag = tag, class_name = class_name, set_html_contents_and_close = f'<figcaption>{html_text}</figcaption>\n{html_children}')

def synced_block(block, ctx, tag = 'figure', class_name = 'notion-synced_block-block'):
    synced_from_block_id = block[synced_block.__name__].get('synced_from', {}).get('block_id', '')
    html_children = children_like(block, ctx)
    return open_block(block, ctx, tag = tag, class_name = class_name, set_html_contents_and_close = f'<figcaption>{synced_from_block_id}</figcaption>\n{html_children}')

def to_do(block, ctx, tag = 'div', class_name = 'notion-to_do-block'):
    checked = block[block_type].get('checked', False) 
    return text_like(block, ctx, tag = tag, class_name = class_name, checked = checked, used_keys = [block.get('type', '') + '-checked'])

def unsupported(block, ctx, tag = 'div', class_name = 'notion-unsupported-block', comment = True):
    block_type = block.get('type', '')
    return '\n<!--\n' * comment + open_block(block, ctx, tag = tag, class_name = class_name, extra_attrstr = f' data-notion-block_type="{block_type}', selfclose = True).replace('-->' * comment, '__>' * comment) + '\n-->\n' * comment

def block2html(block, ctx = {}, begin = False, end = False, **kwargs):
    # https://developers.notion.com/reference/block
    block2render = dict(
        bookmark = bookmark,
        breadcrumb = breadcrumb,
        bulleted_list_item = bulleted_list_item,
        callout = callout,
        child_database = child_database,
        child_page = child_page,
        code = code,
        column_list = column_list, column = column,
        divider = divider,
        embed = embed,
        equation = equation,
        file = file,
        heading_1 = heading_1, heading_2 = heading_2, heading_3 = heading_3,
        image = image,
        link_preview = link_preview,
        mention = mention,
        numbered_list_item = numbered_list_item,
        paragraph = paragraph,
        pdf = pdf,
        quote = quote,
        synced_block = synced_block,
        table = table,
        table_of_contents = table_of_contents,
        template = template,
        to_do = to_do,
        toggle = toggle,
        video = video,

        unsupported = unsupported,
        
        page = page,
        link_to_page = link_to_page,
    )
    block2render_with_begin_end = dict(
        numbered_list_item = numbered_list_item, 
        bulleted_list_item = bulleted_list_item
    )

    block_type = block.get('type') or block.get('object') or ''
    
    if block_type in block2render_with_begin_end:
        return block2render_with_begin_end[block_type](block, ctx, begin = begin, end = end, **kwargs)
    
    if block_type not in block2render or block_type == 'unsupported':
        block_type = 'unsupported'
        id2block, parent_block = get_page_current(block, ctx)
        block_type_parent = parent_block.get('type', '') or parent_block.get('object', '')
        print('unsupported block: type=[{type}] id=[{id}] parent_type=[{parent_type}] parent_id=[{parent_id}] parent_title=[{parent_title}]'.format(type = block['type'], id = block['id'], parent_type = block_type_parent, parent_id = parent_block['id'], parent_title = get_page_title(parent_block)), file = sys.stderr)

    return block2render[block_type](block, ctx, **kwargs)


def pop_and_replace_child_pages_recursively(block, child_pages_by_parent_id = {}, parent_id = None):
    block_type = block.get('type') or block.get('object')
    if block_type in ['page', 'child_page']:
        if block.get('id') not in child_pages_by_parent_id:
            child_pages_by_parent_id[block.get('id')] = [] 
    for keys in ['children', 'blocks']:
        for i in reversed(range(len(block[keys]) if block.get(keys, []) else 0)):
            if block[keys][i]['type'] == 'child_page':
                child_page = block[keys][i]
                parent_id_type = 'page_id' if block_type in ['page', 'child_page'] else 'block_id'
                block[keys][i] = dict( object = 'block', type = 'link_to_page', has_children = False, link_to_page = dict(type = 'page_id', page_id = child_page['id']), parent = {'type' : parent_id_type, parent_id_type : block['id']} )
                if parent_id not in child_pages_by_parent_id:
                    child_pages_by_parent_id[parent_id] = []
                child_pages_by_parent_id[parent_id].append(child_page)
                pop_and_replace_child_pages_recursively(block[keys][i], child_pages_by_parent_id = child_pages_by_parent_id, parent_id = child_page['id'])
            else:
                pop_and_replace_child_pages_recursively(block[keys][i], child_pages_by_parent_id = child_pages_by_parent_id, parent_id = parent_id)

def discover_assets(blocks, asset_urls = [], include_image = True, include_file = False):
    for block in blocks:
        for keys in ['children', 'blocks']:
            if block.get(keys, []):
                discover_assets(block[keys], asset_urls = asset_urls)
        block_type = block.get('type')
        payload = block.get(block_type, {})
        urls = [(block.get('cover') or {}).get('file', {}).get('url'), (block.get('icon') or {}).get('file', {}).get('url')]
        url = payload.get('url') or payload.get('external', {}).get('url') or payload.get('file', {}).get('url')
        if include_image and block_type == 'image' and url:
            urls.append(url)
        if include_file and block_type == 'file' and url:
            urls.append(url)
        asset_urls.extend(url for url in urls if url and not url.startswith('data:'))
    return asset_urls

def prepare_and_extract_assets(notion_pages, assets_dir, notion_assets = {}, extract_assets = False):
    urls = discover_assets(notion_pages.values(), [])
    assets = {url : notion_assets[url] for url in urls}
    if extract_assets and assets:
        os.makedirs(assets_dir, exist_ok = True)
        for asset in assets.values():
            asset_path = os.path.join(assets_dir, asset['name'])
            with open(asset_path, 'wb') as f:
                f.write(base64.b64decode(asset['uri'].split('base64,', maxsplit = 1)[-1].encode()))
            asset['uri'] = 'file:///' + asset_path
            print(asset_path)
    return assets

def extract_html(output_path, ctx, sitepages2html, page_ids = [], notion_pages_flat = {}, extract_assets = False, child_pages_by_parent_id = {}, index_html = False, mode = ''):
    notion_assets = ctx.get('assets', {})

    if mode == 'single':
        ctx['assets'] = prepare_and_extract_assets(notion_pages = ctx['pages'], assets_dir = output_path + '_files', notion_assets = notion_assets, extract_assets = extract_assets)
        with open(output_path, 'w', encoding = 'utf-8') as f:
            f.write(sitepages2html(page_ids, ctx = ctx, notion_pages = notion_pages_flat))
        return print(output_path)

    os.makedirs(output_path, exist_ok = True)
    for page_id in page_ids:
        page_block = notion_pages_flat[page_id]
        os.makedirs(output_path, exist_ok = True)
        slug = get_page_slug(page_id, ctx)
        page_dir = os.path.join(output_path, slug) if index_html and slug != 'index' else output_path
        os.makedirs(page_dir, exist_ok = True)
        html_path = os.path.join(page_dir, 'index.html' if index_html else slug + '.html')
        assets_dir = os.path.join(page_dir, slug + '_files')
        notion_assets_for_block = prepare_and_extract_assets({page_id : page_block}, assets_dir = assets_dir, notion_assets = notion_assets, extract_assets = extract_assets)
        ctx['assets'] = notion_assets_for_block
        with open(html_path, 'w', encoding = 'utf-8') as f:
            f.write(sitepages2html([page_id], ctx = ctx, notion_pages = notion_pages_flat))
        print(html_path)
        if child_pages := child_pages_by_parent_id.pop(page_id, []):
            extract_html_nested(page_dir, ctx = ctx, page_ids = [child_page['id'] for child_page in child_pages], notion_pages_flat = notion_pages_flat, child_pages_by_parent_id = child_pages_by_parent_id, index_html = index_html, extract_assets = extract_assets, sitepages2html = sitepages2html, mode = mode)

def main(args):
    output_path = args.output_path if args.output_path else '_'.join(args.notion_page_id) if args.extract_html != 'single' else (args.input_path.removesuffix('.json') + '.html')
    
    notion_cache = json.load(open(args.input_path)) if args.input_path else {}
    notion_slugs = json.load(open(args.pages_json)) if args.pages_json else {}

    notion_pages = notion_cache.get('pages', {})
    notion_assets = notion_cache.get('assets', {})
   
    notion_pages_flat = copy.deepcopy(notion_pages)
    child_pages_by_parent_id = {}
    for page_id, page in notion_pages_flat.items():
        pop_and_replace_child_pages_recursively(page, child_pages_by_parent_id = child_pages_by_parent_id, parent_id = page_id)
    child_pages_by_id = {child_page['id'] : child_page for pages in child_pages_by_parent_id.values() for child_page in pages}
    notion_pages_flat |= child_pages_by_id

    root_page_ids = args.notion_page_id or list(notion_pages.keys())
    for i in range(len(root_page_ids)):
        for k, v in notion_slugs.items():
            if root_page_ids[i] == v:
                root_page_ids[i] = k
        for k in notion_pages.keys():
            if root_page_ids[i] == k.replace('-', ''):
                root_page_ids[i] = k
    assert all(page_id in notion_pages_flat for page_id in root_page_ids)

    page_ids = root_page_ids + [child_page['id'] for page_id in root_page_ids for child_page in child_pages_by_parent_id.get(page_id, []) if child_page['id'] not in root_page_ids]
    #page_ids = page_ids # child_pages_by_id = child_pages_by_id if args.extract_html in ['flat', 'flat.html'] else {}

    ctx = {}
    ctx['html_details_open'] = args.html_details_open
    ctx['html_columnlist_disable'] = args.html_columnlist_disable
    ctx['html_link_to_page_index_html'] = args.html_link_to_page_index_html
    ctx['extract_html'] = args.extract_html
    ctx['notion_attrs_verbose'] = args.notion_attrs_verbose
    ctx['slugs'] = notion_slugs
    ctx['assets'] = notion_assets
    ctx['unix_seconds_begin'] = notion_cache.get('unix_seconds_begin', 0)
    ctx['unix_seconds_end'] = notion_cache.get('unix_seconds_end', 0)
    ctx['unix_seconds_generated'] = int(time.time())
    ctx['pages'] = notion_pages_flat
    ctx['page_ids'] = page_ids
    ctx['child_pages_by_parent_id'] = child_pages_by_parent_id
    ctx['pages_parent_path'] = {}
    id2block = {}
    stack = list(ctx['pages'].values()) + list(child_pages_by_id.values())
    while stack:
        top = stack.pop()
        id2block[top.get('id')] = top
        stack.extend(top.get('blocks', []) + top.get('children', []))
    for page_id in notion_pages_flat.keys() | child_pages_by_id.keys():
        block_id = page_id
        parent_path = []
        header_parent_page_id = page_id
        while True:
            block = id2block[block_id]
            if (block.get('type') or block.get('object')) in ['page', 'child_page']:
                parent_path.append(dict(type = 'link_to_page', link_to_page = dict(type = 'page_id', page_id = block_id), parent = dict(type = 'page_id', page_id = header_parent_page_id)))
            parent_id = block['parent'].get(block['parent'].get('type'))
            if parent_id not in id2block:
                break
            block_id = parent_id
        ctx['pages_parent_path'][page_id] = parent_path

    try:
        theme = importlib.import_module(os.path.splitext(args.theme_py)[0])
    except:
        assert os.path.isfile(args.theme_py)
        sys.path.append(os.path.dirname(args.theme_py))
        theme = importlib.import_module(os.path.splitext(args.theme_py)[0])

    read_html_snippet = lambda path: open(path).read() if path and os.path.exists(path) else ''
    sitepages2html = functools.partial(theme.sitepages2html, block2html = block2html, toc = args.html_toc, html_body_header_html = read_html_snippet(args.html_body_header_html), html_body_footer_html = read_html_snippet(args.html_body_footer_html), html_article_header_html = read_html_snippet(args.html_article_header_html), html_article_footer_html = read_html_snippet(args.html_article_footer_html))
    
    extract_html(output_path, ctx, sitepages2html = sitepages2html, page_ids = page_ids, notion_pages_flat = notion_pages_flat, extract_assets = args.extract_assets, child_pages_by_parent_id = child_pages_by_parent_id if args.extract_html == 'nested' else {}, index_html = args.extract_html in ['flat', 'nested'], mode = args.extract_html)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--input-path', '-i', required = True)
    parser.add_argument('--output-path', '-o')
    parser.add_argument('--pages-json')
    parser.add_argument('--notion-page-id', nargs = '*', default = [])
    parser.add_argument('--notion-attrs-verbose', action = 'store_true')
    parser.add_argument('--extract-assets', action = 'store_true')
    parser.add_argument('--extract-html', default = 'single', choices = ['single', 'flat', 'flat.html', 'nested'])
    parser.add_argument('--theme-py', default = 'minima.py')
    parser.add_argument('--html-toc', action = 'store_true')
    parser.add_argument('--html-details-open', action = 'store_true')
    parser.add_argument('--html-columnlist-disable', action = 'store_true')
    parser.add_argument('--html-link-to-page-index-html', action = 'store_true')
    parser.add_argument('--html-body-header-html')
    parser.add_argument('--html-body-footer-html')
    parser.add_argument('--html-article-header-html')
    parser.add_argument('--html-article-footer-html')
    args = parser.parse_args()
    print(args)
    main(args)
