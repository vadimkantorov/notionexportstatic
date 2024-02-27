# TODO: for a single or nested mode, what to do with unresolved link_to_pages? extend slug.json info? or scan the current directory?
# TODO: prepare_and_extract_assets: first load in memory? or copy directly to target dir?
# TODO: image: fixup url from assets; when to embed image

# TODO: bookmark or link_preview: generate social media card: title, maybe description, favicon
# TODO: add cmdline option for pages/headings links to notion ✏️
# TODO: move emoji's to CSS

# https://docs.super.so/super-css-classes

import os
import re
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
import xml.dom.minidom
import unicodedata

def open_block(block = {}, ctx = {}, class_name = '', tag = '', selfclose = False, set_html_contents_and_close = '', attrs = {}, **kwargs):
    notion_attrs_class_name = 'notion-block ' + class_name
    notion_attrs = ' data-block-id="{id}" '.format(id = block.get('id', '')) + (f' class="{notion_attrs_class_name}" ' if notion_attrs_class_name else '') + ' ' + ' '.join(f'{k}="{v}"' if v is not None else k for k, v in attrs.items()) + ' '
    return (f'<{tag} ' + (notion_attrs if block else '') + '/' * selfclose + '>\n' + (set_html_contents_and_close + f'\n</{tag}>' if set_html_contents_and_close else '')) if tag else ''

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

def richtext2html(block, ctx = {}, title_mode = False, html_escape = html.escape):
    # https://www.notion.so/help/customize-and-style-your-content#markdown
    # https://developers.notion.com/reference/rich-text

    if isinstance(block, list):
        return ''.join(richtext2html(subblock, ctx, title_mode = title_mode) for subblock in block).strip()
    
    plain_text = block['plain_text']
    anno = block['annotations']
    href = block.get('href', '')
    
    #default_annotations = dict(bold = False, italic = False, strikethrough = False, underline = False, code = False, color = "default")
    
    if block['type'] == 'mention':
        return mention(block, ctx)

    if block['type'] == 'equation':
        return equation(block, ctx, class_name = 'notion-equation-inline')
    
    if title_mode:
        return plain_text
    
    html = html_escape(plain_text)
    
    if href:
        html = link_to_page(block, ctx) if href.startswith('/') else link_like(block, ctx)
    if anno['bold']:
       html = f'<b>{html}</b> ' 
    if anno['italic']:
        html = f'<i>{html}</i>'
    if anno['strikethrough']:
        html = f'<s>{html}</s>'
    if anno['underline']:
        html = f'<u>{html}</u>'
    if anno['code']:
        html = f'<code class="notion-code-inline">{html}</code>'
    if (color := anno['color']) != 'default':
        html = f'<span style="color:{color}">{html}</span>'
    
    return html


def text_like(block, ctx, block_type, tag = 'span', attrs = {}, class_name = '', html_icon = '', checked = None):
    html_text = richtext2html(block[block_type].get('text') or block[block_type].get('rich_text') or [], ctx)
    color = block[block_type].get('color', '')
    html_checked = '<input type="checkbox" disabled {} />'.format('checked' * checked) if checked is not None else ''
    return open_block(block, ctx, tag = tag, class_name = class_name + f' notion-color-{color}', attrs = attrs, set_html_contents_and_close = html_checked + html_text + children_like(block, ctx) + html_icon)

def toggle_like(block, ctx, block_type, tag = 'span', attrs = {}, class_name = '', html_icon = ''):
    html_text = richtext2html(block[block_type].get('text') or block[block_type].get('rich_text') or [], ctx)
    color = block[block_type].get('color', '')
    return open_block(block, ctx, tag = 'details', class_name = f'notion-color-{color} notion-toggle-like ' + class_name, attrs = dict(attrs, open = None) if ctx['html_details_open'] else attrs, set_html_contents_and_close = f'<summary><{tag}>{html_text}{html_icon}</{tag}></summary>\n' + children_like(block, ctx))

def heading_like(block, ctx, tag, class_name = ''):
    block_type = block.get('type', '')
    block_id_no_dashes = block['id'].replace('-', '')
    block_slug = get_heading_slug(block, ctx)
    html_anchor = f'<a href="#{block_slug}"></a><a href="#{block_id_no_dashes}" class="notion-heading-like-icon"></a>'
    
    if block.get(block_type, {}).get('is_toggleable') is not True: 
        return text_like(block, ctx, block_type, tag = tag, attrs = dict(id = block_id_no_dashes), class_name = 'notion-heading-like ' + class_name, html_icon = html_anchor)
    else:
        return toggle_like(block, ctx, block_type, tag = tag, attrs = dict(id = block_id_no_dashes), class_name = 'notion-heading-like ' + class_name, html_icon = html_anchor)

def link_like(block, ctx, tag = 'a', class_name = '', full_url_as_caption = False, html_icon = '', line_break = False, tooltip = ''):
    block_type = block.get('type', '')
    src = block[block_type].get('url') or block[block_type].get('file', {}).get('url') or block[block_type].get('external', {}).get('url') or block[block_type].get('url') or block.get('href') or ''
    html_text = richtext2html(block[block_type].get('caption', []), ctx) or block[block_type].get('name') or block.get('plain_text') or (src if full_url_as_caption else os.path.basename(urllib.parse.urlparse(src).path))
    return open_block(block, ctx, tag = tag, attrs = dict(href = src, title = tooltip), class_name = class_name, set_html_contents_and_close = html_icon + html_text) + '<br/>' * line_break

def get_page_url(block, ctx, base_url = 'https://www.notion.so'):
    return block.get('url', os.path.join(base_url, block.get('id', '').replace('-', '')))

def get_page_title(block, ctx, untitled = 'Untitled'):
    if not block:
        return ''
    page_title = ' '.join(t['plain_text'] for t in block.get('properties', {}).get('title', {}).get('title', [])).strip() or block.get('child_page', {}).get('title', '').strip() or block.get('title', '').strip() or ' '.join(t['plain_text'] for t in block.get('properties', {}).get('Name', {}).get('title', [])).strip() or block.get('plain_text') or untitled
    
    #page_emoji, page_title = '', (block.get('plain_text', '') or untitled)
    #if subblock := ctx['id2block'].get(page_id_no_dashes):
    #    page_emoji, page_title = get_page_emoji(subblock), html.escape(get_page_title(subblock))
    
    return page_title
   
def get_page_emoji(block, ctx):
    if not block:
        return ''
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
    parent_block = block
    while (parent_block.get('type') or parent_block.get('object')) not in ['page', 'child_page']:
        parent_id = parent_block.get('parent', {}).get(parent_block.get('parent', {}).get('type'))
        if not parent_id or parent_id not in ctx['id2block']:
            break
        parent_block = ctx['id2block'][parent_id]
    return parent_block

def get_page_slug(page_id, ctx):
    return ctx['slugs'].get(page_id) or ctx['slugs'].get(page_id.replace('-', '')) or page_id.replace('-', '')

def get_heading_slug(block, ctx, space = '_', lower = False, prefix = ''):
    block_type = block.get('type') or block.get('object') or ''
    s = richtext2html(block[block_type].get('text') or block[block_type].get('rich_text') or [], ctx, title_mode = True)
    if ctx['extract_html'] == 'single':
        page_block = get_page_current(block, ctx)
        page_slug = get_page_slug(page_block.get('id', ''), ctx)
        prefix = page_slug + '-'
    
    s = unicodedata.normalize('NFKC', s)
    s = s.strip()
    s = re.sub(r'\s', space, s, flags = re.U)
    s = re.sub(r'[^-_.\w]', space, s, flags = re.U)
    s = s.lower() if lower else s
    s = s.strip(space)
    s = re.sub(space + '+', space, s)
    s = prefix + s
    return s

def get_page_relative_url(block, ctx):
    page_id = block.get('link_to_page', {}).get('page_id', '') or (block.get('href', '').removeprefix('/') if block.get('href', '').startswith('/') else '') or block.get('id', '')

    page_slug = get_page_slug(page_id, ctx)
    is_index_page = page_slug == 'index'
    page_suffix = '/index.html'.removeprefix('/' if is_index_page else '') if ctx['html_link_to_page_index_html'] else ''
    
    if ctx['extract_html'] == 'flat':
        return './' + ('' if is_index_page else page_slug) + page_suffix
    
    elif ctx['extract_html'] == 'flat.html':
        return './' + (page_suffix if is_index_page else page_slug + '.html')
    
    elif ctx['extract_html'] == 'single':
        #TODO: what to do for a single page generation but in fact some nested?
        # maybe still retrieve from pages.json? or from sitemap.xml?
        return './' + os.path.basename(ctx['output_path']) + ('' if is_index_page else '#' + page_slug)

    elif ctx['extract_html'] == 'nested':
        return ''
        
    return ''

def get_page_relative_link(page_url_base, page_url_target):
    base_path, base_fragment = page_url_base.split('#') if '#' in page_url_base else (page_url_base, None)
    target_path, target_fragment = page_url_target.split('#') if '#' in page_url_target else (page_url_target, None)

    if base_path == target_path:
        return '#' + (target_fragment or '')

    base_path_splitted = base_path.split('/')
    target_path_splitted = target_path.split('/')

    num_common_parts = 0
    for i, (part_base, part_target) in enumerate(zip(base_path_splitted, target_path_splitted)):
        if part_base == part_target:
            num_common_parts += 1
        else:
            break

    num_cd_parent = len(base_path_splitted) - num_common_parts - 1

    href = '../' * num_cd_parent + './' * (num_cd_parent == 0) + '/'.join(target_path_splitted[num_common_parts:]) + ('#' + target_fragment if target_fragment else '')

    return href
   

def get_page_headings(block, ctx):
    headings = []
    stack = [block]
    while stack:
        top = stack.pop()
        is_heading = top.get('type', '') in ['heading_1', 'heading_2', 'heading_3']
        if is_heading:
            headings.append(top)
        if not is_heading or top.get(top.get('type'), {}).get('is_toggleable') is not True:
            stack.extend(reversed(top.get('blocks', []) + top.get('children', [])))
    return headings

def page_like(block, ctx, tag = 'article', class_name = 'notion-page-block', strftime = '%Y/%m/%d %H:%M:%S', html_prefix = '', html_suffix = '', class_name_page_title = '', class_name_page_content = '', class_name_header = '', class_name_page = ''):
    dt_modified = datetime.datetime.fromtimestamp(ctx.get('unix_seconds_end', 0)).strftime(strftime) if ctx.get('unix_seconds_end', 0) else ''
    dt_published = datetime.datetime.fromtimestamp(ctx.get('unix_seconds_generated', 0)).strftime(strftime) if ctx.get('unix_seconds_generated', 0) else ''
    src = (block.get('cover') or {}).get((block.get('cover') or {}).get('type'), {}).get('url', '')
    src = ctx['assets'].get(src, {}).get('uri', src)

    page_id = block.get('id', '')
    page_id_no_dashes = page_id.replace('-', '')

    page_title = html.escape(get_page_title(block, ctx))
    page_emoji = get_page_emoji(block, ctx)
    page_url = get_page_url(block, ctx)
    page_slug = get_page_slug(page_id, ctx) 
    
    return open_block(block, ctx, tag = tag, attrs = {'id': page_slug, 'data-notion-url' : page_url}, class_name = 'notion-page ' + class_name_page) + f'{html_prefix}<header id="{page_id_no_dashes}" class="{class_name_header}"><img src="{src}"></img><h1 class="notion-record-icon">{page_emoji}</h1><h1 class="{class_name} {class_name_page_title}">{page_title}</h1><p><sub><time class="notion-page-block-datetime-published dt-published" datetime="{dt_published}" title="downloaded @{dt_modified or dt_published}">@{dt_published}</time></sub></p></header><div class="notion-page-content {class_name_page_content}">\n' + children_like(block, ctx, key = 'blocks' if 'blocks' in block else 'children') + f'\n</div>{html_suffix}' + close_block(tag)


def table_of_contents(block, ctx, tag = 'ul', class_name = 'notion-table_of_contents-block'):
    # https://www.notion.so/help/columns-headings-and-dividers#how-it-works
    if block.get('site_table_of_contents_page_ids'):
        table_of_contents_page_tree = lambda page_ids: '' if not page_ids else '<ul class="notion-table_of_contents-site-page-list">\n' + '\n'.join('<li class="notion-table_of_contents-site-page-item">\n{html_link_to_page}\n{html_child_pages}\n</li>'.format(html_link_to_page = link_to_page(dict(type = 'link_to_page', link_to_page = dict(type = 'page_id', page_id = page_id)), ctx), html_child_pages = table_of_contents_page_tree(page['id'] for page in ctx['child_pages_by_parent_id'].get(page_id, []))) for page_id in page_ids) + '\n</ul>'
        page_ids = block.get('site_table_of_contents_page_ids', [])
        child_page_ids = set(child_page['id'] for child_pages in ctx['child_pages_by_parent_id'].values() for child_page in child_pages)
        root_page_ids = [page_id for page_id in page_ids if page_id not in child_page_ids]
        return '<div class="notion-table_of_contents-site"><h1 class="notion-table_of_contents-site-header"></h1>\n' + table_of_contents_page_tree(root_page_ids) + '<hr /></div>\n'

    page_block = get_page_current(block, ctx)
    headings = get_page_headings(page_block, ctx)
    
    color = block['table_of_contents'].get('color', '')
    html = open_block(block, ctx, tag = tag, class_name = class_name + f' notion-color-{color}')
    
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

def link_to_page(block, ctx, tag = 'a', html_suffix = '<br/>', class_name = 'notion-alias-block', html_icon = '', untitled = '???'):
    payload = block.get(block.get('type'), {})
    page_id = payload.get(payload.get('type'), '')
    page_id_no_dashes = page_id.replace('-', '') or (block.get('href', '').lstrip('/') if block.get('href', '').startswith('/') else '') 
    page_ids_no_dashes = set(page_id.replace('-', '') for page_id in ctx['page_ids'])
    page_slug = get_page_slug(page_id_no_dashes, ctx) 
    page_block = get_page_current(block, ctx)
    
    page_url_base = get_page_relative_url(page_block, ctx)
    page_url_target = get_page_relative_url(block, ctx)

    href = get_page_relative_link(page_url_base = page_url_base, page_url_target = page_url_target)
    
    page_block = ctx['id2block'].get(page_id_no_dashes)
    
    page_emoji = get_page_emoji(page_block, ctx)
    page_title = get_page_title(page_block, ctx) or block.get('plain_text', '') or untitled
    
    html_caption = f'{html_icon}{page_emoji} ' + html.escape(page_title)
   
    return open_block(block, ctx, tag = tag, attrs = dict(href = href), class_name = class_name, set_html_contents_and_close = html_caption) + html_suffix + '\n'

def table(block, ctx, tag = 'table', class_name = 'notion-table-block'):
    table_width = block['table'].get('table_width', 0)
    has_row_header = block['table'].get('has_row_header', False)
    has_column_header = block['table'].get('has_column_header', False)
    html = open_block(block, ctx, tag = tag, class_name = class_name)
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
    return open_block(block, ctx, tag = tag, class_name = class_name + ' notion_column_list-block-vertical' * ctx['html_columnlist_disable'], set_html_contents_and_close = children_like(block, ctx))

def column(block, ctx, tag = 'div', class_name = 'notion-column-block'):
    return open_block(block, ctx, tag = tag, class_name = class_name, set_html_contents_and_close = children_like(block, ctx, tag = tag)) 

def video(block, ctx, tag = 'p', class_name = 'notion-video-block'):
    caption = richtext2html(block['video'].get('caption', []), ctx)
    src = block['video'].get(block['video']['type'], {}).get('url', '')
    is_youtube = 'youtube.com' in src
    src = src.replace("http://", "https://").replace('/watch?v=', '/embed/').split('&')[0] if is_youtube else src
    html_contents = f'<div><iframe width="640" height="480" src="{src}" frameborder="0" allowfullscreen></iframe></div>' if is_youtube else f'<video playsinline muted loop controls src="{src}"></video>'
    return open_block(block, ctx, tag = tag, class_name = class_name, set_html_contents_and_close = html_contents)

def image(block, ctx, tag = 'img', class_name = 'notion-image-block'):
    assert block['image']['type'] in ['file', 'external']
    src = block['image'].get('file', {}).get('url') or block['image'].get('external', {}).get('url') or ''
    src = ctx['assets'].get(src, {}).get('uri', src)
    if src.startswith('file:///'):
        src = src.split('file:///', maxsplit = 1)[-1]
    html_text = richtext2html(block['image']['caption'], ctx, title_mode = False)
    html_text_alt = richtext2html(block['image']['caption'], ctx, title_mode = True)
    return open_block(block, ctx, tag = 'figure', class_name = class_name, set_html_contents_and_close = f'<{tag} src="{src}" alt="{html_text_alt}"></{tag}><figcaption>{html_text}</figcaption>')

def callout(block, ctx, tag = 'p', class_name = 'notion-callout-block'):
    icon_type = block['callout'].get('icon', {}).get('type')
    icon_emoji = block['callout'].get('icon', {}).get('emoji', '')
    color = block['callout'].get('color', '')
    return open_block(block, ctx, tag = 'div', class_name = class_name + f' notion-color-{color}', set_html_contents_and_close = f'<div>{icon_emoji}</div><div>\n' + text_like(block, ctx, block_type = 'callout', tag = tag)) + '</div>\n'

def embed(block, ctx, tag = 'iframe', class_name = 'notion-embed-block', html_text = ''):
    block_type = block.get('type', '')
    link_type = block[block_type].get('type', '')
    src = block[block_type].get('url') or block[block_type].get(link_type, {}).get('url') or ''
    html_text = html_text or richtext2html(block.get(block_type, {}).get('caption', []), ctx) 
    return open_block(block, ctx, tag = 'figure', class_name = class_name, set_html_contents_and_close = f'<figcaption>{html_text}</figcaption><{tag} src="{src}"></{tag}>')

def pdf(block, ctx, tag = 'a', class_name = 'notion-pdf-block', html_icon = '📄 '):
    return embed(block, ctx, class_name = class_name, html_text = link_like({k : v for k, v in block.items() if k != 'id'}, ctx, tag = tag, html_icon = html_icon))

def file(block, ctx, tag = 'a', class_name = 'notion-file-block', html_icon = '📎 '):
    return link_like(block, ctx, tag = tag, class_name = class_name, html_icon = html_icon, line_break = True)

def bookmark(block, ctx, tag = 'a', class_name = 'notion-bookmark-block', html_icon = '🔖 '):
    # TODO: div and domain name on top: www.ofii.fr, all clickable
    return link_like(block, ctx, tag = tag, class_name = class_name, full_url_as_caption = True, html_icon = html_icon, line_break = True)

def link_preview(block, ctx, tag = 'a', class_name = 'notion-link_preview-block', html_icon = '🌐 '):
    return link_like(block, ctx, tag = tag, class_name = class_name, html_icon = html_icon, line_break = True)

def paragraph(block, ctx, tag = 'p', class_name = 'notion-text-block'):
    if block.get('has_children') is False and not (block[block['type']].get('text') or block[block['type']].get('rich_text')):
        return open_block(block, ctx, tag = 'br', class_name = class_name, selfclose = True)
    return text_like(block, ctx, block_type = 'paragraph', tag = tag, class_name = class_name)

def heading_1(block, ctx, tag = 'h1', class_name = 'notion-header-block'):
    return heading_like(block, ctx, tag = tag, class_name = class_name)

def heading_2(block, ctx, tag = 'h2', class_name = 'notion-sub_header-block'):
    return heading_like(block, ctx, tag = tag, class_name = class_name)
    
def heading_3(block, ctx, tag = 'h3', class_name = 'notion-sub_sub_header-block'):
    return heading_like(block, ctx, tag = tag, class_name = class_name)

def quote(block, ctx, tag = 'blockquote', class_name = 'notion-quote-block'):
    return text_like(block, ctx, block_type = 'quote', tag = tag, class_name = class_name)

def toggle(block, ctx, tag = 'span', class_name = 'notion-toggle-block'):
    return toggle_like(block, ctx, block_type = 'toggle', tag = tag, class_name = class_name)

def divider(block, ctx, tag = 'hr', class_name = 'notion-divider-block'):
    return open_block(block, ctx, tag = tag, class_name = class_name, selfclose = True)

def bulleted_list_item(block, ctx, tag = 'ul', begin = False, end = False, class_name = 'notion-bulleted_list-block'):
    return (f'<{tag} class="{class_name}">\n' if begin else '') + text_like(block, ctx, block_type = 'bulleted_list_item', tag = 'li') + ('\n' + f'</{tag}>\n' if end else '')

def numbered_list_item(block, ctx, tag = 'ol', begin = False, end = False, class_name = 'notion-numbered_list-block'):
    return (f'<{tag} class="{class_name}">\n' if begin else '') + text_like(block, ctx, block_type = 'numbered_list_item', tag = 'li') + ('\n' + f'</{tag}>\n' if end else '')

def code(block, ctx, tag = 'code', class_name = 'notion-code-block'):
    html_caption = richtext2html(block['code'].get('caption', []), ctx)
    language = block['code'].get('language', '')
    return open_block(block, ctx, tag = 'figure', attrs = {'data-language' : language}, class_name = class_name, set_html_contents_and_close = f'<figcaption>{html_caption}</figcaption>\n<pre><{tag}>' + richtext2html(block['code'].get('rich_text', []), ctx) + f'</{tag}></pre>')

def equation(block, ctx, tag = 'code', class_name = 'notion-equation-block'):
    html_expression = html.escape(block['equation'].get('expression', '') or block.get('plain_text', ''))
    return open_block(block, ctx, tag = tag, class_name = class_name, set_html_contents_and_close = html_expression)

def child_database(block, ctx, tag = 'figure', class_name = 'notion-child_database-block', html_icon = '📚', untitled = '???'):
    html_child_database_title = html.escape(block['child_database'].get('title') or untitled)
    return open_block(block, ctx, tag = tag, class_name = class_name, set_html_contents_and_close = f'<figcaption>{html_icon}<strong>{html_child_database_title}</strong>{html_icon}</figcaption>')

def breadcrumb(block, ctx, tag = 'div', class_name = 'notion-breadcrumb-block'):
    page_block = get_page_current(block, ctx)
    page_id = page_block['id']
    return open_block(block, ctx, tag = tag, class_name = class_name, set_html_contents_and_close = '&nbsp;/&nbsp;'.join(block2html(subblock, ctx).replace('<br/>', '') for subblock in reversed(ctx['page_parent_paths'][page_id])))

def mention(block, ctx, tag = 'div', class_name = 'notion-text-mention-token', untitled = 'Untitled'):
    mention_type = block['mention'].get('type')
    mention_payload = block['mention'][mention_type]
  
    if mention_type == 'page':
        page_id = mention_payload.get('id', '')
        return link_to_page(dict(block, type = 'link_to_page', link_to_page = dict(type = 'page_id', page_id = page_id)), ctx, html_icon = '📄⤷', class_name = 'notion-alias-block notion-page-mention-token')

    if mention_type == 'database':
        return link_like(block, ctx, html_icon = '🗃️⤷', tooltip = 'notion mention of database', class_name = class_name)

    if mention_type == 'link_preview':
        return link_preview(block, ctx)

    if mention_type == 'user':
        user_id = mention_payload.get('id', '')
        user_name = block['plain_text'].removeprefix('@')
        return open_block(block, ctx, tag = 'strong', class_name = class_name, attrs = dict(title = "notion mention of user"), set_html_contents_and_close = f'@{user_name}#{user_id}')

    if mention_type == 'date':
        date_text = block.get('plain_text', '')
        return open_block(block, ctx, tag = 'strong', class_name = class_name, attrs = dict(title = "notion mention of date"), set_html_contents_and_close = f'@{date_text}⏰')
    
    return unsupported(block, ctx)

def template(block, ctx, tag = 'figure', class_name = 'notion-template-block'):
    html_text = richtext2html(block[block_type].get('text') or block[block_type].get('rich_text') or [], ctx)
    html_children = children_like(block, ctx)
    return open_block(block, ctx, tag = tag, class_name = class_name, set_html_contents_and_close = f'<figcaption>{html_text}</figcaption>\n{html_children}')

def synced_block(block, ctx, tag = 'figure', class_name = 'notion-synced_block-block'):
    synced_from_block_id = block['synced_block'].get('synced_from', {}).get('block_id', '')
    html_children = children_like(block, ctx)
    return open_block(block, ctx, tag = tag, class_name = class_name, set_html_contents_and_close = f'<figcaption>{synced_from_block_id}</figcaption>\n{html_children}')

def to_do(block, ctx, tag = 'div', class_name = 'notion-to_do-block'):
    checked = block[block_type].get('checked', False) 
    return text_like(block, ctx, tag = tag, class_name = class_name, checked = checked)

def unsupported(block, ctx, tag = 'div', class_name = 'notion-unsupported-block', comment = True, **ignored):
    block_type = block.get('type', '') or block.get('object', '')
    return '\n<!--\n' * comment + open_block(block, ctx, tag = tag, class_name = class_name, attrs = {'data-notion-block_type' : block_type}, selfclose = True).replace('-->' * comment, '__>' * comment) + '\n-->\n' * comment

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
        parent_block = get_page_current(block, ctx)
        print('UNSUPPORTED block: block_type=[{block_type}] block_id=[{block_id}] block_type_parent=[{block_type_parent}] block_id_parent=[{block_id_parent}] title_parent=[{title_parent}]'.format(block_type = block.get('type', '') or block.get('object', ''), block_id = block.get('id', ''), block_type_parent = parent_block.get('type', '') or parent_block.get('object', ''), block_id_parent = parent_block.get('id', ''), title_parent = get_page_title(parent_block)), file = ctx['log_unsupported_blocks'])

    return block2render[block_type](block, ctx, **kwargs)

def sitemap_urlset_read(path):
    xml = ''
    if path and os.path.exists(path):
        with open(path, 'r') as fp:
            xml = f.read()
    if not xml.strip():
        return []

    node_doc = xml.dom.minidom.parseString(xml)
    assert node_doc.documentElement.nodeName == 'urlset'
    return [{n.nodeName : ''.join(nn.nodeValue for nn in n.childNodes if nn.nodeType == nn.TEXT_NODE) for n in node_url.childNodes if n.nodeType == n.ELEMENT_NODE} for node_url in node_doc.documentElement.getElementsByTagName('url')]
    
def sitemap_urlset_write(urlset, path):
    node_doc = xml.dom.minidom.Document()
    node_root = node_doc.appendChild(node_doc.createElement('urlset'))
    node_root.setAttribute('xmlns:xsi', 'http://www.w3.org/2001/XMLSchema-instance')
    node_root.setAttribute('xsi:schemaLocation', 'http://www.sitemaps.org/schemas/sitemap/0.9 http://www.sitemaps.org/schemas/sitemap/0.9/sitemap.xsd')
    node_root.setAttribute('xmlns', 'http://www.sitemaps.org/schemas/sitemap/0.9')
    for entry in urlset:
        node_url = node_root.appendChild(node_doc.createElement('url'))
        for field, value in entry.items():
            node_url.appendChild(node_doc.createElement(field)).appendChild(node_doc.createTextNode(str(value)))
    
    with open(path, 'w') as fp:
        node_doc.writexml(fp, addindent = '  ', newl = '\n')


def pop_and_replace_child_pages_recursively(block, child_pages_by_parent_id = {}, parent_id = None):
    block_type = block.get('type') or block.get('object')
    if block_type in ['page', 'child_page']:
        if block.get('id') not in child_pages_by_parent_id:
            child_pages_by_parent_id[block.get('id')] = [] 
    for key in ['children', 'blocks']:
        for i in reversed(range(len(block[key]) if block.get(key, []) else 0)):
            subblock_type = block[key][i].get('type') or block[key][i].get('object')
            subblock = block[key][i]
            if subblock_type == 'child_page':
                parent_id_type = 'page_id' if block_type in ['page', 'child_page'] else 'block_id'
                block[key][i] = dict( object = 'block', type = 'link_to_page', has_children = False, link_to_page = dict(type = 'page_id', page_id = subblock['id']), parent = {'type' : parent_id_type, parent_id_type : block['id']} )
                if parent_id not in child_pages_by_parent_id:
                    child_pages_by_parent_id[parent_id] = []
                child_pages_by_parent_id[parent_id].append(subblock)
                pop_and_replace_child_pages_recursively(subblock, child_pages_by_parent_id = child_pages_by_parent_id, parent_id = subblock['id'])
            else:
                pop_and_replace_child_pages_recursively(subblock, child_pages_by_parent_id = child_pages_by_parent_id, parent_id = parent_id)

def discover_assets(blocks, asset_urls = [], include_image = True, include_file = False):
    for block in blocks:
        for key in ['children', 'blocks']:
            if block.get(key, []):
                discover_assets(block[key], asset_urls = asset_urls)
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

def prepare_and_extract_assets(notion_pages, ctx, assets_dir, notion_assets = {}, extract_assets = False):
    urls = discover_assets(notion_pages.values(), [])
    print('\n'.join('URL ' + url for url in urls), file = ctx['log_urls'])
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

def extract8html(output_path, ctx, sitepages2html, page_ids = [], notion_pages_flat = {}, extract_assets = False, child_pages_by_parent_id = {}, index_html = False, mode = ''):
    notion_assets = ctx.get('assets', {})

    if mode == 'single':
        ctx['assets'] = prepare_and_extract_assets(ctx['pages'], ctx, assets_dir = output_path + '_files', notion_assets = notion_assets, extract_assets = extract_assets)
        with open(output_path, 'w', encoding = 'utf-8') as f:
            f.write(sitepages2html(page_ids, ctx = ctx, notion_pages = notion_pages_flat))
        return print(output_path)

    os.makedirs(output_path, exist_ok = True)
    for page_id in page_ids:
        page_block = notion_pages_flat[page_id]
        os.makedirs(output_path, exist_ok = True)
        page_slug = get_page_slug(page_id, ctx)
        page_dir = os.path.join(output_path, page_slug) if index_html and page_slug != 'index' else output_path
        os.makedirs(page_dir, exist_ok = True)
        html_path = os.path.join(page_dir, 'index.html' if index_html else page_slug + '.html')
        assets_dir = os.path.join(page_dir, page_slug + '_files')
        notion_assets_for_block = prepare_and_extract_assets({page_id : page_block}, ctx, assets_dir = assets_dir, notion_assets = notion_assets, extract_assets = extract_assets)
        ctx['assets'] = notion_assets_for_block
        with open(html_path, 'w', encoding = 'utf-8') as f:
            f.write(sitepages2html([page_id], ctx = ctx, notion_pages = notion_pages_flat))
        print(html_path)
        if child_pages := child_pages_by_parent_id.pop(page_id, []):
            extract8html(page_dir, ctx = ctx, page_ids = [child_page['id'] for child_page in child_pages], notion_pages_flat = notion_pages_flat, child_pages_by_parent_id = child_pages_by_parent_id, index_html = index_html, extract_assets = extract_assets, sitepages2html = sitepages2html, mode = mode)

def get_block_index(ctx):
    id2block = {}
    stack = list(ctx['pages'].values())
    while stack:
        top = stack.pop()
        id2block[top.get('id', '')] = top
        stack.extend(top.get('blocks', []) + top.get('children', []))
    id2block_no_dashes = {block_id.replace('-', '') : block for block_id, block in id2block.items()}
    return id2block | id2block_no_dashes

def get_page_parent_paths(notion_pages_flat, ctx, child_pages_by_id = {}):
    page_parent_paths = {}
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
                parent_path.append(dict(type = 'link_to_page', link_to_page = dict(type = 'page_id', page_id = block_id), parent = dict(type = 'page_id', page_id = header_parent_page_id), plain_text = get_page_title(block, untitled = '')))
            parent_id = block['parent'].get(block['parent'].get('type'))
            if parent_id not in id2block:
                break
            block_id = parent_id
        page_parent_paths[page_id] = parent_path
    return page_parent_paths

def main(
        input_json,
        output_path,
        notion_page_id,
        extract_assets,
        extract_html,
        theme_py,
        sitemap_xml,

        config_json,
        config_html_toc,
        config_html_details_open,
        config_html_columnlist_disable,
        config_html_link_to_page_index_html,
        config_html_body_header_html,
        config_html_body_footer_html,
        config_html_article_header_html,
        config_html_article_footer_html,
        config_base_url,
        config_edit_url,

        log_unsupported_blocks,
        log_urls,
    ):
    config = json.load(open(config_json)) if config_json else {}
    if config_html_details_open:
        config['html_details_open'] = config_html_details_open
    if config_html_columnlist_disable:
        config['html_columnlist_disable'] = config_html_columnlist_disable
    if config_html_link_to_page_index_html:
        config['html_link_to_page_index_html'] = config_html_link_to_page_index_html
    if config_html_toc:
       config['html_toc'] = config_html_toc
    if config_html_body_header_html:
        config['html_body_header_html'] = config_html_body_header_html
    if config_html_body_footer_html:
        config['html_body_footer_html'] = config_html_body_footer_html
    if config_html_article_header_html:
        config['html_article_header_html'] = config_html_article_header_html
    if config_html_article_footer_html:
        config['html_article_footer_html'] = config_html_article_footer_html

    sitemap = sitemap_urlset_read(sitemap_xml) if sitemap_xml else []

    notion_cache = json.load(open(input_json)) if input_json else {}
    notion_assets = notion_cache.get('assets', {})
    notion_pages = notion_cache.get('pages', {})
    notion_pages = { page_id : page for page_id, page in notion_pages.items() if page['parent']['type'] in ['workspace', 'page_id'] and (page.get('object') or page.get('type')) in ['page', 'child_page'] }

    notion_pages_flat = copy.deepcopy(notion_pages)
    child_pages_by_parent_id = {}
    for page_id, page in notion_pages_flat.items():
        pop_and_replace_child_pages_recursively(page, child_pages_by_parent_id = child_pages_by_parent_id, parent_id = page_id)
    child_pages_by_id = {child_page['id'] : child_page for pages in child_pages_by_parent_id.values() for child_page in pages}
    notion_pages_flat |= child_pages_by_id

    root_page_ids = notion_page_id or list(notion_pages.keys())
    for i in range(len(root_page_ids)):
        for k, v in config.get('slugs', {}).items():
            if root_page_ids[i] == v:
                root_page_ids[i] = k
        for k in notion_pages.keys():
            if root_page_ids[i] == k.replace('-', ''):
                root_page_ids[i] = k
    assert all(page_id in notion_pages_flat for page_id in root_page_ids)

    page_ids = root_page_ids + [child_page['id'] for page_id in root_page_ids for child_page in child_pages_by_parent_id.get(page_id, []) if child_page['id'] not in root_page_ids]
    #page_ids = page_ids # child_pages_by_id = child_pages_by_id if extract_html in ['flat', 'flat.html'] else {}

    ctx = {}
    ctx['html_details_open'] = config.get('html_details_open', False)
    ctx['html_columnlist_disable'] = config.get('html_columnlist_disable', False)
    ctx['html_link_to_page_index_html'] = config.get('html_link_to_page_index_html', False)
    ctx['slugs'] = config.get('slugs', {})
   
    ctx['sitemap'] = sitemap
    ctx['output_path'] = output_path if output_path else '_'.join(notion_page_id) if extract_html != 'single' else (input_json.removesuffix('.json') + '.html')
    ctx['extract_html'] = extract_html
    ctx['assets'] = notion_assets
    ctx['unix_seconds_begin'] = notion_cache.get('unix_seconds_begin', 0)
    ctx['unix_seconds_end'] = notion_cache.get('unix_seconds_end', 0)
    ctx['unix_seconds_generated'] = int(time.time())
    ctx['pages'] = notion_pages_flat
    ctx['page_ids'] = page_ids
    ctx['child_pages_by_parent_id'] = child_pages_by_parent_id
    ctx['page_parent_paths'] = get_page_parent_paths(notion_pages_flat, ctx, child_pages_by_id = child_pages_by_id)
    ctx['id2block'] = get_block_index(ctx)

    ctx['log_unsupported_blocks'] = open(log_unsupported_blocks if log_unsupported_blocks else os.devnull , 'w')
    ctx['log_urls'] = open(log_urls if log_urls else os.devnull , 'w')

    try:
        theme = importlib.import_module(os.path.splitext(theme_py)[0])
    except:
        assert os.path.isfile(theme_py)
        sys.path.append(os.path.dirname(theme_py))
        theme = importlib.import_module(os.path.splitext(theme_py)[0])

    read_html_snippet = lambda path: open(path).read() if path and os.path.exists(path) else ''
    sitepages2html = functools.partial(theme.sitepages2html, block2html = block2html, toc = config.get('html_toc', False), html_body_header_html = read_html_snippet(config.get('html_body_header_html', '')), html_body_footer_html = read_html_snippet(config.get('html_body_footer_html', '')), html_article_header_html = read_html_snippet(config.get('html_article_header_html', '')), html_article_footer_html = read_html_snippet(config.get('html_article_footer_html', '')))
    extract8html(ctx['output_path'], ctx, sitepages2html = sitepages2html, page_ids = page_ids, notion_pages_flat = notion_pages_flat, extract_assets = extract_assets, child_pages_by_parent_id = child_pages_by_parent_id if extract_html == 'nested' else {}, index_html = extract_html in ['flat', 'nested'], mode = extract_html)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--input-json', '-i', required = True)
    parser.add_argument('--output-path', '-o')
    parser.add_argument('--notion-page-id', nargs = '*', default = [])
    parser.add_argument('--extract-assets', action = 'store_true')
    parser.add_argument('--extract-html', default = 'single', choices = ['single', 'flat', 'flat.html', 'nested'])
    parser.add_argument('--theme-py', default = 'minima.py')
    parser.add_argument('--sitemap-xml')

    parser.add_argument('--config-json')
    parser.add_argument('--config-html-toc', action = 'store_true')
    parser.add_argument('--config-html-details-open', action = 'store_true')
    parser.add_argument('--config-html-columnlist-disable', action = 'store_true')
    parser.add_argument('--config-html-link-to-page-index-html', action = 'store_true')
    parser.add_argument('--config-html-body-header-html')
    parser.add_argument('--config-html-body-footer-html')
    parser.add_argument('--config-html-article-header-html')
    parser.add_argument('--config-html-article-footer-html')
    parser.add_argument('--config-base-url')
    parser.add_argument('--config-edit-url')

    parser.add_argument('--log-unsupported-blocks')
    parser.add_argument('--log-urls')

    args = parser.parse_args()
    print(args)
    
    if os.path.exists(args.input_json) and os.path.isfile(args.input_json):
        main(**vars(args))

    elif os.path.exists(args.input_json) and os.path.isdir(args.input_json):
        file_paths_recursive_json = [os.path.join(dirpath, basename) for dirpath, dirnames, filenames in os.walk(args.input_json) for basename in filenames if basename.endswith('.json')]
        for file_path in file_paths_recursive_json:
            try:
                with open(file_path) as f:
                    j = json.load(f)
                if 'pages' not in j:
                    continue
                print(file_path)
                main(**dict(vars(args), input_json = file_path))
            except:
                continue
