# TODO: add basic CSS: minima?
# TODO: flatten child pages and include them
# TODO: put all json props as html attributes
# TODO: get rid of ctx and global vars
# TODO: embed resources by default
# TODO: add basic fixed top nav which should also work for single-page
# TODO: for multi-article add TOC and generation date
# TODO: support recursive conversion of all json to html? or maybe example with find -exec?
# TODO: for a single or nested mode, what to do with unresolved link_to_pages? extend slug.json info? or scan the current directory?
# TODO: fix links in flat/nested mode

import os
import json
import base64
import argparse
import urllib.parse

def richtext2html(richtext, title_mode=False) -> str:
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

def children_like(block, ctx, key = 'children', tag = ''):
    html = ''
    subblocks = block.get(key, [])
    for i, subblock in enumerate(subblocks):
        same_block_type_as_prev = i > 0 and subblock.get('type') == subblocks[i - 1].get('type')
        same_block_type_as_next = i + 1 < len(subblocks) and subblock.get('type') == subblocks[i + 1].get('type')
        html += ((f'<{tag}>') if tag else '') + block2html(subblock, ctx, begin = not same_block_type_as_prev, end = not same_block_type_as_next) + (f'</{tag}>\n' if tag else '')
    return html

def text_like(block, ctx, block_type, tag, used_keys = []):
    color = block[block_type].get('color', '')
    html = f'<{tag} class="notion-color-{color}"' + notionattrs2html(block, used_keys = ['children', block_type + '-text', block_type + '-rich_text', block_type + '-color'] + used_keys) + '>' 
    html += richtext2html(block[block_type].get('text') or block[block_type].get('rich_text') or [])
    html += children_like(block, ctx)
    html += f'</{tag}>\n'
    return html

def toggle_like(block, ctx, block_type, tag):
    text_html = richtext2html(block[block_type].get('text') or block[block_type].get('rich_text') or [])
    color = block[block_type].get('color', '')
    html_details_open = ['', 'open'][toggle_like.html_details_open]
    html = f'<details class="notion-color-{color}" {html_details_open}'  + notionattrs2html(block, used_keys = ['children', block_type + '-text', block_type + '-rich_text', block_type + '-color', block_type + '-is_toggleable']) + '>' 
    html += f'<summary><{tag}>' + text_html + f'</{tag}></summary>\n'
    html += children_like(block, ctx)
    html += '</details>\n'
    return html

def heading_like(block, ctx, block_type, tag):
    if block.get(block_type, {}).get('is_toggleable') is not True: 
        return text_like(block, ctx, block_type, tag, used_keys = [block_type + '-is_toggleable'])
    else:
        return toggle_like(block, ctx, block_type, tag)

def link_like(block, ctx, block_type, tag = 'a'):
    assert block[block_type].get('type') in ['file', 'external', None]
    src = block[block_type].get('file', {}).get('url') or block[block_type].get('external', {}).get('url') or block[block_type].get('url') or ''
    text_html = richtext2html(block[block_type].get('caption', [])) or block[block_type].get('name') or src #TODO: urlquote?
    html = '\n' + f'<{tag}' + notionattrs2html(block, used_keys = [block_type + '-name', block_type + '-url', block_type + '-caption', block_type + '-type', block_type + '-file', block_type + '-external']) + f' href="{src}">📎 {text_html}</{tag}><br />\n'
    return html

def link_to_page(block, ctx, tag = 'a'):
    link_to_page_type = block[link_to_page.__name__].get('type') # should be 'page_id'
    link_to_page_page_id = block[link_to_page.__name__].get('page_id', '')
    href = '#' + link_to_page_page_id #TODO: use slugs
    
    id2block = {}
    stack = list(block2html.notion_cache['pages'].values())
    while stack:
        top = stack.pop()
        id2block[top.get('id')] = top
        stack.extend(top.get('blocks', []) + top.get('children', []))
    
    subblock = id2block.get(link_to_page_page_id) 
    if subblock:
        title = subblock.get("properties", {}).get("title", {}).get("title", [])[0]["plain_text"] if len(subblock.get("properties",{}).get('title', {}).get('title', [])) > 0 else (subblock.get('child_page', {}).get('title') or subblock.get('title', ''))
        icon_emoji = subblock.get('icon', {}).get('emoji', '')
        caption = f'{icon_emoji} {title}' #TODO: html.escape()
    else:
        caption = f'title of linked page [{link_to_page_page_id}] not found'

    return f'<{tag} href="{href}"' + notionattrs2html(block, used_keys = [link_to_page.__name__ + '-type', link_to_page.__name__ + '-page_id']) + f'>{caption}</{tag}><br />\n'

def table(block, ctx, tag = 'table'):
    #TODO: headers: row-header, column-header
    table_width, has_row_header, has_column_header = map(block[table.__name__].get, ['table_width', 'has_row_header', 'has_column_header'])
    html = f'<{tag} data-notion-table_width="{table_width}" data-notion-has_column_header="{has_column_header}" data-notion-has_row_header="{has_row_header}" ' + notionattrs2html(block, used_keys = ['children', 'table-table_width', 'table-has_column_header', 'table-has_row_header']) + '>\n'
    for subblock in block.get('children', []):
        html += '<tr>\n'
        for cell in subblock.get('table_row', {}).get('cells', []):
            html += '<td>' + richtext2html(cell) + '</td>\n' #TODO: array -> divs
        html += '</tr>\n'
    html += f'</{tag}>\n'
    return html

def page_like(block, ctx, tag = 'article'):
    #TODO: page title and mini-nav
    icon_type = block['icon'].get('type') #TODO: for child_page depends on pop_and_replace_child_pages_recursively
    icon_emoji = block['icon'].get('emoji', '')
    cover_type = block.get('cover', {}).get('type')
    src = block.get('cover', {}).get('file', {}).get('url', '')
    src = block2html.notion_cache['assets'].get(src, {}).get('data_uri', src)

    title = block.get("properties", {}).get("title", {}).get("title", [])[0]["plain_text"] if len(block.get("properties",{}).get('title', {}).get('title', [])) > 0 else (block.get('child_page', {}).get('title') or block.get('title', '')) 
    html = f'<{tag} class="post"' + notionattrs2html(block, used_keys = ['blocks', 'icon-type', 'icon-emoji', 'cover-type', 'cover-file', 'properties-title', 'children', 'title', 'child_page-title']) + f'><header class="post-header"><img src="{src}"></img><h1 class="notion-page-icon">{icon_emoji}</h1><h1 class="post-title">{title}</h1></header><div class="post-content">\n'
    html += children_like(block, ctx, key = 'blocks' if 'blocks' in block else 'children')
    html += '\n' + f'</div></{tag}>\n'
    return html

def page(block, ctx, tag = 'article'):
    return page_like(block, ctx, tag = tag)

def child_page(block, ctx, tag = 'article'):
    return page_like(block, ctx, tag = tag)

def video(block, ctx, tag = 'p'):
    caption = richtext2html(block[video.__name__].get('caption', []))
    video_type = block[video.__name__]['type'] # should be "external"
    src = block[video.__name__].get('external', {}).get('url', '')
    is_youtube = 'youtube.com' in src
    src = src.replace("http://", "https://").replace('/watch?v=', '/embed/').split('&')[0] if is_youtube else src
    
    html = f'<{tag}' + notionattrs2html(block, used_keys = [video.__name__ + '-caption', video.__name__ + '-type', video.__name__ + '-external', video.__name__ + '-external-url']) + '>'
    if is_youtube:
        html += f'<div class="res_emb_block"><iframe width="640" height="480" src="{src}" frameborder="0" allowfullscreen></iframe></div>'
    else:
        html += f'<video playsinline autoplay muted loop controls src="{src}"></video>'

    html += f'</{tag}>\n'
    return html

def image(block, ctx, tag = 'img'):
    #TODO: fixup url from assets
    #TODO: when to embed image
    assert block['image']['type'] in ['file', 'external']
    src = block['image'].get('file', {}).get('url') or block['image'].get('external', {}).get('url') or ''
    src = block2html.notion_cache['assets'].get(src, {}).get('data_uri', src)
    if src.startswith('file:///'):
        src = src.split('file:///', maxsplit = 1)[-1]
    caption = richtext2html(block['image']['caption']) # TODO: html.escape
    html = f'<{tag}' + notionattrs2html(block, used_keys = ['image-caption', 'image-type', 'image-file', 'image-external']) + f' src="{src}">{caption}</{tag}>\n'
    return html

def embed(block, ctx, tag = 'iframe'):
    text_html = richtext2html(block[embed.__name__].get('caption', [])) 
    src = block[embed.__name__].get('url', '')
    return f'<{tag}' + notionattrs2html(block, used_keys = [embed.__name__ + '-caption', embed.__name__ + '-url']) + f' src="{src}"></{tag}>\n'

def callout(block, ctx, tag = 'p'):
    icon_type = block[callout.__name__].get('icon', {}).get('type')
    icon_emoji = block[callout.__name__].get('icon', {}).get('emoji', '')
    color = block[callout.__name__].get('color', '')
    text_html = text_like(block, ctx, block_type = callout.__name__, tag = tag, used_keys = [callout.__name__ + '-icon'])
    return f'<div style="display:flex" class="notion-callout-block notion-color-{color}"><div>{icon_emoji}</div><div>\n' + text_html + '\n</div></div>\n'


def column_list(block, ctx, tag = 'div'):
    html = f'<{tag}' + notionattrs2html(block, used_keys = ['children']) + '>\n'
    html += children_like(block, ctx)
    html += f'</{tag}>\n'
    return html

def column(block, ctx, tag = 'div'):
    html = f'<{tag}' + notionattrs2html(block, used_keys = ['children']) + '>\n'
    html += children_like(block, ctx, tag = tag)
    html += f'</{tag}>\n'
    return html

def pdf(block, ctx, tag = 'a'):
    return link_like(block, ctx, block_type = pdf.__name__, tag = tag)

def file(block, ctx, tag = 'a'):
    return link_like(block, ctx, block_type = file.__name__, tag = tag)

def bookmark(block, ctx, tag = 'a'):
    return link_like(block, ctx, block_type = bookmark.__name__, tag = tag)
    
def paragraph(block, ctx, tag = 'p'):
    return text_like(block, ctx, block_type = paragraph.__name__, tag = tag)

def heading_1(block, ctx, tag = 'h1'):
    return heading_like(block, ctx, block_type = heading_1.__name__, tag = tag)

def heading_2(block, ctx, tag = 'h2'):
    return heading_like(block, ctx, block_type = heading_2.__name__, tag = tag)
    
def heading_3(block, ctx, tag = 'h3'):
    return heading_like(block, ctx, block_type = heading_3.__name__, tag = tag)

def quote(block, ctx, tag = 'blockquote'):
    return text_like(block, ctx, block_type = quote.__name__, tag = tag)

def toggle(block, ctx, tag = 'span'):
    return toggle_like(block, ctx, block_type = toggle.__name__, tag = tag)

def divider(block, ctx, tag = 'hr'):
    return f'<{tag}' + notionattrs2html(block) + '/>\n'

def blank(block, ctx, tag = 'br'):
    return f'<{tag}' + notionattrs2html(block) + '/>\n'

def bulleted_list_item(block, ctx, tag = 'ul', begin = False, end = False):
    return (f'<{tag}>\n' if begin else '') + text_like(block, ctx, block_type = bulleted_list_item.__name__, tag = 'li') + ('\n' + f'</{tag}>\n' if end else '')

def numbered_list_item(block, ctx, tag = 'ol', begin = False, end = False):
    return (f'<{tag}>\n' if begin else '') + text_like(block, ctx, block_type = numbered_list_item.__name__, tag = 'li') + ('\n' + f'</{tag}>\n' if end else '')

def table_of_contents(block, ctx, tag = 'ul'):
    color = block[table_of_contents.__name__].get('color', '')
    
    id2block = {}
    stack = list(block2html.notion_cache['pages'].values())
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
    
    html = f'<{tag} class="notion-table-of-contents notion-color-{color}"' +  notionattrs2html(block, used_keys = ['table_of_contents-color']) + '/>\n'
    for block in headings:
        heading_class = dict(heading_1 = 'notion-toc-section', heading_2 = 'notion-toc-subsection', heading_3 = 'notion-toc-subsubsection').get(block.get('type'), '')
        block_id = block['id']
        html += f'<li class="{heading_class}"><a href="#{block_id}">' + richtext2html(block[block.get('type')].get('text') or block[block.get('type')].get('rich_text') or [], title_mode = True) + '</a></li>\n'
    html += f'</{tag}>\n'
    return html


def notionattrs2html(block, used_keys = []):
    used_keys_ = used_keys
    used_keys, used_keys_nested1, used_keys_nested2 = [k for k in used_keys if k.count('-') == 0], [tuple(k.split('-')) for k in used_keys if k.count('-') == 1], [tuple(k.split('-')) for k in used_keys if k.count('-') == 2]

    #TODO: add used_keys_nested2 for block_type
    #default_annotations = dict(bold = False, italic = False, strikethrough = False, underline = False, code = False, color = "default")

    keys = ['object', 'id', 'created_time', 'last_edited_time', 'archived', 'type', 'has_children', 'url', 'public_url', 'request_id'] 
    keys_nested1 = [('created_by', 'object'), ('created_by', 'id'), ('last_edited_by', 'object'), ('last_edited_by', 'id'), ('parent', 'type'), ('parent', 'workspace'), ('parent', 'page_id'), ('parent', 'block_id')] 

    keys_alias = {'id' : 'id'}

    keys_extra = [k for k in block.keys() if k not in keys and k not in used_keys if not isinstance(block[k], dict)] + [f'{k1}-{k2}' for k1 in block.keys() if isinstance(block[k1], dict) for k2 in block[k1].keys() if (k1, k2) not in keys_nested1 and (k1, k2) not in used_keys_nested1]

    if keys_extra:
        print(block.get('type') or block.get('object'), ';'.join(keys_extra))

    if notionattrs2html.notion_attrs_verbose is True:
        return ' ' + ' '.join('{kk}="{v}"'.format(kk = keys_alias.get(k, 'data-notion-' + k), v = block[k]) for k in keys if k in block) + ' ' + ' '.join('data-notion-{k1}-{k2}="{v}"'.format(k1 = k1, k2 = k2, v = block[k1][k2]) for k1, k2 in keys_nested1 if k1 in block and k2 in block[k1]) + (' data-notion-extrakeys="{}"'.format(';'.join(keys_extra)) if keys_extra else '') + ' '
    else:
        return ' id="{id}" '.format(id = block.get('id', ''))
   
def block2html(block, ctx = 0, begin = False, end = False):
    block2render = dict(paragraph = paragraph, heading_1 = heading_1, heading_2 = heading_2, heading_3 = heading_3, toggle = toggle, quote = quote, blank = blank, table = table, divider = divider, table_of_contents = table_of_contents, callout = callout, image = image, page = page, child_page = child_page, column_list = column_list, column = column, video = video, embed = embed, file = file, pdf = pdf, link_to_page = link_to_page, bookmark = bookmark)
    block2render_with_begin_end = dict(numbered_list_item = numbered_list_item, bulleted_list_item = bulleted_list_item)

    block_type = str(block.get('type') or block.get('object'))
    
    if block_type in block2render:
        return block2render[block_type](block, ctx)

    elif block_type in block2render_with_begin_end:
        return block2render_with_begin_end[block_type](block, ctx, begin = begin, end = end)

    else:
        # TODO: print all unsupported to a log? include as comment? or just as element? render children? replace by <!-- --> or maybe "p"?
        return f'\n<{block_type} unsupported="1"' + notionattrs2html(block) + '/>\n\n'

def site2html(page_ids, notion_pages = {}, style = ''):
    html = '\n\n'.join(block2html(notion_pages[k], ctx = 0) for k in page_ids)
    return f'''
    <html><body>
    <style>
    {style}
    </style>
    <header class="site-header"><a class="site-title" href="/notionfun/">Exil Solidaire</a></header>
    <main class="page-content" aria-label="Content"><div class="wrapper">
    {html}
    </div></main>
    </body></html>
    '''

def pop_and_replace_child_pages_recursively(block, parent_id = None):
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
                block[keys][i] = {
                    'object' : 'block', 
                    'has_children' : False,
                    'type' : 'link_to_page',
                    'link_to_page' : {'type' : 'page_id', 'page_id' : child_page['id']} 
                }
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
                f.write(base64.b64decode(asset['data_uri'].split('base64,', maxsplit = 1)[-1].encode()))
            asset['data_uri'] = 'file:///' + asset_path
            print(asset_path)
    return assets

def extract_html_single(output_path, page_ids, child_pages_by_id = {}, extract_assets = False, style = '', notion_cache = {}):
    notion_cache['pages'].update(child_pages_by_id)
    
    notion_cache['assets'] = prepare_and_extract_assets(notion_pages = notion_cache['pages'], assets_dir = output_path + '_files', notion_assets = notion_cache['assets'], extract_assets = extract_assets)
    with open(output_path, 'w', encoding = 'utf-8') as f:
        f.write(site2html(page_ids, style = style, notion_pages = notion_cache['pages']))
    print(output_path)

def extract_html_nested(output_dir, notion_assets = {}, notion_pages = {}, notion_slugs = {}, child_pages_by_id = {}, child_pages_by_parent_id = {}, extract_assets = False, style = '', index_html = False):
    os.makedirs(output_dir, exist_ok = True)
    notion_pages.update(child_pages_by_id)

    for page_id, block in notion_pages.items():
        os.makedirs(output_dir, exist_ok = True)
        slug = notion_slugs.get(page_id) or notion_slugs.get(page_id.replace('-', '')) or page_id
        page_dir = os.path.join(output_dir, slug) if index_html and slug != 'index' else output_dir
        os.makedirs(page_dir, exist_ok = True)

        html_path = os.path.join(page_dir, 'index.html' if index_html else slug + '.html')
        assets_dir = os.path.join(page_dir, slug + '_files')
        notion_assets_for_block = prepare_and_extract_assets({page_id : block}, assets_dir = assets_dir, notion_assets = notion_assets, extract_assets = extract_assets)
        block2html.notion_cache['assets'] = notion_assets_for_block
        with open(html_path, 'w', encoding = 'utf-8') as f:
            f.write(site2html([page_id], style = style, notion_pages = notion_pages))
        print(html_path)
        if children := child_pages_by_parent_id.pop(page_id, []):
            extract_html_nested(page_dir, notion_assets = notion_assets, notion_pages = {child['id'] : child for child in children}, notion_slugs = notion_slugs, child_pages_by_parent_id = child_pages_by_parent_id, extract_assets = extract_assets, style = style, index_html = index_html)

def main(args):
    notion_cache = json.load(open(args.input_path))
    
    notion_slugs = json.load(open(args.slug_json)) if args.slug_json else {}

    notionattrs2html.notion_attrs_verbose = args.notion_attrs_verbose
    toggle_like.html_details_open = args.html_details_open
    block2html.notion_cache = notion_cache
    
    #assert len(notion_cache['pages']) >= 1
    root_page_ids = args.notion_page_id or list(notion_cache['pages'].keys())
    for i in range(len(root_page_ids)):
        for k, v in notion_slugs.items():
            if root_page_ids[i] == v:
                root_page_ids[i] = k
        for k in notion_cache['pages'].keys():
            if root_page_ids[i] == k.replace('-', ''):
                root_page_ids[i] = k 
    # TODO: add error checking that all root_page_ids are found in actual pages?
    # TODO:add all child_pages recursively, and not just a single time. should update child_pages always? add special option
    child_pages_by_parent_id = {k: v for page_id, page in notion_cache['pages'].items() for k, v in pop_and_replace_child_pages_recursively(page, parent_id = page_id).items()}
    child_pages_by_id = {child_page['id'] : child_page for pages in child_pages_by_parent_id.values() for child_page in pages}
    
    page_ids = root_page_ids + [child_page['id'] for page_id in root_page_ids for child_page in child_pages_by_parent_id[page_id] if child_page['id'] not in root_page_ids]
    
    notion_assets = notion_cache.get('assets', {})
    
    style = open(args.default_style_css).read() if args.default_style_css else ''
    
    output_path = args.output_path if args.output_path else '_'.join(args.notion_page_id)

    if args.extract_html == 'single':
        extract_html_single(output_path if args.output_path else output_path + '.html', page_ids, child_pages_by_id = child_pages_by_id, extract_assets = args.extract_assets, style = style, notion_cache = notion_cache)

    else:
        extract_html_nested(output_path, notion_pages = notion_cache['pages'], notion_assets = notion_assets, notion_slugs = notion_slugs, child_pages_by_id = child_pages_by_id if args.extract_html in ['flat', 'flat.html'] else {}, child_pages_by_parent_id = child_pages_by_parent_id if args.extract_html == 'nested' else {}, style = style, index_html = args.extract_html in ['flat', 'nested'], extract_assets = args.extract_assets) #  | child_pages_by_id <- breaks notion_cache in the context and link_to_page resolving
            
        

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--input-path', '-i')
    parser.add_argument('--output-path', '-o')
    parser.add_argument('--slug-json')
    parser.add_argument('--notion-page-id', nargs = '*', default = [])
    parser.add_argument('--notion-attrs-verbose', action = 'store_true')
    parser.add_argument('--html-details-open', action = 'store_true')
    parser.add_argument('--extract-assets', action = 'store_true')
    parser.add_argument('--extract-html', default = 'single', choices = ['single', 'flat', 'flat.html', 'nested'])
    parser.add_argument('--default-style-css')
    args = parser.parse_args()
    print(args)
    main(args)
