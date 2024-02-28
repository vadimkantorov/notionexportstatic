# TODO: rstrip all <br /> at page end
# TODO: delete plain_text: ' ' empty text blocks
# TODO: optional frontmatter gen
# TODO: delete useless "> \n" in callout, ex https://github.com/vadimkantorov/notionfun/edit/gh-pages/_markdown/visa-c.md
# TODO: can deploy pre-generated html?

import os
import json
import argparse
import datetime
import hashlib
import base64

import urllib.parse
import urllib.error
import urllib.request



def block2markdown(block:object,depth=0, ctx={}, page_id='') -> str:
    def render_block_kwargs(payload:dict, ctx: dict, page_id, block_type = None) -> dict:
        kwargs = {}
        if 'checked' in payload:
            kwargs['checked'] = payload['checked']
        if 'language' in payload:
            kwargs['language'] = payload['language']
        if 'cells' in payload:
            kwargs['cells'] = payload['cells']
        if 'expression' in payload:
            kwargs['text'] = payload['expression']
        if 'icon' in payload:
            kwargs['icon'] = payload['icon']['emoji']
        if 'caption' in payload:
            kwargs['caption'] = richtext2markdown(payload['caption'])
        if 'text' in payload:
            kwargs['text'] = richtext2markdown(payload['text'])
        if 'rich_text' in payload:
            kwargs['text'] = richtext2markdown(payload['rich_text'])
        if 'page_id' in payload:
            kwargs['url'] = ctx['pages'][payload['page_id']]['url']
            kwargs['caption'] = ctx['pages'][payload['page_id']]['title']
            kwargs['emoji'] = ctx['pages'][payload['page_id']].get('emoji') or ''
        if 'url' in payload or 'external' in payload or 'file' in payload:
            kwargs['url'] = payload.get('url') or payload.get('external', {}).get('url') or payload.get('file', {}).get('url')
            #print('kwargs url', block_type, payload.get('type'), kwargs['url'])
            if block_type == 'image':
                ctx['pages'][page_id]['assets_to_download'].append(kwargs['url'])
        return kwargs

    paragraph = lambda kwargs: kwargs['text']
    heading_1 = lambda kwargs: "# {text}".format(**kwargs)
    heading_2 = lambda kwargs: "## {text}".format(**kwargs)
    heading_3 = lambda kwargs: "### {text}".format(**kwargs)
    quote = lambda kwargs: "> {text}".format(**kwargs)
    bulleted_list_item = lambda kwargs: "* {text}".format(**kwargs)
    numbered_list_item = lambda kwargs: "1. {text}".format(**kwargs) # numbering is not supported
    toggle = lambda kwargs: "* {text}".format(**kwargs) # toggle item will be changed as bulleted list item
    callout = lambda kwargs: "\n> {icon} {text}".format(**kwargs) # "\n> [!IMPORTANT]\n> {icon} {text}".format(**kwargs)
    to_do = lambda kwargs: "- [{x}] {text}".format(x = 'x' if kwargs['checked'] else ' ', text = kwargs['text'])
    code = lambda kwargs: f"```{lang}\n{text}\n```".format(lang = kwargs['language'].replace(' ', '_'), text = kwargs['text'])
    embed = lambda kwargs, width = 640, height = 480: '<p><div class="res_emb_block"><iframe width="{width}" height="{height}" src="{url}" frameborder="0" allowfullscreen></iframe></div></p>'.format(width = width, height = height, **kwargs)
    image = lambda kwargs: "![{caption}]({url})".format(caption = kwargs['caption'] or '', url = kwargs['url'])
    bookmark = lambda kwargs: "[🔖 {caption}]({url})".format(caption = kwargs['caption'] or kwargs.get('url', ''), url = kwargs['url'])
    link_to_page = lambda kwargs: '[{emoji} {caption}]({url})'.format(**kwargs)
    file = lambda kwargs: "[{emoji} {caption}]({url})".format(emoji = '📎', url = kwargs['url'], caption = urllib.parse.unquote(os.path.basename(urllib.parse.urljoin(kwargs['url'], urllib.parse.urlparse(kwargs['url']).path))))
    equation = lambda kwargs: "$$ {text} $$".format(**kwargs)
    divider = lambda kwargs: "---"
    blank = lambda *args, **kwargs: "<br/>"
    table = lambda kwargs: ''
    pdf = lambda kwargs: "![{caption}]({url})".format(caption = kwargs['caption'] or os.path.basename(kwargs['url']), url = kwargs['url'])
    table_row = lambda kwargs: [richtext2markdown(column) for column in kwargs['cells']]
    video = lambda kwargs: ('<p><video playsinline autoplay muted loop controls src="{url}"></video></p>' if urllib.parse.urljoin(kwargs["url"], urllib.parse.urlparse(kwargs["url"]).path).endswith(".webm") else '<p><div class="res_emb_block"><iframe width="640" height="480" src="{url}" frameborder="0" allowfullscreen></iframe></div></p>').format(url = kwargs["url"].replace("http://", "https://").replace('/watch?v=', '/embed/').split('&')[0])
    column_list = lambda kwargs: '' # '\n\n> [!IMPORTANT]\n> **column_list** will be added here\n\n'
    column = lambda kwargs: '' # '\n\n> [!NOTE]\n> **column** starts here\n\n'
    table_of_contents = lambda kwargs: '\n\n{:toc}\n\n'

    render_block = dict(paragraph = paragraph, heading_1 = heading_1, heading_2 = heading_2, heading_3 = heading_3, callout = callout, toggle = toggle, quote = quote, bulleted_list_item = bulleted_list_item, numbered_list_item = numbered_list_item, to_do = to_do, code = code, embed = embed, image = image, bookmark = bookmark, equation = equation, divider = divider, file = file, table = table, table_row = table_row, video = video, pdf = pdf, table_of_contents = table_of_contents, link_to_page = link_to_page, column = column, column_list = column_list) # "child_page": child_page,

    outcome_block = ""
    block_type = block['type']
    #if block_type in ["child_page", "child_database", "db_entry"]:
    #    title = ctx['pages'][block['id']]['title']
    #    url = ctx['pages'][block['id']]['url']
    #    outcome_block = f"{title}]({url})\n\n"
    #    if ctx['pages'][block['id']]['emoji']:
    #        emoji = ctx['pages'][block['id']]['emoji']
    #        outcome_block = f"[{emoji} {outcome_block}"
    #    elif ctx['pages'][block['id']]['icon']:
    #        icon = ctx['pages'][block['id']]['icon']
    #        outcome_block = f"""[<span class="miniicon"> <img src="{icon}"></img></span> {outcome_block}"""
    #    else:
    #        outcome_block = f"[{outcome_block}"
    #    return outcome_block


    #Special Case: Block is blank
    if block_type == "paragraph" and not block['has_children'] and not (block[block_type].get('text') or block[block_type].get('rich_text')):
        return blank() + "\n\n"

    if block_type in render_block:
        if block_type in ["embed", "video"]:
            block[block_type]["dont_download"] = True
        outcome_block = render_block[block_type](render_block_kwargs(block[block_type], ctx, page_id, block_type = block_type)) + "\n\n"
    else:
        outcome_block = f'''block [type="{block_type}", id="{block.get('id')}"] is unsupported at page="{page_id}", has_children: {block['has_children']}]\n\n'''
        print(outcome_block)
        outcome_block = ''
  
    if block_type == "code":
        outcome_block = outcome_block.rstrip('\n').replace('\n', '\n'+'\t'*depth) + '\n\n'

    if block['has_children'] and block_type == 'table':
        depth += 1
        table_list = [render_block[cell_block['type']](render_block_kwargs(cell_block[cell_block['type']], ctx, page_id, block_type = cell_block['type'])) for cell_block in block["children"]]
        sanitize_table_cell = lambda md: md.replace('\n', ' ')
        for index,value in enumerate(table_list):
            if index == 0:
                outcome_block += "\n | " + " | ".join(map(sanitize_table_cell, value)) + " | " + "\n"
                outcome_block += " | " + " | ".join(['----'] * len(value)) + " | " + "\n"
                continue
            outcome_block += " | " + " | ".join(map(sanitize_table_cell, value)) + " | " + "\n"
        outcome_block += "\n"
   
    elif block['has_children'] and block_type == 'callout':
        outcome_block = outcome_block.rstrip() + '\n'
        outcome_block += '>\n'.join(''.join(f'> {line}\n' for line in block2markdown(subblock, 0, ctx, page_id).splitlines()) + '>\n' for subblock in block["children"])
        outcome_block = outcome_block.rstrip() + '\n'
        
    elif block['has_children'] and block_type in ['column_list', 'column']:
        for subblock in block["children"]:
            outcome_block += block2markdown(subblock, 0, ctx, page_id)
    
    elif block['has_children'] and block_type.startswith('heading_'):
        outcome_block = '\n<details markdown="1">\n<summary markdown="1">\n\n' + outcome_block + '\n\n</summary>\n\n'
        for subblock in block["children"]:
            outcome_block += block2markdown(subblock, 0, ctx, page_id)
        outcome_block += '\n\n</details>\n\n'
    
    elif block['has_children']:
        depth += 1
        for subblock in block["children"]:
            # This is needed, because notion thinks, that if 
            # the page contains numbered list, header 1 will be the 
            # child block for it, which is strange.
            if subblock['type'] == "heading_1":
                depth = 0
            outcome_block += "\t"*depth + block2markdown(subblock, depth, ctx, page_id)

    return outcome_block

def richtext2markdown(richtext, title_mode=False) -> str:
    if isinstance(richtext, list):
        return "".join(richtext2markdown(r, title_mode) for r in richtext)
    code = lambda content: f"`{content}`"
    color = lambda content, color: f"<span style='color:{color}'>{content}</span>"
    equation = lambda content: f"$ {content} $"
    user = lambda kwargs: f"({kwargs['content']})"
    date = lambda kwargs: f"({kwargs['content']})"
    italic = lambda content: f"*{content}*"
    strikethrough = lambda content: f"~~{content}~~"
    underline = lambda content: f"<u>{content}</u>"
    bold = lambda content: content if ((not content) or content.isspace()) else  (content[0] * (bool(content) and content[0].isspace())) + f" **{content.strip()}** "
    _mention_link = lambda content, url: ('<a href="{url}" target="_blank"> <i class="fa fa-lg fa-github"> </i> {repo} </a>' if "https://github.com/" in url else "[{content}]({url})").format(repo = os.path.basename(url), url = url, content = content)
    page = lambda kwargs: _mention_link(kwargs['content'], kwargs['url'])
    link_preview = lambda kwargs: _mention_link(kwargs['content'], kwargs['url'])
    mention_kwargs = lambda payload: {'content' : payload['plain_text']} if not payload['href'] else {'url': payload['href'], 'content': payload['plain_text'] if payload['plain_text'] != "Untitled" else payload['href']}
    text_link = lambda kwargs: "[{caption}]({url})".format(caption = kwargs['content'], url = kwargs['link']['url'])
    database = lambda kwargs: _mention_link(kwargs['content'], kwargs['url'])

    annotation_map = { "bold": bold, "italic": italic, "strikethrough": strikethrough, "underline": underline, "code": code}
    mention_map = { "user": user, "page": page, "database": database, "date": date, "link_preview": link_preview}

    outcome_word = ""
    plain_text = richtext["plain_text"]
    if richtext['type'] == "equation":
        outcome_word = equation(plain_text)
        if title_mode:
            return outcome_word
    elif richtext['type'] == "mention":
        mention_type = richtext['mention']['type']
        if mention_type in mention_map:
            outcome_word = mention_map[mention_type](mention_kwargs(richtext))
    else:
        if title_mode:
            outcome_word = plain_text
            return outcome_word
        if "href" in richtext:
            if richtext["href"]:
                outcome_word = text_link(richtext["text"])
            else:
                outcome_word = plain_text
        else:
            outcome_word = plain_text
        annot = richtext["annotations"]
        for key,transfer in annotation_map.items():
            if richtext["annotations"][key]:
                outcome_word = transfer(outcome_word)
        if annot["color"] != "default":
            outcome_word = color(outcome_word,annot["color"])
    return outcome_word

def prepare_notion_content(raw_notion: dict, args) -> dict:
    def collect_parent_path_recursively(page_id: str, parent_path: list, pages: dict):
        if pages[page_id].get("parent") is not None:
            par_id = pages[page_id]["parent"]
            parent_path.insert(0, par_id)
            parent_path = collect_parent_path_recursively(par_id, parent_path, pages)
        return parent_path

    def fill_page_urls_recursively(page_id:str, ctx: dict, output_dir:str, root_page_id:str, slug:dict = {}, translate = {ord(" "): "_", ord("$"): "_", ord("\\"): "_"}):
        parent_id = ctx["pages"][page_id]["parent"]
        parent_url = ctx["pages"][parent_id]["url"] if parent_id is not None else ''
        #basename = ctx["pages"][page_id]["title"].translate(translate) + '.md'
        
        basename = slug.get(page_id.replace('-', ''), page_id) + '.md'
        
        url = os.path.join(output_dir, basename)
        ctx["pages"][page_id]["basename"] = basename
        ctx["pages"][page_id]["url"] = basename #url
        ctx["urls"].append(url)
        for child_id in ctx["pages"][page_id]["children"]:
            fill_page_urls_recursively(child_id, ctx, output_dir = output_dir, root_page_id = root_page_id, slug = slug)

    def fix_markdown_lists(page_md: str) -> str:
        page_md_fixed_lines = []
        prev_line_type = ''
        for line in page_md.splitlines():
            line_type = ''
            norm_line = line.lstrip('\t').lstrip()
            if norm_line.startswith('- [ ]') or norm_line.startswith('- [x]'):
                line_type = 'checkbox'
            elif norm_line.startswith('* '):
                line_type = 'bullet'
            elif norm_line.startswith('1. '):
                line_type = 'numbered'
            if prev_line_type != '':
                if line == '':
                    continue
            if line_type != prev_line_type:
                page_md_fixed_lines.append('')
            page_md_fixed_lines.append(line)
            prev_line_type = line_type
        return "\n".join(page_md_fixed_lines)

    def download_assets_(page_id, page, assets_dir):
        assert page['type'] != 'db_entry'
        for i, file_url in enumerate(page["assets_to_download"]):
            sha1 = hashlib.sha1()
            sha1.update(file_url.encode())
            file_url_hash = sha1.hexdigest()

            if file_url.startswith('data:image/'):
                ext = '.jpg' if file_url.startswith('data:image/jpeg') else '.svg' if file_url.startswith('data:image/svg+xml') else '.png' if file_url.startswith('data:image/png') else ''
                basename = file_url_hash + ext
                new_url = os.path.join('..', assets_dir, basename)
                local_path = os.path.join(assets_dir, basename)
                
                if os.path.exists(local_path):
                    print(f"🤖 [{local_path}] already exists.")
                else:
                    with open(local_path, 'wb') as f:
                        f.write(base64.b64decode(file_url.split(';base64,', maxsplit = 1)[-1].encode()))

            else:
                clean_url = urllib.parse.urljoin(file_url, urllib.parse.urlparse(file_url).path)
                basename = urllib.parse.unquote(os.path.basename(clean_url))
                new_url = os.path.join('..', assets_dir, basename)
                local_path = os.path.join(assets_dir, basename)
                    
                os.makedirs(assets_dir, exist_ok=True)

                print(local_path, file_url, new_url)

                if os.path.exists(local_path):
                    print(f"🤖 [{local_path}] already exists.")
                else:
                    try:
                        urllib.request.urlretrieve(file_url, local_path)
                        print(f"🤖 Downloaded [{local_path}] from {file_url}")
                    except urllib.error.HTTPError:
                        print(f"🤖Cannot download [{basename}] from link {file_url}.")
                    except ValueError as exc:
                        print(exc)
                        continue 

            page["assets_to_download"][i] = new_url
            page["md_content"] = page["md_content"].replace(file_url, new_url)
            if page['icon'] == file_url:
                page['icon'] = new_url
            if page['cover'] == file_url:
                page['cover'] = new_url
    
    def dict_search_recursively(dictionary, key):
        for k, v in (dictionary.items() if hasattr(dictionary, "items") else []):
            if k == key:
                yield v
            if isinstance(v, dict):
                for result in dict_search_recursively(v, key):
                    yield result
            elif isinstance(v, list):
                for d in v:
                    for result in dict_search_recursively(d, key):
                        yield result

   
    ##########################

    slug = (json.load(open(args.config_json)) if args.config_json else {}).get('slugs', {})
    
    raw_notion = raw_notion['pages']
    raw_notion = raw_notion.copy()
    child_pages = {block['id'] : block for page in raw_notion.values() for parent_id, blocks in pop_and_replace_child_pages_recursively(page).items() for block in blocks}
    for page in child_pages.values():
        page['url'] = page.get('url', 'https://www.notion.so/' + page.get('id', '').replace('-', ''))
    print('Child pages:', len(child_pages))
    raw_notion.update(child_pages)

    pages = {}
    for page_id, page in raw_notion.items():
        pages[page_id] = {}
        pages[page_id]["assets_to_download"] = []

        pages[page_id]["last_edited_time"] = page.get("last_edited_time", 'N/A')
        pages[page_id]['title'] = page.get('title', 'N/A')
        pages[page_id]["type"] = page.get('type') or page.get("object")
        if pages[page_id]["type"] is None:
            breakpoint()
        #pages[page_id]['url'] = page.get('url', 'https://notion.so/' + page.get('id', '').replace('-', ''))

        assert pages[page_id]["type"] not in ["database", "db_entry"]
       
        assert pages[page_id]["type"] in ["page", "child_page"]

        pages[page_id]["title"] = page["properties"]["title"]["title"][0]["plain_text"] if len(page.get("properties",{}).get('title', {}).get('title', [])) > 0 else pages[page_id].get("title")

        if "workspace" in page["parent"].keys():
            parent_id = None
            pages[page_id]["parent"] = parent_id

        if pages[page_id]["type"] in ["page"]:
            parent_id = page["parent"].get("page_id")
            pages[page_id]["parent"] = parent_id
        else:
            parent_id = None
            pages[page_id]["parent"] = parent_id

        if "children" not in pages[page_id].keys():
            pages[page_id]["children"] = []
        if parent_id is not None:
            pages[parent_id]["children"].append(page_id)

        if page.get("cover") is not None:
            cover = list(dict_search_recursively(page["cover"], "url"))[0]
            pages[page_id]["cover"] = cover
            pages[page_id]["assets_to_download"].append(cover)
        else:
            pages[page_id]["cover"] = None

        pages[page_id]["icon"] = None
        pages[page_id]["emoji"] = None
        
        if page.get("icon") and "emoji" in page["icon"]:
            pages[page_id]["emoji"] = page["icon"]["emoji"]
        elif page.get("icon"):
            icon = page["icon"]["file"]["url"]
            pages[page_id]["icon"] = icon
            pages[page_id]["assets_to_download"].append(icon)
    

    ctx = dict(
        urls = [],
        #include_footer = args.include_footer,
        root_page_id = list(raw_notion.keys())[0],
        pages = pages # "type" (str):  "page", "database" or "db_entry" | "files" (list): list of urls for nested "title" (str): title of corresponding page,  | "last_edited_time" (str): last edited time in iso format,  | "date" (str): date start in iso format,  | "date_end" (str): date end in iso format,  | "parent" (str): id of parent page, | "children" (list): list of ids of children page, | "cover" (str): cover url, | "emoji" (str): emoji symbol, | "icon" (str): icon url. | 
    )

    for page_id, page in pages.items():
        page["parent_path"] = collect_parent_path_recursively(page_id, [], pages)

    for page_id, page in pages.items():
        fill_page_urls_recursively(page_id, ctx, output_dir = args.output_dir, root_page_id = ctx["root_page_id"], slug = slug)
    
    #if args.download_assets:
    #    for page_id, page in pages.items():
    #        download_assets_(page_id, page, assets_dir = args.assets_dir)
    
    for page_id in raw_notion:
        pages[page_id]["md_content"] = fix_markdown_lists("".join(block2markdown(block, 0, ctx, page_id) for block in (raw_notion[page_id].get("blocks", []) or raw_notion[page_id].get("children", [])))).replace("\n\n\n", "\n\n") # page_md = code_aligner(page_md)

    return ctx

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

def main(args):
    with open(args.input_path, "r") as f:
        notion_cache = json.load(f)
   
    output_dir = args.output_dir
    isoparse = "%Y-%m-%dT%H:%M:%S.%fZ"
    ctx = prepare_notion_content(notion_cache, args)
    ctx['base_url'] = output_dir
    ctx['archive_url'] = 'N/A'
    for page_id, page in ctx["pages"].items():
        for k in page.keys() & ['date', 'date_end', 'last_edited_time']:
            ctx["pages"][page_id][k] = datetime.datetime.strptime(page[k], isoparse)

    for page_id, page in ctx["pages"].items():
        metadata = '''---\ntitle: "{title}"\ncover: {cover}\nemoji: {emoji}\n{properties}\n---\n\n'''.format(properties = '\n'.join(f"{k}: {v}" for k, v in page.get("properties_md", {}).items()), **page)
        #page_md_content = metadata + page['md_content']
        page_md_content = '[#](../) / {emoji} {title}\n<hr/>\n\n'.format(**page) + ('![cover]({cover})\n\n' if page.get('cover') else '').format(**page) + '# {emoji} {title}\n\n'.format(**page) + page['md_content']
        
        os.makedirs(output_dir, exist_ok = True)
        with open(os.path.join(output_dir, page["basename"]), 'w+', encoding='utf-8') as m: #  + '.md'
            print('generated', os.path.join(output_dir, page["basename"]), '|', page['title'])
            m.write(page_md_content)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--input-path', '-i')
    parser.add_argument('--output-dir', '-o')
    parser.add_argument('--assets-dir', default = './_assets')
    parser.add_argument('--config-json')
    parser.add_argument('--config-html-details-open', action = 'store_true')
    parser.add_argument('--extract-mode', choices = ['flat', 'single'], default = 'flat')
    args = parser.parse_args()
    print(args)
    main(args)
