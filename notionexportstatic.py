# TODO: markdown: quote-tab
# TODO: child_page CSS block
# TODO: markdown: check numbered_list + heading1 - maybe need to lift up heading_1 out of numbered_list # notion4ever: This is needed, because notion thinks, that if the page contains numbered list, header 1 will be the child block for it, which is strange.
# TODO: image detection for summary image
# TODO: if no page_ids passed -> use slugs and make sure that child pages are not downloaded twice
# TODO: for symmetry, implement flat mode of table_of_contents_2markdown

import os
import re
import sys
import json
import html
import time
import copy
import base64
import hashlib
import datetime
import argparse
import functools
import importlib
import unicodedata
import urllib.parse
import urllib.error
import urllib.request
import xml.dom.minidom

mimedb = {
    '.gif'      : 'image/gif', 
    '.jpg'      : 'image/jpeg', 
    '.jpeg'     : 'image/jpeg', 
    '.png'      : 'image/png', 
    '.svg'      : 'image/svg+xml', 
    '.webp'     : 'image/webp', 
    '.pdf'      : 'application/pdf', 
    '.txt'      : 'text/plain'
}
mimedefault     = 'application/octet-stream'

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36'
}

##############################

def notionapi_retrieve_page_list(notion_token, notion_page_ids_no_dashes):
    # https://developers.notion.com/reference/retrieve-a-page
    # https://developers.notion.com/reference/retrieve-a-page-property
    # https://developers.notion.com/reference/retrieve-a-block
    # https://developers.notion.com/reference/get-block-children
    # https://developers.notion.com/reference/retrieve-a-database

    import notion_client
    notionapi = notion_client.Client(auth = notion_token)
    
    notion_pages_and_databases = {}
    for notion_page_id_no_dashes in notion_page_ids_no_dashes:
        page_type, page = None, {}
        for k, f in [('page', notionapi.pages.retrieve), ('database', notionapi.databases.retrieve), ('child_page', notionapi.blocks.retrieve)]:
            try:
                page_type, page = k, f(notion_page_id_no_dashes)
                break
            except notion_client.APIResponseError as exc:
                continue
            except Exception as exc:
                print(exc)
                break
        assert page_type
        
        notion_pages_and_databases[page['id']] = page

        stack = [page]
        while stack:
            block = stack.pop()
            block_type = block.get('object') or block.get('type') or ''
            block_id_no_dashes = block['id'].replace('-', '')
            children = block['blocks' if block_type in ['page', 'database'] else 'children'] = []
            start_cursor = None
            while True:
                if block_type in ['database', 'child_database']:
                    response = notionapi.databases.query(block_id_no_dashes, **(dict(start_cursor = start_cursor) if start_cursor is not None else {}))
                else:
                    response = notionapi.blocks.children.list(block_id_no_dashes, **(dict(start_cursor = start_cursor) if start_cursor is not None else {}))
                start_cursor = response['next_cursor']
                children.extend(response['results'])
                stack.extend(response['results'])
                if start_cursor is None or response['has_more'] is False:
                    break 
    
    notionjson = dict(pages = notion_pages_and_databases, unix_seconds_downloaded = int(time.time()))
    return notionjson

##############################

def blocktag_2html(block = {}, ctx = {}, class_name = '', tag = '', selfclose = False, set_html_contents_and_close = None, prefix = '', suffix = '', attrs = {}, **kwargs):
    notion_attrs_class_name = 'notion-block ' + class_name
    notion_attrs = (' data-block-id="{id}" '.format(id = get_block_id(block))) * bool(get_block_id(block)) + (f' class="{notion_attrs_class_name}" ' if notion_attrs_class_name else '') + ' ' + ' '.join(f'{k}="{v}"' if v is not None else k for k, v in attrs.items()) + ' '
    endline_if_html = '\n' * ('<' in (set_html_contents_and_close or '') or '>' in (set_html_contents_and_close or ''))
    return (f'{prefix}<{tag} ' + (notion_attrs if block else '') + '/' * selfclose + f'>{endline_if_html}' + (set_html_contents_and_close + f'{endline_if_html}</{tag}>\n' if set_html_contents_and_close is not None else '') + suffix) if tag else ''

def childrenlike_2html(block, ctx, tag = ''):
    res = ''
    subblocks = sum([block.get(key, []) or block.get(block.get('type'), {}).get(key, []) for key in ('children', 'blocks')], [])
    for i, subblock in enumerate(subblocks):
        same_block_type_as_prev = i > 0 and subblock.get('type') == subblocks[i - 1].get('type')
        same_block_type_as_next = i + 1 < len(subblocks) and subblock.get('type') == subblocks[i + 1].get('type')
        res += ((f'<{tag}>') if tag else '') + block_2html(subblock, ctx, begin = not same_block_type_as_prev, end = not same_block_type_as_next) + (f'</{tag}>\n' if tag else '')
    return res

def richtext_2html(block, ctx = {}, title_mode = False, caption = False, rich_text = False):
    # https://www.notion.so/help/customize-and-style-your-content#markdown
    # https://developers.notion.com/reference/rich-text
    if isinstance(block, dict):
        block_type = get_block_type(block)
        if rich_text:
            block = get_block_rich_text(block)
        if caption: 
            block = block.get(get_block_type(block), {}).get('caption', [])
    if isinstance(block, list):
        return ''.join(richtext_2html(subblock, ctx, title_mode = title_mode) for subblock in block).strip()
    
    plain_text = block['plain_text']
    content = block.get('content', '')
    anno = block['annotations']
    href = block.get('href', '')
    if title_mode:
        return plain_text
    if block['type'] == 'mention':
        return mention_2html(block, ctx)
    if block['type'] == 'equation':
        return equation_2html(block, ctx, inline = True)
    
    res = html.escape(plain_text)
    if href:
        res = link_to_page_2html(block, ctx, line_break = False) if href.startswith('/') else linklike_2html(block, ctx)
    if anno['bold']:
        res = f'<b>{res}</b>' 
    if anno['italic']:
        res = f'<i>{res}</i>'
    if anno['strikethrough']:
        res = f'<s>{res}</s>'
    if anno['underline']:
        res = f'<u>{res}</u>'
    if anno['code']:
        res = f'<code class="notion-code-inline">{res}</code>'
    if (color := anno['color']) != 'default':
        res = f'<span style="color:{color}">{res}</span>'
    return res

def textlike_2html(block, ctx, tag = 'span', class_name = '', attrs = {}, icon = '', checked = None):
    color = block.get(get_block_type(block), {}).get('color', '')
    rich_text = richtext_2html(block, ctx, rich_text = True)
    checkbox = '<input type="checkbox" disabled {} />'.format('checked' * checked) if checked is not None else ''
    html = checkbox + rich_text + childrenlike_2html(block, ctx) + icon
    return blocktag_2html(block, ctx, tag = tag, class_name = class_name + f' notion-color-{color}', attrs = attrs, set_html_contents_and_close = html)

def toggle_2html(block, ctx, tag = 'span', class_name = 'notion-toggle-block', attrs = {}, icon = ''):
    color = block.get(get_block_type(block), {}).get('color', '')
    rich_text = richtext_2html(block, ctx, rich_text = True)
    return blocktag_2html(block, ctx, tag = 'details', class_name = f'notion-color-{color} notion-toggle-like ' + class_name, attrs = dict(attrs, open = None) if ctx['html_details_open'] else attrs, set_html_contents_and_close = f'<summary><{tag}>{rich_text}{icon}</{tag}></summary>\n' + childrenlike_2html(block, ctx))

def headinglike_2html(block, ctx, tag, class_name = ''):
    block_id_no_dashes = get_block_id_no_dashes(block)
    block_slug = get_heading_slug(block, ctx)
    is_toggleable = block.get(get_block_type(block), {}).get('is_toggleable')
    anchor = f'<a href="#{block_slug}"></a><a href="#{block_id_no_dashes}" class="notion-heading-like-icon"></a>'
    return (textlike_2html if not is_toggleable else toggle_2html)(block, ctx, tag = tag, class_name = 'notion-heading-like ' + class_name, attrs = dict(id = block_id_no_dashes), icon = anchor)

def linklike_2html(block, ctx, tag = 'a', class_name = '', full_url_as_caption = False, icon = '', line_break = False, download = None):
    src = get_block_url(block)
    asset_url = get_asset_url(block, ctx)
    download = get_url_basename(src) if download is None and is_url_datauri(asset_url) else download
    rich_text = richtext_2html(block, ctx, caption = True) or html.escape(block.get(get_block_type(block), {}).get('name') or block.get('plain_text') or (src if full_url_as_caption else get_url_basename(src)))
    return blocktag_2html(block, ctx, tag = tag, attrs = dict(href = src) | (dict(download = download) if download is not None else {}), class_name = class_name, set_html_contents_and_close = icon + rich_text) + '<br/>' * line_break

def page_2html(block, ctx, tag = 'article', class_name = 'notion-page-block', strftime = '%Y/%m/%d %H:%M:%S', prefix = '', suffix = '', class_name_page_title = '', class_name_page_content = '', class_name_header = '', class_name_page = ''):
    datetime_published = get_page_time_published(block, ctx, strftime = strftime, key = 'unix_seconds_generated' if ctx['timestamp_published'] else 'unix_seconds_downloaded') 
    src_cover = get_asset_url(get_page_cover_url(block), ctx)
    page_id = get_block_id(block)
    page_id_no_dashes = get_block_id_no_dashes(block)
    page_title = html.escape(get_page_title(block, ctx))
    page_emoji, page_icon_url = get_page_icon(block, ctx)
    page_url = get_page_url(block, ctx)
    page_slug = get_page_slug(page_id, ctx)
    src_edit = get_page_edit_url(page_id, ctx, page_slug = page_slug)
    children = childrenlike_2html(block, ctx)

    anchor = link_to_page_2html(block, ctx, caption = '', line_break = False, class_name = 'notion-page-like-icon') + f'<a href="{src_edit}" target="_blank" class="notion-page-like-edit-icon"></a>' * bool(src_edit)
    page_icon_id = f'id="{page_id_no_dashes}"' * bool(page_id_no_dashes != page_slug)
    page_icon = f'<img src="{page_icon_url}"></img>' * bool(page_icon_url)
    
    return blocktag_2html(block, ctx, tag = tag, attrs = {'data-notion-url' : page_url}, class_name = 'notion-page ' + class_name_page, set_html_contents_and_close = f'''
        {prefix}
        <header class="{class_name_header}">
            <img src="{src_cover}" class="notion-page-cover"></img>
            <h1 {page_icon_id} class="notion-record-icon">{page_emoji}{page_icon}</h1> 
            <h1 id="{page_slug}" class="{class_name} {class_name_page_title}">{page_title}{anchor}</h1>
            <i><time class="notion-page-block-datetime-published dt-published" datetime="{datetime_published}">@{datetime_published}</time></i>
        </header>
        <div class="notion-page-content {class_name_page_content}">
            {children}
        </div>
        {suffix}
    ''')

##############################

def table_of_contents_2html(block, ctx, tag = 'ul', class_name = 'notion-table_of_contents-block'):
    # https://www.notion.so/help/columns-headings-and-dividers#how-it-works
    if block.get('site_table_of_contents_page_ids'):
        table_of_contents_page_tree = lambda page_ids: '' if not page_ids else ('<ul class="notion-table_of_contents-site-page-list">\n' + '\n'.join('<li class="notion-table_of_contents-site-page-item">\n{link_to_page}\n{child_pages}\n</li>'.format(link_to_page = link_to_page_2html(dict(type = 'link_to_page', link_to_page = dict(type = 'page_id', page_id = page_id)), ctx, line_break = False), child_pages = table_of_contents_page_tree([ get_block_id(page) for page in ctx['child_pages_by_parent_id'].get(page_id, []) ]) ) for page_id in page_ids) + '\n</ul>')
        page_ids = block.get('site_table_of_contents_page_ids', [])
        child_page_ids = set(get_block_id(child_page) for child_pages in ctx['child_pages_by_parent_id'].values() for child_page in child_pages)
        root_page_ids = [page_id for page_id in page_ids if page_id not in child_page_ids]
        return '<nav class="notion-table_of_contents-site"><h1 class="notion-table_of_contents-site-header"></h1>\n' + table_of_contents_page_tree(root_page_ids) + '\n<hr/></nav>'
    
    if block.get('site_table_of_contents_flat_page_ids'):
        table_of_contents_page_tree = lambda page_ids: '' if not page_ids else '\n'.join('<li class="notion-table_of_contents-site-page-item">{link_to_page}</li>\n{child_pages}'.format(link_to_page = link_to_page_2html(dict(type = 'link_to_page', link_to_page = dict(type = 'page_id', page_id = page_id)), ctx, line_break = False, class_name = 'page-link'), child_pages = table_of_contents_page_tree([ get_block_id(page) for page in ctx['child_pages_by_parent_id'].get(page_id, []) ]) ) for page_id in page_ids)
        page_ids = block.get('site_table_of_contents_flat_page_ids', [])
        child_page_ids = set(get_block_id(child_page) for child_pages in ctx['child_pages_by_parent_id'].values() for child_page in child_pages)
        root_page_ids = [page_id for page_id in page_ids if page_id not in child_page_ids]
        return '<ul class="notion-table_of_contents-site-page-list">\n' + table_of_contents_page_tree(root_page_ids) + '\n</ul>\n'
    
    page_block = get_page_current(block, ctx)
    headings = get_page_headings(page_block, ctx)
    color = block['table_of_contents'].get('color', '')
    inc_heading_type = dict(heading_0 = 'heading_1', heading_1 = 'heading_2', heading_2 = 'heading_3', heading_3 = 'heading_3').get
    nominal_heading_type, effective_heading_type = 'heading_0', 'heading_0'
    children = ''
    for block in headings:
        block_id_no_dashes = get_block_id_no_dashes(block)
        block_slug = get_heading_slug(block, ctx)
        block_hash = block_slug if ctx['extract_mode'] in ['flat.html', 'flat/index.html'] else block_id_no_dashes
        heading_type = get_block_type(block)
        nominal_heading_type, effective_heading_type = heading_type, min(heading_type, inc_heading_type(effective_heading_type) if heading_type > nominal_heading_type else effective_heading_type)
        rich_text = richtext_2html(block, ctx, rich_text = True, title_mode = True)
        children += f'<li class="notion-table_of_contents-heading notion-table_of_contents-{effective_heading_type}"><a href="#{block_hash}">' + rich_text + '</a></li>\n'
    return blocktag_2html(block, ctx, tag = tag, class_name = class_name + f' notion-color-{color}', set_html_contents_and_close = children, prefix = '<hr/>', suffix = '<hr/>')

def table_2html(block, ctx, tag = 'table', class_name = 'notion-table-block'):
    table_width = block['table'].get('table_width', 0)
    has_row_header = block['table'].get('has_row_header', False)
    has_column_header = block['table'].get('has_column_header', False)
    rows = get_block_children(block)
    children = ''
    for i, subblock in enumerate(rows):
        if i == 0:
            children += '\n<thead>\n' if has_row_header else '\n<tbody>\n'
        children += '<tr>\n'
        cells = subblock.get('table_row', {}).get('cells', [])
        for j, cell in enumerate(cells):
            tag_cell = 'th' if (has_row_header and i == 0) or (has_column_header and j == 0) else 'td'
            children += f'<{tag_cell}>' + (''.join('<div>{rich_text}</div>'.format(rich_text = richtext_2html(subcell, ctx)) for subcell in cell) if isinstance(cell, list) else richtext_2html(cell, ctx)) + f'</{tag_cell}>\n'
        if len(cells) < table_width:
            children += '<td></td>' * (table_width - len(cells))
        children += '</tr>\n'
        if i == 0:
            children += '\n</thead>\n<tbody>\n' if has_row_header else ''
    children += '\n</tbody>\n'
    return blocktag_2html(block, ctx, tag = tag, class_name = class_name, set_html_contents_and_close = children)

def video_2html(block, ctx, tag = 'p', class_name = 'notion-video-block'):
    url = get_asset_url(block, ctx)
    is_youtube, url, urlimg = normalize_youtube_url(url, embed = True)
    caption = richtext_2html(block, ctx, caption = True)
    html_contents = f'<div><iframe width="640" height="480" src="{url}" frameborder="0" allowfullscreen></iframe></div>' if is_youtube else f'<video playsinline muted loop controls src="{url}"></video>'
    return blocktag_2html(block, ctx, tag = tag, class_name = class_name, set_html_contents_and_close = html_contents)

image_2html = lambda block, ctx, tag = 'img', class_name = 'notion-image-block': blocktag_2html(block, ctx, tag = 'figure', class_name = class_name, set_html_contents_and_close = '<{tag} src="{src}" alt="{rich_text_alt}"></{tag}><figcaption>{rich_text}</figcaption>'.format(tag = tag, src = get_asset_url(block, ctx), rich_text_alt = richtext_2html(block, ctx, caption = True, title_mode = True), rich_text = richtext_2html(block, ctx, caption = True, title_mode = False)))

def embed_2html(block, ctx, tag = 'iframe', class_name = 'notion-embed-block', caption = '', attrs = dict(width = 640, height = 480)):
    block_type = get_block_type(block)
    src = get_block_url(block) or block.get(block_type, {}).get(block.get(block_type, {}).get('type', ''), {}).get('url') or ''
    src = get_asset_url(src, ctx)
    rich_text = caption or richtext_2html(block, ctx, caption = True) 
    attrstr = ' '.join(f'{k}="{v}"' if v is not None else k for k, v in attrs.items())
    return blocktag_2html(block, ctx, tag = 'figure', class_name = class_name, set_html_contents_and_close = f'<figcaption>{rich_text}</figcaption><{tag} src="{src}" {attrstr}></{tag}>')

def bookmark_2html(block, ctx, tag = 'a', class_name = 'notion-bookmark-block'):
    src = get_block_url(block)
    rich_text = richtext_2html(block, ctx, caption = True) or html.escape(block.get(get_block_type(block), {}).get('name') or block.get('plain_text') or src)
    try:
        netloc = urllib.parse.urlparse(src).netloc
    except:
        netloc = ''
    return blocktag_2html(block, ctx, tag = tag, attrs = dict(href = src), class_name = class_name, set_html_contents_and_close = f'<figure>{netloc}<br/><figcaption>{rich_text}</figcaption></figure>')

def mention_2html(block, ctx, tag = 'div', class_name = dict(page = 'notion-page-mention-token', database = 'notion-database-mention-token', link_preview = 'notion-link-mention-token', user = 'notion-user-mention-token', date = 'notion-date-mention-token'), untitled = 'Untitled'):
    mention_type = block['mention'].get('type')
    mention_payload = block['mention'][mention_type]
    if mention_type == 'page':
        return link_to_page_2html(dict(block, type = 'link_to_page', link_to_page = dict(type = 'page_id', page_id = mention_payload.get('id', ''))), ctx, class_name = class_name[mention_type])
    if mention_type == 'database':
        return linklike_2html(block, ctx, class_name = class_name[mention_type])
    if mention_type == 'link_preview':
        return link_preview_2html(block, ctx, class_name = class_name[mention_type])
    if mention_type == 'user':
        return blocktag_2html(block, ctx, tag = 'strong', class_name = class_name[mention_type], set_html_contents_and_close = '@{user_name}#{user_id}'.format(user_id = mention_payload.get('id', ''), user_name = block.get('plain_text', '').removeprefix('@')))
    if mention_type == 'date':
        return blocktag_2html(block, ctx, tag = 'strong', class_name = class_name[mention_type], set_html_contents_and_close = '@{date_text}'.format(date_text = html.escape(block.get('plain_text', ''))))
    return unsupported_2html(block, ctx)

def link_to_page_2html(block, ctx, tag = 'a', caption = None, line_break = True, class_name = 'notion-alias-block', icon = '', untitled = '???'):
    link_to_page_info = get_page_link_info(block, ctx)
    caption = caption if caption is not None else '{icon}{page_emoji} {page_title}'.format(icon = icon, page_title = html.escape(link_to_page_info['page_title']), page_emoji = link_to_page_info['page_emoji'])
    return blocktag_2html(block, ctx, tag = tag, attrs = dict(href = link_to_page_info['href']), class_name = class_name, set_html_contents_and_close = caption) + '<br/>' * line_break

get_block_rich_text = lambda block: block.get('rich_text', []) or block.get('text', []) or block.get(get_block_type(block), {}).get('rich_text', []) or block.get(get_block_type(block), {}).get('text', []) or []

paragraph_is_empty = lambda block, ctx: block.get('has_children') is False and not get_plain_text(get_block_rich_text(block)).strip()

child_page_2html = lambda block, ctx, tag = 'article', class_name = 'notion-page-block', **kwargs: page_2html(block, ctx, tag = tag, class_name = class_name, **kwargs)
unsupported_2html = lambda block, ctx, tag = 'br', class_name = 'notion-unsupported-block', **ignored: blocktag_2html(block, ctx, tag = tag, class_name = class_name, attrs = {'data-notion-block_type' : get_block_type(block)}, selfclose = True)
divider_2html = lambda block, ctx, tag = 'hr', class_name = 'notion-divider-block': blocktag_2html(block, ctx, tag = tag, class_name = class_name, selfclose = True)
heading_1_2html = lambda block, ctx, tag = 'h1', class_name = 'notion-header-block': headinglike_2html(block, ctx, tag = tag, class_name = class_name)
heading_2_2html = lambda block, ctx, tag = 'h2', class_name = 'notion-sub_header-block': headinglike_2html(block, ctx, tag = tag, class_name = class_name)
heading_3_2html = lambda block, ctx, tag = 'h3', class_name = 'notion-sub_sub_header-block': headinglike_2html(block, ctx, tag = tag, class_name = class_name)

paragraph_2html = lambda block, ctx, tag = 'p', class_name = 'notion-text-block': blocktag_2html(block, ctx, tag = 'br', class_name = class_name, selfclose = True) if paragraph_is_empty(block, ctx) else textlike_2html(block, ctx, tag = tag, class_name = class_name)

column_list_2html = lambda block, ctx, tag = 'div', class_name = 'notion-column_list-block': blocktag_2html(block, ctx, tag = tag, class_name = class_name + ' notion_column_list-block-vertical' * (ctx['html_columnlist_disable'] is True), set_html_contents_and_close = childrenlike_2html(block, ctx))
column_2html = lambda block, ctx, tag = 'div', class_name = 'notion-column-block': blocktag_2html(block, ctx, tag = tag, class_name = class_name, set_html_contents_and_close = childrenlike_2html(block, ctx, tag = tag)) 
bulleted_list_item_2html = lambda block, ctx, tag = 'ul', begin = False, end = False, class_name = 'notion-bulleted_list-block': f'<{tag} class="{class_name}">\n' * begin + textlike_2html(block, ctx, tag = 'li') + f'\n</{tag}>\n' * end
numbered_list_item_2html = lambda block, ctx, tag = 'ol', begin = False, end = False, class_name = 'notion-numbered_list-block': f'<{tag} class="{class_name}">\n' * begin + textlike_2html(block, ctx, tag = 'li') + f'\n</{tag}>\n' * end 
to_do_2html = lambda block, ctx, tag = 'div', class_name = 'notion-to_do-block', begin = False, end = False: textlike_2html(block, ctx, tag = tag, class_name = class_name, checked = block.get(get_block_type(block), {}).get('checked', False))
code_2html = lambda block, ctx, tag = 'code', class_name = 'notion-code-block': blocktag_2html(block, ctx, tag = 'figure', attrs = {'data-language' : block['code'].get('language', '')}, class_name = class_name, set_html_contents_and_close = '<figcaption>{caption}</figcaption>\n<pre><{tag} class="language-{language}">\n'.format(language = block['code'].get('language', ''), caption = richtext_2html(block, ctx, caption = True), tag = tag) + richtext_2html(block, ctx, rich_text = True) + f'\n</{tag}></pre>')
synced_block_2html = lambda block, ctx, tag = 'figure', class_name = 'notion-synced_block-block': blocktag_2html(block, ctx, tag = tag, class_name = class_name, set_html_contents_and_close = '<figcaption>{synced_from_block_id}</figcaption>\n{children}'.format(synced_from_block_id = block['synced_block'].get('synced_from', {}).get('block_id', ''), children = childrenlike_2html(block, ctx)))
equation_2html = lambda block, ctx, tag = 'code', class_name = 'notion-equation-block', inline = False: blocktag_2html(block, ctx, tag = tag, class_name = class_name if not inline else class_name.replace('block', 'inline'), set_html_contents_and_close = html.escape(block['equation'].get('expression', '') or block.get('plain_text', '')))
pdf_2html = lambda block, ctx, tag = 'a', class_name = 'notion-pdf-block': embed_2html(block, ctx, class_name = class_name, caption = linklike_2html({k : v for k, v in block.items() if k != 'id'}, ctx, tag = tag) if not is_url_datauri(get_asset_url(block, ctx)) else '<div><b>{caption}</b></div>'.format(caption = html.escape(get_url_basename(get_block_url(block)))) )
file_2html = lambda block, ctx, tag = 'a', class_name = 'notion-file-block': linklike_2html(block, ctx, tag = tag, class_name = class_name, line_break = True)
breadcrumb_2html = lambda block, ctx, tag = 'div', class_name = 'notion-breadcrumb-block', sep = '&nbsp;/&nbsp;': blocktag_2html(block, ctx, tag = tag, class_name = class_name, set_html_contents_and_close = sep.join(link_to_page_2html(subblock, ctx, line_break = False) for subblock in reversed(ctx['page_parent_paths'][get_block_id(get_page_current(block, ctx)) ])))
template_2html = lambda block, ctx, tag = 'figure', class_name = 'notion-template-block': blocktag_2html(block, ctx, tag = tag, class_name = class_name, set_html_contents_and_close = '<figcaption>{rich_text}</figcaption>\n{children}'.format(rich_text = richtext_2html(block, ctx, rich_text = True), children = childrenlike_2html(block, ctx)))
child_database_2html = lambda block, ctx, tag = 'figure', class_name = 'notion-child_database-block', untitled = '???': blocktag_2html(block, ctx, tag = tag, class_name = class_name, set_html_contents_and_close = '<figcaption><strong>{child_database_title}</strong></figcaption>'.format(child_database_title = html.escape(block['child_database'].get('title') or untitled)))
link_preview_2html = lambda block, ctx, tag = 'a', class_name = 'notion-link_preview-block': linklike_2html(block, ctx, tag = tag, class_name = class_name, line_break = True)

quote_2html = lambda block, ctx, tag = 'blockquote', class_name = 'notion-quote-block': textlike_2html(block, ctx, tag = tag, class_name = class_name)
callout_2html = lambda block, ctx, tag = 'p', class_name = 'notion-callout-block': blocktag_2html(block, ctx, tag = 'div', class_name = class_name + ' notion-color-{color}'.format(color = block['callout'].get('color', '')), set_html_contents_and_close = '<div>{icon_emoji}</div><div>\n'.format(icon_emoji = get_callout_icon(block)) + textlike_2html(block, ctx, tag = tag)) + '</div>\n'

##############################

childrenlike_2markdown = lambda block, ctx, tag = '', newline = '\n': newline.join(block_2markdown(subblock, ctx) for i, subblock in enumerate(sum([block.get(key, []) or block.get(block.get('type'), {}).get(key, []) for key in ('children', 'blocks')], []))) + newline
toggle_2markdown = lambda block, ctx, tag = '', icon = '', title_mode = False: ('<details markdown="1"><summary markdown="1">\n\n' + tag + richtext_2markdown(block, ctx, rich_text = True, title_mode = title_mode) + icon + '\n\n</summary>\n\n' + childrenlike_2markdown(block, ctx) + '\n\n</details>') if ctx['markdown_toggle'] else (tag + '▼ ' + richtext_2markdown(block, ctx, rich_text = True, title_mode = title_mode) + icon + '\n' + childrenlike_2markdown(block, ctx))

def textlike_2markdown(block, ctx, tag = '', icon = '', checked = None, title_mode = False):
    rich_text = richtext_2markdown(block, ctx, rich_text = True, title_mode = title_mode)
    color_unused = block.get(get_block_type(block), {}).get('color', '')
    checkbox = '[{}] '.format('x' if checked else ' ') if checked is not None else ''
    return tag + checkbox + rich_text + icon + '\n' + childrenlike_2markdown(block, ctx)

def headinglike_2markdown(block, ctx, tag = ''):
    block_id_no_dashes = get_block_id_no_dashes(block)
    block_slug = get_heading_slug(block, ctx)
    is_toggleable = block.get(get_block_type(block), {}).get('is_toggleable')
    block_hash = block_slug if ctx['extract_mode'] == 'flat.md' else block_id_no_dashes
    anchor = f' [#](#{block_hash})'
    return (textlike_2markdown if not is_toggleable else toggle_2markdown)(block, ctx, tag = f'<i id="{block_id_no_dashes}"></i><i id="{block_slug}"></i>\n' + tag, icon = anchor)

def linklike_2markdown(block, ctx, tag = '', full_url_as_caption = True, line_break = False):
    src = get_block_url(block)
    asset_url = get_asset_url(block, ctx)
    rich_text = richtext_2markdown(block, ctx, caption = True) or (block.get(get_block_type(block), {}).get('name') or block.get('plain_text') or (src if full_url_as_caption else get_url_basename(src)))
    return (linklike_2html({k : v for k, v in block.items() if k != 'id'}, ctx) if is_url_datauri(asset_url) else f'[{tag}{rich_text}]({src})') + '\n\n' * line_break

def table_2markdown(block, ctx, sanitize_table_cell = lambda md: md.replace('\n', ' ')):
    table_width = block['table'].get('table_width', 0)
    has_row_header = block['table'].get('has_row_header', False)
    has_column_header = block['table'].get('has_column_header', False)
    rows = get_block_children(block)
    children = '\n'
    for i, subblock in enumerate(rows):
        cells = subblock.get('table_row', {}).get('cells', [])
        children += ' | ' + ' | '.join(sanitize_table_cell(richtext_2markdown(cell, ctx)) for cell in cells) + ' | ' + '\n'
        if i == 0:
            children += ' | ' + ' | '.join(['----'] * len(cells)) + ' | ' + '\n'
    children += '\n'
    return children

def table_of_contents_2markdown(block, ctx, tag = '* '):
    if block.get('site_table_of_contents_page_ids'):
        table_of_contents_page_tree = lambda page_ids, depth = 0: '' if not page_ids else ''.join(depth * 4 * ' ' + '{tag}{link_to_page}\n{child_pages}'.format(tag = tag, link_to_page = link_to_page_2markdown(dict(type = 'link_to_page', link_to_page = dict(type = 'page_id', page_id = page_id)), ctx, line_break = False), child_pages = table_of_contents_page_tree([get_block_id(page) for page in ctx['child_pages_by_parent_id'].get(page_id, [])], depth + 1)) for page_id in page_ids)
        page_ids = block.get('site_table_of_contents_page_ids', [])
        child_page_ids = set(get_block_id(child_page) for child_pages in ctx['child_pages_by_parent_id'].values() for child_page in child_pages)
        root_page_ids = [page_id for page_id in page_ids if page_id not in child_page_ids]
        return table_of_contents_page_tree(root_page_ids, depth = 0)
    
    if ctx['markdown_toc_page']:
        return ctx['markdown_toc_page']

    page_block = get_page_current(block, ctx)
    headings = get_page_headings(page_block, ctx)
    color_unused = block['table_of_contents'].get('color', '')
    inc_heading_type = dict(heading_0 = 'heading_1', heading_1 = 'heading_2', heading_2 = 'heading_3', heading_3 = 'heading_3').get
    nominal_heading_type, effective_heading_type = 'heading_0', 'heading_0'
    heading_type2depth = dict(heading_0 = 0, heading_1 = 1, heading_2 = 2, heading_3 = 3)
    children = '---\n'
    for block in headings:
        block_id_no_dashes = get_block_id_no_dashes(block)
        block_slug = get_heading_slug(block, ctx)
        block_hash = block_slug if ctx['extract_mode'] == 'flat.md' else block_id_no_dashes
        heading_type = get_block_type(block)
        nominal_heading_type, effective_heading_type = heading_type, min(heading_type, inc_heading_type(effective_heading_type) if heading_type > nominal_heading_type else effective_heading_type)
        rich_text = richtext_2markdown(block, ctx, rich_text = True, title_mode = True)
        children += max(0, heading_type2depth[effective_heading_type] - 1) * 4 * ' ' + f'{tag}[{rich_text}](#{block_hash})\n'
    children += '---\n'
    return children

def mention_2markdown(block, ctx):
    mention_type = block['mention'].get('type')
    mention_payload = block['mention'][mention_type]
    if mention_type == 'page':
        return link_to_page_2markdown(dict(block, type = 'link_to_page', link_to_page = dict(type = 'page_id', page_id = mention_payload.get('id', ''))), ctx, line_break = False)
    if mention_type == 'database':
        return linklike_2markdown(block, ctx)
    if mention_type == 'link_preview':
        return link_preview_2markdown(block, ctx)
    if mention_type == 'user':
        return ' **@{user_name}#{user_id}** '.format(user_id = mention_payload.get('id', ''), user_name = block.get('plain_text', '').removeprefix('@'))
    if mention_type == 'date':
        return ' **@{date_text}** '.format(date_text = html.escape(block.get('plain_text', '')))
    return unsupported_2markdown(block, ctx)

def page_2markdown(block, ctx, strftime = '%Y/%m/%d %H:%M:%S'):
    datetime_published = get_page_time_published(block, ctx, strftime = strftime, key = 'unix_seconds_generated' if ctx['timestamp_published'] else 'unix_seconds_downloaded') 
    src_cover = get_asset_url(get_page_cover_url(block), ctx)
    page_id = get_block_id(block)
    page_id_no_dashes = get_block_id_no_dashes(block)
    page_title = (get_page_title(block, ctx))
    page_emoji, page_icon_url = get_page_icon(block, ctx)
    page_url = get_page_url(block, ctx)
    page_slug = get_page_slug(page_id, ctx)
    src_edit = get_page_edit_url(page_id, ctx, page_slug = page_slug)
    children = childrenlike_2markdown(block, ctx)
    
    anchor = link_to_page_2markdown(block, ctx, caption = '#', line_break = False)

    res  = f'''---\ntitle: "{page_title}"\ncover: {src_cover}\nemoji: {page_emoji}\n---\n\n''' * bool(ctx['markdown_frontmatter'])
    res += f'![cover]({src_cover})\n\n' * bool(src_cover)
    res += f'<i id="{page_slug}"></i>\n' * bool(ctx['extract_mode'] == 'single.md')
    res += f'# {page_emoji} {page_title}{anchor}\n'
    res += f'[✏️]({src_edit}) ' * bool(src_edit) + f'*@{datetime_published}*\n\n'
    res += children
    return res

child_page_2markdown = lambda block, ctx: page_2markdown(block, ctx)
unsupported_2markdown = lambda block, ctx, tag = '*': ' {tag}unsupported notion block [{block_id}, {block_type}]{tag} '.format(tag = tag, block_id = get_block_id(block), block_type = get_block_type(block))
divider_2markdown = lambda block, ctx, tag = '---': tag
heading_1_2markdown = lambda block, ctx, tag = '# '  : headinglike_2markdown(block, ctx, tag = tag) 
heading_2_2markdown = lambda block, ctx, tag = '## ' : headinglike_2markdown(block, ctx, tag = tag) 
heading_3_2markdown = lambda block, ctx, tag = '### ': headinglike_2markdown(block, ctx, tag = tag) 
paragraph_2markdown = lambda block, ctx: '\n\n' if paragraph_is_empty(block, ctx) else textlike_2markdown(block, ctx)
column_list_2markdown = lambda block, ctx: childrenlike_2markdown(block, ctx)
column_2markdown      = lambda block, ctx: childrenlike_2markdown(block, ctx)
bulleted_list_item_2markdown = lambda block, ctx, tag = '* ' , begin = False, end = False: '\n' * begin + tag + textlike_2markdown(block, ctx) + '\n' * end
numbered_list_item_2markdown = lambda block, ctx, tag = '1. ', begin = False, end = False: '\n' * begin + tag + textlike_2markdown(block, ctx) + '\n' * end
to_do_2markdown              = lambda block, ctx, tag = '- ' , begin = False, end = False: '\n' * begin + textlike_2markdown(block, ctx, tag = tag, checked = block.get(get_block_type(block), {}).get('checked', False)) + '\n' * end
synced_block_2markdown = lambda block, ctx: '---\n**{synced_from_block_id}**\n{children}\n---'.format(synced_from_block_id = block['synced_block'].get('synced_from', {}).get('block_id', ''), children = childrenlike_2markdown(block, ctx))
equation_2markdown     = lambda block, ctx, inline = False: ('```math\n' if not inline else '`' ) + (block['equation'].get('expression', '') or block.get('plain_text', '')) + ('\n```' if not inline else '`')
file_2markdown         = lambda block, ctx, tag = '📎': linklike_2markdown(block, ctx, tag = tag, line_break = True)
pdf_2markdown          = lambda block, ctx, tag = '📄': linklike_2markdown(block, ctx, tag = tag, line_break = True)
bookmark_2markdown     = lambda block, ctx, tag = '🔖': linklike_2markdown(block, ctx, tag = tag, line_break = True)
link_preview_2markdown = lambda block, ctx, tag = '🌐': linklike_2markdown(block, ctx, tag = tag, line_break = True)
embed_2markdown = lambda block, ctx: embed_2html(block, ctx)
child_database_2markdown = lambda block, ctx, untitled = '???', tag = '**': ' {tag}{child_database_title}{tag} '.format(tag = tag, child_database_title = (block['child_database'].get('title') or untitled))
template_2markdown = lambda block, ctx: '---\n{rich_text}\n{children}\n---'.format(rich_text = richtext_2markdown(block, ctx, rich_text = True), children = childrenlike_2markdown(block, ctx))
breadcrumb_2markdown = lambda block, ctx, sep = ' / ': sep.join(link_to_page_2markdown(subblock, ctx, line_break = False) for subblock in reversed(ctx['page_parent_paths'][get_block_id(get_page_current(block, ctx))]))
code_2markdown = lambda block, ctx: '{caption}\n```{language}\n'.format(language = block.get('language', '').replace(' ', '_'), caption = richtext_2html(block, ctx, caption = True)) + richtext_2markdown(block, ctx, rich_text = True) + '\n```'
image_2markdown = lambda block, ctx: '![{rich_text_alt}]({src})\n{rich_text}'.format(src = get_asset_url(block, ctx), rich_text_alt = richtext_2markdown(block, ctx, caption = True, title_mode = True), rich_text = richtext_2markdown(block, ctx, caption = True, title_mode = False))

quote_2markdown = lambda block, ctx, tag = '> ': tag + textlike_2markdown(block, ctx)
def callout_2markdown(block, ctx):
    res = '> {icon_emoji} '.format(icon_emoji = get_callout_icon(block)) + richtext_2markdown(block, ctx, rich_text = True, title_mode = False).rstrip()
    res += '>\n'.join(''.join(f'> {line}\n' for line in block_2markdown(subblock, ctx).splitlines()) + '>\n' for subblock in get_block_children(block))
    return res

def video_2markdown(block, ctx, tag = 'p', class_name = 'notion-video-block'):
    url = get_asset_url(block, ctx)
    is_youtube, url, urlimg = normalize_youtube_url(url, embed = False)
    caption = richtext_2html(block, ctx, caption = True)
    return f'[YouTube: {url}]({url})\n[![YouTube]({urlimg})]({url} "YouTube")' if is_youtube else f'<video playsinline muted loop controls src="{url}"></video>'

def link_to_page_2markdown(block, ctx, line_break = True, caption = None):
    link_to_page_info = get_page_link_info(block, ctx)
    caption = caption if caption is not None else '{page_emoji} {page_title}'.format(page_title = (link_to_page_info['page_title']), page_emoji = link_to_page_info['page_emoji'])
    return '[{caption}]({href})'.format(caption = caption, href = link_to_page_info['href']) + '\n\n' * line_break

def richtext_2markdown(block, ctx, title_mode = False, caption = False, rich_text = False):
    if isinstance(block, dict):
        block_type = get_block_type(block)
        if rich_text:
            block = get_block_rich_text(block)
        if caption: 
            block = block.get(get_block_type(block), {}).get('caption', [])
    if isinstance(block, list):
        return ''.join(richtext_2markdown(subblock, ctx, title_mode = title_mode) for subblock in block).strip()
    
    plain_text = block['plain_text']
    anno = block['annotations']
    content = block.get('content', '')
    href = block.get('href', '')
    if title_mode:
        return plain_text
    if block['type'] == 'mention':
        return mention_2markdown(block, ctx)
    if block['type'] == 'equation':
        return equation_2markdown(block, ctx, inline = True)
    res = (plain_text)
    if href:
        res = link_to_page_2markdown(block, ctx, line_break = False) if href.startswith('/') else linklike_2markdown(block, ctx)
    
    space_left = bool(res) and res[0].isspace()
    space_right = bool(res) and res[-1].isspace()
    if anno['bold']:
       res = ' **{res}** '.format(res = res.strip())
    if anno['italic']:
        res = ' *{res}* '.format(res = res.strip())
    if anno['strikethrough']:
        res = ' ~~~{res}~~~ '.format(res = res.strip())
    if anno['underline']:
        res = f'<u>{res}</u>'
    if anno['code']:
        res = f' `{res}` '
    if (color := anno['color']) != 'default':
        res = f'<span style="color:{color}">{res}</span>' # NOTE: https://github.com/github/markup/issues/1440
    return ' ' * space_left + res + ' ' * space_right


##############################

def is_url_datauri(url):
    return url and url.startswith('data:')

def get_url_basename(url):
    try:
        return os.path.basename(urllib.parse.urlparse(url).path)
    except:
        return url

def sanitize_url_and_strip_querystring(url):
    # url sanitization is non-trivial https://github.com/python/cpython/pull/103855#issuecomment-1906481010, a basic hack below, for proper punycode support need requests module instead
    urlparsed = urllib.parse.urlparse(url)
    try:
        urlparsed.query.encode('ascii')
        urlparsed_query = urlparsed.query
    except UnicodeEncodeError:
        urlparsed_query = urllib.parse.quote(urlparsed.query)
    urlopen_url = urllib.parse.urlunparse(urllib.parse.ParseResult(urlparsed.scheme, urlparsed.netloc, urlparsed.path, urlparsed.params, urlparsed_query, urlparsed.fragment))
    path = urllib.parse.urlunparse(urllib.parse.ParseResult(urlparsed.scheme, urlparsed.netloc, urlparsed.path, '', '', '')) 
    return urlopen_url, path

def hash_url(path):
    sha1 = hashlib.sha1()
    sha1.update(path.encode())
    return sha1.hexdigest()

def get_block_type(block):
    return block.get('type') or block.get('object') or ''

def get_page_link_info(block, ctx, untitled = '???'):
    payload = block.get(block.get('type'), {})
    page_id = payload.get(payload.get('type'), '') or get_block_id(block)
    page_id_no_dashes = get_block_id_no_dashes(page_id) or (block.get('href', '').lstrip('/') if block.get('href', '').startswith('/') else '') 
    page_ids_no_dashes = set(get_block_id_no_dashes(page_id) for page_id in ctx['page_ids'])
    page_slug = get_page_slug(page_id_no_dashes, ctx) 
    page_block = get_page_current(block, ctx)
    page_url_base = get_page_url_relative(page_block, ctx)
    page_url_target = get_page_url_relative(block, ctx)
    href = get_page_relative_link(page_url_base = page_url_base, page_url_target = page_url_target)
    page_block = ctx['id2block'].get(page_id_no_dashes)
    page_emoji, page_icon_url = get_page_icon(page_block, ctx)
    page_title = get_page_title(page_block, ctx) or block.get('plain_text', '') or untitled
    return dict(page_emoji = page_emoji, page_title = page_title, href = href)


def get_page_title(block, ctx, untitled = 'Untitled'):
    if not block: 
        return ''
    return ' '.join(t['plain_text'] for t in block.get('properties', {}).get('title', {}).get('title', [])).strip() or block.get('child_page', {}).get('title', '').strip() or block.get('title', '').strip() or ' '.join(t['plain_text'] for t in block.get('properties', {}).get('Name', {}).get('title', [])).strip() or block.get('plain_text') or untitled
  

def get_block_children(block):
    return block.get('children', []) + block.get('blocks', [])

def get_page_icon(block, ctx):
    if not block:
        return '', ''
    
    payload_icon = block.get('icon') or {}
    icon_emoji = payload_icon.get('emoji', '')
    icon_url = get_block_url(payload_icon)
    
    children = get_block_children(block)
    for subblock in children * (not bool(icon_emoji or icon_url)):
        if subblock.get('type') == 'callout':
            payload_icon = subblock.get('callout', {}).get('icon') or {}
            icon_emoji = icon_emoji or payload_icon.get('emoji', '')
            icon_url = icon_url or get_block_url(payload_icon)
            if bool(icon_emoji or icon_url):
                break

    return icon_emoji, icon_url

def get_page_description(block, ctx, prefix_len = 300, ellipsis = '...'):
    plain_text = get_page_title(block, ctx) + ' | ' + get_plain_text(block)
    return plain_text[:prefix_len] + ellipsis

def get_plain_text(block):
    plain_text = []
    stack = list(block) if isinstance(block, list) else [block]
    while stack:
        top = stack.pop()
        if 'plain_text' in top:
            plain_text.append(top['plain_text'])
        else:
            stack.extend(reversed(get_block_rich_text(top)))
            stack.extend(reversed(get_block_children(top)))
    return ' '.join(plain_text).strip()

def get_page_current(block, ctx):
    parent_block = block
    while get_block_type(parent_block) not in ['page', 'child_page']:
        parent_id = parent_block.get('parent', {}).get(parent_block.get('parent', {}).get('type'))
        if not parent_id or parent_id not in ctx['id2block']:
            break
        parent_block = ctx['id2block'][parent_id]
    return parent_block

def resolve_page_ids(root_page_ids, all_page_and_child_page_ids, notion_slugs):
    for i in range(len(root_page_ids)):
        for k, v in notion_slugs.items():
            if root_page_ids[i].lower() == v.lower():
                root_page_ids[i] = get_block_id_no_dashes(k)
        for k in all_page_and_child_page_ids:
            if root_page_ids[i] == get_block_id_no_dashes(k):
                root_page_ids[i] = k
    return root_page_ids

def resolve_page_ids_no_dashes(notion_page_id, notion_slugs):
    return  [ get_block_id_no_dashes( ([k for k, v in notion_slugs.items() if v.lower() == page_id.lower()] or [page_id])[0] ) for page_id in notion_page_id]

def get_page_edit_url(page_id, ctx, page_slug, base_url = 'https://notion.so'):
    page_id_no_dashes = get_block_id_no_dashes(page_id)
    return ctx['edit_url'].format(page_id_no_dashes = page_id_no_dashes, page_id = page_id, page_slug = page_slug) if ctx['edit_url'] else os.path.join(base_url, page_id_no_dashes)

def get_page_url(block, ctx, base_url = 'https://www.notion.so'):
    page_id_no_dashes = get_block_id_no_dashes(block)
    return block.get('url', os.path.join(base_url, page_id_no_dashes))

def get_page_url_absolute(block, ctx):
    page_url_relative = get_page_url_relative(block, ctx) if isinstance(block, dict) else block
    page_url_absolute = (os.path.join(ctx['base_url'], page_url_relative.removeprefix('./'))) if ctx['base_url'] else ('file:///' + page_url_relative.removeprefix('file:///'))
    if ctx['base_url_removesuffix']:
        page_url_absolute = page_url_absolute.removesuffix(ctx['base_url_removesuffix'])
    return page_url_absolute

def get_page_url_relative(block, ctx):
    page_id = block.get('link_to_page', {}).get('page_id', '') or (block.get('href', '').removeprefix('/') if block.get('href', '').startswith('/') else '') or get_block_id(block)
    page_id_no_dashes = get_block_id_no_dashes(page_id)
    
    page_slug = get_page_slug(page_id, ctx)
    page_slug_only = get_page_slug(page_id, ctx, only_slug = True)
    is_index_page = page_slug == 'index'
    page_suffix = '/index.html'.removeprefix('/' if is_index_page else '') if ctx['html_link_to_page_index_html'] else ''
    
    if ctx['extract_mode'] == 'flat/index.html':
        return './' + ('' if is_index_page else page_slug) + page_suffix
    
    elif ctx['extract_mode'] == 'flat.html':
        return './' + (page_suffix if is_index_page else page_slug + '.html')

    elif ctx['extract_mode'] == 'flat.md':
        return './' + ('index.md' if is_index_page else page_slug + '.md')
    
    elif ctx['extract_mode'] in ['single.html', 'single.md']:
        page_url_relative = './' + os.path.basename(ctx['output_path']) + ('' if is_index_page else '#' + page_slug)

        if page_slug_only:
            return './' + os.path.basename(ctx['output_path']) + ('' if is_index_page else '#' + page_slug_only)
        
        if (k := sitemap_urlset_index(ctx['sitemap'], page_id)) != -1:
            return ctx['sitemap'][k].get('locrel') or page_url_relative

        return page_url_relative 
        
    return ''

def get_block_url(block):
    payload = block.get(get_block_type(block), {})
    if not isinstance(payload, dict):
        payload = {}
    url = block.get('file', {}).get('url') or block.get('external', {}).get('url') or payload.get('file', {}).get('url') or payload.get('external', {}).get('url') or block.get('url') or block.get('href') or payload.get('url') or '' 
    return url

def get_page_cover_url(block):
    payload = block.get('cover') or {}
    payload_type = payload.get('type', '')
    return payload.get(payload_type, {}).get('url', '')

def get_asset_url(block, ctx):
    url = block if isinstance(block, str) else get_block_url(block)
    asset_dict = ctx['assets'].get(url, {})
    if asset_dict.get('ok'):
        url = asset_dict.get('uri', '')
        if url.startswith('file:///'):
            return url.split('file:///', maxsplit = 1)[-1]
    return url.replace('http://', 'https://')

def normalize_youtube_url(url, embed = False):
    is_youtube = url.startswith('https://youtube.com/') or url.startswith('https://www.youtube.com/') or url.startswith('https://youtu.be/')
    if is_youtube:
        url_youtube_embed = url.replace('/watch?v=', '/embed/').split('&')[0]
        url_youtube_watch = url.replace('/embed/', '/watch?v=').split('&')[0]
        id_youtube = os.path.basename(url_youtube_embed)
        url_youtube = url_youtube_embed if embed else url_youtube_watch
    else:
        url_youtube = url 
        id_youtube = ''
    urlimg_youtube = f'https://img.youtube.com/vi/{id_youtube}/0.jpg' * is_youtube
    return is_youtube, url_youtube, urlimg_youtube

def get_block_id(block):
    return block.get('id', '')

def get_block_id_no_dashes(block):
    return (get_block_id(block) if isinstance(block, dict) else block).replace('-', '')

def get_page_slug(page_id, ctx, use_page_title_for_missing_slug = False, only_slug = False):
    page_id_no_dashes = get_block_id_no_dashes(page_id)
    page_title_slug = slugify(get_page_title(ctx['id2block'].get(page_id), ctx).strip()) or page_id_no_dashes
    return ctx['slugs'].get(page_id) or ctx['slugs'].get(page_id_no_dashes) or (None if only_slug else (page_title_slug if use_page_title_for_missing_slug else page_id_no_dashes))

def get_heading_slug(block, ctx, space = '-', lower = True, prefix = ''):
    s = richtext_2html(block, ctx, rich_text = True, title_mode = True)
    if ctx['extract_mode'] in extract_mode_single:
        page_block = get_page_current(block, ctx)
        page_slug = get_page_slug(get_block_id(page_block), ctx)
        prefix = page_slug + '-'
    
    s = slugify(s.strip(), space = space, lower = lower)
    s = s.strip(space)
    s = re.sub(space + '+', space, s)
    s = prefix + s
    return s

def get_page_parent_paths(notion_pages_flat, ctx):
    page_parent_paths = {}
    for page_id in notion_pages_flat:
        block_id = page_id
        parent_path = []
        header_parent_page_id = page_id
        while True:
            block = ctx['id2block'][block_id]
            if get_block_type(block) in ['page', 'child_page']:
                parent_path.append(dict(type = 'link_to_page', link_to_page = dict(type = 'page_id', page_id = block_id), parent = dict(type = 'page_id', page_id = header_parent_page_id), plain_text = get_page_title(block, ctx, untitled = '')))
            parent_id = block['parent'].get(block['parent'].get('type'))
            if parent_id not in ctx['id2block']:
                break
            block_id = parent_id
        page_parent_paths[page_id] = parent_path
    return page_parent_paths

def get_block_index(ctx):
    id2block = {}
    stack = list(ctx['pages'].values())
    while stack:
        top = stack.pop()
        id2block[get_block_id(top)] = top
        stack.extend(get_block_children(top))
    id2block_no_dashes = {get_block_id_no_dashes(block_id) : block for block_id, block in id2block.items()}
    return id2block | id2block_no_dashes

def get_page_relative_link(page_url_base, page_url_target):
    base_path, base_fragment = page_url_base.split('#') if '#' in page_url_base else (page_url_base, None)
    target_path, target_fragment = page_url_target.split('#') if '#' in page_url_target else (page_url_target, None)

    if base_path == target_path:
        return '#' + (target_fragment or '')

    base_path_splitted = base_path.split('/')
    target_path_splitted = target_path.split('/')

    num_common_parts = ([i for i, (part_base, part_target) in enumerate(zip(base_path_splitted, target_path_splitted)) if part_base != part_target] or [min(len(base_path_splitted), len(target_path_splitted))])[0]
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
            stack.extend(reversed(get_block_children(top)))
    return headings

def get_page_time_published(block, ctx, strftime = '', key = 'unix_seconds_generated'):
    return datetime.datetime.utcfromtimestamp(ctx.get(key, 0)).strftime(strftime) if key in ctx else ''

def get_page_image(block, ctx):
    # {% if page.cover %} {{page.cover}} {% else %} {{site['pages'][site['root_page_id']]['cover']}} {% endif %} 
    return dict(image_url = '', image_height = '', image_width = '', image_alt = '')

get_callout_icon = lambda block: block['callout'].get('icon', {}).get(block['callout'].get('icon', {}).get('type'), '')

def get_page_info(notion_pages_flat, ctx, strftime = '%Y-%m-%dT%H:%M:%S+00:00', translate = {ord('"') : ' ', ord("'") : ' ', ord('#') : ' ', ord('<') : ' ', ord('>') : ' ', ord('#') : ' '}):
    page_info = {}
    for page_id, page in notion_pages_flat.items():
        image_info = get_page_image(page, ctx)
        page_info[page_id] = dict(
            site_name                     = ctx['site_info_name']               or '', # {{ site['pages'][site['root_page_id']]['title'] }}
            site_locale                   = ctx['site_info_locale']             or '',
            site_twitter_card_type        = ctx['site_info_twitter_card_type']  or '',
            site_twitter_atusername       = ctx['site_info_twitter_atusername'] or '',
            site_title                    = ctx['site_info_title']              or get_page_title(page, ctx),
            site_url_absolute             = ctx['site_info_url_absolute']       or get_page_url_absolute(page, ctx),
            site_description              = ctx['site_info_description']        or get_page_description(page, ctx),
            site_published_time_xmlschema = ctx['site_info_time_published']     or get_page_time_published(page, ctx, strftime = strftime, key = 'unix_seconds_generated' if ctx['timestamp_published'] else 'unix_seconds_downloaded'),
            site_image_url                = ctx['site_info_image_url']          or image_info['image_url'],
            site_image_height             = ctx['site_info_image_height']       or image_info['image_height'],
            site_image_width              = ctx['site_info_image_width']        or image_info['image_width'],
            site_image_alt                = ctx['site_info_image_alt']          or image_info['image_alt'],
        )
        page_info[page_id] = {k : v.translate(translate) for k, v in page_info[page_id].items()}
        
    return page_info

def sitemap_urlset_read(path):
    xmlstr = ''
    if path and os.path.exists(path):
        with open(path, 'r') as fp:
            xmlstr = fp.read()
    if not xmlstr.strip():
        return []
    node_doc = xml.dom.minidom.parseString(xmlstr)
    assert node_doc.documentElement.nodeName == 'urlset'
    return [dict({n.nodeName : ''.join(nn.nodeValue for nn in n.childNodes if nn.nodeType == nn.TEXT_NODE) for n in node_url.childNodes if n.nodeType == n.ELEMENT_NODE}, id = node_url.getAttribute('id')) for node_url in node_doc.documentElement.getElementsByTagName('url')]
    
def sitemap_urlset_write(urlset, path):
    # https://sitemaps.org/protocol.html
    node_doc = xml.dom.minidom.Document()
    node_root = node_doc.appendChild(node_doc.createElement('urlset'))
    node_root.setAttribute('xmlns:xsi', 'http://www.w3.org/2001/XMLSchema-instance')
    node_root.setAttribute('xsi:schemaLocation', 'http://www.sitemaps.org/schemas/sitemap/0.9 http://www.sitemaps.org/schemas/sitemap/0.9/sitemap.xsd')
    node_root.setAttribute('xmlns', 'http://www.sitemaps.org/schemas/sitemap/0.9')
    for entry in urlset:
        entry = entry.copy()
        node_url = node_root.appendChild(node_doc.createElement('url'))
        if entry.get('id'):
            node_url.setAttribute('id', entry.pop('id'))
        for field, value in entry.items():
            node_url.appendChild(node_doc.createElement(field)).appendChild(node_doc.createTextNode(str(value)))
    with open(path, 'w') as fp:
        node_doc.writexml(fp, addindent = '  ', newl = '\n')

def sitemap_urlset_index(urlset, id):
    return ([i for i, u in enumerate(urlset) if u['id'] == id or get_block_id_no_dashes(u['id']) == id] or [-1])[0]

def sitemap_urlset_update(urlset, id, loc, locrel = ''):
    k = sitemap_urlset_index(urlset, id)
    if k == -1:
        urlset.append({})
    urlset[k].update(dict(id = id, loc = loc, locrel = locrel))
    return urlset

def pop_and_replace_child_pages_recursively(block, child_pages_by_parent_id = {}, parent_id = None):
    stack = [(block, parent_id)]
    while stack:
        block, parent_id = stack.top()
        block_type = get_block_type(block)
        if block_type in ['page', 'child_page']:
            if get_block_id(block) not in child_pages_by_parent_id:
                child_pages_by_parent_id[get_block_id(block)] = [] 
        for key in ['children', 'blocks']:
            for i in reversed(range(len(block[key]) if block.get(key, []) else 0)):
                subblock = block[key][i]
                subblock_type = get_block_type(subblock)
                if subblock_type == 'child_page':
                    parent_id_type = 'page_id' if block_type in ['page', 'child_page'] else 'block_id'
                    block[key][i] = dict( object = 'block', type = 'link_to_page', has_children = False, link_to_page = dict(type = 'page_id', page_id = get_block_id(subblock)), parent = {'type' : parent_id_type, parent_id_type : get_block_id(block)} )
                    if parent_id not in child_pages_by_parent_id:
                        child_pages_by_parent_id[parent_id] = []
                    child_pages_by_parent_id[parent_id].append(subblock)
                    stack.append((subblock, get_block_id(subblock)))
                else:
                    stack.append((subblock, parent_id))

def slugify(s, space = '_', lower = True):
    # regex from https://github.com/Flet/github-slugger, see https://github.com/github/cmark-gfm/issues/361
    regex_bad_chars = r'[\0-\x1F!-,\.\/:-@\[-\^`\{-\xA9\xAB-\xB4\xB6-\xB9\xBB-\xBF\xD7\xF7\u02C2-\u02C5\u02D2-\u02DF\u02E5-\u02EB\u02ED\u02EF-\u02FF\u0375\u0378\u0379\u037E\u0380-\u0385\u0387\u038B\u038D\u03A2\u03F6\u0482\u0530\u0557\u0558\u055A-\u055F\u0589-\u0590\u05BE\u05C0\u05C3\u05C6\u05C8-\u05CF\u05EB-\u05EE\u05F3-\u060F\u061B-\u061F\u066A-\u066D\u06D4\u06DD\u06DE\u06E9\u06FD\u06FE\u0700-\u070F\u074B\u074C\u07B2-\u07BF\u07F6-\u07F9\u07FB\u07FC\u07FE\u07FF\u082E-\u083F\u085C-\u085F\u086B-\u089F\u08B5\u08C8-\u08D2\u08E2\u0964\u0965\u0970\u0984\u098D\u098E\u0991\u0992\u09A9\u09B1\u09B3-\u09B5\u09BA\u09BB\u09C5\u09C6\u09C9\u09CA\u09CF-\u09D6\u09D8-\u09DB\u09DE\u09E4\u09E5\u09F2-\u09FB\u09FD\u09FF\u0A00\u0A04\u0A0B-\u0A0E\u0A11\u0A12\u0A29\u0A31\u0A34\u0A37\u0A3A\u0A3B\u0A3D\u0A43-\u0A46\u0A49\u0A4A\u0A4E-\u0A50\u0A52-\u0A58\u0A5D\u0A5F-\u0A65\u0A76-\u0A80\u0A84\u0A8E\u0A92\u0AA9\u0AB1\u0AB4\u0ABA\u0ABB\u0AC6\u0ACA\u0ACE\u0ACF\u0AD1-\u0ADF\u0AE4\u0AE5\u0AF0-\u0AF8\u0B00\u0B04\u0B0D\u0B0E\u0B11\u0B12\u0B29\u0B31\u0B34\u0B3A\u0B3B\u0B45\u0B46\u0B49\u0B4A\u0B4E-\u0B54\u0B58-\u0B5B\u0B5E\u0B64\u0B65\u0B70\u0B72-\u0B81\u0B84\u0B8B-\u0B8D\u0B91\u0B96-\u0B98\u0B9B\u0B9D\u0BA0-\u0BA2\u0BA5-\u0BA7\u0BAB-\u0BAD\u0BBA-\u0BBD\u0BC3-\u0BC5\u0BC9\u0BCE\u0BCF\u0BD1-\u0BD6\u0BD8-\u0BE5\u0BF0-\u0BFF\u0C0D\u0C11\u0C29\u0C3A-\u0C3C\u0C45\u0C49\u0C4E-\u0C54\u0C57\u0C5B-\u0C5F\u0C64\u0C65\u0C70-\u0C7F\u0C84\u0C8D\u0C91\u0CA9\u0CB4\u0CBA\u0CBB\u0CC5\u0CC9\u0CCE-\u0CD4\u0CD7-\u0CDD\u0CDF\u0CE4\u0CE5\u0CF0\u0CF3-\u0CFF\u0D0D\u0D11\u0D45\u0D49\u0D4F-\u0D53\u0D58-\u0D5E\u0D64\u0D65\u0D70-\u0D79\u0D80\u0D84\u0D97-\u0D99\u0DB2\u0DBC\u0DBE\u0DBF\u0DC7-\u0DC9\u0DCB-\u0DCE\u0DD5\u0DD7\u0DE0-\u0DE5\u0DF0\u0DF1\u0DF4-\u0E00\u0E3B-\u0E3F\u0E4F\u0E5A-\u0E80\u0E83\u0E85\u0E8B\u0EA4\u0EA6\u0EBE\u0EBF\u0EC5\u0EC7\u0ECE\u0ECF\u0EDA\u0EDB\u0EE0-\u0EFF\u0F01-\u0F17\u0F1A-\u0F1F\u0F2A-\u0F34\u0F36\u0F38\u0F3A-\u0F3D\u0F48\u0F6D-\u0F70\u0F85\u0F98\u0FBD-\u0FC5\u0FC7-\u0FFF\u104A-\u104F\u109E\u109F\u10C6\u10C8-\u10CC\u10CE\u10CF\u10FB\u1249\u124E\u124F\u1257\u1259\u125E\u125F\u1289\u128E\u128F\u12B1\u12B6\u12B7\u12BF\u12C1\u12C6\u12C7\u12D7\u1311\u1316\u1317\u135B\u135C\u1360-\u137F\u1390-\u139F\u13F6\u13F7\u13FE-\u1400\u166D\u166E\u1680\u169B-\u169F\u16EB-\u16ED\u16F9-\u16FF\u170D\u1715-\u171F\u1735-\u173F\u1754-\u175F\u176D\u1771\u1774-\u177F\u17D4-\u17D6\u17D8-\u17DB\u17DE\u17DF\u17EA-\u180A\u180E\u180F\u181A-\u181F\u1879-\u187F\u18AB-\u18AF\u18F6-\u18FF\u191F\u192C-\u192F\u193C-\u1945\u196E\u196F\u1975-\u197F\u19AC-\u19AF\u19CA-\u19CF\u19DA-\u19FF\u1A1C-\u1A1F\u1A5F\u1A7D\u1A7E\u1A8A-\u1A8F\u1A9A-\u1AA6\u1AA8-\u1AAF\u1AC1-\u1AFF\u1B4C-\u1B4F\u1B5A-\u1B6A\u1B74-\u1B7F\u1BF4-\u1BFF\u1C38-\u1C3F\u1C4A-\u1C4C\u1C7E\u1C7F\u1C89-\u1C8F\u1CBB\u1CBC\u1CC0-\u1CCF\u1CD3\u1CFB-\u1CFF\u1DFA\u1F16\u1F17\u1F1E\u1F1F\u1F46\u1F47\u1F4E\u1F4F\u1F58\u1F5A\u1F5C\u1F5E\u1F7E\u1F7F\u1FB5\u1FBD\u1FBF-\u1FC1\u1FC5\u1FCD-\u1FCF\u1FD4\u1FD5\u1FDC-\u1FDF\u1FED-\u1FF1\u1FF5\u1FFD-\u203E\u2041-\u2053\u2055-\u2070\u2072-\u207E\u2080-\u208F\u209D-\u20CF\u20F1-\u2101\u2103-\u2106\u2108\u2109\u2114\u2116-\u2118\u211E-\u2123\u2125\u2127\u2129\u212E\u213A\u213B\u2140-\u2144\u214A-\u214D\u214F-\u215F\u2189-\u24B5\u24EA-\u2BFF\u2C2F\u2C5F\u2CE5-\u2CEA\u2CF4-\u2CFF\u2D26\u2D28-\u2D2C\u2D2E\u2D2F\u2D68-\u2D6E\u2D70-\u2D7E\u2D97-\u2D9F\u2DA7\u2DAF\u2DB7\u2DBF\u2DC7\u2DCF\u2DD7\u2DDF\u2E00-\u2E2E\u2E30-\u3004\u3008-\u3020\u3030\u3036\u3037\u303D-\u3040\u3097\u3098\u309B\u309C\u30A0\u30FB\u3100-\u3104\u3130\u318F-\u319F\u31C0-\u31EF\u3200-\u33FF\u4DC0-\u4DFF\u9FFD-\u9FFF\uA48D-\uA4CF\uA4FE\uA4FF\uA60D-\uA60F\uA62C-\uA63F\uA673\uA67E\uA6F2-\uA716\uA720\uA721\uA789\uA78A\uA7C0\uA7C1\uA7CB-\uA7F4\uA828-\uA82B\uA82D-\uA83F\uA874-\uA87F\uA8C6-\uA8CF\uA8DA-\uA8DF\uA8F8-\uA8FA\uA8FC\uA92E\uA92F\uA954-\uA95F\uA97D-\uA97F\uA9C1-\uA9CE\uA9DA-\uA9DF\uA9FF\uAA37-\uAA3F\uAA4E\uAA4F\uAA5A-\uAA5F\uAA77-\uAA79\uAAC3-\uAADA\uAADE\uAADF\uAAF0\uAAF1\uAAF7-\uAB00\uAB07\uAB08\uAB0F\uAB10\uAB17-\uAB1F\uAB27\uAB2F\uAB5B\uAB6A-\uAB6F\uABEB\uABEE\uABEF\uABFA-\uABFF\uD7A4-\uD7AF\uD7C7-\uD7CA\uD7FC-\uD7FF\uE000-\uF8FF\uFA6E\uFA6F\uFADA-\uFAFF\uFB07-\uFB12\uFB18-\uFB1C\uFB29\uFB37\uFB3D\uFB3F\uFB42\uFB45\uFBB2-\uFBD2\uFD3E-\uFD4F\uFD90\uFD91\uFDC8-\uFDEF\uFDFC-\uFDFF\uFE10-\uFE1F\uFE30-\uFE32\uFE35-\uFE4C\uFE50-\uFE6F\uFE75\uFEFD-\uFF0F\uFF1A-\uFF20\uFF3B-\uFF3E\uFF40\uFF5B-\uFF65\uFFBF-\uFFC1\uFFC8\uFFC9\uFFD0\uFFD1\uFFD8\uFFD9\uFFDD-\uFFFF]|\uD800[\uDC0C\uDC27\uDC3B\uDC3E\uDC4E\uDC4F\uDC5E-\uDC7F\uDCFB-\uDD3F\uDD75-\uDDFC\uDDFE-\uDE7F\uDE9D-\uDE9F\uDED1-\uDEDF\uDEE1-\uDEFF\uDF20-\uDF2C\uDF4B-\uDF4F\uDF7B-\uDF7F\uDF9E\uDF9F\uDFC4-\uDFC7\uDFD0\uDFD6-\uDFFF]|\uD801[\uDC9E\uDC9F\uDCAA-\uDCAF\uDCD4-\uDCD7\uDCFC-\uDCFF\uDD28-\uDD2F\uDD64-\uDDFF\uDF37-\uDF3F\uDF56-\uDF5F\uDF68-\uDFFF]|\uD802[\uDC06\uDC07\uDC09\uDC36\uDC39-\uDC3B\uDC3D\uDC3E\uDC56-\uDC5F\uDC77-\uDC7F\uDC9F-\uDCDF\uDCF3\uDCF6-\uDCFF\uDD16-\uDD1F\uDD3A-\uDD7F\uDDB8-\uDDBD\uDDC0-\uDDFF\uDE04\uDE07-\uDE0B\uDE14\uDE18\uDE36\uDE37\uDE3B-\uDE3E\uDE40-\uDE5F\uDE7D-\uDE7F\uDE9D-\uDEBF\uDEC8\uDEE7-\uDEFF\uDF36-\uDF3F\uDF56-\uDF5F\uDF73-\uDF7F\uDF92-\uDFFF]|\uD803[\uDC49-\uDC7F\uDCB3-\uDCBF\uDCF3-\uDCFF\uDD28-\uDD2F\uDD3A-\uDE7F\uDEAA\uDEAD-\uDEAF\uDEB2-\uDEFF\uDF1D-\uDF26\uDF28-\uDF2F\uDF51-\uDFAF\uDFC5-\uDFDF\uDFF7-\uDFFF]|\uD804[\uDC47-\uDC65\uDC70-\uDC7E\uDCBB-\uDCCF\uDCE9-\uDCEF\uDCFA-\uDCFF\uDD35\uDD40-\uDD43\uDD48-\uDD4F\uDD74\uDD75\uDD77-\uDD7F\uDDC5-\uDDC8\uDDCD\uDDDB\uDDDD-\uDDFF\uDE12\uDE38-\uDE3D\uDE3F-\uDE7F\uDE87\uDE89\uDE8E\uDE9E\uDEA9-\uDEAF\uDEEB-\uDEEF\uDEFA-\uDEFF\uDF04\uDF0D\uDF0E\uDF11\uDF12\uDF29\uDF31\uDF34\uDF3A\uDF45\uDF46\uDF49\uDF4A\uDF4E\uDF4F\uDF51-\uDF56\uDF58-\uDF5C\uDF64\uDF65\uDF6D-\uDF6F\uDF75-\uDFFF]|\uD805[\uDC4B-\uDC4F\uDC5A-\uDC5D\uDC62-\uDC7F\uDCC6\uDCC8-\uDCCF\uDCDA-\uDD7F\uDDB6\uDDB7\uDDC1-\uDDD7\uDDDE-\uDDFF\uDE41-\uDE43\uDE45-\uDE4F\uDE5A-\uDE7F\uDEB9-\uDEBF\uDECA-\uDEFF\uDF1B\uDF1C\uDF2C-\uDF2F\uDF3A-\uDFFF]|\uD806[\uDC3B-\uDC9F\uDCEA-\uDCFE\uDD07\uDD08\uDD0A\uDD0B\uDD14\uDD17\uDD36\uDD39\uDD3A\uDD44-\uDD4F\uDD5A-\uDD9F\uDDA8\uDDA9\uDDD8\uDDD9\uDDE2\uDDE5-\uDDFF\uDE3F-\uDE46\uDE48-\uDE4F\uDE9A-\uDE9C\uDE9E-\uDEBF\uDEF9-\uDFFF]|\uD807[\uDC09\uDC37\uDC41-\uDC4F\uDC5A-\uDC71\uDC90\uDC91\uDCA8\uDCB7-\uDCFF\uDD07\uDD0A\uDD37-\uDD39\uDD3B\uDD3E\uDD48-\uDD4F\uDD5A-\uDD5F\uDD66\uDD69\uDD8F\uDD92\uDD99-\uDD9F\uDDAA-\uDEDF\uDEF7-\uDFAF\uDFB1-\uDFFF]|\uD808[\uDF9A-\uDFFF]|\uD809[\uDC6F-\uDC7F\uDD44-\uDFFF]|[\uD80A\uD80B\uD80E-\uD810\uD812-\uD819\uD824-\uD82B\uD82D\uD82E\uD830-\uD833\uD837\uD839\uD83D\uD83F\uD87B-\uD87D\uD87F\uD885-\uDB3F\uDB41-\uDBFF][\uDC00-\uDFFF]|\uD80D[\uDC2F-\uDFFF]|\uD811[\uDE47-\uDFFF]|\uD81A[\uDE39-\uDE3F\uDE5F\uDE6A-\uDECF\uDEEE\uDEEF\uDEF5-\uDEFF\uDF37-\uDF3F\uDF44-\uDF4F\uDF5A-\uDF62\uDF78-\uDF7C\uDF90-\uDFFF]|\uD81B[\uDC00-\uDE3F\uDE80-\uDEFF\uDF4B-\uDF4E\uDF88-\uDF8E\uDFA0-\uDFDF\uDFE2\uDFE5-\uDFEF\uDFF2-\uDFFF]|\uD821[\uDFF8-\uDFFF]|\uD823[\uDCD6-\uDCFF\uDD09-\uDFFF]|\uD82C[\uDD1F-\uDD4F\uDD53-\uDD63\uDD68-\uDD6F\uDEFC-\uDFFF]|\uD82F[\uDC6B-\uDC6F\uDC7D-\uDC7F\uDC89-\uDC8F\uDC9A-\uDC9C\uDC9F-\uDFFF]|\uD834[\uDC00-\uDD64\uDD6A-\uDD6C\uDD73-\uDD7A\uDD83\uDD84\uDD8C-\uDDA9\uDDAE-\uDE41\uDE45-\uDFFF]|\uD835[\uDC55\uDC9D\uDCA0\uDCA1\uDCA3\uDCA4\uDCA7\uDCA8\uDCAD\uDCBA\uDCBC\uDCC4\uDD06\uDD0B\uDD0C\uDD15\uDD1D\uDD3A\uDD3F\uDD45\uDD47-\uDD49\uDD51\uDEA6\uDEA7\uDEC1\uDEDB\uDEFB\uDF15\uDF35\uDF4F\uDF6F\uDF89\uDFA9\uDFC3\uDFCC\uDFCD]|\uD836[\uDC00-\uDDFF\uDE37-\uDE3A\uDE6D-\uDE74\uDE76-\uDE83\uDE85-\uDE9A\uDEA0\uDEB0-\uDFFF]|\uD838[\uDC07\uDC19\uDC1A\uDC22\uDC25\uDC2B-\uDCFF\uDD2D-\uDD2F\uDD3E\uDD3F\uDD4A-\uDD4D\uDD4F-\uDEBF\uDEFA-\uDFFF]|\uD83A[\uDCC5-\uDCCF\uDCD7-\uDCFF\uDD4C-\uDD4F\uDD5A-\uDFFF]|\uD83B[\uDC00-\uDDFF\uDE04\uDE20\uDE23\uDE25\uDE26\uDE28\uDE33\uDE38\uDE3A\uDE3C-\uDE41\uDE43-\uDE46\uDE48\uDE4A\uDE4C\uDE50\uDE53\uDE55\uDE56\uDE58\uDE5A\uDE5C\uDE5E\uDE60\uDE63\uDE65\uDE66\uDE6B\uDE73\uDE78\uDE7D\uDE7F\uDE8A\uDE9C-\uDEA0\uDEA4\uDEAA\uDEBC-\uDFFF]|\uD83C[\uDC00-\uDD2F\uDD4A-\uDD4F\uDD6A-\uDD6F\uDD8A-\uDFFF]|\uD83E[\uDC00-\uDFEF\uDFFA-\uDFFF]|\uD869[\uDEDE-\uDEFF]|\uD86D[\uDF35-\uDF3F]|\uD86E[\uDC1E\uDC1F]|\uD873[\uDEA2-\uDEAF]|\uD87A[\uDFE1-\uDFFF]|\uD87E[\uDE1E-\uDFFF]|\uD884[\uDF4B-\uDFFF]|\uDB40[\uDC00-\uDCFF\uDDF0-\uDFFF]'
    
    s = unicodedata.normalize('NFKC', s)
    s = s.lower() if lower else s
    s = re.sub(regex_bad_chars, '', s)
    #s = re.sub(r'[^-_\w]', space, s)
    s = re.sub(r'\s', space, s)
    return s

def block2(block, ctx = {}, block2render = {}, block2render_with_begin_end = {}, begin = False, end = False, newline = '', **kwargs):
    # https://developers.notion.com/reference/block
    block_type = get_block_type(block)
    if block_type in block2render_with_begin_end:
        return block2render_with_begin_end[block_type](block, ctx, begin = begin, end = end, **kwargs) + newline
    if block_type not in block2render or block_type == 'unsupported':
        block_type = 'unsupported'
        parent_block = get_page_current(block, ctx)
        print('UNSUPPORTED block: block_type=[{block_type}] block_id=[{block_id}] block_type_parent=[{block_type_parent}] block_id_parent=[{block_id_parent}] title_parent=[{title_parent}]'.format(block_type = get_block_type(block), block_id = get_block_id(block), block_type_parent = get_block_type(parent_block), block_id_parent = get_block_id(parent_block), title_parent = get_page_title(parent_block, ctx)), file = ctx['log_unsupported_blocks_file'])
    return block2render[block_type](block, ctx, **kwargs) + newline

##############################

def download_asset_if_not_exists(url, asset_path = '', datauri = False):
    asset_path = asset_path or os.path.basename(asset_path)
    asset_path_file_protocol = 'file:///./' + os.path.sep.join(asset_path.split(os.path.sep)[-2:])
    ext = os.path.splitext(asset_path.lower())[-1]
    mime = mimedb.get(ext, mimedefault)
    if not datauri and os.path.exists(asset_path):
        return asset_path_file_protocol
    req = urllib.request.Request(url, headers = headers)
    with urllib.request.urlopen(req) as f:
        file_bytes = f.read()
    if datauri:
        return f'data:{mime};base64,' + base64.b64encode(file_bytes).decode()
    with open(asset_path, 'wb') as f:
        f.write(file_bytes)
    return asset_path_file_protocol

def discover_assets(blocks, assets_urls, exclude_datauri = True, download_assets_types = []):
    for block in blocks:
        #print('discover_assets', get_block_type(block), get_block_id(block))
        discover_assets(get_block_children(block), assets_urls, exclude_datauri = exclude_datauri, download_assets_types = download_assets_types)
        block_type = get_block_type(block)
        payload = block.get(block_type) or {}
        payload_type = payload.get('type', '')
        
        assets_types_urls = [
            ('cover', get_block_url(block.get('cover') or {})),
            ('icon', get_block_url(block.get('icon') or {})),
            (block_type + '-' + payload_type, get_block_url(block)),
        ]
        #print(assets_types_urls)

        assets_urls.extend( asset_url for asset_type, asset_url in assets_types_urls if asset_url and asset_type in download_assets_types and (exclude_datauri is False or not is_url_datauri(asset_url)) )
    return assets_urls

def download_and_extract_assets(assets_urls, ctx, assets_dir = None, notion_assets = {}, extdefault = '.bin'):
    print('\n'.join('URL ' + url for url in assets_urls), file = ctx['log_urls_file'])
    extract_assets_and_assets_dir = bool(ctx['extract_assets'] and ctx['assets_dir'])
    if extract_assets_and_assets_dir:
        os.makedirs(ctx['assets_dir'], exist_ok = True)
        print(assets_dir)
    
    assets = {}

    for url in set(assets_urls) & (notion_assets.keys() or set(assets_urls)):
        asset = notion_assets.get(url, {})
        asset_uri = asset.get('uri', '')
        asset_basename = asset.get('basename', '')
        asset_basename_hashed = asset.get('basename_hashed', '')
        asset_ext = os.path.splitext(asset.get('basename', ''))[-1]
        ok = bool(asset.get('ok')) if asset.get('ok') is not None else True
        
        if is_url_datauri(asset_uri):
            urlopen_url, path = url, url
            basename, datauri = (asset_basename or 'datauri'), asset_uri
            ext = asset_ext
            basename_hashed = asset_basename_hashed

        elif is_url_datauri(url):
            urlopen_url, path = url, url
            basename, datauri = 'datauri', url
            ext = ([k for k, v in mimedb.items() if datauri.startswith('data:' + v)] or [extdefault])[0]
            basename_hashed = basename + '.' + hash_url(path) + ext

        else:
            urlopen_url, path = sanitize_url_and_strip_querystring(url)
            basename, datauri = os.path.basename(path), None
            ext = os.path.splitext(path.lower())[-1]
            basename_hashed = basename + '.' + hash_url(path) + ext

        asset_path = os.path.join(ctx['assets_dir'] or '', basename_hashed)

        if datauri is None:
            try:
                if not extract_assets_and_assets_dir or not os.path.exists(asset_path):
                    print('download_asset_if_not_exists', asset_path, '<-', urlopen_url)
                
                datauri = download_asset_if_not_exists(urlopen_url, asset_path, datauri = not extract_assets_and_assets_dir)
            except Exception as exc:
                print(f'ERROR: cannot download [{basename}] from link {url}, unparsed {urlopen_url}', exc)
                datauri = 'data:text/plain;base64,' + base64.b64encode(str(exc).encode()).decode()
                ok = False
                if os.path.exists(asset_path):
                    os.remove(asset_path)

        elif is_url_datauri(datauri) and extract_assets_and_assets_dir:
            if not os.path.exists(asset_path):
                with open(asset_path, 'wb') as f:
                    f.write(base64.b64decode(datauri.split('base64,', maxsplit = 1)[-1].encode()))
                print('download_asset_if_not_exists', asset_path)
            datauri = 'file:///./' + os.path.sep.join(asset_path.split(os.path.sep)[-2:])

        assets[url] = dict(basename = basename, basename_hashed = basename_hashed, uri = datauri, ok = ok)

    return assets

##############################

def extractall(output_path, ctx, theme, page_ids = [], notion_pages = {}, notion_pages_flat = {},  snippets = {}):
    ext = os.path.splitext(ctx['extract_mode'])[-1]
    notion_assets = ctx.get('assets', {})
    index_html = ctx['extract_mode'] in extract_mode_index_html
    
    if ctx['extract_mode'] in extract_mode_single:
        assets_urls = discover_assets(ctx['pages'].values(), [], download_assets_types = ctx['download_assets_types'])
        notion_assets_for_blocks = download_and_extract_assets(assets_urls, ctx, assets_dir = ctx['assets_dir'], notion_assets = notion_assets)
        meta_tags = ctx['page_info'][page_ids[0]]
        if ext == '.md':
           notionstr = theme.sitepages_2markdown(page_ids, ctx = dict(ctx, assets = notion_assets_for_blocks, meta_tags = meta_tags), notion_pages = notion_pages_flat, render_block = block_2markdown, snippets = snippets)
        if ext == '.html':
           notionstr = theme.sitepages_2html(page_ids, ctx = dict(ctx, assets = notion_assets_for_blocks, meta_tags = meta_tags), notion_pages = notion_pages_flat, render_block = block_2html, snippets = snippets)
        if ext == '.json':
            notionjson = dict(
                pages = {page_id : page for page_id, page in (notion_pages if ctx['extract_mode'] == 'single.json' else notion_pages_flat).items() if page_id in page_ids}, 
                assets = notion_assets_for_blocks,
                unix_seconds_downloaded = ctx.get('unix_seconds_downloaded', 0),
            )
            notionstr = json.dumps(notionjson, ensure_ascii = False, indent = 4)
        
        if ctx['sitemap_xml']:
            for page_id in page_ids:
                page_block = notion_pages_flat[page_id]
                page_url_relative = get_page_url_relative(page_block, ctx)
                page_url_absolute = get_page_url_absolute(page_url_relative, ctx)
                sitemap_urlset_update(ctx['sitemap'], page_id, loc = page_url_absolute, locrel = page_url_relative)
            sitemap_urlset_write(ctx['sitemap'], ctx['sitemap_xml'])
            print(ctx['sitemap_xml'])
        
        with open(output_path, 'w', encoding = 'utf-8') as f:
            f.write(notionstr)
        return print(output_path)

    assert ctx['extract_mode'] in extract_mode_flat

    if page_ids and ctx['sitemap_xml']:
        print(ctx['sitemap_xml'])
        
    os.makedirs(output_path, exist_ok = True)
    for page_id in page_ids:
        page_block = notion_pages_flat[page_id]
        page_url_relative = get_page_url_relative(page_block, ctx)
        page_url_absolute = get_page_url_absolute(page_url_relative, ctx)
        if ctx['sitemap_xml']:
            sitemap_urlset_update(ctx['sitemap'], page_id, loc = page_url_absolute, locrel = page_url_relative)
            sitemap_urlset_write(ctx['sitemap'], ctx['sitemap_xml'])

        page_slug = get_page_slug(page_id, ctx, use_page_title_for_missing_slug = ctx['use_page_title_for_missing_slug'])
        page_nested_dir = os.path.join(output_path, page_slug)
        page_dir = page_nested_dir if (index_html and page_slug != 'index') else output_path
        
        os.makedirs(page_dir, exist_ok = True)
            
        assets_urls = discover_assets([page_block], [], download_assets_types = ctx['download_assets_types'])
        notion_assets_for_block = download_and_extract_assets(assets_urls, ctx, assets_dir = ctx['assets_dir'] or os.path.join(page_dir, page_slug + '_files'), notion_assets = notion_assets)
        meta_tags = ctx['page_info'][page_id]

        dump_path = os.path.join(page_dir, 'index.html' if index_html else page_slug + ext)
    
        if ext == '.html':
            notionstr = theme.sitepages_2html([page_id], ctx = dict(ctx, assets = notion_assets_for_block, meta_tags = meta_tags), notion_pages = notion_pages_flat, render_block = block_2html, snippets = snippets)

        if ext == '.md':
            notionstr = theme.sitepages_2markdown([page_id], ctx = dict(ctx, assets = notion_assets_for_block, meta_tags = meta_tags), notion_pages = notion_pages_flat, render_block = block_2markdown, snippets = snippets)

        if ext == '.json':
            notionjson = dict(
                pages = {page_id : page_block}, 
                assets = notion_assets_for_block, 
                unix_seconds_downloaded = ctx.get('unix_seconds_downloaded', 0),
            )
            notionstr = json.dumps(notionjson, ensure_ascii = False, indent = 4)

        with open(dump_path, 'w', encoding = 'utf-8') as f:
            f.write(notionstr)
        print(dump_path)

def read_and_write_config(config_json, config):
    config_args = config
    config = json.load(open(config_json)) if config_json and os.path.exists(config_json) and os.path.isfile(config_json) else {}
    for k, v in config_args.items():
        if (k not in config) or v:
            config[k] = v
        elif k in config and v and isinstance(v, dict):
            config[k].update(v)

    if config_json and not os.path.exists(config_json):
        os.makedirs(os.path.dirname(config_json) or '.', exist_ok = True)
        with open(config_json, 'w') as f:
            json.dump(config, f, ensure_ascii = False, indent = 4, sort_keys = True)
    return config

def read_snippets(snippets_dir, snippets_extra_paths = {}):
    snippets = {}
    if snippets_dir and os.path.exists(snippets_dir):
        for basename in os.listdir(snippets_dir):
            k = basename.replace('.', '_')
            with open(os.path.join(snippets_dir, basename)) as f:
                snippets[k] = f.read()
    for k, v in snippets_extra_paths.items():
        if v and os.path.exists(v):
            with open(v) as f:
                snippets[k] = f.read()
        elif v and snippets_dir and os.path.exists(snippets_dir) and os.path.exists(os.path.join(snippets_dir, v)):
            with open(os.path.join(snippets_dir, v)) as f:
                snippets[k] = f.read()
    return snippets

def notion2static(
    config_json,
    input_json,
    output_path,
    notion_token,
    notion_page_id,
    extract_assets,
    download_assets_types,

    timestamp_published,
    
    slugs,
    extract_mode,
    theme_py,
    sitemap_xml,
    snippets_dir,
    assets_dir,
    base_url,
    base_url_removesuffix,
    edit_url,
    use_page_title_for_missing_slug,
    log_unsupported_blocks,
    log_urls,

    markdown_toc_page,
    markdown_toggle,
    markdown_frontmatter,
    html_details_open,
    html_columnlist_disable,
    html_link_to_page_index_html,
    html_privacynotice,
    html_googleanalytics,
    html_equation_katex,
    html_code_highlightjs,
    bodyheader_html,
    bodyfooter_html,
    articleheader_html,
    articlefooter_html,

    site_info_name,
    site_info_locale,
    site_info_title,
    site_info_description,
    site_info_url_absolute,
    site_info_time_published,
    site_info_twitter_card_type,
    site_info_twitter_atusername,
    site_info_image_url,
    site_info_image_height,
    site_info_image_width,
    site_info_image_alt,
    site_info_author_name,
    site_info_author_email,
    site_info_github
):
    slugs = {k.lower().strip() : v.lower().strip() for s in slugs for kv in s.split(',') for k, v in [kv.split('=')]}
    notion_page_id = [page_id.lower().strip() for comma_separated_page_ids in notion_page_id for page_id in comma_separated_page_ids.split(',')]
    config = read_and_write_config(args.config_json, locals())
    sitemap = sitemap_urlset_read(sitemap_xml) if sitemap_xml else []
    notion_slugs = config.get('slugs', {})
    notion_page_id = config.get('notion_page_id', [])

    notionjson = json.load(open(input_json)) if input_json else notionapi_retrieve_page_list(notion_token, resolve_page_ids_no_dashes(notion_page_id, notion_slugs)) if notion_page_id else {}
    
    notion_pages = notionjson.get('pages', {})
    notion_pages = { page_id : page for page_id, page in notion_pages.items() if page['parent']['type'] in ['workspace', 'page_id'] and get_block_type(page) in ['page', 'child_page'] }

    notion_pages_flat = copy.deepcopy(notion_pages)
    child_pages_by_parent_id = {}
    for page_id, page in notion_pages_flat.items():
        pop_and_replace_child_pages_recursively(page, child_pages_by_parent_id = child_pages_by_parent_id, parent_id = page_id)
    child_pages_by_id = {get_block_id(child_page) : child_page for pages in child_pages_by_parent_id.values() for child_page in pages}
    notion_pages_flat |= child_pages_by_id

    root_page_ids = resolve_page_ids(notion_page_id or list(notion_pages.keys()), notion_pages_flat.keys(), notion_slugs)
    page_ids = root_page_ids + [get_block_id(child_page) for page_id in root_page_ids for child_page in child_pages_by_parent_id.get(page_id, []) if get_block_id(child_page) not in root_page_ids]
    assert notion_pages_flat and root_page_ids and all(page_id in notion_pages_flat for page_id in root_page_ids), f'{notion_pages_flat.keys()=}, {root_page_ids=}'
    
    ext = os.path.splitext(extract_mode)[-1]
    ctx = config.copy()
    ctx['output_path'] = ctx['output_path'] or ('_'.join(notion_page_id) if ctx['extract_mode'] not in extract_mode_single else input_json.removesuffix('.json')) + ext
    ctx['assets_dir'] = ctx['assets_dir'] if ctx['assets_dir'] else os.path.join(ctx['output_path'], 'assets') if ctx['extract_mode'] in extract_mode_flat[:-1] else os.path.join(os.path.dirname(ctx['output_path']), 'assets') if ctx['extract_mode'] in extract_mode_single else None
    ctx['log_unsupported_blocks_file'] = open(log_unsupported_blocks if log_unsupported_blocks else os.devnull , 'w')
    ctx['log_urls_file'] = open(log_urls if log_urls else os.devnull , 'w')
    ctx['sitemap'] = sitemap
    ctx['unix_seconds_downloaded'] = notionjson.get('unix_seconds_downloaded', 0)
    ctx['unix_seconds_generated'] = int(time.time())
    ctx['pages'] = notion_pages_flat
    ctx['page_ids'] = page_ids
    ctx['child_pages_by_parent_id'] = child_pages_by_parent_id
    ctx['id2block'] = get_block_index(ctx)
    ctx['page_parent_paths'] = get_page_parent_paths(notion_pages_flat, ctx)
    ctx['page_info'] = get_page_info(ctx['pages'], ctx)
    ctx['assets'] = notionjson.get('assets', {}) or download_and_extract_assets(discover_assets(notion_pages.values(), [], exclude_datauri = False, download_assets_types = ctx['download_assets_types']), ctx, notion_assets = {})
    
    try:
        theme = importlib.import_module(os.path.splitext(theme_py)[0])
    except:
        assert os.path.exists(theme_py) and os.path.isfile(theme_py)
        sys.path.append(os.path.dirname(theme_py))
        theme = importlib.import_module(os.path.splitext(theme_py)[0])

    snippets = read_snippets(snippets_dir, snippets_extra_paths = dict(
        bodyheader_html    = bodyheader_html   ,
        bodyfooter_html    = bodyfooter_html   ,
        articleheader_html = articleheader_html,
        articlefooter_html = articlefooter_html,
    ))
    snippets_read = list(snippets.keys())

    extractall(
        ctx['output_path'],
        ctx = ctx, 
        theme = theme,
        page_ids = page_ids, 
        notion_pages = notion_pages,
        notion_pages_flat = notion_pages_flat, 
        snippets = snippets
    )
    

##############################

html_block2render = dict(
    bookmark = bookmark_2html,
    breadcrumb = breadcrumb_2html,
    bulleted_list_item = bulleted_list_item_2html,
    callout = callout_2html,
    child_database = child_database_2html,
    child_page = child_page_2html,
    code = code_2html,
    column_list = column_list_2html, column = column_2html,
    divider = divider_2html,
    embed = embed_2html,
    equation = equation_2html,
    file = file_2html,
    heading_1 = heading_1_2html, heading_2 = heading_2_2html, heading_3 = heading_3_2html,
    image = image_2html,
    link_preview = link_preview_2html,
    mention = mention_2html,
    numbered_list_item = numbered_list_item_2html,
    paragraph = paragraph_2html,
    pdf = pdf_2html,
    quote = quote_2html,
    synced_block = synced_block_2html,
    table = table_2html,
    table_of_contents = table_of_contents_2html,
    template = template_2html,
    to_do = to_do_2html,
    toggle = toggle_2html,
    video = video_2html,

    link_to_page = link_to_page_2html,
    page = page_2html,
    unsupported = unsupported_2html,
)
html_block2render_with_begin_end = dict(
    numbered_list_item = numbered_list_item_2html,
    bulleted_list_item = bulleted_list_item_2html,
    to_do = to_do_2html
)

markdown_block2render = dict(
    bookmark = bookmark_2markdown, 
    breadcrumb = breadcrumb_2markdown,
    bulleted_list_item = bulleted_list_item_2markdown, 
    callout = callout_2markdown, 
    child_database = child_database_2markdown,
    child_page = child_page_2markdown,
    code = code_2markdown, 
    column_list = column_list_2markdown, column = column_2markdown, 
    divider = divider_2markdown, 
    embed = embed_2markdown, 
    equation = equation_2markdown, 
    file = file_2markdown, 
    heading_1 = heading_1_2markdown, heading_2 = heading_2_2markdown, heading_3 = heading_3_2markdown, 
    image = image_2markdown,
    link_preview = link_preview_2markdown,
    mention = mention_2markdown,
    numbered_list_item = numbered_list_item_2markdown, 
    paragraph = paragraph_2markdown, 
    pdf = pdf_2markdown, 
    quote = quote_2markdown, 
    synced_block = synced_block_2markdown,
    table = table_2markdown, 
    table_of_contents = table_of_contents_2markdown, 
    template = template_2markdown,
    to_do = to_do_2markdown, 
    toggle = toggle_2markdown, 
    video = video_2markdown, 
    
    link_to_page = link_to_page_2markdown, 
    page = page_2markdown,
    unsupported = unsupported_2markdown,
)
markdown_block2render_with_begin_end = dict(
    numbered_list_item = numbered_list_item_2markdown,
    bulleted_list_item = bulleted_list_item_2markdown,
    to_do = to_do_2markdown
)

block_2html = lambda block, ctx = {}, begin = False, end = False, **kwargs: block2(block, ctx, block2render = html_block2render, block2render_with_begin_end = html_block2render_with_begin_end, begin = begin, end = end, **kwargs)
block_2markdown = lambda block, ctx = {}, begin = False, end = False, **kwargs: block2(block, ctx, block2render = markdown_block2render, block2render_with_begin_end = markdown_block2render_with_begin_end, begin = begin, end = end, **kwargs)

##############################

extract_mode_single = ['single.html', 'single.md', 'single.json']
extract_mode_flat = ['flat.html', 'flat.md', 'flat.json', 'flat/index.html']
extract_mode_json = ['flat.json', 'single.json']
extract_mode_index_html = ['flat/index.html']

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--config-json', default = '_config.json')
    parser.add_argument('--input-json', '-i')
    parser.add_argument('--output-path', '-o')
    parser.add_argument('--notion-token', default = os.getenv('NOTION_TOKEN', ''))
    parser.add_argument('--notion-page-id', nargs = '*', default = [])
    parser.add_argument('--theme-py', default = 'minima.py')
    parser.add_argument('--extract-mode', default = 'single.html', choices = extract_mode_single + extract_mode_flat)
    parser.add_argument('--snippets-dir')
    parser.add_argument('--assets-dir')
    parser.add_argument('--sitemap-xml')
    parser.add_argument('--base-url-removesuffix')
    parser.add_argument('--base-url')
    parser.add_argument('--edit-url')
    parser.add_argument('--log-unsupported-blocks')
    parser.add_argument('--log-urls')
    parser.add_argument('--download-assets-types', nargs = '*', choices = ['icon', 'cover', 'image-external', 'image-file', 'video-external', 'video-file', 'pdf-external', 'pdf-file', 'file-external', 'file-file'], default = ['cover', 'icon', 'image-file', 'image-external', 'pdf-file', 'file-file', 'video-file'])
    parser.add_argument('--extract-assets', action = 'store_true')
    parser.add_argument('--slugs', nargs = '*', default = [])
    parser.add_argument('--use-page-title-for-missing-slug', action = 'store_true')
    parser.add_argument('--timestamp-published', action = 'store_true')

    parser.add_argument('--markdown-toc-page')
    parser.add_argument('--markdown-toggle', action = 'store_true')
    parser.add_argument('--markdown-frontmatter', action = 'store_true')
    parser.add_argument('--html-details-open', action = 'store_true')
    parser.add_argument('--html-columnlist-disable', action = 'store_true')
    parser.add_argument('--html-link-to-page-index-html', action = 'store_true')
    parser.add_argument('--html-privacynotice')
    parser.add_argument('--html-googleanalytics')
    parser.add_argument('--html-equation-katex', action = 'store_true')
    parser.add_argument('--html-code-highlightjs', action = 'store_true')

    parser.add_argument('--bodyheader-html')
    parser.add_argument('--bodyfooter-html')
    parser.add_argument('--articleheader-html')
    parser.add_argument('--articlefooter-html')

    parser.add_argument('--site-info-name', default = 'notionexportstatic')
    parser.add_argument('--site-info-locale', default = 'en_EN')
    parser.add_argument('--site-info-title')
    parser.add_argument('--site-info-description')
    parser.add_argument('--site-info-url-absolute')
    parser.add_argument('--site-info-time-published')
    parser.add_argument('--site-info-twitter-card-type')
    parser.add_argument('--site-info-twitter-atusername')
    parser.add_argument('--site-info-image-url')
    parser.add_argument('--site-info-image-height')
    parser.add_argument('--site-info-image-width')
    parser.add_argument('--site-info-image-alt')
    parser.add_argument('--site-info-author-name', default = '')
    parser.add_argument('--site-info-author-email', default = '')
    parser.add_argument('--site-info-github', default = '')

    args = parser.parse_args()
    print(args)

    if args.extract_mode in extract_mode_json or args.notion_page_id or (args.input_json and os.path.exists(args.input_json) and os.path.isfile(args.input_json)):
        notion2static(**vars(args))

    elif args.input_json and os.path.exists(args.input_json) and os.path.isdir(args.input_json):
        file_paths_recursive_json = [os.path.join(dirpath, basename) for dirpath, dirnames, filenames in os.walk(args.input_json) for basename in filenames if basename.endswith('.json')]
        for file_path in file_paths_recursive_json:
            try:
                with open(file_path) as f:
                    j = json.load(f)
                if 'pages' not in j:
                    continue
                print(file_path)
                notion2static(**dict(vars(args), input_json = file_path))
            except:
                continue
