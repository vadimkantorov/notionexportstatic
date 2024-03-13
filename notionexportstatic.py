# TODO: refactor _config.json / to allow not just slug but a full path | use parent path to determine link
# TODO: embedded pdf in markdown and html
# TODO: page_icon with path, not just emoji

# https://docs.super.so/super-css-classes
# Name	HTML Element	CSS Class	Category
# Link <a> .notion-link
# Page <div> .notion-page
# Page Icon <div> .notion-page__icon
# Page Title <div> .notion-page__title
# Bullet List <ul> .notion-bulleted-list
# Numbered List <ol> .notion-numbered-list
# List Item <li> .notion-list-item
# To-do <div> .notion-to-do
# To-do Content Wrapper <div> .notion-to-do__content
# To-do Checkbox Wrapper <div> .notion-to-do__icon
# To-do Checkbox (Unchecked) <div> .notion-checkbox
# To-do Checkbox (Checked) <div> .notion-checkbox.checked
# To-do Title (Unchecked) <div> .notion-to-do__title
# To-do Title (Checked) <div> .notion-to-do__title.checked
# To-do Check Icon (Unchecked) <svg> .notion-checkbox>svg
# To-do Check Icon (Checked) <svg> .notion-checkbox.checked>svg
# Toggle <details> .notion-toggle
# Toggle Title (Summary) <summary> .notion-toggle__summary
# Toggle Icon (pseudo element) .notion-toggle__summary::before
# Toggle Content <div> .notion-toggle__content
# Quote <blockquote> .notion-quote
# Callout <div> .notion-callout
# Callout Icon <div> .notion-callout__icon
# Callout Content <p> .notion-callout__content
# Callout Border <div> .notion-callout.border
# Code Content Wrapper <pre> .notion-code>pre
# Code Content <code> .notion-code code
# Divider <div> .notion-divider
# Table of Contents <ul> .notion-table-of-contents
# Table of Contents Item <li> .notion-table-of-contents__item
# Notion Equations <span> .notion-equation
# Notion Equation (Inline) <span> .notion-equation.notion-equation__inline
# Notion Equation (Block) <span> .notion-equation.notion-equation__block
# Content Container <article> .notion-root
# Column list <div> .notion-column-list
# Column <div> .notion-column
# Notion Header Section <div> .notion-header
# Notion Header Title Wrapper <div> .notion-header__title-wrapper
# Notion Header Title <h1> .notion-header__title
# Notion Header Icon Wrapper <div> .notion-header__icon-wrapper
# Notion Header Icon <div> .notion-header__icon
# Notion Header Cover <div> .notion-header__cover
# Text <p> .notion-text__content
# Bold Text <b> strong
# All Headings n/a .notion-heading
# Heading 1 <h1> h1.notion-heading
# Heading 2 <h2> h2.notion-heading
# Heading 3 <h3> h3.notion-heading
# Notion Caption <figcaption> .notion-caption
# Image <div> .notion-image
# Image (Type 2) <img> .notion-image img
# Bookmark <div> .notion-bookmark
# Bookmark Content <div> .notion-bookmark__content
# Bookmark Title <h5> .notion-bookmark__title
# Bookmark Description <p> .notion-bookmark__description
# Bookmark Link <div> .notion-bookmark__link
# Bookmark Cover Wrapper <div> .notion-bookmark__cover
# Bookmark Cover Image <img> .notion-bookmark__cover img
# Video <div> .notion-video
# Audio <div> .notion-audio
# File <a> .notion-file
# File Icon <div> .notion-file__icon
# File Title <span> .notion-file__title
# File Size Text <span> .notion-file__size
# Embedded Content Wrapper (Including caption) <div> .notion-embed
# Embedded Content <div> .notion-embed__content
# Embedded Content Loader <div> .notion-embed__loader
# Embedded Content Iframe wrapper <div> .notion-embed__container
# Tweet <div> .notion-tweet
# Tweet Header Wrapper <div> .static-tweet-header
# Tweet Header Avatar <a> .static-tweet-header-avatar
# Tweet Header Author Wrapper <a> .static-tweet-header-author
# Tweet Header Name <span> .static-tweet-header-name
# Tweet Header Username <span> .static-tweet-header-username
# Tweet Header Twitter Button <a> .static-tweet-header-brand
# Tweet Text <p> .static-tweet-p
# Tweet Image Wrapepr <div> .image-container
# Tweet Info <div> .static-tweet-info
# Notion Navbar <div> .notion-navbar
# Notion Navbar Link <a> .notion-navbar>a
# Notion Navbar Title <div> .notion-navbar__title
# Notion Navbar Icon <div> .notion-navbar__icon
# Notion Navbar Search Button <div> .notion-navbar__search
# Notion Navbar Breadcrumb Divider <span> .notion-breadcrumb__divider
# Notion Navbar Breadcrumb Item <div> .notion-breadcrumb__item
# Notion Navbar Breadcrumb Dots <div> .notion-breadcrumb__dots


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

def notionapi_retrieve_page_list(notion_token, notion_page_ids_no_dashes):
    import notion_client
    notionapi = notion_client.Client(auth = notion_token)
    notion_pages_and_databases = {}
    for notion_page_id_no_dashes in notion_page_ids_no_dashes:
        notionapi_retrieve_recursively(notion_client, notionapi, notion_page_id_no_dashes, notion_pages_and_databases = notion_pages_and_databases)
    notionjson = dict(pages = notion_pages_and_databases, unix_seconds_downloaded = int(time.time()))
    return notionjson

def notionapi_retrieve_recursively(notion_client, notionapi, notion_page_id_no_dashes, notion_pages_and_databases = {}):
    # https://developers.notion.com/reference/retrieve-a-page
    # https://developers.notion.com/reference/retrieve-a-page-property
    # https://developers.notion.com/reference/retrieve-a-block
    # https://developers.notion.com/reference/get-block-children
    # https://developers.notion.com/reference/retrieve-a-database
    def notionapi_blocks_children_list(block, notionapi):
        print('block', block.get('id'), block.get('type'))
        if block['has_children']:
            block['children'] = []
            while True:
                if start_cursor is None:
                    blocks = notionapi.blocks.children.list(block['id'])
                prev_cursor = blocks['next_cursor']
                block['children'].extend(blocks['results'])
                if start_cursor is None or blocks['has_more'] is False:
                    break  
            for subblock in block['children']:
                notionapi_blocks_children_list(subblock, notionapi)
        return block
    try:
        page_type, page = 'page', notionapi.pages.retrieve(notion_page_id_no_dashes)
    except notion_client.APIResponseError as exc:
        page_type, page = 'database', notionapi.databases.retrieve(notion_page_id_no_dashes)
    except notion_client.APIResponseError as exc:
        page_type, page = 'child_page', notionapi.blocks.retrieve(notion_page_id_no_dashes)
    except Exception as exc:
        page_type, page = None, {}
        print(exc)
        return
    print(page_type, page['id'])
    start_cursor = None
    notion_pages_and_databases[page['id']] = page
    notion_pages_and_databases[page['id']]['blocks'] = []
    while True:
        if page_type == 'page' or page_type == 'child_page':
            blocks = notionapi.blocks.children.list(notion_page_id_no_dashes, **(dict(start_cursor = start_cursor) if start_cursor is not None else {}))
        elif page_type == 'database':
            blocks = notionapi.databases.query(notion_page_id_no_dashes, **(dict(start_cursor = start_cursor) if start_cursor is not None else {}))
        start_cursor = blocks['next_cursor']
        notion_pages_and_databases[page['id']]['blocks'].extend(blocks['results'])
        if start_cursor is None or blocks['has_more'] is False:
            break  
    for i_block, block in enumerate(notion_pages_and_databases[page['id']]['blocks']):
        if page_type == 'page':
            if block['type'] in ['page', 'child_page', 'child_database']:
                notionapi_retrieve_recursively(notion_client, notionapi, block['id'], notion_pages_and_databases = notion_pages_and_databases)
            else:
                block = notionapi_blocks_children_list(block, notionapi)
                notion_pages_and_databases[page['id']]['blocks'][i_block] = block
        elif page_type == 'database':
            block['type'] = 'db_entry'
            notion_pages_and_databases[page['id']]['blocks'][i_block] = block
            if block['object'] in ['page', 'child_page', 'child_database']:
                notionapi_retrieve_recursively(notion_client, notionapi, block['id'], notion_pages_and_databases = notion_pages_and_databases)

##############################

def blocktag2html(block = {}, ctx = {}, class_name = '', tag = '', selfclose = False, set_html_contents_and_close = '', prefix = '', suffix = '', attrs = {}, **kwargs):
    notion_attrs_class_name = 'notion-block ' + class_name
    notion_attrs = (' data-block-id="{id}" '.format(id = block.get('id', ''))) * bool(block.get('id')) + (f' class="{notion_attrs_class_name}" ' if notion_attrs_class_name else '') + ' ' + ' '.join(f'{k}="{v}"' if v is not None else k for k, v in attrs.items()) + ' '
    return (f'{prefix}<{tag} ' + (notion_attrs if block else '') + '/' * selfclose + '>\n' + (set_html_contents_and_close + f'\n</{tag}>\n' if set_html_contents_and_close else '') + suffix) if tag else ''

def childrenlike2html(block, ctx, tag = ''):
    html = ''
    subblocks = sum([block.get(key, []) or block.get(block.get('type'), {}).get(key, []) for key in ('children', 'blocks')], [])
    for i, subblock in enumerate(subblocks):
        same_block_type_as_prev = i > 0 and subblock.get('type') == subblocks[i - 1].get('type')
        same_block_type_as_next = i + 1 < len(subblocks) and subblock.get('type') == subblocks[i + 1].get('type')
        html += ((f'<{tag}>') if tag else '') + block2html(subblock, ctx, begin = not same_block_type_as_prev, end = not same_block_type_as_next) + (f'</{tag}>\n' if tag else '')
    return html

def richtext2html(block, ctx = {}, title_mode = False, caption = False, rich_text = False):
    # https://www.notion.so/help/customize-and-style-your-content#markdown
    # https://developers.notion.com/reference/rich-text
    # default_annotations = dict(bold = False, italic = False, strikethrough = False, underline = False, code = False, color = "default")
    if isinstance(block, dict):
        block_type = get_block_type(block)
        if rich_text:
            block = block.get(get_block_type(block), {}).get('rich_text', [])
        if caption: 
            block = block.get(get_block_type(block), {}).get('caption', [])
    if isinstance(block, list):
        return ''.join(richtext2html(subblock, ctx, title_mode = title_mode) for subblock in block).strip()
    
    plain_text = block['plain_text']
    anno = block['annotations']
    href = block.get('href', '')
    if title_mode:
        return plain_text
    if block['type'] == 'mention':
        return mention2html(block, ctx)
    if block['type'] == 'equation':
        return equation2html(block, ctx, inline = True)
    
    res = html.escape(plain_text)
    if href:
        res = link_to_page2html(block, ctx, line_break = False) if href.startswith('/') else linklike2html(block, ctx)
    if anno['bold']:
        res = f'<b>{res}</b> ' 
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

def textlike2html(block, ctx, tag = 'span', class_name = '', attrs = {}, html_icon = '', checked = None):
    color = block.get(get_block_type(block), {}).get('color', '')
    html_text = richtext2html(block, ctx, rich_text = True)
    html_checked = '<input type="checkbox" disabled {} />'.format('checked' * checked) if checked is not None else ''
    return blocktag2html(block, ctx, tag = tag, class_name = class_name + f' notion-color-{color}', attrs = attrs, set_html_contents_and_close = html_checked + html_text + childrenlike2html(block, ctx) + html_icon)

def toggle2html(block, ctx, tag = 'span', class_name = 'notion-toggle-block', attrs = {}, html_icon = ''):
    color = block.get(get_block_type(block), {}).get('color', '')
    html_text = richtext2html(block, ctx, rich_text = True)
    return blocktag2html(block, ctx, tag = 'details', class_name = f'notion-color-{color} notion-toggle-like ' + class_name, attrs = dict(attrs, open = None) if ctx.get('html_details_open') else attrs, set_html_contents_and_close = f'<summary><{tag}>{html_text}{html_icon}</{tag}></summary>\n' + childrenlike2html(block, ctx))

def headinglike2html(block, ctx, tag, class_name = ''):
    block_id_no_dashes = block['id'].replace('-', '')
    block_slug = get_heading_slug(block, ctx)
    html_anchor = f'<a href="#{block_slug}"></a><a href="#{block_id_no_dashes}" class="notion-heading-like-icon"></a>'
    return (textlike2html if block.get(get_block_type(block), {}).get('is_toggleable') is not True else toggle2html)(block, ctx, tag = tag, class_name = 'notion-heading-like ' + class_name, attrs = dict(id = block_id_no_dashes), html_icon = html_anchor)

def linklike2html(block, ctx, tag = 'a', class_name = '', full_url_as_caption = False, html_icon = '', line_break = False):
    src = get_block_url(block)
    html_text = richtext2html(block, ctx, caption = True) or html.escape(block.get(get_block_type(block), {}).get('name') or block.get('plain_text') or (src if full_url_as_caption else os.path.basename(urllib.parse.urlparse(src).path)))
    return blocktag2html(block, ctx, tag = tag, attrs = dict(href = src), class_name = class_name, set_html_contents_and_close = html_icon + html_text) + '<br/>' * line_break

def page2html(block, ctx, tag = 'article', class_name = 'notion-page-block', strftime = '%Y/%m/%d %H:%M:%S', html_prefix = '', html_suffix = '', class_name_page_title = '', class_name_page_content = '', class_name_header = '', class_name_page = ''):
    # if page.get("cover") is not None:
    #     cover = list(markdown_dict_search_recursively(page["cover"], "url"))[0]
    #     pages[page_id]["cover"] = cover
    #     pages[page_id]["assets_to_download"].append(cover)
    # else:
    #     pages[page_id]["cover"] = None
    # pages[page_id]["icon"] = None
    # pages[page_id]["emoji"] = None
    # if page.get("icon") and "emoji" in page["icon"]:
    #     pages[page_id]["emoji"] = page["icon"]["emoji"]
    # elif page.get("icon"):
    #     icon = page["icon"]["file"]["url"]
    #     pages[page_id]["icon"] = icon
    #     pages[page_id]["assets_to_download"].append(icon)

    dt_modified = datetime.datetime.fromtimestamp(ctx.get('unix_seconds_downloaded', 0)).strftime(strftime) if ctx.get('unix_seconds_downloaded', 0) else ''
    dt_published = datetime.datetime.fromtimestamp(ctx.get('unix_seconds_generated', 0)).strftime(strftime) if ctx.get('unix_seconds_generated', 0) else ''
    src_cover = (block.get('cover') or {}).get((block.get('cover') or {}).get('type'), {}).get('url', '')
    src_cover = get_asset_url(src_cover, ctx)
    page_id = block.get('id', '')
    page_id_no_dashes = page_id.replace('-', '')
    page_title = html.escape(get_page_title(block, ctx))
    page_emoji = get_page_emoji(block, ctx)
    page_url = get_page_url(block, ctx)
    page_slug = get_page_slug(page_id, ctx)
    src_edit = ctx.get('edit_url', '').format(page_id_no_dashes = page_id_no_dashes, page_id = page_id, page_slug = page_slug) if ctx.get('edit_url') else page_url
    
    html_anchor = f'<a href="#{page_slug}" class="notion-page-like-icon"></a><a href="{src_edit}" target="_blank" class="notion-page-like-edit-icon"></a>'
    
    return blocktag2html(block, ctx, tag = tag, attrs = {'data-notion-url' : page_url}, class_name = 'notion-page ' + class_name_page, set_html_contents_and_close = f'{html_prefix}<header class="{class_name_header}"><img src="{src_cover}" class="notion-page-cover"></img><h1 id="{page_id_no_dashes}" class="notion-record-icon">{page_emoji}</h1><h1 id="{page_slug}" class="{class_name} {class_name_page_title}">{page_title}{html_anchor}</h1><i><time class="notion-page-block-datetime-published dt-published" datetime="{dt_published}" title="@{dt_modified or dt_published} -> @{dt_published}">@{dt_published}</time></i></p></header><div class="notion-page-content {class_name_page_content}">\n' + childrenlike2html(block, ctx) + f'\n</div>{html_suffix}')

##############################

def table_of_contents2html(block, ctx, tag = 'ul', class_name = 'notion-table_of_contents-block'):
    # https://www.notion.so/help/columns-headings-and-dividers#how-it-works
    if block.get('site_table_of_contents_page_ids'):
        table_of_contents_page_tree = lambda page_ids: '' if not page_ids else '<ul class="notion-table_of_contents-site-page-list">\n' + '\n'.join('<li class="notion-table_of_contents-site-page-item">\n{html_link_to_page}\n{html_child_pages}\n</li>'.format(html_link_to_page = link_to_page2html(dict(type = 'link_to_page', link_to_page = dict(type = 'page_id', page_id = page_id)), ctx), html_child_pages = table_of_contents_page_tree(page['id'] for page in ctx['child_pages_by_parent_id'].get(page_id, []))) for page_id in page_ids) + '\n</ul>'
        page_ids = block.get('site_table_of_contents_page_ids', [])
        child_page_ids = set(child_page['id'] for child_pages in ctx['child_pages_by_parent_id'].values() for child_page in child_pages)
        root_page_ids = [page_id for page_id in page_ids if page_id not in child_page_ids]
        return '<div class="notion-table_of_contents-site"><h1 class="notion-table_of_contents-site-header"></h1>\n' + table_of_contents_page_tree(root_page_ids) + '<hr/></div>\n'
    page_block = get_page_current(block, ctx)
    headings = get_page_headings(page_block, ctx)
    color = block['table_of_contents'].get('color', '')
    inc_heading_type = dict(heading_0 = 'heading_1', heading_1 = 'heading_2', heading_2 = 'heading_3', heading_3 = 'heading_3').get
    nominal_heading_type, effective_heading_type = 'heading_0', 'heading_0'
    html_children = ''
    for block in headings:
        block_id_no_dashes = block.get('id', '').replace('-', '')
        block_slug = get_heading_slug(block, ctx)
        block_hash = block_slug if ctx['extract_mode'] in ['flat.html', 'flat/index.html'] else block_id_no_dashes
        heading_type = block.get('type', '')
        nominal_heading_type, effective_heading_type = heading_type, min(heading_type, inc_heading_type(effective_heading_type) if heading_type > nominal_heading_type else effective_heading_type)
        html_text = richtext2html(block, ctx, rich_text = True, title_mode = True)
        html_children += f'<li class="notion-table_of_contents-heading notion-table_of_contents-{effective_heading_type}"><a href="#{block_hash}">' + html_text + '</a></li>\n'
    return blocktag2html(block, ctx, tag = tag, class_name = class_name + f' notion-color-{color}', set_html_contents_and_close = html_children, prefix = '<hr/>', suffix = '<hr/>')

def table2html(block, ctx, tag = 'table', class_name = 'notion-table-block'):
    table_width = block['table'].get('table_width', 0)
    has_row_header = block['table'].get('has_row_header', False)
    has_column_header = block['table'].get('has_column_header', False)
    rows = block.get('children', [])
    html_children = ''
    for i, subblock in enumerate(rows):
        if i == 0:
            html_children += '\n<thead>\n' if has_row_header else '\n<tbody>\n'
        html_children += '<tr>\n'
        cells = subblock.get('table_row', {}).get('cells', [])
        for j, cell in enumerate(cells):
            tag_cell = 'th' if (has_row_header and i == 0) or (has_column_header and j == 0) else 'td'
            html_children += f'<{tag_cell}>' + (''.join('<div>{html_text}</div>'.format(html_text = richtext2html(subcell, ctx)) for subcell in cell) if isinstance(cell, list) else richtext2html(cell, ctx)) + f'</{tag_cell}>\n'
        if len(cells) < table_width:
            html_children += '<td></td>' * (table_width - len(cells))
        html_children += '</tr>\n'
        if i == 0:
            html_children += '\n</thead>\n<tbody>\n' if has_row_header else ''
    html_children += '\n</tbody>\n'
    return blocktag2html(block, ctx, tag = tag, class_name = class_name, set_html_contents_and_close = html_children)

def video2html(block, ctx, tag = 'p', class_name = 'notion-video-block'):
    url = get_asset_url(block, ctx)
    is_youtube, url, urlimg = normalize_youtube_url(url, embed = True)
    caption = richtext2html(block, ctx, caption = True)
    html_contents = f'<div><iframe width="640" height="480" src="{url}" frameborder="0" allowfullscreen></iframe></div>' if is_youtube else f'<video playsinline muted loop controls src="{url}"></video>'
    return blocktag2html(block, ctx, tag = tag, class_name = class_name, set_html_contents_and_close = html_contents)

def image2html(block, ctx, tag = 'img', class_name = 'notion-image-block'):
    src = get_asset_url(block, ctx)
    html_text = richtext2html(block, ctx, caption = True, title_mode = False)
    html_text_alt = richtext2html(block, ctx, caption = True, title_mode = True)
    return blocktag2html(block, ctx, tag = 'figure', class_name = class_name, set_html_contents_and_close = f'<{tag} src="{src}" alt="{html_text_alt}"></{tag}><figcaption>{html_text}</figcaption>')

def embed2html(block, ctx, tag = 'iframe', class_name = 'notion-embed-block', html_text = '', attrs = dict(width = 640, height = 480)):
    block_type = get_block_type(block)
    src = get_block_url(block) or block.get(block_type, {}).get(block.get(block_type, {}).get('type', ''), {}).get('url') or ''
    src = get_asset_url(src, ctx)
    html_text = html_text or richtext2html(block, ctx, caption = True) 
    attrstr = ' '.join(f'{k}="{v}"' if v is not None else k for k, v in attrs.items())
    return blocktag2html(block, ctx, tag = 'figure', class_name = class_name, set_html_contents_and_close = f'<figcaption>{html_text}</figcaption><{tag} src="{src}" {attrstr}></{tag}>')

def bookmark2html(block, ctx, tag = 'a', class_name = 'notion-bookmark-block'):
    src = get_block_url(block)
    html_text = richtext2html(block, ctx, caption = True) or html.escape(block.get(get_block_type(block), {}).get('name') or block.get('plain_text') or src)
    try:
        netloc = urllib.parse.urlparse(src).netloc
    except:
        netloc = ''
    return blocktag2html(block, ctx, tag = tag, attrs = dict(href = src), class_name = class_name, set_html_contents_and_close = f'<figure>{netloc}<br/><figcaption>{html_text}</figcaption></figure>')

def mention2html(block, ctx, tag = 'div', class_name = dict(page = 'notion-page-mention-token', database = 'notion-database-mention-token', link_preview = 'notion-link-mention-token', user = 'notion-user-mention-token', date = 'notion-date-mention-token'), untitled = 'Untitled'):
    mention_type = block['mention'].get('type')
    mention_payload = block['mention'][mention_type]
    if mention_type == 'page':
        return link_to_page2html(dict(block, type = 'link_to_page', link_to_page = dict(type = 'page_id', page_id = mention_payload.get('id', ''))), ctx, class_name = class_name[mention_type])
    if mention_type == 'database':
        return linklike2html(block, ctx, class_name = class_name[mention_type])
    if mention_type == 'link_preview':
        return link_preview2html(block, ctx, class_name = class_name[mention_type])
    if mention_type == 'user':
        return blocktag2html(block, ctx, tag = 'strong', class_name = class_name[mention_type], set_html_contents_and_close = '@{user_name}#{user_id}'.format(user_id = mention_payload.get('id', ''), user_name = block.get('plain_text', '').removeprefix('@')))
    if mention_type == 'date':
        return blocktag2html(block, ctx, tag = 'strong', class_name = class_name[mention_type], set_html_contents_and_close = '@{date_text}'.format(date_text = html.escape(block.get('plain_text', ''))))
    return unsupported2html(block, ctx)

def link_to_page2html(block, ctx, tag = 'a', line_break = True, class_name = 'notion-alias-block', html_icon = '', untitled = '???'):
    link_to_page_info  = get_page_link_info(block, ctx)
    html_caption = '{html_icon}{page_emoji} {page_title}'.format(html_icon = html_icon, page_title = html.escape(link_to_page_info['page_title']), page_emoji = link_to_page_info['page_emoji'])
    return blocktag2html(block, ctx, tag = tag, attrs = dict(href = link_to_page_info['href']), class_name = class_name, set_html_contents_and_close = html_caption) + '<br/>' * line_break

def child_page2html(block, ctx, tag = 'article', class_name = 'notion-page-block', **kwargs): return page2html(block, ctx, tag = tag, class_name = class_name, **kwargs)
def unsupported2html(block, ctx, tag = 'div', class_name = 'notion-unsupported-block', comment = True, **ignored): return '\n<!--\n' * comment + blocktag2html(block, ctx, tag = tag, class_name = class_name, attrs = {'data-notion-block_type' : block.get('type', '') or block.get('object', '')}, selfclose = True).replace('-->' * comment, '__>' * comment) + '\n-->\n' * comment
def divider2html(block, ctx, tag = 'hr', class_name = 'notion-divider-block'): return blocktag2html(block, ctx, tag = tag, class_name = class_name, selfclose = True)
def heading_12html(block, ctx, tag = 'h1', class_name = 'notion-header-block'): return headinglike2html(block, ctx, tag = tag, class_name = class_name)
def heading_22html(block, ctx, tag = 'h2', class_name = 'notion-sub_header-block'): return headinglike2html(block, ctx, tag = tag, class_name = class_name)
def heading_32html(block, ctx, tag = 'h3', class_name = 'notion-sub_sub_header-block'): return headinglike2html(block, ctx, tag = tag, class_name = class_name)
def paragraph2html(block, ctx, tag = 'p', class_name = 'notion-text-block'): return blocktag2html(block, ctx, tag = 'br', class_name = class_name, selfclose = True) if block.get('has_children') is False and not (block.get(get_block_type(block), {}).get('rich_text')) else textlike2html(block, ctx, tag = tag, class_name = class_name)
def column_list2html(block, ctx, tag = 'div', class_name = 'notion-column_list-block'): return blocktag2html(block, ctx, tag = tag, class_name = class_name + ' notion_column_list-block-vertical' * (ctx.get('html_columnlist_disable') is True), set_html_contents_and_close = childrenlike2html(block, ctx))
def column2html(block, ctx, tag = 'div', class_name = 'notion-column-block'): return blocktag2html(block, ctx, tag = tag, class_name = class_name, set_html_contents_and_close = childrenlike2html(block, ctx, tag = tag)) 
def bulleted_list_item2html(block, ctx, tag = 'ul', begin = False, end = False, class_name = 'notion-bulleted_list-block'): return f'<{tag} class="{class_name}">\n' * begin + textlike2html(block, ctx, tag = 'li') + f'\n</{tag}>\n' * end
def numbered_list_item2html(block, ctx, tag = 'ol', begin = False, end = False, class_name = 'notion-numbered_list-block'): return f'<{tag} class="{class_name}">\n' * begin + textlike2html(block, ctx, tag = 'li') + f'\n</{tag}>\n' * end 
def quote2html(block, ctx, tag = 'blockquote', class_name = 'notion-quote-block'): return textlike2html(block, ctx, tag = tag, class_name = class_name)
def code2html(block, ctx, tag = 'code', class_name = 'notion-code-block'): return blocktag2html(block, ctx, tag = 'figure', attrs = {'data-language' : block['code'].get('language', '')}, class_name = class_name, set_html_contents_and_close = '<figcaption>{html_caption}</figcaption>\n<pre><{tag}>'.format(html_caption = richtext2html(block, ctx, caption = True), tag = tag) + richtext2html(block, ctx, rich_text = True) + f'</{tag}></pre>')
def to_do2html(block, ctx, tag = 'div', class_name = 'notion-to_do-block'): return textlike2html(block, ctx, tag = tag, class_name = class_name, checked = block.get(get_block_type(block), {}).get('checked', False))
def synced_block2html(block, ctx, tag = 'figure', class_name = 'notion-synced_block-block'): return blocktag2html(block, ctx, tag = tag, class_name = class_name, set_html_contents_and_close = '<figcaption>{synced_from_block_id}</figcaption>\n{html_children}'.format(synced_from_block_id = block['synced_block'].get('synced_from', {}).get('block_id', ''), html_children = childrenlike2html(block, ctx)))
def equation2html(block, ctx, tag = 'code', class_name = 'notion-equation-block', inline = False): return blocktag2html(block, ctx, tag = tag, class_name = class_name if not inline else class_name.replace('block', 'inline'), set_html_contents_and_close = html.escape(block['equation'].get('expression', '') or block.get('plain_text', '')))
def file2html(block, ctx, tag = 'a', class_name = 'notion-file-block'): return linklike2html(block, ctx, tag = tag, class_name = class_name, line_break = True)
def callout2html(block, ctx, tag = 'p', class_name = 'notion-callout-block'): return blocktag2html(block, ctx, tag = 'div', class_name = class_name + ' notion-color-{color}'.format(color = block['callout'].get('color', '')), set_html_contents_and_close = '<div>{icon_emoji}</div><div>\n'.format(icon_emoji = block['callout'].get('icon', {}).get(block['callout'].get('icon', {}).get('type'), '')) + textlike2html(block, ctx, tag = tag)) + '</div>\n'
def pdf2html(block, ctx, tag = 'a', class_name = 'notion-pdf-block'): return embed2html(block, ctx, class_name = class_name, html_text = linklike2html({k : v for k, v in block.items() if k != 'id'}, ctx, tag = tag))
def breadcrumb2html(block, ctx, tag = 'div', class_name = 'notion-breadcrumb-block', sep = '&nbsp;/&nbsp;'): return blocktag2html(block, ctx, tag = tag, class_name = class_name, set_html_contents_and_close = sep.join(link_to_page2html(subblock, ctx, line_break = False) for subblock in reversed(ctx['page_parent_paths'][get_page_current(block, ctx)['id']])))
def template2html(block, ctx, tag = 'figure', class_name = 'notion-template-block'): return blocktag2html(block, ctx, tag = tag, class_name = class_name, set_html_contents_and_close = '<figcaption>{html_text}</figcaption>\n{html_children}'.format(html_text = richtext2html(block, ctx, rich_text = True), html_children = childrenlike2html(block, ctx)))
def child_database2html(block, ctx, tag = 'figure', class_name = 'notion-child_database-block', untitled = '???'): return blocktag2html(block, ctx, tag = tag, class_name = class_name, set_html_contents_and_close = '<figcaption><strong>{html_child_database_title}</strong></figcaption>'.format(html_child_database_title = html.escape(block['child_database'].get('title') or untitled)))
def pdf2html(block, ctx, tag = 'a', class_name = 'notion-pdf-block'): return embed2html(block, ctx, class_name = class_name, html_text = linklike2html({k : v for k, v in block.items() if k != 'id'}, ctx, tag = tag))
def link_preview2html(block, ctx, tag = 'a', class_name = 'notion-link_preview-block'): return linklike2html(block, ctx, tag = tag, class_name = class_name, line_break = True)

##############################

def childrenlike2markdown(block, ctx, tag = '', newline = '\n\n'): return newline.join(block2markdown(subblock, ctx) for i, subblock in enumerate(sum([block.get(key, []) or block.get(block.get('type'), {}).get(key, []) for key in ('children', 'blocks')], []))) + newline

def textlike2markdown(block, ctx, tag = '', markdown_icon = '', checked = None, title_mode = False):
    markdown_text = richtext2markdown(block, ctx, rich_text = True, title_mode = title_mode)
    color = block.get(get_block_type(block), {}).get('color', '')
    markdown_checked = '[{}] '.format('x' if checked else ' ') if checked is not None else ''
    return tag + markdown_checked + markdown_text + markdown_icon + '\n' + childrenlike2markdown(block, ctx)

def toggle2markdown(block, ctx, tag = '', markdown_icon = '', title_mode = False): return tag + '▼ ' + richtext2markdown(block, ctx, rich_text = True, title_mode = title_mode)  + markdown_icon + '\n' + childrenlike2markdown(block, ctx)
# outcome_block = '\n<details markdown="1">\n<summary markdown="1">\n\n' + outcome_block + '\n\n</summary>\n\n' + ''.join(block2markdown(subblock, ctx, page_id = page_id) for subblock in block["children"]) + '\n\n</details>\n\n'

def headinglike2markdown(block, ctx, tag = ''):
    block_id_no_dashes = block['id'].replace('-', '')
    block_slug = get_heading_slug(block, ctx)
    block_hash = block_slug if ctx['extract_mode'] == 'flat.md' else block_id_no_dashes
    markdown_anchor = f' [#](#{block_hash})'
    return (textlike2markdown if block.get(get_block_type(block), {}).get('is_toggleable') is not True else toggle2markdown)(block, ctx, tag = f'<i id="{block_id_no_dashes}"></i><i id="{block_slug}"></i>\n' + tag, markdown_icon = markdown_anchor)

def linklike2markdown(block, ctx, tag = '', full_url_as_caption = True, line_break = False):
    src = get_block_url(block)
    markdown_text = richtext2markdown(block, ctx, caption = True) or (block.get(get_block_type(block), {}).get('name') or block.get('plain_text') or (src if full_url_as_caption else os.path.basename(urllib.parse.urlparse(src).path)))
    return f'[{tag}{markdown_text}]({src})' + '\n\n' * line_break

def table2markdown(block, ctx, sanitize_table_cell = lambda md: md.replace('\n', ' ')):
    table_width = block['table'].get('table_width', 0)
    has_row_header = block['table'].get('has_row_header', False)
    has_column_header = block['table'].get('has_column_header', False)
    rows = block.get('children', [])
    markdown_children = '\n'
    for i, subblock in enumerate(rows):
        cells = subblock.get('table_row', {}).get('cells', [])
        markdown_children += ' | ' + ' | '.join(sanitize_table_cell(richtext2markdown(cell, ctx)) for cell in cells) + ' | ' + '\n'
        if i == 0:
            markdown_children += ' | ' + ' | '.join(['----'] * len(cells)) + ' | ' + '\n'
    markdown_children += '\n'
    return markdown_children

def table_of_contents2markdown(block, ctx, tag = '* '):
    #return '\n\n{:toc}\n\n'
    if block.get('site_table_of_contents_page_ids'):
        table_of_contents_page_tree = lambda page_ids, depth = 0: '' if not page_ids else ''.join(depth * 4 * ' ' + '{tag}{markdown_link_to_page}\n{markdown_child_pages}'.format(tag = tag, markdown_link_to_page = link_to_page2markdown(dict(type = 'link_to_page', link_to_page = dict(type = 'page_id', page_id = page_id)), ctx, line_break = False), markdown_child_pages = table_of_contents_page_tree([page['id'] for page in ctx['child_pages_by_parent_id'].get(page_id, [])], depth + 1)) for page_id in page_ids)
        page_ids = block.get('site_table_of_contents_page_ids', [])
        child_page_ids = set(child_page['id'] for child_pages in ctx['child_pages_by_parent_id'].values() for child_page in child_pages)
        root_page_ids = [page_id for page_id in page_ids if page_id not in child_page_ids]
        return table_of_contents_page_tree(root_page_ids, depth = 0)
    if ctx.get('markdown_toc_page'):
        return ctx['markdown_toc_page']

    page_block = get_page_current(block, ctx)
    headings = get_page_headings(page_block, ctx)
    color = block['table_of_contents'].get('color', '')
    inc_heading_type = dict(heading_0 = 'heading_1', heading_1 = 'heading_2', heading_2 = 'heading_3', heading_3 = 'heading_3').get
    nominal_heading_type, effective_heading_type = 'heading_0', 'heading_0'
    heading_type2depth = dict(heading_0 = 0, heading_1 = 1, heading_2 = 2, heading_3 = 3)
    markdown_children = '---\n'
    for block in headings:
        block_id_no_dashes = block.get('id', '').replace('-', '')
        block_slug = get_heading_slug(block, ctx)
        block_hash = block_slug if ctx['extract_mode'] == 'flat.md' else block_id_no_dashes
        heading_type = block.get('type', '')
        nominal_heading_type, effective_heading_type = heading_type, min(heading_type, inc_heading_type(effective_heading_type) if heading_type > nominal_heading_type else effective_heading_type)
        markdown_text = richtext2markdown(block, ctx, rich_text = True, title_mode = True)
        markdown_children += max(0, heading_type2depth[effective_heading_type] - 1) * 4 * ' ' + f'{tag}[{markdown_text}](#{block_hash})\n'
    markdown_children += '---\n'
    return markdown_children

def mention2markdown(block, ctx):
    mention_type = block['mention'].get('type')
    mention_payload = block['mention'][mention_type]
    if mention_type == 'page':
        return link_to_page2markdown(dict(block, type = 'link_to_page', link_to_page = dict(type = 'page_id', page_id = mention_payload.get('id', ''))), ctx, line_break = False)
    if mention_type == 'database':
        return linklike2markdown(block, ctx)
    if mention_type == 'link_preview':
        return link_preview2markdown(block, ctx)
    if mention_type == 'user':
        return ' **@{user_name}#{user_id}** '.format(user_id = mention_payload.get('id', ''), user_name = block.get('plain_text', '').removeprefix('@'))
    if mention_type == 'date':
        return ' **@{date_text}** '.format(date_text = html.escape(block.get('plain_text', '')))
    return unsupported2markdown(block, ctx)

def page2markdown(block, ctx, strftime = '%Y/%m/%d %H:%M:%S'):
    dt_modified = datetime.datetime.fromtimestamp(ctx.get('unix_seconds_downloaded', 0)).strftime(strftime) if ctx.get('unix_seconds_downloaded', 0) else ''
    dt_published = datetime.datetime.fromtimestamp(ctx.get('unix_seconds_generated', 0)).strftime(strftime) if ctx.get('unix_seconds_generated', 0) else ''
    src_cover = (block.get('cover') or {}).get((block.get('cover') or {}).get('type'), {}).get('url', '')
    src_cover = get_asset_url(src_cover, ctx)
    page_id = block.get('id', '')
    page_id_no_dashes = page_id.replace('-', '')
    page_title = (get_page_title(block, ctx))
    page_emoji = get_page_emoji(block, ctx)
    page_url = get_page_url(block, ctx)
    page_slug = get_page_slug(page_id, ctx)
    src_edit = ctx.get('edit_url', '').format(page_id_no_dashes = page_id_no_dashes, page_id = page_id, page_slug = page_slug) if ctx.get('edit_url') else page_url
    

    res = f'![cover]({src_cover})\n\n' * bool(src_cover)
    res += f'<i id="{page_slug}"></i>\n' * bool(ctx['extract_mode'] == 'single.md')
    res += f'# {page_emoji} {page_title}\n'
    
    #markdown_anchor = f' [#](#{block_hash})'
    # <a href="{src_edit}" target="_blank" class="notion-page-like-edit-icon"></a>'

    res += '*@' + ' -> '.join([dt_modified, dt_published]) + '*\n\n'
    res += childrenlike2markdown(block, ctx)
    res += '\n\n---\n\n'
    
    if ctx['markdown_frontmatter']:
        res = f'''---\ntitle: "{page_title}"\ncover: {src_cover}\nemoji: {page_emoji}\n---\n\n''' + res
        
    #    elif page.get("icon"):
    #        icon = page["icon"]["file"]["url"]
    #        pages[page_id]["icon"] = icon
    #    elif ctx['pages'][block['id']]['icon']:
    #        icon = ctx['pages'][block['id']]['icon']
    #        outcome_block = f"""[<span class="miniicon"> <img src="{icon}"></img></span> {outcome_block}"""

    #    elif block['has_children']:
    #        depth += 1
    #        for subblock in block["children"]: # This is needed, because notion thinks, that if the page contains numbered list, header 1 will be the child block for it, which is strange.
    #            if subblock['type'] == "heading_1":
    #                depth = 0
    #            outcome_block += "\t"*depth + block2markdown(subblock, ctx, depth = depth, page_id = page_id)
    
    #page_md_fixed_lines = []
    #prev_line_type = ''
    #for line in res.splitlines():
    #    line_type = ''
    #    norm_line = line.lstrip('\t').lstrip()
    #    if norm_line.startswith('- [ ]') or norm_line.startswith('- [x]'):
    #        line_type = 'checkbox'
    #    elif norm_line.startswith('* '):
    #        line_type = 'bullet'
    #    elif norm_line.startswith('1. '):
    #        line_type = 'numbered'
    #    if prev_line_type != '':
    #        if line == '':
    #            continue
    #    if line_type != prev_line_type:
    #        page_md_fixed_lines.append('')
    #    page_md_fixed_lines.append(line)
    #    prev_line_type = line_type
    #res = '\n'.join(page_md_fixed_lines)
    #res = res.replace('\n\n\n', '\n\n')
    # page_md = code_aligner(page_md)
    return res

def child_page2markdown(block, ctx): return page2markdown(block, ctx)
def unsupported2markdown(block, ctx): return '*unsupported notion block [{block_id}]*'.format(block_id = block.get('id', ''))
def divider2markdown(block, ctx, tag = '---'): return tag
def heading_12markdown(block, ctx, tag = '# '  ): return headinglike2markdown(block, ctx, tag = tag) 
def heading_22markdown(block, ctx, tag = '## ' ): return headinglike2markdown(block, ctx, tag = tag) 
def heading_32markdown(block, ctx, tag = '### '): return headinglike2markdown(block, ctx, tag = tag) 
def paragraph2markdown(block, ctx): return '' if block.get('has_children') is False and not (block.get(get_block_type(block), {}).get('rich_text')) else textlike2markdown(block, ctx)
def column_list2markdown(block, ctx): return childrenlike2markdown(block, ctx)
def column2markdown(block, ctx):      return childrenlike2markdown(block, ctx)
def bulleted_list_item2markdown(block, ctx, tag = '* '): return tag + textlike2markdown(block, ctx)
def numbered_list_item2markdown(block, ctx, tag = '1. '): return tag + textlike2markdown(block, ctx)
def quote2markdown(block, ctx, tag = '> '): return  tag + textlike2markdown(block, ctx)
def to_do2markdown(block, ctx, tag = '- [{x}] '): return textlike2markdown(block, ctx, tag = tag.format(x = 'x' if block.get('checked', '') else ' '), checked = block.get(get_block_type(block), {}).get('checked', False))
def synced_block2markdown(block, ctx): return '---\n**{synced_from_block_id}**\n{markdown_children}\n---'.format(synced_from_block_id = block['synced_block'].get('synced_from', {}).get('block_id', ''), markdown_children = childrenlike2markdown(block, ctx))
def equation2markdown(block, ctx, inline = False): return ('```math\n' if not inline else '`' ) + (block['equation'].get('expression', '') or block.get('plain_text', '')) + ('\n```' if not inline else '`')
def file2markdown(block, ctx, tag = '📎'): return linklike2markdown(block, ctx, tag = tag, line_break = True)
def pdf2markdown(block, ctx, tag = '📄'): return linklike2markdown(block, ctx, tag = tag, line_break = True)
def bookmark2markdown(block, ctx, tag = '🔖'): return linklike2markdown(block, ctx, tag = tag, line_break = True)
def link_preview2markdown(block, ctx, tag = '🌐'): return linklike2markdown(block, ctx, tag = tag, line_break = True)
def embed2markdown(block, ctx): return embed2html(block, ctx)
def child_database2markdown(block, ctx, untitled = '???'): return ' **{html_child_database_title}** '.format(child_database_title = (block['child_database'].get('title') or untitled))
def template2markdown(block, ctx): return '---\n{markdown_text}\n{markdown_children}\n---'.format(markdown_text = richtext2markdown(block, ctx, rich_text = True), markdown_children = childrenlike2markdown(block, ctx))
def breadcrumb2markdown(block, ctx, sep = ' / '): return  sep.join(link_to_page2markdown(subblock, ctx, line_break = False) for subblock in reversed(ctx['page_parent_paths'][get_page_current(block, ctx)['id']]))

def code2markdown(block, ctx): return '{markdown_caption}\n```{language}\n'.format(language = block.get('language', '').replace(' ', '_'), markdown_caption = richtext2html(block, ctx, caption = True)) + richtext2markdown(block, ctx, rich_text = True) + '\n```'
# outcome_block = outcome_block.rstrip('\n').replace('\n', '\n'+'\t'*depth) + '\n\n'


def callout2markdown(block, ctx):
    return '> {icon_emoji} '.format(icon_emoji = block['callout'].get('icon', {}).get(block['callout'].get('icon', {}).get('type'), '')) + textlike2markdown(block, ctx).rstrip() 
    #outcome_block += '>\n'.join(''.join(f'> {line}\n' for line in block2markdown(subblock, ctx, page_id = page_id).splitlines()) + '>\n' for subblock in block["children"])

def image2markdown(block, ctx): 
    src = get_asset_url(block, ctx)
    markdown_text = richtext2markdown(block, ctx, caption = True, title_mode = False)
    markdown_text_alt = richtext2markdown(block, ctx, caption = True, title_mode = True)
    return f'![{markdown_text_alt}]({src})\n' + f'{markdown_text}' * bool(markdown_text)

def video2markdown(block, ctx, tag = 'p', class_name = 'notion-video-block'):
    url = get_asset_url(block, ctx)
    is_youtube, url, urlimg = normalize_youtube_url(url, embed = False)
    caption = richtext2html(block, ctx, caption = True)
    return f'[YouTube: {url}]({url})\n[![YouTube]({urlimg})]({url} "YouTube")' if is_youtube else f'<video playsinline muted loop controls src="{url}"></video>'

def link_to_page2markdown(block, ctx, line_break = True):
    link_to_page_info  = get_page_link_info(block, ctx)
    markdown_caption = '{page_emoji} {page_title}'.format(page_title = (link_to_page_info['page_title']), page_emoji = link_to_page_info['page_emoji'])
    return '[{markdown_caption}]({href})'.format(markdown_caption = markdown_caption, href = link_to_page_info['href'])# + '\n\n' * line_break

def richtext2markdown(block, ctx, title_mode = False, caption = False, rich_text = False):
    if isinstance(block, dict):
        block_type = get_block_type(block)
        if rich_text:
            block = block.get(get_block_type(block), {}).get('rich_text', [])
        if caption: 
            block = block.get(get_block_type(block), {}).get('caption', [])
    if isinstance(block, list):
        return ''.join(richtext2markdown(subblock, ctx, title_mode = title_mode) for subblock in block).strip()
    
    plain_text = block['plain_text']
    anno = block['annotations']
    href = block.get('href', '')
    if title_mode:
        return plain_text
    if block['type'] == 'mention':
        return mention2markdown(block, ctx)
    if block['type'] == 'equation':
        return equation2markdown(block, ctx, inline = True)
    res = (plain_text)
    if href:
        res = link_to_page2markdown(block, ctx, line_break = False) if href.startswith('/') else linklike2markdown(block, ctx)
    
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
        res = f'<span style="color:{color}">{res}</span>'
    return ' ' * space_left + res + ' ' * space_right


##############################

def get_block_type(block):
    return block.get('type') or block.get('object') or ''

def get_page_link_info(block, ctx, untitled = '???'):
    payload = block.get(block.get('type'), {})
    page_id = payload.get(payload.get('type'), '')
    page_id_no_dashes = page_id.replace('-', '') or (block.get('href', '').lstrip('/') if block.get('href', '').startswith('/') else '') 
    page_ids_no_dashes = set(page_id.replace('-', '') for page_id in ctx['page_ids'])
    page_slug = get_page_slug(page_id_no_dashes, ctx) 
    page_block = get_page_current(block, ctx)
    page_url_base = get_page_url_relative(page_block, ctx)
    page_url_target = get_page_url_relative(block, ctx)
    href = get_page_relative_link(page_url_base = page_url_base, page_url_target = page_url_target)
    page_block = ctx['id2block'].get(page_id_no_dashes)
    page_emoji = get_page_emoji(page_block, ctx)
    page_title = get_page_title(page_block, ctx) or block.get('plain_text', '') or untitled
    return dict(page_emoji = page_emoji, page_title = page_title, href = href)


def get_page_title(block, ctx, untitled = 'Untitled'):
    #  pages[page_id]["title"] = page["properties"]["title"]["title"][0]["plain_text"] if len(page.get("properties",{}).get('title', {}).get('title', [])) > 0 else pages[page_id].get("title")
    if not block:
        return ''
    page_title = ' '.join(t['plain_text'] for t in block.get('properties', {}).get('title', {}).get('title', [])).strip() or block.get('child_page', {}).get('title', '').strip() or block.get('title', '').strip() or ' '.join(t['plain_text'] for t in block.get('properties', {}).get('Name', {}).get('title', [])).strip() or block.get('plain_text') or untitled
    
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

def get_page_ids_normalized(root_page_ids, all_page_and_child_page_ids, notion_slugs):
    for i in range(len(root_page_ids)):
        for k, v in notion_slugs.items():
            if root_page_ids[i] == v:
                root_page_ids[i] = k
        for k in all_page_and_child_page_ids:
            if root_page_ids[i] == k.replace('-', ''):
                root_page_ids[i] = k
    return root_page_ids

def get_page_url(block, ctx, base_url = 'https://www.notion.so'):
    return block.get('url', os.path.join(base_url, block.get('id', '').replace('-', '')))

def get_page_url_absolute(page_url_relative, ctx):
    return (ctx['base_url'].rstrip('/') + page_url_relative.removeprefix('./')) if ctx.get('base_url') else ('file:///' + page_url_relative)

def get_page_url_relative(block, ctx):
    page_id = block.get('link_to_page', {}).get('page_id', '') or (block.get('href', '').removeprefix('/') if block.get('href', '').startswith('/') else '') or block.get('id', '')
    page_id_no_dashes = page_id.replace('-', '')
    
    page_slug = get_page_slug(page_id, ctx)
    page_slug_only = get_page_slug(page_id, ctx, only_slug = True)
    is_index_page = page_slug == 'index'
    page_suffix = '/index.html'.removeprefix('/' if is_index_page else '') if ctx.get('html_link_to_page_index_html') else ''
    
    if ctx['extract_mode'] == 'flat/index.html':
        return './' + ('' if is_index_page else page_slug) + page_suffix
    
    elif ctx['extract_mode'] == 'flat.html':
        return './' + (page_suffix if is_index_page else page_slug + '.html')

    elif ctx['extract_mode'] == 'flat.md':
        #return './' + ('' if is_index_page else page_slug)
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
    url = block.get('file', {}).get('url') or block.get('external', {}).get('url') or payload.get('file', {}).get('url') or payload.get('external', {}).get('url') or block.get('url') or block.get('href') or block.get('url') or '' 
    return url

def get_asset_url(block, ctx):
    url = block if isinstance(block, str) else get_block_url(block)
    src = ctx['assets'].get(url, {}).get('uri', url)
    if src.startswith('file:///'):
        return src.split('file:///', maxsplit = 1)[-1]
    return src.replace('http://', 'https://')

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

def get_page_slug(page_id, ctx, use_page_title_for_missing_slug = False, only_slug = False):
    page_id_no_dashes = page_id.replace('-', '')
    page_title_slug = slugify(get_page_title(ctx.get('id2block', {}).get(page_id), ctx)) or page_id_no_dashes
    return ctx.get('slugs', {}).get(page_id) or ctx.get('slugs', {}).get(page_id_no_dashes) or (None if only_slug else (page_title_slug if use_page_title_for_missing_slug else page_id_no_dashes))

def get_heading_slug(block, ctx, space = '-', lower = True, prefix = ''):
    s = richtext2html(block, ctx, rich_text = True, title_mode = True)
    if ctx['extract_mode'] in extract_mode_single:
        page_block = get_page_current(block, ctx)
        page_slug = get_page_slug(page_block.get('id', ''), ctx)
        prefix = page_slug + '-'
    
    s = slugify(s, space = space, lower = lower)
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
            if (block.get('type') or block.get('object')) in ['page', 'child_page']:
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
        id2block[top.get('id', '')] = top
        stack.extend(top.get('blocks', []) + top.get('children', []))
    id2block_no_dashes = {block_id.replace('-', '') : block for block_id, block in id2block.items()}
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
            stack.extend(reversed(top.get('blocks', []) + top.get('children', [])))
    return headings

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
    return ([i for i, u in enumerate(urlset) if u['id'] == id or u['id'].replace('-', '') == id] or [-1])[0]

def sitemap_urlset_update(urlset, id, loc, locrel = ''):
    k = sitemap_urlset_index(urlset, id)
    if k == -1:
        urlset.append({})
    urlset[k].update(dict(id = id, loc = loc, locrel = locrel))
    return urlset

def pop_and_replace_child_pages_recursively(block, child_pages_by_parent_id = {}, parent_id = None):
    block_type = get_block_type(block)
    if block_type in ['page', 'child_page']:
        if block.get('id') not in child_pages_by_parent_id:
            child_pages_by_parent_id[block.get('id')] = [] 
    for key in ['children', 'blocks']:
        for i in reversed(range(len(block[key]) if block.get(key, []) else 0)):
            subblock_type = get_block_type(block[key][i])
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

def discover_assets(blocks, asset_urls = [], exclude_datauri = True, block_types = []):
    for block in blocks:
        for key in ['children', 'blocks']:
            if block.get(key, []):
                discover_assets(block[key], asset_urls = asset_urls, exclude_datauri = exclude_datauri, block_types = block_types)
        block_type = get_block_type(block)
        urls = [
            get_block_url(block.get('cover') or {}),
            get_block_url(block.get('icon') or {})
        ]
        
        url = get_block_url(block)
        if block_type in block_types:
            urls.append(url)
        asset_urls.extend( url for url in urls if url and (exclude_datauri is False or not url.startswith('data:')) )
    return asset_urls

def download_assets(blocks, mimedb = {'.gif' : 'image/gif', '.jpg' : 'image/jpeg', '.jpeg' : 'image/jpeg', '.png' : 'image/png', '.svg' : 'image/svg+xml', '.webp': 'image/webp', '.pdf' : 'application/pdf', '.txt' : 'text/plain'}, mimedefault = 'application/octet-stream', block_types = []):
    urls = discover_assets(blocks, [], exclude_datauri = False, block_types = block_types)
    notion_assets = {} 
    for url in urls:
        ok = True
        if url.startswith('data:'):
            ext = ([k for k, v in mimedb.items() if url.startswith('data:' + v)] or ['.' + url.split(';', maxsplit = 1)[0].replace('/', '_')])[0]
            basename = 'datauri'
            path = url
            datauri = url
        else:
            # url sanitization is non-trivial https://github.com/python/cpython/pull/103855#issuecomment-1906481010, a basic hack below, for proper punycode support need requests module instead
            urlparsed = urllib.parse.urlparse(url)
            try:
                urlparsed.query.encode('ascii')
                urlparsed_query = urlparsed.query
            except UnicodeEncodeError:
                urlparsed_query = urllib.parse.quote(urlparsed.query)
            urlparsed_unicode_sanitized_query = urllib.parse.ParseResult(urlparsed.scheme, urlparsed.netloc, urlparsed.path, urlparsed.params, urlparsed_query, urlparsed.fragment)
            urlopen_url = urllib.parse.urlunparse(urlparsed_unicode_sanitized_query)
            ext = os.path.splitext(urlparsed.path.lower())[-1]
            basename = os.path.basename(urlparsed.path)
            path = urlparsed.scheme + '://' + urlparsed.netloc + urlparsed.path
            mime = mimedb.get(ext, mimedefault)
            file_bytes = b''
            try:
                print(url, urlopen_url)
                file_bytes = urllib.request.urlopen(urlopen_url).read()
            except Exception as exc: # urllib.error.HTTPError is first effort, but url encoding is UnicodeEncodeError
                print(f'cannot download [{basename}] from link {url}, unparsed {urlopen_url}', exc)
                file_bytes = str(exc).encode()
                mime = 'text/plain'
                ok = False
            datauri = f'data:{mime};base64,' + base64.b64encode(file_bytes).decode()
        sha1 = hashlib.sha1()
        sha1.update(path.encode())
        url_hash = sha1.hexdigest()
        basename_hashed = basename + '.' + url_hash + ext
        notion_assets[url] = dict(basename = basename, basename_hashed = basename_hashed, uri = datauri, ok = ok)
        print(url, basename, basename_hashed, ok)
    return notion_assets

def prepare_and_extract_assets(notion_pages, ctx, assets_dir, notion_assets = {}, extract_assets = False, block_types = []):
    urls = discover_assets(notion_pages.values(), [], block_types = block_types)
    print('\n'.join('URL ' + url for url in urls), file = ctx['log_urls_file'])
    assets = {url : notion_assets[url] for url in set(urls) & notion_assets.keys()}
    if extract_assets and assets:
        os.makedirs(assets_dir, exist_ok = True)
        print(assets_dir)
        for asset in assets.values():
            asset_path = os.path.join(assets_dir, asset['basename_hashed'])
            with open(asset_path, 'wb') as f:
                f.write(base64.b64decode(asset['uri'].split('base64,', maxsplit = 1)[-1].encode()))
            #asset['uri'] = 'file:///' +  '/'.join(asset_path.split(os.path.sep))
            asset['uri'] = 'file:///./' + os.path.sep.join(asset_path.split(os.path.sep)[-2:])
            print(asset_path)
    return assets

def slugify(s, space = '_', lower = True):
    s = unicodedata.normalize('NFKC', s)
    s = s.strip()
    s = re.sub(r'\s', space, s, flags = re.U)
    s = re.sub(r'[^-_\w]', space, s, flags = re.U)
    s = s.lower() if lower else s
    return s

def block2(block, ctx = {}, block2render = {}, block2render_with_begin_end = {}, begin = False, end = False, newline = '', **kwargs):
    # https://developers.notion.com/reference/block
    block_type = get_block_type(block)
    if block_type in block2render_with_begin_end:
        return block2render_with_begin_end[block_type](block, ctx, begin = begin, end = end, **kwargs) + newline
    if block_type not in block2render or block_type == 'unsupported':
        block_type = 'unsupported'
        parent_block = get_page_current(block, ctx)
        print('UNSUPPORTED block: block_type=[{block_type}] block_id=[{block_id}] block_type_parent=[{block_type_parent}] block_id_parent=[{block_id_parent}] title_parent=[{title_parent}]'.format(block_type = get_block_type(block), block_id = block.get('id', ''), block_type_parent = parent_block.get('type', '') or parent_block.get('object', ''), block_id_parent = parent_block.get('id', ''), title_parent = get_page_title(parent_block, ctx)), file = ctx['log_unsupported_blocks_file'])
    return block2render[block_type](block, ctx, **kwargs) + newline

##############################

def extractall(
    output_path, 
    ctx,
    theme,
    page_ids = [], 
    notion_pages = {}, 
    notion_pages_flat = {}, 
    snippets = {}
):
    ext = os.path.splitext(ctx['extract_mode'])[-1]
    notion_assets = ctx.get('assets', {})
    index_html = ctx.get('extract_mode') in extract_mode_index_html
    
    assets_dir = os.path.join(output_path, 'assets') if ctx['extract_mode'] in extract_mode_flat[:-1] else None

    if ctx['extract_mode'] in extract_mode_single:
        notion_assets_for_blocks = prepare_and_extract_assets(ctx['pages'], ctx, assets_dir = assets_dir or (output_path + '_files'), notion_assets = notion_assets, extract_assets = ctx['extract_assets'], block_types = ctx['download_assets_block_types'])
        if ext == '.md':
           notionstr = theme.sitepages2markdown(page_ids, ctx = dict(ctx, assets = notion_assets_for_blocks), notion_pages = notion_pages_flat, block2markdown = block2markdown, snippets = snippets)
        if ext == '.html':
           notionstr = theme.sitepages2html(page_ids, ctx = dict(ctx, assets = notion_assets_for_blocks), notion_pages = notion_pages_flat, block2html = block2html, snippets = snippets)
        if ext == '.json':
            notionjson = dict(
                pages = {page_id : page for page_id, page in (notion_pages if ctx['extract_mode'] == 'single.json' else notion_pages_flat).items() if page_id in page_ids}, 
                assets = notion_assets_for_blocks,
                unix_seconds_downloaded = ctx.get('unix_seconds_downloaded', 0),
            )
            notionstr = json.dumps(notionjson, ensure_ascii = False, indent = 4)
        
        for page_id in page_ids:
            page_block = notion_pages_flat[page_id]
            page_url_relative = get_page_url_relative(page_block, ctx)
            page_url_absolute = get_page_url_absolute(page_url_relative, ctx)
            if ctx['sitemap_xml']:
                sitemap_urlset_update(ctx['sitemap'], page_id, loc = page_url_absolute, locrel = page_url_relative)
                sitemap_urlset_write(ctx['sitemap'], ctx['sitemap_xml'])
                print(ctx['sitemap_xml'])
        
        with open(output_path, 'w', encoding = 'utf-8') as f:
            f.write(notionstr)
        return print(output_path)

    os.makedirs(output_path, exist_ok = True)

    for page_id in page_ids:
        page_block = notion_pages_flat[page_id]
        page_url_relative = get_page_url_relative(page_block, ctx)
        page_url_absolute = get_page_url_absolute(page_url_relative, ctx)
        if ctx['sitemap_xml']:
            sitemap_urlset_update(ctx['sitemap'], page_id, loc = page_url_absolute, locrel = page_url_relative)
            sitemap_urlset_write(ctx['sitemap'], ctx['sitemap_xml'])
            print(ctx['sitemap_xml'])

        os.makedirs(output_path, exist_ok = True)
        
        page_slug = get_page_slug(page_id, ctx, use_page_title_for_missing_slug = ctx.get('use_page_title_for_missing_slug'))
        page_nested_dir = os.path.join(output_path, page_slug)
        page_dir = page_nested_dir if (index_html and page_slug != 'index') else output_path
        
        os.makedirs(page_dir, exist_ok = True)
            
        notion_assets_for_block = prepare_and_extract_assets({page_id : page_block}, ctx = ctx, assets_dir = assets_dir or os.path.join(page_dir, page_slug + '_files'), notion_assets = notion_assets, extract_assets = ctx.get('extract_assets', False), block_types = ctx['download_assets_block_types'])
        dump_path = os.path.join(page_dir, 'index.html' if index_html else page_slug + ext)
    
        if ext == '.html':
            notionstr = theme.sitepages2html([page_id], ctx = dict(ctx, assets = notion_assets_for_block), notion_pages = notion_pages_flat, block2html = block2html, snippets = snippets)

        if ext == '.md':
            notionstr = theme.sitepages2markdown([page_id], ctx = dict(ctx, assets = notion_assets_for_block), notion_pages = notion_pages_flat, block2markdown = block2markdown, snippets = snippets)

        if ext == '.json':
            notionjson = dict(
                pages = {page_id : page_block}, 
                assets = notion_assets_for_block, 
                unix_seconds_downloaded = ctx.get('unix_seconds_downloaded', 0)
            )
            notionstr = json.dumps(notionjson, ensure_ascii = False, indent = 4)

        with open(dump_path, 'w', encoding = 'utf-8') as f:
            f.write(notionstr)
        print(dump_path)

def read_and_write_config(config_json, config):
    config_args = config
    config = json.load(open(config_json)) if config_json and os.path.exists(config_json) else {}
    for k, v in config_args.items():
        if (k not in config) or v:
            config[k] = v
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
    download_assets_block_types,
    extract_mode,
    theme_py,
    sitemap_xml,
    snippets_dir,
    base_url,
    edit_url,
    markdown_frontmatter,
    markdown_toc_page,
    use_page_title_for_missing_slug,
    log_unsupported_blocks,
    log_urls,

    toc,
    html_cookies,
    html_details_open,
    html_columnlist_disable,
    html_link_to_page_index_html,
    
    body_header_html,
    body_footer_html,
    article_header_html,
    article_footer_html,
):
    config = read_and_write_config(args.config_json, locals())
    sitemap = sitemap_urlset_read(sitemap_xml) if sitemap_xml else []

    if input_json:
        notionjson = json.load(open(input_json)) if input_json else {}
    else:
        notion_page_ids_no_dashes = [([k for k, v in config.get('slugs', {}).items() if v.lower() == notion_page_id.lower()] or [notion_page_id])[0].replace('-', '') for notion_page_id in notion_page_id]
        notionjson = notionapi_retrieve_page_list(notion_token, notion_page_ids_no_dashes)
    notion_pages = notionjson.get('pages', {})
    notion_assets = notionjson.get('assets', {}) or download_assets(notion_pages.values(), block_types = download_assets_block_types)

    notion_pages = { page_id : page for page_id, page in notion_pages.items() if page['parent']['type'] in ['workspace', 'page_id'] and (page.get('object') or page.get('type')) in ['page', 'child_page'] }
    notion_slugs = config.get('slugs', {})

    notion_pages_flat = copy.deepcopy(notion_pages)
    child_pages_by_parent_id = {}
    for page_id, page in notion_pages_flat.items():
        pop_and_replace_child_pages_recursively(page, child_pages_by_parent_id = child_pages_by_parent_id, parent_id = page_id)
    child_pages_by_id = {child_page['id'] : child_page for pages in child_pages_by_parent_id.values() for child_page in pages}
    notion_pages_flat |= child_pages_by_id
        
    root_page_ids = get_page_ids_normalized(notion_page_id or list(notion_pages.keys()), notion_pages_flat.keys(), notion_slugs)
    page_ids = root_page_ids + [child_page['id'] for page_id in root_page_ids for child_page in child_pages_by_parent_id.get(page_id, []) if child_page['id'] not in root_page_ids]
    assert all(page_id in notion_pages_flat for page_id in root_page_ids)
    
    ext = os.path.splitext(extract_mode)[-1]
    output_path = output_path or ('_'.join(notion_page_id) + ext if extract_mode not in extract_mode_single else (input_json.removesuffix('.json') + ext))

    ctx = config.copy()
    ctx['output_path'] = output_path
    ctx['log_unsupported_blocks_file'] = open(log_unsupported_blocks if log_unsupported_blocks else os.devnull , 'w')
    ctx['log_urls_file'] = open(log_urls if log_urls else os.devnull , 'w')
    ctx['sitemap'] = sitemap
    ctx['assets'] = notion_assets
    ctx['unix_seconds_downloaded'] = notionjson.get('unix_seconds_downloaded', 0)
    ctx['unix_seconds_generated'] = int(time.time())
    ctx['pages'] = notion_pages_flat
    ctx['page_ids'] = page_ids
    ctx['child_pages_by_parent_id'] = child_pages_by_parent_id
    ctx['id2block'] = get_block_index(ctx)
    ctx['page_parent_paths'] = get_page_parent_paths(notion_pages_flat, ctx)

    try:
        theme = importlib.import_module(os.path.splitext(theme_py)[0])
    except:
        assert os.path.isfile(theme_py)
        sys.path.append(os.path.dirname(theme_py))
        theme = importlib.import_module(os.path.splitext(theme_py)[0])

    snippets = read_snippets(snippets_dir, snippets_extra_paths = dict(
        body_header_html    = body_header_html   ,
        body_footer_html    = body_footer_html   ,
        article_header_html = article_header_html,
        article_footer_html = article_footer_html,
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
    bookmark = bookmark2html,
    breadcrumb = breadcrumb2html,
    bulleted_list_item = bulleted_list_item2html,
    callout = callout2html,
    child_database = child_database2html,
    child_page = child_page2html,
    code = code2html,
    column_list = column_list2html, column = column2html,
    divider = divider2html,
    embed = embed2html,
    equation = equation2html,
    file = file2html,
    heading_1 = heading_12html, heading_2 = heading_22html, heading_3 = heading_32html,
    image = image2html,
    link_preview = link_preview2html,
    mention = mention2html,
    numbered_list_item = numbered_list_item2html,
    paragraph = paragraph2html,
    pdf = pdf2html,
    quote = quote2html,
    synced_block = synced_block2html,
    table = table2html,
    table_of_contents = table_of_contents2html,
    template = template2html,
    to_do = to_do2html,
    toggle = toggle2html,
    video = video2html,

    link_to_page = link_to_page2html,
    page = page2html,
    unsupported = unsupported2html,
)
html_block2render_with_begin_end = dict(
    numbered_list_item = numbered_list_item2html, 
    bulleted_list_item = bulleted_list_item2html
)

markdown_block2render = dict(
    bookmark = bookmark2markdown, 
    breadcrumb = breadcrumb2markdown,
    bulleted_list_item = bulleted_list_item2markdown, 
    callout = callout2markdown, 
    child_database = child_database2markdown,
    child_page = child_page2markdown,
    code = code2markdown, 
    column_list = column_list2markdown, column = column2markdown, 
    divider = divider2markdown, 
    embed = embed2markdown, 
    equation = equation2markdown, 
    file = file2markdown, 
    heading_1 = heading_12markdown, heading_2 = heading_22markdown, heading_3 = heading_32markdown, 
    image = image2markdown,
    link_preview = link_preview2markdown,
    mention = mention2markdown,
    numbered_list_item = numbered_list_item2markdown, 
    paragraph = paragraph2markdown, 
    pdf = pdf2markdown, 
    quote = quote2markdown, 
    synced_block = synced_block2markdown,
    table = table2markdown, 
    table_of_contents = table_of_contents2markdown, 
    template = template2markdown,
    to_do = to_do2markdown, 
    toggle = toggle2markdown, 
    video = video2markdown, 
    
    link_to_page = link_to_page2markdown, 
    page = page2markdown,
    unsupported = unsupported2markdown,
)
markdown_block2render_with_begin_end = {}

def block2html(block, ctx = {}, begin = False, end = False, **kwargs):
    return block2(block, ctx, block2render = html_block2render, block2render_with_begin_end = html_block2render_with_begin_end, begin = begin, end = end, **kwargs)

def block2markdown(block, ctx = {}, begin = False, end = False, **kwargs):
    return block2(block, ctx, block2render = markdown_block2render, block2render_with_begin_end = markdown_block2render_with_begin_end, begin = begin, end = end, **kwargs)

##############################

extract_mode_single = ['single.html', 'single.md', 'single.json']
extract_mode_flat = ['flat.html', 'flat.md', 'flat.json', 'flat/index.html']
extract_mode_json = ['flat.json',  'single.json']
extract_mode_index_html = ['flat/index.html']

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--config-json')
    parser.add_argument('--input-json', '-i')
    parser.add_argument('--output-path', '-o')
    parser.add_argument('--notion-token', default = os.getenv('NOTION_TOKEN', ''))
    parser.add_argument('--notion-page-id', nargs = '*', default = [])
    parser.add_argument('--theme-py', default = 'minima.py')
    parser.add_argument('--extract-mode', default = 'single.html', choices = extract_mode_single + extract_mode_flat)
    parser.add_argument('--snippets-dir')
    parser.add_argument('--sitemap-xml')
    parser.add_argument('--base-url')
    parser.add_argument('--edit-url')
    parser.add_argument('--log-unsupported-blocks')
    parser.add_argument('--log-urls')
    parser.add_argument('--download-assets-block-types', nargs = '*', choices = ['image', 'video', 'pdf', 'file'], default = ['image'])
    parser.add_argument('--extract-assets', action = 'store_true')
    parser.add_argument('--use-page-title-for-missing-slug', action = 'store_true')
    parser.add_argument('--toc', action = 'store_true')
    parser.add_argument('--markdown-frontmatter', action = 'store_true')
    parser.add_argument('--markdown-toc-page')
    parser.add_argument('--html-cookies', action = 'store_true')
    parser.add_argument('--html-details-open', action = 'store_true')
    parser.add_argument('--html-columnlist-disable', action = 'store_true')
    parser.add_argument('--html-link-to-page-index-html', action = 'store_true')
    parser.add_argument('--body-header-html')
    parser.add_argument('--body-footer-html')
    parser.add_argument('--article-header-html')
    parser.add_argument('--article-footer-html')
    args = parser.parse_args()
    print(args)

    #notionjson2html : assert args.input_json
    #notionapi2notionjson: assert args.notion_page_id
    if args.extract_mode in extract_mode_json or (os.path.exists(args.input_json) and os.path.isfile(args.input_json)):
        notion2static(**vars(args))

    elif os.path.exists(args.input_json) and os.path.isdir(args.input_json):
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
