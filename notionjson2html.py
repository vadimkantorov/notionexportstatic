# TODO: flatten child pages and include them
# TODO: put all json props as html attributes
# TODO: embed resources by default
# TODO: add basic fixed top nav which should also work for single-page
# TODO: for multi-article add TOC and generation date
# TODO: support recursive conversion of all json to html? or maybe example with find -exec?
# TODO: for a single or nested mode, what to do with unresolved link_to_pages? extend slug.json info? or scan the current directory?
# TODO: fix links in flat/nested mode
# TODO: basename -> urlparse
# https://docs.super.so/super-css-classes

import os
import json
import base64
import argparse
import urllib.parse

def richtext2html(richtext, title_mode=False) -> str:
    # https://www.notion.so/help/customize-and-style-your-content#markdown
    if isinstance(richtext, list):
        return ''.join(richtext2html(r, title_mode) for r in richtext).strip()
    code = lambda content: f'<code>{content}</code>'
    color = lambda content, color: f'<span style="color:{color}">{content}</span>'
    equation = lambda content: f'<code data-equation=1>{content}</code>'
    user = lambda kwargs: f'({kwargs["content"]})'
    date = lambda kwargs: f'({kwargs["content"]})'
    italic = lambda content: f'<i>{content}</i>'
    strikethrough = lambda content: f'<s>{content}</s>'
    underline = lambda content: f'<u>{content}</u>'
    bold = lambda content: content if ((not content) or content.isspace()) else  (content[0] * (bool(content) and content[0].isspace())) + f' <b>{content.strip()}</b> '
    _mention_link = lambda content, url: ('<a href="{url}" target="_blank"> <i class="fa fa-lg fa-github"> </i> {repo} </a>' if "https://github.com/" in url else '<a href="{url}">{content}</a>').format(repo = os.path.basename(url), url = url, content = content)
    page = lambda kwargs: _mention_link(kwargs['content'], kwargs['url'])
    link_preview = lambda kwargs: _mention_link(kwargs['content'], kwargs['url'])
    mention_kwargs = lambda payload: {'content' : payload['plain_text']} if not payload['href'] else {'url': payload['href'], 'content': payload['plain_text'] if payload['plain_text'] != 'Untitled' else payload['href']}
    text_link = lambda kwargs: '<a href="{url}">{caption}</a>'.format(caption = kwargs['content'], url = kwargs['link']['url'])
    #TODO: format link to page
    #"toggle": {
    # "rich_text": [
    #     {
    #         "type": "text",
    #         "text": {
    #             "content": "LGBTQI+",
    #             "link": {
    #                 "url": "/e924e4c97ced46d48e7bfe0c177d13c0"
    #             }
    #         },
    database = lambda kwargs: _mention_link(kwargs['content'], kwargs['url'])
    annotation_map = dict(bold = bold, italic = italic, strikethrough = strikethrough, underline = underline, code = code)
    mention_map = dict(user = user, page = page, database = database, date = date, link_preview = link_preview)
    outcome_word = ''
    plain_text = richtext['plain_text']
    if richtext['type'] == 'equation':
        outcome_word = equation(plain_text)
        if title_mode:
            return outcome_word
    elif richtext['type'] == 'mention':
        mention_type = richtext['mention']['type']
        if mention_type in mention_map:
            outcome_word = mention_map[mention_type](mention_kwargs(richtext))
    else:
        if title_mode:
            return plain_text
        if 'href' in richtext:
            if richtext['href']:
                outcome_word = text_link(richtext['text'])
            else:
                outcome_word = plain_text
        else:
            outcome_word = plain_text
        annot = richtext['annotations']
        for key, transfer in annotation_map.items():
            if richtext['annotations'][key]:
                outcome_word = transfer(outcome_word)
        if annot['color'] != 'default':
            outcome_word = color(outcome_word, annot['color'])
    return outcome_word

def notionattrs2html(block, ctx = {}, used_keys = [], class_name = '', attrs = {}):
    used_keys_ = used_keys
    used_keys, used_keys_nested1, used_keys_nested2 = [k for k in used_keys if k.count('-') == 0], [tuple(k.split('-')) for k in used_keys if k.count('-') == 1], [tuple(k.split('-')) for k in used_keys if k.count('-') == 2]

    #TODO: add used_keys_nested2 for block_type
    #default_annotations = dict(bold = False, italic = False, strikethrough = False, underline = False, code = False, color = "default")

    keys = ['object', 'id', 'created_time', 'last_edited_time', 'archived', 'type', 'has_children', 'url', 'public_url', 'request_id'] 
    keys_nested1 = [('created_by', 'object'), ('created_by', 'id'), ('last_edited_by', 'object'), ('last_edited_by', 'id'), ('parent', 'type'), ('parent', 'workspace'), ('parent', 'page_id'), ('parent', 'block_id')] 

    keys_extra = [k for k in block.keys() if k not in keys and k not in used_keys if not isinstance(block[k], dict)] + [f'{k1}-{k2}' for k1 in block.keys() if isinstance(block[k1], dict) for k2 in block[k1].keys() if (k1, k2) not in keys_nested1 and (k1, k2) not in used_keys_nested1]
    
    html_attrs = ' ' + ' '.join(f'{k}="{v}"' for k, v in attrs.items()) + ' '

    if keys_extra:
        print(block.get('type') or block.get('object'), ';'.join(keys_extra))
    
    res = ' data-block-id="{id}" '.format(id = block.get('id', '')) + (f' class="{class_name}" ' if class_name else '') + html_attrs
    keys.remove('id')

    if ctx['notion_attrs_verbose'] is True:
        res += ' '.join('{kk}="{v}"'.format(kk = keys_alias.get(k, 'data-notion-' + k), v = block[k]) for k in keys if k in block) + ' ' + ' '.join('data-notion-{k1}-{k2}="{v}"'.format(k1 = k1, k2 = k2, v = block[k1][k2]) for k1, k2 in keys_nested1 if k1 in block and k2 in block[k1]) + (' data-notion-extrakeys="{}"'.format(';'.join(keys_extra)) if keys_extra else '') + ' '

    return res

def open_tag(block, ctx, class_name = '', tag = '', used_keys = [], attrs_kwargs = {}):
    return (f'<{tag}' + notionattrs2html(block, ctx, class_name = class_name, used_keys = used_keys, **attrs_kwargs) + '>\n') if tag else ''

def close_tag(tag = ''):
    return f'</{tag}>\n' if tag else ''

def children_like(block, ctx, key = 'children', tag = ''):
    html = ''
    subblocks = block.get(key, [])
    for i, subblock in enumerate(subblocks):
        same_block_type_as_prev = i > 0 and subblock.get('type') == subblocks[i - 1].get('type')
        same_block_type_as_next = i + 1 < len(subblocks) and subblock.get('type') == subblocks[i + 1].get('type')
        html += ((f'<{tag}>') if tag else '') + block2html(subblock, ctx, begin = not same_block_type_as_prev, end = not same_block_type_as_next) + (f'</{tag}>\n' if tag else '')
    return html

def text_like(block, ctx, block_type, tag, used_keys = [], attrs = {}, class_name = ''):
    color = block[block_type].get('color', '')
    return f'<{tag}' + notionattrs2html(block, ctx, class_name = class_name + f' notion-color-{color}', attrs = attrs, used_keys = ['children', block_type + '-text', block_type + '-rich_text', block_type + '-color'] + used_keys) + '>' + richtext2html(block[block_type].get('text') or block[block_type].get('rich_text') or []) + children_like(block, ctx) + f'</{tag}>\n'

def toggle_like(block, ctx, block_type, tag, attrs = {}, class_name = ''):
    html_text = richtext2html(block[block_type].get('text') or block[block_type].get('rich_text') or [])
    color = block[block_type].get('color', '')
    html_details_open = ['', 'open'][ctx['html_details_open']]
    class_name_summary = ' red' if ' red' in class_name else ''
    class_name = class_name.replace(' red', '')
    return f'<details {html_details_open}' + notionattrs2html(block, ctx, class_name = class_name + f' notion-color-{color}', attrs = attrs, used_keys = ['children', block_type + '-text', block_type + '-rich_text', block_type + '-color', block_type + '-is_toggleable']) + f'><summary class="{class_name_summary}"><{tag}>{html_text}</{tag}></summary>\n' + children_like(block, ctx) + '</details>\n'

def heading_like(block, ctx, block_type, tag, class_name = ''):
    has_several_parts = len(block[block['type']].get('text', []) or block[block['type']].get('rich_text', [])) > 1
    if has_several_parts:
        class_name += ' red'

    if block.get(block_type, {}).get('is_toggleable') is not True: 
        return text_like(block, ctx, block_type, tag, used_keys = [block_type + '-is_toggleable'], attrs = dict(id = block['id']), class_name = class_name)
    else:
        return toggle_like(block, ctx, block_type, tag, attrs = dict(id = block['id']), class_name = class_name)

def link_like(block, ctx, tag = 'a', class_name = '', full_url_as_caption = False):
    block_type = block.get('type', '')
    assert block[block_type].get('type') in ['file', 'external', None]
    src = block[block_type].get('file', {}).get('url') or block[block_type].get('external', {}).get('url') or block[block_type].get('url') or ''
    html_text = richtext2html(block[block_type].get('caption', [])) or block[block_type].get('name') or (src if full_url_as_caption else os.path.basename(src)) #TODO: urlquote?
    html = f'<{tag}' + notionattrs2html(block, ctx, class_name = class_name, used_keys = [block_type + '-name', block_type + '-url', block_type + '-caption', block_type + '-type', block_type + '-file', block_type + '-external']) + f' href="{src}">📎 {html_text}</{tag}><br />\n'
    return html

def page_like(block, ctx, tag = 'article', class_name = 'notion-page-block'):
    icon_type = block['icon'].get('type') #TODO: for child_page depends on pop_and_replace_child_pages_recursively
    icon_emoji = block['icon'].get('emoji', '')
    cover_type = block.get('cover', {}).get('type')
    src = block.get('cover', {}).get('file', {}).get('url', '')
    src = ctx['assets'].get(src, {}).get('uri', src)

    page_title = ' '.join(t['plain_text'] for t in block.get("properties", {}).get("title", {}).get("title", [])) if len(block.get("properties",{}).get('title', {}).get('title', [])) > 0 else (block.get('child_page', {}).get('title') or block.get('title', ''))
    
    link_to_page_page_id = block.get('id', '')
    slug = ctx['notion_slugs'].get(link_to_page_page_id) or ctx['notion_slugs'].get(link_to_page_page_id.replace('-', '')) or link_to_page_page_id.replace('-', '')
    
    html = f'<{tag} class="post" id="{slug}" ' + notionattrs2html(block, ctx, class_name = '', used_keys = ['id', 'blocks', 'icon-type', 'icon-emoji', 'cover-type', 'cover-file', 'properties-title', 'children', 'title', 'child_page-title']) + f'><header class="post-header"><img src="{src}"></img><h1 class="notion-record-icon">{icon_emoji}</h1><h1 class="post-title {class_name}">{page_title}</h1></header><div class="post-content">\n'
    html += children_like(block, ctx, key = 'blocks' if 'blocks' in block else 'children')
    html += '\n' + f'</div></{tag}>\n'
    return html



def table_of_contents(block, ctx, tag = 'ul', class_name = 'notion-table_of_contents-block'):
    # https://www.notion.so/help/columns-headings-and-dividers#how-it-works
    id2block = {}
    stack = list(ctx['pages'].values())
    while stack:
        top = stack.pop()
        id2block[top.get('id')] = top
        stack.extend(top.get('blocks', []) + top.get('children', []))

    parent_block = block
    while (parent_block.get('type') or parent_block.get('object')) not in ['page', 'child_page']:
        parent_id = parent_block['parent'].get(parent_block['parent'].get('type'))
        if parent_id not in id2block:
            break
        parent_block = id2block[parent_id]

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
    html = f'<{tag}' +  notionattrs2html(block, ctx, class_name = class_name + f' notion-color-{color}', used_keys = ['table_of_contents-color']) + '/>\n'
    
    inc_heading_type = dict(heading_0 = 'heading_1', heading_1 = 'heading_2', heading_2 = 'heading_3', heading_3 = 'heading_3').get
    nominal_heading_type, effective_heading_type = 'heading_0', 'heading_0'
    for block in headings:
        block_id = block['id']
        heading_type = block.get('type', '')
        nominal_heading_type, effective_heading_type = heading_type, min(heading_type, inc_heading_type(effective_heading_type) if heading_type > nominal_heading_type else effective_heading_type)
        html_text = richtext2html(block[block.get('type')].get('text') or block[block.get('type')].get('rich_text') or [], title_mode = True)
        html += f'<li class="notion-table_of_contents-heading notion-table_of_contents-{effective_heading_type}"><a href="#{block_id}">' + html_text + '</a></li>\n'

    html += f'</{tag}>\n'
    return html

def link_to_page(block, ctx, tag = 'a', suffix_html = '<br/>', class_name = 'notion-alias-block'):
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

    cur_page_id = parent_block['id']
    curslug = ctx['notion_slugs'].get(cur_page_id) or ctx['notion_slugs'].get(cur_page_id.replace('-', '')) or cur_page_id.replace('-', '')

    link_to_page_page_id = block[link_to_page.__name__].get(block[link_to_page.__name__].get('type'), '')
    
    slug = ctx['notion_slugs'].get(link_to_page_page_id) or ctx['notion_slugs'].get(link_to_page_page_id.replace('-', '')) or link_to_page_page_id.replace('-', '')

    href = '#404'
    is_index_page = curslug == 'index'
    url_suffix = '/index.html'.lstrip('/' if slug == 'index' else '') if args.html_link_to_page_index_html else ''
    if ctx['extract_html'] == 'single':
        if link_to_page_page_id in ctx['page_ids']:
            href = '#' + slug 
        else:
            #TODO: find the page path in relation to the current path, need to know flat or flat.html
            #TODO: allow passing url-style explicitly, if not set, detect if slug.html or if /slug/ exists already and maybe have some url-style as default
            href = './' + slug + url_suffix
    elif ctx['extract_html'] == 'flat':
        href = ('./' if is_index_page else '../') + ('' if slug == 'index' else slug) + url_suffix

    
    subblock = id2block.get(link_to_page_page_id) 
    if subblock:
        page_title = ' '.join(t['plain_text'] for t in subblock.get("properties", {}).get("title", {}).get("title", [])) if len(subblock.get("properties",{}).get('title', {}).get('title', [])) > 0 else (subblock.get('child_page', {}).get('title') or subblock.get('title', ''))
        icon_emoji = subblock.get('icon', {}).get('emoji', '')
        caption = f'{icon_emoji} {page_title}' #TODO: html.escape()
    else:
        caption = f'title of linked page [{link_to_page_page_id}] not found'

    return f'<{tag} href="{href}"' + notionattrs2html(block, ctx, class_name = class_name, used_keys = [link_to_page.__name__ + '-type', link_to_page.__name__ + '-page_id']) + f'>{caption}</{tag}>{suffix_html}\n'

def table(block, ctx, tag = 'table', class_name = 'notion-table-block'):
    #TODO: headers: table_width, row-header, column-header
    table_width = block[table.__name__].get('table_width')
    has_row_header = block[table.__name__].get('has_row_header')
    has_column_header = block[table.__name__].get('has_column_header')
    html = f'<{tag}' + notionattrs2html(block, ctx, class_name = class_name, used_keys = ['children', 'table-table_width', 'table-has_column_header', 'table-has_row_header']) + '>\n'
    for subblock in block.get('children', []):
        html += '<tr>\n'
        for cell in subblock.get('table_row', {}).get('cells', []):
            html += '<td>' + (''.join('<div>{html}</div>'.format(html = richtext2html(subcell)) for subcell in cell) if isinstance(cell, list) else richtext2html(cell)) + '</td>\n'
        html += '</tr>\n'
    html += f'</{tag}>\n'
    return html

def page(block, ctx, tag = 'article', class_name = 'notion-page-block'):
    return page_like(block, ctx, tag = tag, class_name = class_name)

def child_page(block, ctx, tag = 'article', class_name = 'notion-page-block'):
    return page_like(block, ctx, tag = tag, class_name = class_name)

def column_list(block, ctx, tag = 'div', class_name = 'notion-column_list-block'):
    return f'<{tag}' + notionattrs2html(block, ctx, class_name = class_name + ' notion_column_list-block-vertical' * ctx['html_columnlist_disable'], used_keys = ['children']) + '>\n' + children_like(block, ctx) + f'</{tag}>\n'

def column(block, ctx, tag = 'div', class_name = 'notion-column-block'):
    return f'<{tag}' + notionattrs2html(block, ctx, class_name = class_name, used_keys = ['children']) + '>\n' + children_like(block, ctx, tag = tag) + f'</{tag}>\n'

def video(block, ctx, tag = 'p', class_name = 'notion-video-block'):
    caption = richtext2html(block[video.__name__].get('caption', []))
    src = block[video.__name__].get(block[video.__name__]['type'], {}).get('url', '')
    is_youtube = 'youtube.com' in src
    src = src.replace("http://", "https://").replace('/watch?v=', '/embed/').split('&')[0] if is_youtube else src
    
    html = f'<{tag}' + notionattrs2html(block, ctx, class_name = class_name, used_keys = [video.__name__ + '-caption', video.__name__ + '-type', video.__name__ + '-external', video.__name__ + '-external-url']) + '>'
    if is_youtube:
        html += f'<div class="res_emb_block"><iframe width="640" height="480" src="{src}" frameborder="0" allowfullscreen></iframe></div>'
    else:
        html += f'<video playsinline autoplay muted loop controls src="{src}"></video>'
    html += f'</{tag}>\n'
    return html

def image(block, ctx, tag = 'img', class_name = 'notion-image-block'):
    #TODO: fixup url from assets
    #TODO: when to embed image
    assert block['image']['type'] in ['file', 'external']
    src = block['image'].get('file', {}).get('url') or block['image'].get('external', {}).get('url') or ''
    src = ctx['assets'].get(src, {}).get('uri', src)
    if src.startswith('file:///'):
        src = src.split('file:///', maxsplit = 1)[-1]
    html_text = richtext2html(block['image']['caption']) # TODO: html.escape, TODO: figure
    html = f'<{tag}' + notionattrs2html(block, ctx, class_name = class_name, used_keys = ['image-caption', 'image-type', 'image-file', 'image-external']) + f' src="{src}"></{tag}><div>{html_text}</div>\n'
    return html

def callout(block, ctx, tag = 'p', class_name = 'notion-callout-block'):
    icon_type = block[callout.__name__].get('icon', {}).get('type')
    icon_emoji = block[callout.__name__].get('icon', {}).get('emoji', '')
    color = block[callout.__name__].get('color', '')
    return f'<div' + notionattrs2html(block, ctx, class_name = class_name + f' notion-color-{color}', used_keys = [callout.__name__ + '-icon', callout.__name__ + '-color', callout.__name__ + '-rich_text', 'children']) + f'><div>{icon_emoji}</div><div>\n' + text_like(block, ctx, block_type = callout.__name__, tag = tag, used_keys = [callout.__name__ + '-icon']) + '\n</div></div>\n'

def embed(block, ctx, tag = 'iframe', class_name = 'notion-embed-block'):
    block_type = block.get('type', '')
    link_type = block[block_type].get('type', '')
    src = block[block_type].get('url') or block[block_type].get(link_type, {}).get('url') or ''
    html_text = richtext2html(block.get(block_type, {}).get('caption', [])) 
    return f'<{tag}' + notionattrs2html(block, ctx, class_name = class_name, used_keys = [block_type + '-caption', block_type + '-url', block_type + '-type', block_type + '-' + link_type]) + f' src="{src}"></{tag}><div>{html_text}</div>\n'

def pdf(block, ctx, tag = 'a', class_name = 'notion-pdf-block'):
    return link_like(block, ctx, tag = tag, class_name = class_name) + embed(block, ctx)

def file(block, ctx, tag = 'a', class_name = 'notion-file-block'):
    return link_like(block, ctx, tag = tag, class_name = class_name)

def bookmark(block, ctx, tag = 'a', class_name = 'notion-bookmark-block'):
    # TODO: generate social media card: title, maybe description, favicon
    return link_like(block, ctx, tag = tag, class_name = class_name, full_url_as_caption = True)

def paragraph(block, ctx, tag = 'p', class_name = 'notion-text-block'):
    if block.get('has_children') is False and not (block[block['type']].get('text') or block[block['type']].get('rich_text')):
        return '<br ' + notionattrs2html(block, ctx, class_name = class_name, used_keys = ['children', paragraph.__name__ + '-text', paragraph.__name__ + '-rich_text', paragraph.__name__ + '-color']) + '/>\n'
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
    return f'<{tag}' + notionattrs2html(block, ctx, class_name = class_name) + '/>\n'

def bulleted_list_item(block, ctx, tag = 'ul', begin = False, end = False, class_name = 'notion-bulleted_list-block'):
    return (f'<{tag} class="{class_name}">\n' if begin else '') + text_like(block, ctx, block_type = bulleted_list_item.__name__, tag = 'li') + ('\n' + f'</{tag}>\n' if end else '')

def numbered_list_item(block, ctx, tag = 'ol', begin = False, end = False, class_name = 'notion-numbered_list-block'):
    return (f'<{tag} class="{class_name}">\n' if begin else '') + text_like(block, ctx, block_type = numbered_list_item.__name__, tag = 'li') + ('\n' + f'</{tag}>\n' if end else '')

def code(block, ctx, tag = 'code', class_name = 'notion-code-block'):
    caption = richtext2html(block[code.__name__].get('caption', []))
    language = block[code.__name__].get('language', '')
    return f'<pre><{tag} data-language="{language}"' + notionattrs2html(block, ctx, class_name = class_name, used_keys = [code.__name__ + '-caption', code.__name__ + '-rich_text', code.__name__ + '-language']) + '>\n' + richtext2html(block[code.__name__].get('rich_text', [])) + f'\n</{tag}>\n<div>{caption}</div></pre>\n'

def equation(block, ctx, tag = 'pre', class_name = 'notion-equation-block'):
    expression = block[equation.__name__].get('expression', '')
    return f'<{tag}' + notionattrs2html(block, ctx, class_name = class_name, used_keys = [equation.__name__ + '-expression']) + '>\n{expression}\n</{tag}>\n'

   
def block2html(block, ctx = {}, begin = False, end = False):
    # https://developers.notion.com/reference/block
    block2render = dict(
        bookmark = bookmark,
        #breadcrumb
        bulleted_list_item = bulleted_list_item,
        callout = callout,
        #child_database
        child_page = child_page,
        #code = code,
        column_list = column_list, column = column,
        divider = divider,
        embed = embed,
        #equation = equation,
        file = file,
        heading_1 = heading_1, heading_2 = heading_2, heading_3 = heading_3,
        image = image,
        #link_preview
        #mention
        numbered_list_item = numbered_list_item,
        paragraph = paragraph,
        pdf = pdf,
        quote = quote,
        #synced_block
        table = table,
        table_of_contents = table_of_contents,
        #template
        #to_do
        toggle = toggle,
        video = video,
        
        page = page,
        link_to_page = link_to_page,
    )
    block2render_with_begin_end = dict(
        numbered_list_item = numbered_list_item, 
        bulleted_list_item = bulleted_list_item
    )

    block_type = block.get('type') or block.get('object') or ''
    
    if block_type in block2render_with_begin_end:
        return block2render_with_begin_end[block_type](block, ctx, begin = begin, end = end)
    
    elif block_type in block2render:
        return block2render[block_type](block, ctx)
    else:
        # TODO: print all unsupported to a log? include as comment? or just as element? render children? replace by <!-- --> or maybe "p"?
        return f'\n<{block_type} unsupported="1"' + notionattrs2html(block, ctx) + '/>\n\n'


def pop_and_replace_child_pages_recursively(block, parent_id = None):
    block_type = block.get('type') or block.get('object')
    child_pages = {}
    for keys in ['children', 'blocks']:
        for i in reversed(range(len(block[keys]) if block.get(keys, []) else 0)):
            if block[keys][i]['type'] == 'child_page':
                child_page = block[keys][i]
                if (not child_page.get('icon')) and child_page['has_children'] and child_page['children']:
                    for subblock in child_page['children']:
                        if subblock['type'] == 'callout':
                            child_page['icon'] = dict(emoji = subblock.get('callout', {}).get('icon', {})).get('emoji')
                            break
                parent_id_type = 'page_id' if block_type in ['page', 'child_page'] else 'block_id'
                block[keys][i] = dict(
                    object = 'block', 
                    has_children = False,
                    type = 'link_to_page',
                    link_to_page = dict(type = 'page_id', page_id = child_page['id']),
                    parent = {'type' : parent_id_type, parent_id_type : block['id']}
                )
                child_page['title'] = child_page['child_page']['title']
                child_page['url'] = child_page.get('url', 'https://www.notion.so/' + child_page.get('id', '').replace('-', ''))
                if parent_id not in child_pages:
                    child_pages[parent_id] = []
                child_pages[parent_id].append(child_page)

                for k, l in pop_and_replace_child_pages_recursively(block[keys][i], parent_id = child_page['id']).items():
                    if k not in child_pages:
                        child_pages[k] = []
                    child_pages[k].extend(l)
            else:
                for k, l in pop_and_replace_child_pages_recursively(block[keys][i], parent_id = parent_id).items():
                    if k not in child_pages:
                        child_pages[k] = []
                    child_pages[k].extend(l)
    return child_pages

def discover_assets(blocks, asset_urls = []):
    for block in blocks:
        for keys in ['children', 'blocks']:
            if block.get(keys, []):
                discover_assets(block[keys], asset_urls = asset_urls)
        block_type = block.get('type')
        payload = block.get(block_type, {})
        urls = [block.get('cover', {}).get('file', {}).get('url'), block.get('icon', {}).get('file', {}).get('url')]
        if block_type == 'image' and ('file' in payload or 'external' in payload): # TODO block_type == 'file'
            urls.append(payload.get('url') or payload.get('external', {}).get('url') or payload.get('file', {}).get('url'))
        asset_urls.extend(filter(bool, urls))
    return asset_urls

def prepare_and_extract_assets(notion_pages, assets_dir, notion_assets = {}, extract_assets = False):
    urls = discover_assets(notion_pages.values(), [])
    assets = {url : notion_assets[url] for url in urls}
    # TODO: first load in memory? or copy directly to target dir?
    if extract_assets and assets:
        os.makedirs(assets_dir, exist_ok = True)
        for asset in assets.values():
            asset_path = os.path.join(assets_dir, asset['name'])
            with open(asset_path, 'wb') as f:
                f.write(base64.b64decode(asset['uri'].split('base64,', maxsplit = 1)[-1].encode()))
            asset['uri'] = 'file:///' + asset_path
            print(asset_path)
    return assets

def extract_html_single(output_path, ctx = {}, page_ids = [], child_pages_by_id = {}, extract_assets = False, sitepages2html = (lambda page_ids, ctx, style, notion_pages: '')):
    notion_cache = ctx
    notion_assets = notion_cache.get('assets', {})
    
    notion_cache['pages'].update(child_pages_by_id)
    
    notion_cache['assets'] = prepare_and_extract_assets(notion_pages = notion_cache['pages'], assets_dir = output_path + '_files', notion_assets = notion_assets, extract_assets = extract_assets)
    with open(output_path, 'w', encoding = 'utf-8') as f:
        f.write(sitepages2html(page_ids, ctx = ctx, notion_pages = notion_cache['pages'], block2html = block2html))
    print(output_path)

def extract_html_nested(output_dir, ctx = {}, page_ids = [], child_pages_by_id = {}, extract_assets = False, notion_pages = {}, child_pages_by_parent_id = {}, index_html = False, sitepages2html = (lambda page_ids, ctx, style, notion_pages: '')):
    notion_cache = ctx
    notion_pages = notion_cache['pages'] if notion_pages is not None else {}
    notion_slugs = ctx['notion_slugs']
    notion_assets =  notion_cache.get('assets', {})
    os.makedirs(output_dir, exist_ok = True)
    notion_pages.update(child_pages_by_id)

    for page_id, block in notion_pages.items():
        os.makedirs(output_dir, exist_ok = True)
        slug = notion_slugs.get(page_id) or notion_slugs.get(page_id.replace('-', '')) or page_id.replace('-', '')
        page_dir = os.path.join(output_dir, slug) if index_html and slug != 'index' else output_dir
        os.makedirs(page_dir, exist_ok = True)

        html_path = os.path.join(page_dir, 'index.html' if index_html else slug + '.html')
        assets_dir = os.path.join(page_dir, slug + '_files')
        notion_assets_for_block = prepare_and_extract_assets({page_id : block}, assets_dir = assets_dir, notion_assets = notion_assets, extract_assets = extract_assets)
        ctx['assets'] = notion_assets_for_block
        with open(html_path, 'w', encoding = 'utf-8') as f:
            f.write(sitepages2html([page_id], ctx = ctx, notion_pages = notion_pages, block2html = block2html))
        print(html_path)
        if children := child_pages_by_parent_id.pop(page_id, []):
            extract_html_nested(page_dir, ctx = ctx, notion_assets = notion_assets, notion_pages = {child['id'] : child for child in children}, child_pages_by_parent_id = child_pages_by_parent_id, extract_assets = extract_assets, index_html = index_html)

def main(args):
    output_path = args.output_path if args.output_path else '_'.join(args.notion_page_id)
    
    notion_cache = json.load(open(args.input_path)) if args.input_path else {}
    notion_slugs = json.load(open(args.pages_json)) if args.pages_json else {}

    root_page_ids = args.notion_page_id or list(notion_cache['pages'].keys())
    for i in range(len(root_page_ids)):
        for k, v in notion_slugs.items():
            if root_page_ids[i] == v:
                root_page_ids[i] = k
        for k in notion_cache['pages'].keys():
            if root_page_ids[i] == k.replace('-', ''):
                root_page_ids[i] = k
    # TODO: add error checking that all root_page_ids are found in actual pages and non zero pages
    # TODO:add all child_pages recursively, and not just a single time. should update child_pages always? add special option
    child_pages_by_parent_id = {k: v for page_id, page in notion_cache['pages'].items() for k, v in pop_and_replace_child_pages_recursively(page, parent_id = page_id).items()}
    child_pages_by_id = {child_page['id'] : child_page for pages in child_pages_by_parent_id.values() for child_page in pages}
    page_ids = root_page_ids + [child_page['id'] for page_id in root_page_ids for child_page in child_pages_by_parent_id[page_id] if child_page['id'] not in root_page_ids]

    ctx = notion_cache
    ctx['notion_attrs_verbose'] = args.notion_attrs_verbose
    ctx['html_details_open'] = args.html_details_open
    ctx['html_columnlist_disable'] = args.html_columnlist_disable
    ctx['html_link_to_page_index_html'] = args.html_link_to_page_index_html
    ctx['page_ids'] = page_ids
    ctx['extract_html'] = args.extract_html
    ctx['notion_slugs'] = notion_slugs

    import minima as theme; sitepages2html = theme.sitepages2html

    if args.extract_html == 'single':
        extract_html_single(output_path if args.output_path else output_path + '.html', ctx = ctx, page_ids = page_ids, child_pages_by_id = child_pages_by_id, extract_assets = args.extract_assets, sitepages2html = sitepages2html)

    else:
        extract_html_nested(output_path, ctx = ctx, page_ids = page_ids, child_pages_by_id = child_pages_by_id if args.extract_html in ['flat', 'flat.html'] else {}, extract_assets = args.extract_assets, child_pages_by_parent_id = child_pages_by_parent_id if args.extract_html == 'nested' else {}, index_html = args.extract_html in ['flat', 'nested'], sitepages2html = sitepages2html) #  | child_pages_by_id <- breaks notion_cache in the context and link_to_page resolving


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--input-path', '-i', required = True)
    parser.add_argument('--output-path', '-o')
    parser.add_argument('--pages-json')
    parser.add_argument('--notion-page-id', nargs = '*', default = [])
    parser.add_argument('--notion-attrs-verbose', action = 'store_true')
    parser.add_argument('--html-details-open', action = 'store_true')
    parser.add_argument('--html-columnlist-disable', action = 'store_true')
    parser.add_argument('--html-link-to-page-index-html', action = 'store_true')
    parser.add_argument('--extract-assets', action = 'store_true')
    parser.add_argument('--extract-html', default = 'single', choices = ['single', 'flat', 'flat.html', 'nested'])
    args = parser.parse_args()
    print(args)
    main(args)
