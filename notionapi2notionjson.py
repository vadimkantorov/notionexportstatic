# TODO: for single mode support lifting child_pages
# TODO: download JSON per given child page
# TODO: url naming styles: id, slug, and sanitized title
# TODO: rename data_uri to uri
# TODO: support column_list / column
# TODO: delete nested mode? delete nested + extract_files ?
# TODO: allow multiple page_ids

import os
import json
import base64
import hashlib
import argparse
import urllib.parse
import urllib.error
import urllib.request

import notion_client

def notionapi_retrieve_recursively(notionapi, notion_page_id, notion_pages = {}):
    def block_parser(block: dict, notionapi)-> dict:
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
                block_parser(subblock, notionapi)
        return block

    try:
        page_type, page = 'page', notionapi.pages.retrieve(notion_page_id)
    except notion_client.APIResponseError as exc:
        page_type, page = 'database', notionapi.databases.retrieve(notion_page_id)
    except Exception as exc:
        page_type, page = None, {}
        print(exc)
        
    print('page', page['id'], page_type)
    
    start_cursor = None
    notion_pages[page['id']] = page
    notion_pages[page['id']]['blocks'] = []

    while True:
        if page_type == 'page':
            blocks = notionapi.blocks.children.list(notion_page_id, **(dict(start_cursor = start_cursor) if start_cursor is not None else {}))
        elif page_type == 'database':
            blocks = notionapi.databases.query(notion_page_id, **(dict(start_cursor = start_cursor) if start_cursor is not None else {}))
        
        start_cursor = blocks['next_cursor']
        notion_pages[page['id']]['blocks'].extend(blocks['results'])
        if start_cursor is None or blocks['has_more'] is False:
            break  
   
    for i_block, block in enumerate(notion_pages[page['id']]['blocks']):
        if page_type == 'page':
            if block['type'] in ['page', 'child_page', 'child_database']:
                notionapi_retrieve_recursively(notionapi, block['id'], notion_pages = notion_pages)
            else:
                block = block_parser(block, notionapi)
                notion_pages[page['id']]['blocks'][i_block] = block

        elif page_type == 'database':
            block['type'] = 'db_entry'
            notion_pages[page['id']]['blocks'][i_block] = block
            if block['object'] in ['page', 'child_page', 'child_database']:
                notionapi_retrieve_recursively(notionapi, block['id'], notion_pages = notion_pages)

    return notion_pages

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


def download_assets(blocks):
    urls = discover_assets(blocks, [])
    notion_assets = {} 
    for url in urls:
        ok = True
        if url.startswith('data:image/'):
            ext = '.jpg' if url.startswith('data:image/jpeg') else '.svg' if url.startswith('data:image/svg+xml') else '.png' if url.startswith('data:image/png') else '.webp' if url.startswith('data:image/webp') else ''
            basename = 'datauri'
            path = url
            datauri = url
        else:
            urlparsed = urllib.parse.urlparse(url)
            ext = os.path.splitext(urlparsed.path.lower())[-1]
            basename = os.path.basename(urlparsed.path)
            path = urlparsed.scheme + '://' + urlparsed.netloc + urlparsed.path
            mime = 'image/jpeg' if ext in ['.jpg', '.jpeg'] else 'image/png' if ext == '.png' else 'image/svg+xml' if ext == '.svg' else 'image/webp' if ext == '.webp' else 'text/plain'
            file_bytes = b''
            try:
                file_bytes = urllib.request.urlopen(url).read()
            except urllib.error.HTTPError as exc:
                file_bytes = str(exc).encode()
                print(f'🤖Cannot download [{basename}] from link {url}.')
                mime = 'text/plain'
                ok = False
            datauri = f'data:{mime};base64,' + base64.b64encode(file_bytes).decode()

        sha1 = hashlib.sha1()
        sha1.update(path.encode())
        url_hash = sha1.hexdigest()

        file_name = basename + '.' + url_hash + ext
        notion_assets[url] = dict(basename = basename, data_uri = datauri, ok = ok)

        print(url, file_name, ok)
                
    return notion_assets

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

def prepare_and_extract_assets(notion_pages, assets_dir, notion_assets = {}, extract_assets = False):
    urls = discover_assets(notion_pages.values(), [])
    assets = {url : notion_assets[url] for url in urls}
    if extract_assets and assets:
        os.makedirs(assets_dir, exist_ok = True)
        for asset in assets.values():
            asset_path = os.path.join(assets_dir, asset['name'])
            with open(asset_path, 'wb') as f:
                f.write(base64.b64decode(asset['data_uri'].split('base64,', maxsplit = 1)[-1].encode()))
            asset['data_uri'] = 'data:,' #TODO: replace by file:///
            print(asset_path)
    return assets

def extract_json_single(output_path, notion_cache = {}, child_pages_by_id = {}, extract_assets = False):
    notion_cache['pages'].update(child_pages_by_id)
    notion_cache['assets'] = prepare_and_extract_assets(notion_pages = notion_cache['pages'], assets_dir = output_path + '_files', notion_assets = notion_cache['assets'], extract_assets = extract_assets)
    with open(output_path, 'w', encoding = 'utf-8') as f:
        json.dump(notion_cache, f, ensure_ascii = False, indent = 4)
    print(output_path)
    
def extract_json_nested(output_dir, notion_assets = {}, notion_pages = {}, notion_slugs = {}, child_pages_by_parent_id = {}, child_pages_by_id = {}, extract_assets = False):
    os.makedirs(output_dir, exist_ok = True)
    notion_pages |= child_pages_by_id
    for page_id, block in notion_pages.items():
        os.makedirs(output_dir, exist_ok = True)
        slug = notion_slugs.get(page_id) or notion_slugs.get(page_id.replace('-', '')) or page_id.replace('-', '')
        json_path = os.path.join(output_dir, slug + '.json')
        with open(json_path, 'w', encoding = 'utf-8') as f:
            assets_dir = os.path.join(output_dir, slug + '_files')
            notion_assets_for_block = prepare_and_extract_assets({block['id'] : block}, assets_dir = assets_dir, notion_assets = notion_assets, extract_assets = extract_assets)
            json.dump(dict(pages = {page_id : block}, assets = notion_assets_for_block), f, ensure_ascii = False, indent = 4)
        print(json_path)
        if children := child_pages_by_parent_id.pop(page_id, []):
            extract_json_nested(os.path.join(output_dir, slug), notion_assets = notion_assets, notion_pages = {child['id'] : child for child in children}, notion_slugs = notion_slugs, child_pages_by_parent_id = child_pages_by_parent_id, extract_assets = extract_assets)

def main(args):
    notionapi = notion_client.Client(auth = args.notion_token)

    notion_slugs = json.load(open(args.pages_json)) if args.pages_json else {}
    
    # TODO: support flattening pages for single?
    # TODO: support multiple notion_page_id
    # TODO: support resolving notion_page_id from slugs

    notion_pages = notionapi_retrieve_recursively(notionapi, args.notion_page_id[0], {})
    notion_assets = download_assets(notion_pages.values()) if args.download_assets else {}
    
    notion_cache = dict(pages = notion_pages, assets = notion_assets)
    
    output_path = args.output_path if args.output_path else '_'.join(args.notion_page_id) 
    
    if args.extract_json == 'single':
        extract_json_single(output_path if args.output_path else (output_path + '.json'), notion_cache = notion_cache, extract_assets = args.extract_assets)

    else:
        child_pages_by_parent_id = {k: v for page_id, page in notion_cache['pages'].items() for k, v in pop_and_replace_child_pages_recursively(page, parent_id = page_id).items()}
        child_pages_by_id = {child_page['id'] : child_page for parent_id, pages in child_pages_by_parent_id.items() for child_page in pages}
        extract_json_nested(output_path, notion_pages = notion_cache['pages'], notion_assets = notion_assets, notion_slugs = notion_slugs, child_pages_by_id = child_pages_by_id if args.extract_json == 'flat' else {}, child_pages_by_parent_id = child_pages_by_parent_id if args.extract_json == 'nested' else {}, extract_assets = args.extract_assets)
            

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--notion-token', required = True)
    parser.add_argument('--notion-page-id', nargs = '+')
    parser.add_argument('--download-assets', action = 'store_true')
    parser.add_argument('--extract-assets', action = 'store_true')
    parser.add_argument('--extract-json', default = 'single', choices = ['flat', 'single', 'nested'])
    parser.add_argument('--output-path', '-o')
    parser.add_argument('--pages-json')
    args = parser.parse_args()
    print(args)
    main(args)
