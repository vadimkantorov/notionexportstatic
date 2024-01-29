# https://github.com/jekyll/minima
# https://github.com/jekyll/jekyll-seo-tag/blob/master/lib/template.html
# https://github.com/jekyll/jekyll-feed/blob/master/lib/jekyll-feed/generator.rb
# https://github.com/jekyll/jekyll-sitemap

# TODO: add InteractionObserver-based nav for single-page or for side menu
# TODO: margin between blocks
# TODO: extract the html template if needed? support jinja2 templates? liquid/jekyll templates? string.Template?
# TODO: move nav path computation to ctx

def sitepages2html(page_ids = [], ctx = {}, notion_pages = {}, block2html = (lambda page, ctx: '')):
    header_html = '&nbsp;/&nbsp;'.join(block2html(block, ctx).replace('<br/>', '') for block in reversed(ctx['pages_parent_path'][page_ids[0]]))
    main_html = '\n<hr />\n'.join(block2html(notion_pages[k], ctx = ctx).replace('class="notion-page-block"', 'class="notion-page-block post-title"').replace('<header>', '<header class="post-header">').replace('class="notion-page-content"', 'class="notion-page-content post-content"').replace(' notion-page"', ' notion-page post"') for k in page_ids)
    style = notion_css + notion_colors_css + twitter_emoji_font_css + minimacss_classic_full # CSS from https://github.com/vadimkantorov/minimacss and https://github.com/jekyll/minima

    return f'''
        <!DOCTYPE html>
        <html>
        <head>
        <meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no">
        </head>
        <body>
        <style>
        {style}
        </style>
        <header class="site-header notion-topbar">
        {header_html}
        </header>
        <main class="page-content" aria-label="Content"><div class="wrapper">
        {main_html}
        </div></main>
        </body>
        </html>
    '''

notion_css = '''
.notion-topbar { font-family: 'Twemoji Country Flags', sans-serif !important; position: sticky !important; top: 0 !important; width: 100% !important; z-index: 9 !important; background-color: white !important; }

.notion-record-icon { font-family: 'Twemoji Country Flags', sans-serif !important; font-size: 78px !important; line-height: 1.1 !important; margin-left: 0 !important; }

.notion-page-block { font-family: 'Twemoji Country Flags', sans-serif !important; font-size: 2.5em !important; line-height: 1.1 !important; margin-left: 0 !important; }

.notion-header-block, .notion-sub_header-block, .notion-sub_sub_header-block {scroll-margin-top: 60px !important}

.notion-column-block { display:flex; flex-direction: column; }
.notion-column_list-block { display:flex; flex-direction: row; }
.notion_column_list-block-vertical {flex-direction: column!important;}

.notion-callout-block { display:flex; }

.notion-quote-block {font-style: normal !important }

.notion-table_of_contents-block { margin-top: 10px !important; margin-left: 0 !important; }
.notion-table_of_contents-block { list-style-type: none !important; }
.notion-table_of_contents-heading > a {color: rgb(120, 119, 116) !important;}
.notion-table_of_contents-heading:hover {background: rgba(55, 53, 47, 0.08) !important;}
.notion-table_of_contents-heading_1 {padding-left: 10px}
.notion-table_of_contents-heading_2 {padding-left: 20px}
.notion-table_of_contents-heading_3 {padding-left: 30px}

.notion-bookmark-block {border: 0.66px solid rgba(55, 53, 47, 0.16)  !important; width: 100% !important; display: block !important; }

.notion-embed-block {width: 100% !important; height: 500px; border: 0!important}

details>summary>h1,details>summary>h2,details>summary>h3 {display:inline !important; } 

article { page-break-after: always; page-break-inside: avoid; scroll-margin-top: 60px !important }

.red {background-color: lightcoral}
'''


minima_template_base = '''
<!DOCTYPE html>
<html lang="{{ page.lang | default: site.lang | default: "en" }}">

    <head>
      <meta charset="utf-8">
      <meta http-equiv="X-UA-Compatible" content="IE=edge">
      <meta name="viewport" content="width=device-width, initial-scale=1">
      
<!-- Begin Jekyll SEO tag v{{ seo_tag.version }} -->
{% if seo_tag.title? %}
  <title>{{ seo_tag.title }}</title>
{% endif %}

<meta name="generator" content="Jekyll v{{ jekyll.version }}" />

{% if seo_tag.page_title %}
  <meta property="og:title" content="{{ seo_tag.page_title }}" />
{% endif %}

{% if seo_tag.author.name %}
  <meta name="author" content="{{ seo_tag.author.name }}" />
{% endif %}

<meta property="og:locale" content="{{ seo_tag.page_locale }}" />

{% if seo_tag.description %}
  <meta name="description" content="{{ seo_tag.description }}" />
  <meta property="og:description" content="{{ seo_tag.description }}" />
  <meta property="twitter:description" content="{{ seo_tag.description }}" />
{% endif %}

{% if site.url %}
  <link rel="canonical" href="{{ seo_tag.canonical_url }}" />
  <meta property="og:url" content="{{ seo_tag.canonical_url }}" />
{% endif %}

{% if seo_tag.site_title %}
  <meta property="og:site_name" content="{{ seo_tag.site_title }}" />
{% endif %}

{% if seo_tag.image %}
  <meta property="og:image" content="{{ seo_tag.image.path }}" />
  {% if seo_tag.image.height %}
    <meta property="og:image:height" content="{{ seo_tag.image.height }}" />
  {% endif %}
  {% if seo_tag.image.width %}
    <meta property="og:image:width" content="{{ seo_tag.image.width }}" />
  {% endif %}
  {% if seo_tag.image.alt %}
    <meta property="og:image:alt" content="{{ seo_tag.image.alt }}" />
  {% endif %}
{% endif %}

{% if page.date %}
  <meta property="og:type" content="article" />
  <meta property="article:published_time" content="{{ page.date | date_to_xmlschema }}" />
{% else %}
  <meta property="og:type" content="website" />
{% endif %}

{% if paginator.previous_page %}
  <link rel="prev" href="{{ paginator.previous_page_path | absolute_url }}" />
{% endif %}
{% if paginator.next_page %}
  <link rel="next" href="{{ paginator.next_page_path | absolute_url }}" />
{% endif %}

{% if seo_tag.image %}
  <meta name="twitter:card" content="{{ page.twitter.card | default: site.twitter.card | default: "summary_large_image" }}" />
  <meta property="twitter:image" content="{{ seo_tag.image.path }}" />
{% else %}
  <meta name="twitter:card" content="summary" />
{% endif %}

{% if seo_tag.image.alt %}
  <meta name="twitter:image:alt" content="{{ seo_tag.image.alt }}" />
{% endif %}

{% if seo_tag.page_title %}
  <meta property="twitter:title" content="{{ seo_tag.page_title }}" />
{% endif %}

{% if site.twitter %}
  <meta name="twitter:site" content="@{{ site.twitter.username | remove:'@' }}" />

  {% if seo_tag.author.twitter %}
    <meta name="twitter:creator" content="@{{ seo_tag.author.twitter | remove:'@' }}" />
  {% endif %}
{% endif %}

{% if site.facebook %}
  {% if site.facebook.admins %}
    <meta property="fb:admins" content="{{ site.facebook.admins }}" />
  {% endif %}

  {% if site.facebook.publisher %}
    <meta property="article:publisher" content="{{ site.facebook.publisher }}" />
  {% endif %}

  {% if site.facebook.app_id %}
    <meta property="fb:app_id" content="{{ site.facebook.app_id }}" />
  {% endif %}
{% endif %}

{% if site.webmaster_verifications %}
  {% if site.webmaster_verifications.google %}
    <meta name="google-site-verification" content="{{ site.webmaster_verifications.google }}" />
  {% endif %}

  {% if site.webmaster_verifications.bing %}
    <meta name="msvalidate.01" content="{{ site.webmaster_verifications.bing }}" />
  {% endif %}

  {% if site.webmaster_verifications.alexa %}
    <meta name="alexaVerifyID" content="{{ site.webmaster_verifications.alexa }}" />
  {% endif %}

  {% if site.webmaster_verifications.yandex %}
    <meta name="yandex-verification" content="{{ site.webmaster_verifications.yandex }}" />
  {% endif %}

  {% if site.webmaster_verifications.baidu %}
    <meta name="baidu-site-verification" content="{{ site.webmaster_verifications.baidu }}" />
  {% endif %}

  {% if site.webmaster_verifications.facebook %}
    <meta name="facebook-domain-verification" content="{{ site.webmaster_verifications.facebook }}" />
  {% endif %}
{% elsif site.google_site_verification %}
  <meta name="google-site-verification" content="{{ site.google_site_verification }}" />
{% endif %}

<script type="application/ld+json">
  {{ seo_tag.json_ld | jsonify }}
</script>

<!-- End Jekyll SEO tag -->

      <link rel="stylesheet" href="{{ "/assets/css/style.css" | relative_url }}">
      {% comment %}<!-- {%- feed_meta -%} -->{% endcomment %}
      {%- if jekyll.environment == 'production' and site.google_analytics -%}
        <script async src="https://www.googletagmanager.com/gtag/js?id={{ site.google_analytics }}"></script>
        <script>
          window['ga-disable-{{ site.google_analytics }}'] = window.doNotTrack === "1" || navigator.doNotTrack === "1" || navigator.doNotTrack === "yes" || navigator.msDoNotTrack === "1";
          window.dataLayer = window.dataLayer || [];
          function gtag(){window.dataLayer.push(arguments);}
          gtag('js', new Date());

          gtag('config', '{{ site.google_analytics }}');
        </script>
      {%- endif -%}

      {%- include custom-head.html -%}
      
    </head>


  <body>

    <header class="site-header">

      <div class="wrapper">
        {%- assign default_paths = site.pages | map: "path" -%}
        {%- assign page_paths = site.header_pages | default: default_paths -%}
        {%- assign titles_size = site.pages | map: 'title' | join: '' | size -%}
        <a class="site-title" rel="author" href="{{ "/" | relative_url }}">{{ site.title | escape }}</a>

        {%- if titles_size > 0 -%}
          <nav class="site-nav">
            <input type="checkbox" id="nav-trigger" class="nav-trigger" />
            <label for="nav-trigger">
              <span class="menu-icon">
                <svg viewBox="0 0 18 15" width="18px" height="15px">
                  <path d="M18,1.484c0,0.82-0.665,1.484-1.484,1.484H1.484C0.665,2.969,0,2.304,0,1.484l0,0C0,0.665,0.665,0,1.484,0 h15.032C17.335,0,18,0.665,18,1.484L18,1.484z M18,7.516C18,8.335,17.335,9,16.516,9H1.484C0.665,9,0,8.335,0,7.516l0,0 c0-0.82,0.665-1.484,1.484-1.484h15.032C17.335,6.031,18,6.696,18,7.516L18,7.516z M18,13.516C18,14.335,17.335,15,16.516,15H1.484 C0.665,15,0,14.335,0,13.516l0,0c0-0.82,0.665-1.483,1.484-1.483h15.032C17.335,12.031,18,12.695,18,13.516L18,13.516z"/>
                </svg>
              </span>
            </label>

            <div class="trigger">
              {%- for path in page_paths -%}
                {%- assign my_page = site.pages | where: "path", path | first -%}
                {%- if my_page.title -%}
                <a class="page-link" href="{{ my_page.url | relative_url }}">{{ my_page.title | escape }}</a>
                {%- endif -%}
              {%- endfor -%}
            </div>
          </nav>
        {%- endif -%}
      </div>
    </header>

    <main class="page-content" aria-label="Content">
      <div class="wrapper">
        {{ content }}
      </div>
    </main>

    <footer class="site-footer h-card">
      <data class="u-url" href="{{ "/" | relative_url }}"></data>

      <div class="wrapper">

        <div class="footer-col-wrapper">
          <div class="footer-col">
            <p class="feed-subscribe">
              <a href="{{ site.feed.path | default: 'feed.xml' | absolute_url }}">
                <svg class="svg-icon orange">
                  <use xlink:href="{{ 'assets/minima-social-icons.svg#rss' | relative_url }}"></use>
                </svg><span>Subscribe</span>
              </a>
            </p>
          {%- if site.author %}
            <ul class="contact-list">
              {% if site.author.name -%}
                <li class="p-name">{{ site.author.name | escape }}</li>
              {% endif -%}
              {% if site.author.email -%}
                <li><a class="u-email" href="mailto:{{ site.author.email }}">{{ site.author.email }}</a></li>
              {%- endif %}
            </ul>
          {%- endif %}
          </div>
          <div class="footer-col">
            <p>{{ site.description | escape }}</p>
          </div>
        </div>

        <div class="social-links">
            <ul class="social-media-list">
            {%- for entry in site.minima.social_links -%}
                <li>{% assign entry = include.item %}
                  <a {% unless entry.platform == 'rss' %}rel="me" {% endunless %}href="{{ entry.user_url }}" target="_blank" title="{{ entry.title | default: entry.platform }}">
                    <svg class="svg-icon grey">
                      <use xlink:href="{{ '/assets/minima-social-icons.svg#' | append: entry.platform | relative_url }}"></use>
                    </svg>
                  </a>
                </li>
            {%- endfor -%}
            </ul>
        </div>

      </div>

    </footer>

  </body>

</html>
'''


minima_template_page_post = '''
<article class="post">

  <header class="post-header">
    <h1 class="post-title">{{ page.title | escape }}</h1>
  </header>

  <div class="post-content">
    {{ content }}
  </div>

</article>
<article class="post h-entry" itemscope itemtype="http://schema.org/BlogPosting">

  <header class="post-header">
    <h1 class="post-title p-name" itemprop="name headline">{{ page.title | escape }}</h1>
    <p class="post-meta">
      {%- assign date_format = site.minima.date_format | default: "%b %-d, %Y" -%}
      <time class="dt-published" datetime="{{ page.date | date_to_xmlschema }}" itemprop="datePublished">
        {{ page.date | date: date_format }}
      </time>
      {%- if page.modified_date -%}
        ~ 
        {%- assign mdate = page.modified_date | date_to_xmlschema -%}
        <time class="dt-modified" datetime="{{ mdate }}" itemprop="dateModified">
          {{ mdate | date: date_format }}
        </time>
      {%- endif -%}
      {%- if page.author -%}
        • {% for author in page.author %}
          <span itemprop="author" itemscope itemtype="http://schema.org/Person">
            <span class="p-author h-card" itemprop="name">{{ author }}</span></span>
            {%- if forloop.last == false %}, {% endif -%}
        {% endfor %}
      {%- endif -%}</p>
  </header>

  <div class="post-content e-content" itemprop="articleBody">
    {{ content }}
  </div>

  {%- if site.disqus.shortname -%}
    {%- include disqus_comments.html -%}
  {%- endif -%}

  <a class="u-url" href="{{ page.url | relative_url }}" hidden></a>
</article>

'''


######

notion_colors_css = '''

:root {
/* https://docs.super.so/notion-colors */
/* light mode */
--color-text-default: #37352F;
--color-bg-default: #FFFFFF;
--color-pill-default: rgba(206,205,202,0.5);
--color-text-gray : #9B9A97;
--color-bg-gray : #EBECED;
--color-pill-gray : rgba(155,154,151,0.4);
--color-text-brown : #64473A;
--color-bg-brown : #E9E5E3;
--color-pill-brown : rgba(140,46,0,0.2);
--color-text-orange : #D9730D;
--color-bg-orange : #FAEBDD;
--color-pill-orange : rgba(245,93,0,0.2);
--color-text-yellow : #DFAB01;
--color-bg-yellow : #FBF3DB;
--color-pill-yellow : rgba(233,168,0,0.2);
--color-text-green : #0F7B6C;
--color-bg-green : #DDEDEA;
--color-pill-green : rgba(0,135,107,0.2);
--color-text-blue : #0B6E99;
--color-bg-blue : #DDEBF1;
--color-pill-blue : rgba(0,120,223,0.2);
--color-text-purple : #6940A5;
--color-bg-purple : #EAE4F2;
--color-pill-purple : rgba(103,36,222,0.2);
--color-text-pink : #AD1A72;
--color-bg-pink : #F4DFEB;
--color-pill-pink : rgba(221,0,129,0.2);
--color-text-red : #E03E3E;
--color-bg-red : #FBE4E4;
--color-pill-red : rgba(255,0,26,0.2);

/* dark mode */
/*
--color-text-default : rgba(255,255,255,0.9);
--color-bg-default : #2F3437;
--color-pill-default : rgba(206,205,202,0.5);
--color-text-gray : rgba(151,154,155,0.95);
--color-bg-gray : #454B4E;
--color-pill-gray : rgba(151,154,155,0.5);
--color-text-brown : #937264;
--color-bg-brown : #434040;
--color-pill-brown : rgba(147,114,100,0.5);
--color-text-orange : #FFA344;
--color-bg-orange : #594A3A;
--color-pill-orange : rgba(255,163,68,0.5);
--color-text-yellow : #FFDC49;
--color-bg-yellow : #59563B;
--color-pill-yellow : rgba(255,220,73,0.5);
--color-text-green : #4DAB9A;
--color-bg-green : #354C4B;
--color-pill-green : rgba(77,171,154,0.5);
--color-text-blue : #529CCA;
--color-bg-blue : #364954;
--color-pill-blue : rgba(82,156,202,0.5);
--color-text-purple : #9A6DD7;
--color-bg-purple : #443F57;
--color-pill-purple : rgba(154,109,215,0.5);
--color-text-pink : #E255A1;
--color-bg-pink : #533B4C;
--color-pill-pink : rgba(226,85,161,0.5);
--color-text-red : #FF7369;
--color-bg-red : #594141;
--color-pill-red : rgba(255,115,105,0.5);
*/
}

/*
.notion-color-default { color: #37352f }
.notion-color-gray { color: #787774 }
.notion-color-brown { color: #9f6b53 }
.notion-color-orange { color: #d9730d }
.notion-color-yellow { color: #cb912f }
.notion-color-green { color: #448361 }
.notion-color-blue { color: #337ea9 }
.notion-color-purple { color: #9065b0 }
.notion-color-pink { color: #c14c8a }
.notion-color-red { color: #d44c47 }
.notion-color-gray_background { background-color:  #f1f1ef }
.notion-color-brown_background { background-color:  #f4eeee }
.notion-color-orange_background { background-color:  #faebdd }
.notion-color-yellow_background { background-color:  #fbf3db }
.notion-color-green_background { background-color:  #edf3ec }
.notion-color-blue_background { background-color:  #e7f3f8 }
.notion-color-purple_background { background-color:  #f6f3f9 }
.notion-color-pink_background { background-color:  #faf1f5 }
.notion-color-red_background { background-color:  #fdebec }
*/

.notion-color-default { color: var(--color-text-default); }
.notion-color-gray    { color: var(--color-text-gray); }
.notion-color-brown   { color: var(--color-text-brown); }
.notion-color-orange  { color: var(--color-text-orange); }
.notion-color-yellow  { color: var(--color-text-yellow); }
.notion-color-green   { color: var(--color-text-green); }
.notion-color-blue    { color: var(--color-text-blue); }
.notion-color-purple  { color: var(--color-text-purple); }
.notion-color-pink    { color: var(--color-text-pink); }
.notion-color-red     { color: var(--color-text-red); }

.notion-color-default_background { background-color: var(--color-bg-default); }
.notion-color-gray_background    { background-color: var(--color-bg-gray); }
.notion-color-brown_background   { background-color: var(--color-bg-brown); }
.notion-color-orange_background  { background-color: var(--color-bg-orange); }
.notion-color-yellow_background  { background-color: var(--color-bg-yellow); }
.notion-color-green_background   { background-color: var(--color-bg-green); }
.notion-color-blue_background    { background-color: var(--color-bg-blue); }
.notion-color-purple_background  { background-color: var(--color-bg-purple); }
.notion-color-pink_background    { background-color: var(--color-bg-pink); }
.notion-color-red_background     { background-color: var(--color-bg-red); }

'''

#https://www.notionavenue.co/post/notion-color-code-hex-palette 
#Notion Light Mode Hex Code for Background
#Text Color (Best for Icon)
#Notion Default: #37352F
#Notion Grey: #787774
#Notion Brown: #9F6B53
#Notion Orange: #D9730D
#Notion Yellow: #CB912F
#Notion Green: #448361
#Notion Blue: #337EA9
#Notion Purple: #9065B0
#Notion Pink: #C14C8A
#Notion Red: #D44C47
#Notion Light Mode Hex Code for Background
#(Callout and Text background) Best for banner or background
#Notion Grey: #F1F1EF
#Notion Brown: #F4EEEE
#Notion Orange: #FAEBDD
#Notion yellow: #FBF3DB
#Notion green: #EDF3EC
#Notion blue: #E7F3F8
#Notion purple: #F6F3F9
#Notion pink: #FAF1F5
#Notion red: #FDEBEC
#Notion Dark Mode Hex Code
#Notion Dark Mode Hex Code for Text
#Best for Icon
#Notion Grey: #979A9B
#Notion Brown: #937264
#Notion Orange: #FFA344
#Notion Yellow: #FFDC49
#Notion Green: #4DAB9A
#Notion Blue: #529CCA
#Notion Purple: #9A6DD7
#Notion Pink: #E255A1
#Notion Red: #FF7369
#Notion Dark Mode Hex Code for Background
#Best for banner or background
#Notion Grey: #454B4E
#Notion Brown: #594A3A
#Notion Orange: #594A3A
#Notion Yellow: #59563B
#Notion Green: #354C4B
#Notion Blue: #364954
#Notion Purple: #443F57
#Notion Pink: #533B4C
#Notion Red: #594141

twitter_emoji_font_css = '''

@font-face {
    font-family: 'Twemoji Country Flags';
    unicode-range: U+1F1E6-1F1FF, U+1F3F4, U+E0062-E0063, U+E0065, U+E0067, U+E006C, U+E006E, U+E0073-E0074, U+E0077, U+E007F;
    /*src: url('https://cdn.jsdelivr.net/npm/country-flag-emoji-polyfill@0.1/dist/TwemojiCountryFlags.woff2') format('woff2'); */
  src: url(data:font/woff2;base64,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) format('woff2');
}
'''

minimacss_classic_full = '''

@media (prefers-color-scheme: light) and (max-width: 1000000px), (min-width: 0px) {
  :root {
    --minima-brand-color:                       var(--minima-light-brand-color);
    --minima-brand-color-light:                 var(--minima-light-brand-color-light);
    --minima-brand-color-dark:                  var(--minima-light-brand-color-dark );
    --minima-site-title-color:                  var(--minima-light-site-title-color);
    --minima-text-color:                        var(--minima-light-text-color);
    --minima-background-color:                  var(--minima-light-background-color);
    --minima-code-background-color:             var(--minima-light-code-background-color);
    --minima-link-base-color:                   var(--minima-light-link-base-color);
    --minima-link-visited-color:                var(--minima-light-link-visited-color);
    --minima-link-hover-color:                  var(--minima-light-link-hover-color);
    --minima-border-color-01:                   var(--minima-light-border-color-01);
    --minima-border-color-02:                   var(--minima-light-border-color-02);
    --minima-border-color-03:                   var(--minima-light-border-color-03);
    --minima-table-text-color:                  var(--minima-light-table-text-color);
    --minima-table-zebra-color:                 var(--minima-light-table-zebra-color);
    --minima-table-header-bg-color:             var(--minima-light-table-header-bg-color);
    --minima-table-header-border:               var(--minima-light-table-header-border);
    --minima-table-border-color:                var(--minima-light-table-border-color);
    --minima-highlight-c-color:                 var(--minima-light-highlight-c-color);
    --minima-highlight-c-font-style:            var(--minima-light-highlight-c-font-style);
    --minima-highlight-err-color:               var(--minima-light-highlight-err-color);
    --minima-highlight-err-background-color:    var(--minima-light-highlight-err-background-color);
    --minima-highlight-k-font-weight:           var(--minima-light-highlight-k-font-weight);
    --minima-highlight-o-font-weight:           var(--minima-light-highlight-o-font-weight);
    --minima-highlight-cm-color:                var(--minima-light-highlight-cm-color);
    --minima-highlight-cm-font-style:           var(--minima-light-highlight-cm-font-style);
    --minima-highlight-cp-color:                var(--minima-light-highlight-cp-color);
    --minima-highlight-cp-font-weight:          var(--minima-light-highlight-cp-font-weight);
    --minima-highlight-c1-color:                var(--minima-light-highlight-c1-color);
    --minima-highlight-c1-font-style:           var(--minima-light-highlight-c1-font-style);
    --minima-highlight-cs-color:                var(--minima-light-highlight-cs-color);
    --minima-highlight-cs-font-weight:          var(--minima-light-highlight-cs-font-weight);
    --minima-highlight-cs-font-style:           var(--minima-light-highlight-cs-font-style);
    --minima-highlight-gd-color:                var(--minima-light-highlight-gd-color);
    --minima-highlight-gd-background-color:     var(--minima-light-highlight-gd-background-color);
    --minima-highlight-gdx-color:               var(--minima-light-highlight-gdx-color);
    --minima-highlight-gdx-background-color:    var(--minima-light-highlight-gdx-background-color);
    --minima-highlight-ge-font-style:           var(--minima-light-highlight-ge-font-style);
    --minima-highlight-gr-color:                var(--minima-light-highlight-gr-color);
    --minima-highlight-gh-color:                var(--minima-light-highlight-gh-color);
    --minima-highlight-gi-color:                var(--minima-light-highlight-gi-color);
    --minima-highlight-gi-background-color:     var(--minima-light-highlight-gi-background-color);
    --minima-highlight-gix-color:               var(--minima-light-highlight-gix-color);
    --minima-highlight-gix-background-color:    var(--minima-light-highlight-gix-background-color);
    --minima-highlight-go-color:                var(--minima-light-highlight-go-color);
    --minima-highlight-gp-color:                var(--minima-light-highlight-gp-color);
    --minima-highlight-gs-font-weight:          var(--minima-light-highlight-gs-font-weight);
    --minima-highlight-gu-color:                var(--minima-light-highlight-gu-color);
    --minima-highlight-gt-color:                var(--minima-light-highlight-gt-color);
    --minima-highlight-kc-font-weight:          var(--minima-light-highlight-kc-font-weight);
    --minima-highlight-kd-font-weight:          var(--minima-light-highlight-kd-font-weight);
    --minima-highlight-kp-font-weight:          var(--minima-light-highlight-kp-font-weight);
    --minima-highlight-kr-font-weight:          var(--minima-light-highlight-kr-font-weight);
    --minima-highlight-kt-color:                var(--minima-light-highlight-kt-color);
    --minima-highlight-kt-font-weight:          var(--minima-light-highlight-kt-font-weight);
    --minima-highlight-m-color:                 var(--minima-light-highlight-m-color );
    --minima-highlight-s-color:                 var(--minima-light-highlight-s-color );
    --minima-highlight-na-color:                var(--minima-light-highlight-na-color);
    --minima-highlight-nb-color:                var(--minima-light-highlight-nb-color);
    --minima-highlight-nc-color:                var(--minima-light-highlight-nc-color);
    --minima-highlight-nc-font-weight:          var(--minima-light-highlight-nc-font-weight);
    --minima-highlight-no-color:                var(--minima-light-highlight-no-color);
    --minima-highlight-ni-color:                var(--minima-light-highlight-ni-color);
    --minima-highlight-ne-color:                var(--minima-light-highlight-ne-color);
    --minima-highlight-ne-font-weight:          var(--minima-light-highlight-ne-font-weight);
    --minima-highlight-nf-color:                var(--minima-light-highlight-nf-color);
    --minima-highlight-nf-font-weight:          var(--minima-light-highlight-nf-font-weight);
    --minima-highlight-nn-color:                var(--minima-light-highlight-nn-color);
    --minima-highlight-nt-color:                var(--minima-light-highlight-nt-color);
    --minima-highlight-nv-color:                var(--minima-light-highlight-nv-color);
    --minima-highlight-ow-font-weight:          var(--minima-light-highlight-ow-font-weight);
    --minima-highlight-w-color:                 var(--minima-light-highlight-w-color );
    --minima-highlight-mf-color:                var(--minima-light-highlight-mf-color);
    --minima-highlight-mh-color:                var(--minima-light-highlight-mh-color);
    --minima-highlight-mi-color:                var(--minima-light-highlight-mi-color);
    --minima-highlight-mo-color:                var(--minima-light-highlight-mo-color);
    --minima-highlight-sb-color:                var(--minima-light-highlight-sb-color);
    --minima-highlight-sc-color:                var(--minima-light-highlight-sc-color);
    --minima-highlight-sd-color:                var(--minima-light-highlight-sd-color);
    --minima-highlight-s2-color:                var(--minima-light-highlight-s2-color);
    --minima-highlight-se-color:                var(--minima-light-highlight-se-color);
    --minima-highlight-sh-color:                var(--minima-light-highlight-sh-color);
    --minima-highlight-si-color:                var(--minima-light-highlight-si-color);
    --minima-highlight-sx-color:                var(--minima-light-highlight-sx-color);
    --minima-highlight-sr-color:                var(--minima-light-highlight-sr-color);
    --minima-highlight-s1-color:                var(--minima-light-highlight-s1-color);
    --minima-highlight-ss-color:                var(--minima-light-highlight-ss-color);
    --minima-highlight-bp-color:                var(--minima-light-highlight-bp-color);
    --minima-highlight-vc-color:                var(--minima-light-highlight-vc-color);
    --minima-highlight-vg-color:                var(--minima-light-highlight-vg-color);
    --minima-highlight-vi-color:                var(--minima-light-highlight-vi-color);
    --minima-highlight-il-color:                var(--minima-light-highlight-il-color); } }

@media (prefers-color-scheme: dark) and (max-width: 0px), (min-width: 1000000px) {
  :root {
    --minima-brand-color:                       var(--minima-dark-brand-color);
    --minima-brand-color-light:                 var(--minima-dark-brand-color-light);
    --minima-brand-color-dark:                  var(--minima-dark-brand-color-dark );
    --minima-site-title-color:                  var(--minima-dark-site-title-color);
    --minima-text-color:                        var(--minima-dark-text-color);
    --minima-background-color:                  var(--minima-dark-background-color);
    --minima-code-background-color:             var(--minima-dark-code-background-color);
    --minima-link-base-color:                   var(--minima-dark-link-base-color);
    --minima-link-visited-color:                var(--minima-dark-link-visited-color);
    --minima-link-hover-color:                  var(--minima-dark-link-hover-color);
    --minima-border-color-01:                   var(--minima-dark-border-color-01);
    --minima-border-color-02:                   var(--minima-dark-border-color-02);
    --minima-border-color-03:                   var(--minima-dark-border-color-03);
    --minima-table-text-color:                  var(--minima-dark-table-text-color);
    --minima-table-zebra-color:                 var(--minima-dark-table-zebra-color);
    --minima-table-header-bg-color:             var(--minima-dark-table-header-bg-color);
    --minima-table-header-border:               var(--minima-dark-table-header-border);
    --minima-table-border-color:                var(--minima-dark-table-border-color);
    --minima-highlight-c-color:                 var(--minima-dark-highlight-c-color);
    --minima-highlight-c-font-style:            var(--minima-dark-highlight-c-font-style);
    --minima-highlight-err-color:               var(--minima-dark-highlight-err-color);
    --minima-highlight-err-background-color:    var(--minima-dark-highlight-err-background-color);
    --minima-highlight-k-font-weight:           var(--minima-dark-highlight-k-font-weight);
    --minima-highlight-o-font-weight:           var(--minima-dark-highlight-o-font-weight);
    --minima-highlight-cm-color:                var(--minima-dark-highlight-cm-color);
    --minima-highlight-cm-font-style:           var(--minima-dark-highlight-cm-font-style);
    --minima-highlight-cp-color:                var(--minima-dark-highlight-cp-color);
    --minima-highlight-cp-font-weight:          var(--minima-dark-highlight-cp-font-weight);
    --minima-highlight-c1-color:                var(--minima-dark-highlight-c1-color);
    --minima-highlight-c1-font-style:           var(--minima-dark-highlight-c1-font-style);
    --minima-highlight-cs-color:                var(--minima-dark-highlight-cs-color);
    --minima-highlight-cs-font-weight:          var(--minima-dark-highlight-cs-font-weight);
    --minima-highlight-cs-font-style:           var(--minima-dark-highlight-cs-font-style);
    --minima-highlight-gd-color:                var(--minima-dark-highlight-gd-color);
    --minima-highlight-gd-background-color:     var(--minima-dark-highlight-gd-background-color);
    --minima-highlight-gdx-color:               var(--minima-dark-highlight-gdx-color);
    --minima-highlight-gdx-background-color:    var(--minima-dark-highlight-gdx-background-color);
    --minima-highlight-ge-font-style:           var(--minima-dark-highlight-ge-font-style);
    --minima-highlight-gr-color:                var(--minima-dark-highlight-gr-color);
    --minima-highlight-gh-color:                var(--minima-dark-highlight-gh-color);
    --minima-highlight-gi-color:                var(--minima-dark-highlight-gi-color);
    --minima-highlight-gi-background-color:     var(--minima-dark-highlight-gi-background-color);
    --minima-highlight-gix-color:               var(--minima-dark-highlight-gix-color);
    --minima-highlight-gix-background-color:    var(--minima-dark-highlight-gix-background-color);
    --minima-highlight-go-color:                var(--minima-dark-highlight-go-color);
    --minima-highlight-gp-color:                var(--minima-dark-highlight-gp-color);
    --minima-highlight-gs-font-weight:          var(--minima-dark-highlight-gs-font-weight);
    --minima-highlight-gu-color:                var(--minima-dark-highlight-gu-color);
    --minima-highlight-gt-color:                var(--minima-dark-highlight-gt-color);
    --minima-highlight-kc-font-weight:          var(--minima-dark-highlight-kc-font-weight);
    --minima-highlight-kd-font-weight:          var(--minima-dark-highlight-kd-font-weight);
    --minima-highlight-kp-font-weight:          var(--minima-dark-highlight-kp-font-weight);
    --minima-highlight-kr-font-weight:          var(--minima-dark-highlight-kr-font-weight);
    --minima-highlight-kt-color:                var(--minima-dark-highlight-kt-color);
    --minima-highlight-kt-font-weight:          var(--minima-dark-highlight-kt-font-weight);
    --minima-highlight-m-color:                 var(--minima-dark-highlight-m-color );
    --minima-highlight-s-color:                 var(--minima-dark-highlight-s-color );
    --minima-highlight-na-color:                var(--minima-dark-highlight-na-color);
    --minima-highlight-nb-color:                var(--minima-dark-highlight-nb-color);
    --minima-highlight-nc-color:                var(--minima-dark-highlight-nc-color);
    --minima-highlight-nc-font-weight:          var(--minima-dark-highlight-nc-font-weight);
    --minima-highlight-no-color:                var(--minima-dark-highlight-no-color);
    --minima-highlight-ni-color:                var(--minima-dark-highlight-ni-color);
    --minima-highlight-ne-color:                var(--minima-dark-highlight-ne-color);
    --minima-highlight-ne-font-weight:          var(--minima-dark-highlight-ne-font-weight);
    --minima-highlight-nf-color:                var(--minima-dark-highlight-nf-color);
    --minima-highlight-nf-font-weight:          var(--minima-dark-highlight-nf-font-weight);
    --minima-highlight-nn-color:                var(--minima-dark-highlight-nn-color);
    --minima-highlight-nt-color:                var(--minima-dark-highlight-nt-color);
    --minima-highlight-nv-color:                var(--minima-dark-highlight-nv-color);
    --minima-highlight-ow-font-weight:          var(--minima-dark-highlight-ow-font-weight);
    --minima-highlight-w-color:                 var(--minima-dark-highlight-w-color );
    --minima-highlight-mf-color:                var(--minima-dark-highlight-mf-color);
    --minima-highlight-mh-color:                var(--minima-dark-highlight-mh-color);
    --minima-highlight-mi-color:                var(--minima-dark-highlight-mi-color);
    --minima-highlight-mo-color:                var(--minima-dark-highlight-mo-color);
    --minima-highlight-sb-color:                var(--minima-dark-highlight-sb-color);
    --minima-highlight-sc-color:                var(--minima-dark-highlight-sc-color);
    --minima-highlight-sd-color:                var(--minima-dark-highlight-sd-color);
    --minima-highlight-s2-color:                var(--minima-dark-highlight-s2-color);
    --minima-highlight-se-color:                var(--minima-dark-highlight-se-color);
    --minima-highlight-sh-color:                var(--minima-dark-highlight-sh-color);
    --minima-highlight-si-color:                var(--minima-dark-highlight-si-color);
    --minima-highlight-sx-color:                var(--minima-dark-highlight-sx-color);
    --minima-highlight-sr-color:                var(--minima-dark-highlight-sr-color);
    --minima-highlight-s1-color:                var(--minima-dark-highlight-s1-color);
    --minima-highlight-ss-color:                var(--minima-dark-highlight-ss-color);
    --minima-highlight-bp-color:                var(--minima-dark-highlight-bp-color);
    --minima-highlight-vc-color:                var(--minima-dark-highlight-vc-color);
    --minima-highlight-vg-color:                var(--minima-dark-highlight-vg-color);
    --minima-highlight-vi-color:                var(--minima-dark-highlight-vi-color);
    --minima-highlight-il-color:                var(--minima-dark-highlight-il-color); } }

/* begin skins/auto.scss */
:root {
  /* Light mode */
  --minima-light-brand-color-hue: 0;
  --minima-light-brand-color-saturation: 0%;
  --minima-light-brand-color-lightness: 51%;
  --minima-light-text-color-hue: 0;
  --minima-light-text-color-saturation: 0%;
  --minima-light-text-color-lightness: 7%;
  --minima-light-link-base-color-hue: 214;
  --minima-light-link-base-color-saturation: 76%;
  --minima-light-link-base-color-lightness: 53%;
  --minima-light-brand-color:          hsl(var(--minima-light-brand-color-hue), var(--minima-light-brand-color-saturation), var(--minima-light-brand-color-lightness));
  --minima-light-brand-color-light:    hsl(var(--minima-light-brand-color-hue), var(--minima-light-brand-color-saturation), calc(var(--minima-light-brand-color-lightness) + 40%));
  --minima-light-brand-color-dark:    hsl(var(--minima-light-brand-color-hue), var(--minima-light-brand-color-saturation), calc(var(--minima-light-brand-color-lightness) - 25%));
  --minima-light-site-title-color:     var(--minima-light-brand-color-dark);
  --minima-light-text-color:           hsl(var(--minima-light-text-color-hue), var(--minima-light-text-color-saturation), var(--minima-light-text-color-lightness));
  --minima-light-background-color:     #fdfdfd;
  --minima-light-code-background-color:#eeeeff;
  --minima-light-link-base-color:      hsl(var(--minima-light-link-base-color-hue), var(--minima-light-link-base-color-saturation), var(--minima-light-link-base-color-lightness)) ;
  --minima-light-link-visited-color:   hsl(var(--minima-light-link-base-color-hue), var(--minima-light-link-base-color-saturation), calc(var(--minima-light-link-base-color-lightness) - 15%)) ;
  --minima-light-link-hover-color:     var(--minima-light-text-color) ;
  --minima-light-border-color-01:      var(--minima-light-brand-color-light) ;
  --minima-light-border-color-02:      hsl(var(--minima-light-brand-color-hue), var(--minima-light-brand-color-saturation), calc(var(--minima-light-brand-color-lightness) + 35%)) ;
  --minima-light-border-color-03:      var(--minima-light-brand-color-dark) ;
  --minima-light-table-text-color:     hsl(var(--minima-light-text-color-hue), var(--minima-light-text-color-saturation), calc(var(--minima-light-text-color-lightness) + 18%)) ;
  --minima-light-table-zebra-color:    hsl(var(--minima-light-brand-color-hue), var(--minima-light-brand-color-saturation), calc(var(--minima-light-brand-color-lightness) + 46%)) ;
  --minima-light-table-header-bg-color:hsl(var(--minima-light-brand-color-hue), var(--minima-light-brand-color-saturation), calc(var(--minima-light-brand-color-lightness) + 43%)) ;
  --minima-light-table-header-border:  hsl(var(--minima-light-brand-color-hue), var(--minima-light-brand-color-saturation), calc(var(--minima-light-brand-color-lightness) + 37%)) ;
  --minima-light-table-border-color:   var(--minima-light-border-color-01) ;
  /* Dark mode */
  --minima-dark-brand-color-hue: 0;
  --minima-dark-brand-color-saturation: 0%;
  --minima-dark-brand-color-lightness: 60%;
  --minima-dark-background-color-hue: 0;
  --minima-dark-background-color-saturation: 0%;
  --minima-dark-background-color-lightness: 9%;
  --minima-dark-brand-color:           hsl(var(--minima-dark-brand-color-hue), var(--minima-dark-brand-color-saturation), var(--minima-dark-brand-color-lightness));
  --minima-dark-brand-color-light:     hsl(var(--minima-dark-brand-color-hue), var(--minima-dark-brand-color-saturation), calc(var(--minima-dark-brand-color-lightness) + 5%));
  --minima-dark-brand-color-dark:      hsl(var(--minima-dark-brand-color-hue), var(--minima-dark-brand-color-saturation), calc(var(--minima-dark-brand-color-lightness) - 35%));
  --minima-dark-site-title-color:      var(--minima-dark-brand-color-lightt);
  --minima-dark-text-color:            #bbbbbb;
  --minima-dark-background-color:      hsl(var(--minima-dark-background-color-hue), var(--minima-dark-background-color-saturation), var(--minima-dark-background-color-lightness));
  --minima-dark-code-background-color: #212121;
  --minima-dark-link-base-color:       #79b8ff ;
  --minima-dark-link-visited-color:    var(--minima-dark-link-base-color);
  --minima-dark-link-hover-color:      var(--minima-dark-text-color);
  --minima-dark-border-color-01:       var(--minima-dark-brand-color-dark);
  --minima-dark-border-color-02:       var(--minima-dark-brand-color-light);
  --minima-dark-border-color-03:       var(--minima-dark-brand-color);
  --minima-dark-table-text-color:      var(--minima-dark-text-color);
  --minima-dark-table-zebra-color:     hsl(var(--minima-dark-background-color-hue), var(--minima-dark-background-color-saturation), calc(var(--minima-dark-background-color-lightness) + 4%));
  --minima-dark-table-header-bg-color: hsl(var(--minima-dark-background-color-hue), var(--minima-dark-background-color-saturation), calc(var(--minima-dark-background-color-lightness) + 10%));
  --minima-dark-table-header-border:   hsl(var(--minima-dark-background-color-hue), var(--minima-dark-background-color-saturation), calc(var(--minima-dark-background-color-lightness) + 21%));
  --minima-dark-table-border-color:    var(--minima-dark-border-color-01); }

/*
// Syntax highlighting styles should be adjusted appropriately for every "skin"
// ----------------------------------------------------------------------------
*/
/* .lm-highlight */
:root {
  --minima-light-highlight-c-color: #998;
  /*Comment*/
  --minima-light-highlight-c-font-style: italic ;
  /*Comment*/
  --minima-light-highlight-err-color: #a61717;
  /*Error*/
  --minima-light-highlight-err-background-color: #e3d2d2 ;
  /*Error*/
  --minima-light-highlight-k-font-weight: bold ;
  /*Keyword*/
  --minima-light-highlight-o-font-weight: bold ;
  /*Operator*/
  --minima-light-highlight-cm-color: #998;
  /*Comment.Multiline*/
  --minima-light-highlight-cm-font-style: italic ;
  /*Comment.Multiline*/
  --minima-light-highlight-cp-color: #999;
  /*Comment.Preproc*/
  --minima-light-highlight-cp-font-weight: bold ;
  /*Comment.Preproc*/
  --minima-light-highlight-c1-color: #998;
  /*Comment.Single*/
  --minima-light-highlight-c1-font-style: italic ;
  /*Comment.Single*/
  --minima-light-highlight-cs-color: #999;
  /*Comment.Special*/
  --minima-light-highlight-cs-font-weight: bold;
  /*Comment.Special*/
  --minima-light-highlight-cs-font-style: italic ;
  /*Comment.Special*/
  --minima-light-highlight-gd-color: #000;
  /*Generic.Deleted*/
  --minima-light-highlight-gd-background-color: #fdd ;
  /*Generic.Deleted*/
  --minima-light-highlight-gdx-color: #000;
  /*Generic.Deleted.Specific*/
  --minima-light-highlight-gdx-background-color: #faa ;
  /*Generic.Deleted.Specific*/
  --minima-light-highlight-ge-font-style: italic ;
  /*Generic.Emph*/
  --minima-light-highlight-gr-color: #a00 ;
  /*Generic.Error*/
  --minima-light-highlight-gh-color: #999 ;
  /*Generic.Heading*/
  --minima-light-highlight-gi-color: #000;
  /*Generic.Inserted*/
  --minima-light-highlight-gi-background-color: #dfd ;
  /*Generic.Inserted*/
  --minima-light-highlight-gix-color: #000;
  /*Generic.Inserted.Specific*/
  --minima-light-highlight-gix-background-color: #afa ;
  /*Generic.Inserted.Specific*/
  --minima-light-highlight-go-color: #888 ;
  /*Generic.Output*/
  --minima-light-highlight-gp-color: #555 ;
  /*Generic.Prompt*/
  --minima-light-highlight-gs-font-weight: bold ;
  /*Generic.Strong*/
  --minima-light-highlight-gu-color: #aaa ;
  /*Generic.Subheading*/
  --minima-light-highlight-gt-color: #a00 ;
  /*Generic.Traceback*/
  --minima-light-highlight-kc-font-weight: bold ;
  /*Keyword.Constant*/
  --minima-light-highlight-kd-font-weight: bold ;
  /*Keyword.Declaration*/
  --minima-light-highlight-kp-font-weight: bold ;
  /*Keyword.Pseudo*/
  --minima-light-highlight-kr-font-weight: bold ;
  /*Keyword.Reserved*/
  --minima-light-highlight-kt-color: #458;
  /*Keyword.Type */
  --minima-light-highlight-kt-font-weight: bold ;
  /*Keyword.Type*/
  --minima-light-highlight-m-color: #099 ;
  /*Literal.Number*/
  --minima-light-highlight-s-color: #d14 ;
  /*Literal.String*/
  --minima-light-highlight-na-color: #008080 ;
  /*Name.Attribute*/
  --minima-light-highlight-nb-color: #0086B3 ;
  /*Name.Builtin*/
  --minima-light-highlight-nc-color: #458;
  /*Name.Class*/
  --minima-light-highlight-nc-font-weight: bold ;
  /*Name.Class*/
  --minima-light-highlight-no-color: #008080 ;
  /*Name.Constant*/
  --minima-light-highlight-ni-color: #800080 ;
  /*Name.Entity*/
  --minima-light-highlight-ne-color: #900;
  /*Name.Exception*/
  --minima-light-highlight-ne-font-weight: bold ;
  /*Name.Exception*/
  --minima-light-highlight-nf-color: #900;
  /*Name.Function*/
  --minima-light-highlight-nf-font-weight: bold ;
  /*Name.Function*/
  --minima-light-highlight-nn-color: #555;
  /*Name.Namespace*/
  --minima-light-highlight-nt-color: #000080;
  /*Name.Tag*/
  --minima-light-highlight-nv-color: #008080;
  /*Name.Variable*/
  --minima-light-highlight-ow-font-weight: bold ;
  /*Operator.Word*/
  --minima-light-highlight-w-color: #bbb;
  /*Text.Whitespace*/
  --minima-light-highlight-mf-color: #099;
  /*Literal.Number.Float*/
  --minima-light-highlight-mh-color: #099;
  /*Literal.Number.Hex*/
  --minima-light-highlight-mi-color: #099;
  /*Literal.Number.Integer*/
  --minima-light-highlight-mo-color: #099;
  /*Literal.Number.Oct*/
  --minima-light-highlight-sb-color: #d14;
  /*Literal.String.Backtick*/
  --minima-light-highlight-sc-color: #d14;
  /*Literal.String.Char*/
  --minima-light-highlight-sd-color: #d14;
  /*Literal.String.Doc*/
  --minima-light-highlight-s2-color: #d14;
  /*Literal.String.Double*/
  --minima-light-highlight-se-color: #d14;
  /*Literal.String.Escape*/
  --minima-light-highlight-sh-color: #d14;
  /*Literal.String.Heredoc*/
  --minima-light-highlight-si-color: #d14;
  /*Literal.String.Interpol*/
  --minima-light-highlight-sx-color: #d14;
  /*Literal.String.Other*/
  --minima-light-highlight-sr-color: #009926;
  /*Literal.String.Regex*/
  --minima-light-highlight-s1-color: #d14;
  /*Literal.String.Single*/
  --minima-light-highlight-ss-color: #990073;
  /*Literal.String.Symbol*/
  --minima-light-highlight-bp-color: #999;
  /*Name.Builtin.Pseudo*/
  --minima-light-highlight-vc-color: #008080;
  /*Name.Variable.Class*/
  --minima-light-highlight-vg-color: #008080;
  /*Name.Variable.Global*/
  --minima-light-highlight-vi-color: #008080;
  /*Name.Variable.Instance*/
  --minima-light-highlight-il-color: #099;
  /*Literal.Number.Integer.Long*/ }

/* .dm-highlight */
:root {
  --minima-dark-highlight-c-color: #545454;
  /*Comment*/
  --minima-dark-highlight-c-font-style: italic ;
  /*Comment*/
  --minima-dark-highlight-err-color: #f07178;
  /*Error*/
  --minima-dark-highlight-err-background-color: #e3d2d2 ;
  /*Error*/
  --minima-dark-highlight-k-color: #89DDFF;
  /*Keyword*/
  --minima-dark-highlight-k-font-weight: bold ;
  /*Keyword*/
  --minima-dark-highlight-o-font-weight: bold ;
  /*Operator*/
  --minima-dark-highlight-cm-color: #545454;
  /*Comment.Multiline*/
  --minima-dark-highlight-cm-font-style: italic ;
  /*Comment.Multiline*/
  --minima-dark-highlight-cp-color: #545454;
  /*Comment.Preproc*/
  --minima-dark-highlight-cp-font-weight: bold ;
  /*Comment.Preproc*/
  --minima-dark-highlight-c1-color: #545454;
  /*Comment.Single*/
  --minima-dark-highlight-c1-font-style: italic ;
  /*Comment.Single*/
  --minima-dark-highlight-cs-color: #545454;
  /*Comment.Special*/
  --minima-dark-highlight-cs-font-weight: bold;
  /*Comment.Special*/
  --minima-dark-highlight-cs-font-style: italic ;
  /*Comment.Special*/
  --minima-dark-highlight-gd-color: #000;
  /*Generic.Deleted*/
  --minima-dark-highlight-gd-background-color: #fdd;
  /*Generic.Deleted*/
  --minima-dark-highlight-gdx-color: #000;
  /*Generic.Deleted.Specific*/
  --minima-dark-highlight-gdx-background-color: #faa ;
  /*Generic.Deleted.Specific*/
  --minima-dark-highlight-ge-font-style: italic ;
  /*Generic.Emph*/
  --minima-dark-highlight-gr-color: #f07178 ;
  /*Generic.Error*/
  --minima-dark-highlight-gh-color: #999 ;
  /*Generic.Heading*/
  --minima-dark-highlight-gi-color: #000;
  /*Generic.Inserted*/
  --minima-dark-highlight-gi-background-color: #dfd ;
  /*Generic.Inserted*/
  --minima-dark-highlight-gix-color: #000;
  /*Generic.Inserted.Specific*/
  --minima-dark-highlight-gix-background-color: #afa ;
  /*Generic.Inserted.Specific*/
  --minima-dark-highlight-go-color: #888 ;
  /*Generic.Output*/
  --minima-dark-highlight-gp-color: #555 ;
  /*Generic.Prompt*/
  --minima-dark-highlight-gs-font-weight: bold ;
  /*Generic.Strong*/
  --minima-dark-highlight-gu-color: #aaa ;
  /*Generic.Subheading*/
  --minima-dark-highlight-gt-color: #f07178 ;
  /*Generic.Traceback*/
  --minima-dark-highlight-kc-font-weight: bold ;
  /*Keyword.Constant*/
  --minima-dark-highlight-kd-font-weight: bold ;
  /*Keyword.Declaration*/
  --minima-dark-highlight-kp-font-weight: bold ;
  /*Keyword.Pseudo*/
  --minima-dark-highlight-kr-font-weight: bold ;
  /*Keyword.Reserved*/
  --minima-dark-highlight-kt-color: #FFCB6B;
  /*Keyword.Type*/
  --minima-dark-highlight-kt-font-weight: bold ;
  /*Keyword.Type*/
  --minima-dark-highlight-m-color: #F78C6C ;
  /*Literal.Number*/
  --minima-dark-highlight-s-color: #C3E88D ;
  /*Literal.String*/
  --minima-dark-highlight-na-color: #008080 ;
  /*Name.Attribute*/
  --minima-dark-highlight-nb-color: #EEFFFF ;
  /*Name.Builtin*/
  --minima-dark-highlight-nc-color: #FFCB6B;
  /*Name.Class*/
  --minima-dark-highlight-nc-font-weight: bold ;
  /*Name.Class*/
  --minima-dark-highlight-no-color: #008080 ;
  /*Name.Constant*/
  --minima-dark-highlight-ni-color: #800080 ;
  /*Name.Entity*/
  --minima-dark-highlight-ne-color: #900;
  /*Name.Exception*/
  --minima-dark-highlight-ne-font-weight: bold ;
  /*Name.Exception*/
  --minima-dark-highlight-nf-color: #82AAFF;
  /*Name.Function*/
  --minima-dark-highlight-nf-font-weight: bold ;
  /*Name.Function*/
  --minima-dark-highlight-nn-color: #555 ;
  /*Name.Namespace*/
  --minima-dark-highlight-nt-color: #FFCB6B ;
  /*Name.Tag*/
  --minima-dark-highlight-nv-color: #EEFFFF ;
  /*Name.Variable*/
  --minima-dark-highlight-ow-font-weight: bold ;
  /*Operator.Word*/
  --minima-dark-highlight-w-color: #EEFFFF ;
  /*Text.Whitespace*/
  --minima-dark-highlight-mf-color: #F78C6C ;
  /*Literal.Number.Float*/
  --minima-dark-highlight-mh-color: #F78C6C ;
  /*Literal.Number.Hex*/
  --minima-dark-highlight-mi-color: #F78C6C ;
  /*Literal.Number.Integer*/
  --minima-dark-highlight-mo-color: #F78C6C ;
  /*Literal.Number.Oct*/
  --minima-dark-highlight-sb-color: #C3E88D ;
  /*Literal.String.Backtick*/
  --minima-dark-highlight-sc-color: #C3E88D ;
  /*Literal.String.Char*/
  --minima-dark-highlight-sd-color: #C3E88D ;
  /*Literal.String.Doc*/
  --minima-dark-highlight-s2-color: #C3E88D ;
  /*Literal.String.Double*/
  --minima-dark-highlight-se-color: #EEFFFF ;
  /*Literal.String.Escape*/
  --minima-dark-highlight-sh-color: #C3E88D ;
  /*Literal.String.Heredoc*/
  --minima-dark-highlight-si-color: #C3E88D ;
  /*Literal.String.Interpol*/
  --minima-dark-highlight-sx-color: #C3E88D ;
  /*Literal.String.Other*/
  --minima-dark-highlight-sr-color: #C3E88D ;
  /*Literal.String.Regex*/
  --minima-dark-highlight-s1-color: #C3E88D ;
  /*Literal.String.Single*/
  --minima-dark-highlight-ss-color: #C3E88D ;
  /*Literal.String.Symbol*/
  --minima-dark-highlight-bp-color: #999 ;
  /*Name.Builtin.Pseudo*/
  --minima-dark-highlight-vc-color: #FFCB6B ;
  /*Name.Variable.Class*/
  --minima-dark-highlight-vg-color: #EEFFFF ;
  /*Name.Variable.Global*/
  --minima-dark-highlight-vi-color: #EEFFFF ;
  /*Name.Variable.Instance*/
  --minima-dark-highlight-il-color: #F78C6C ;
  /*Literal.Number.Integer.Long*/ }

.highlight {
  /* Comment*/
  /* Error*/
  /* Keyword*/
  /* Operator*/
  /* Comment.Multiline*/
  /* Comment.Preproc*/
  /* Comment.Single*/
  /* Comment.Special*/
  /* Generic.Deleted*/
  /* Generic.Deleted.Specific*/
  /* Generic.Emph*/
  /* Generic.Error*/
  /* Generic.Heading*/
  /* Generic.Inserted*/
  /* Generic.Inserted.Specific*/
  /* Generic.Output*/
  /* Generic.Prompt*/
  /* Generic.Strong*/
  /* Generic.Subheading*/
  /* Generic.Traceback*/
  /* Keyword.Constant*/
  /* Keyword.Declaration*/
  /* Keyword.Pseudo*/
  /* Keyword.Reserved*/
  /* Keyword.Type*/
  /* Literal.Number*/
  /* Literal.String*/
  /* Name.Attribute*/
  /* Name.Builtin*/
  /* Name.Class*/
  /* Name.Constant*/
  /* Name.Entity*/
  /* Name.Exception*/
  /* Name.Function*/
  /* Name.Namespace*/
  /* Name.Tag*/
  /* Name.Variable*/
  /* Operator.Word*/
  /* Text.Whitespace*/
  /* Literal.Number.Float*/
  /* Literal.Number.Hex*/
  /* Literal.Number.Integer*/
  /* Literal.Number.Oct*/
  /* Literal.String.Backtick*/
  /* Literal.String.Char*/
  /* Literal.String.Doc*/
  /* Literal.String.Double*/
  /* Literal.String.Escape*/
  /* Literal.String.Heredoc*/
  /* Literal.String.Interpol*/
  /* Literal.String.Other*/
  /* Literal.String.Regex*/
  /* Literal.String.Single*/
  /* Literal.String.Symbol*/
  /* Name.Builtin.Pseudo*/
  /* Name.Variable.Class*/
  /* Name.Variable.Global*/
  /* Name.Variable.Instance*/
  /* Literal.Number.Integer.Long*/ }
  .highlight .c {
    color: var(--minima-highlight-c-color);
    background-color: var(--minima-highlight-c-background-color);
    font-style: var(--minima-highlight-c-font-style);
    font-weight: var(--minima-highlight-c-font-weight); }
  .highlight .err {
    color: var(--minima-highlight-err-color);
    background-color: var(--minima-highlight-err-background-color);
    font-style: var(--minima-highlight-err-font-style);
    font-weight: var(--minima-highlight-err-font-weight); }
  .highlight .k {
    color: var(--minima-highlight-k-color);
    background-color: var(--minima-highlight-k-background-color);
    font-style: var(--minima-highlight-k-font-style);
    font-weight: var(--minima-highlight-k-font-weight); }
  .highlight .o {
    color: var(--minima-highlight-o-color);
    background-color: var(--minima-highlight-o-background-color);
    font-style: var(--minima-highlight-o-font-style);
    font-weight: var(--minima-highlight-o-font-weight); }
  .highlight .cm {
    color: var(--minima-highlight-cm-color);
    background-color: var(--minima-highlight-cm-background-color);
    font-style: var(--minima-highlight-cm-font-style);
    font-weight: var(--minima-highlight-cm-font-weight); }
  .highlight .cp {
    color: var(--minima-highlight-cp-color);
    background-color: var(--minima-highlight-cp-background-color);
    font-style: var(--minima-highlight-cp-font-style);
    font-weight: var(--minima-highlight-cp-font-weight); }
  .highlight .c1 {
    color: var(--minima-highlight-c1-color);
    background-color: var(--minima-highlight-c1-background-color);
    font-style: var(--minima-highlight-c1-font-style);
    font-weight: var(--minima-highlight-c1-font-weight); }
  .highlight .cs {
    color: var(--minima-highlight-cs-color);
    background-color: var(--minima-highlight-cs-background-color);
    font-style: var(--minima-highlight-cs-font-style);
    font-weight: var(--minima-highlight-cs-font-weight); }
  .highlight .gd {
    color: var(--minima-highlight-gd-color);
    background-color: var(--minima-highlight-gd-background-color);
    font-style: var(--minima-highlight-gd-font-style);
    font-weight: var(--minima-highlight-gd-font-weight); }
  .highlight .gd .x {
    color: var(--minima-highlight-gdx-color);
    background-color: var(--minima-highlight-gdx-background-color);
    font-style: var(--minima-highlight-gdx-font-style);
    font-weight: var(--minima-highlight-gdx-font-weight); }
  .highlight .ge {
    color: var(--minima-highlight-ge-color);
    background-color: var(--minima-highlight-ge-background-color);
    font-style: var(--minima-highlight-ge-font-style);
    font-weight: var(--minima-highlight-ge-font-weight); }
  .highlight .gr {
    color: var(--minima-highlight-gr-color);
    background-color: var(--minima-highlight-gr-background-color);
    font-style: var(--minima-highlight-gr-font-style);
    font-weight: var(--minima-highlight-gr-font-weight); }
  .highlight .gh {
    color: var(--minima-highlight-gh-color);
    background-color: var(--minima-highlight-gh-background-color);
    font-style: var(--minima-highlight-gh-font-style);
    font-weight: var(--minima-highlight-gh-font-weight); }
  .highlight .gi {
    color: var(--minima-highlight-gi-color);
    background-color: var(--minima-highlight-gi-background-color);
    font-style: var(--minima-highlight-gi-font-style);
    font-weight: var(--minima-highlight-gi-font-weight); }
  .highlight .gi .x {
    color: var(--minima-highlight-gix-color);
    background-color: var(--minima-highlight-gix-background-color);
    font-style: var(--minima-highlight-gix-font-style);
    font-weight: var(--minima-highlight-gix-font-weight); }
  .highlight .go {
    color: var(--minima-highlight-go-color);
    background-color: var(--minima-highlight-go-background-color);
    font-style: var(--minima-highlight-go-font-style);
    font-weight: var(--minima-highlight-go-font-weight); }
  .highlight .gp {
    color: var(--minima-highlight-gp-color);
    background-color: var(--minima-highlight-gp-background-color);
    font-style: var(--minima-highlight-gp-font-style);
    font-weight: var(--minima-highlight-gp-font-weight); }
  .highlight .gs {
    color: var(--minima-highlight-gs-color);
    background-color: var(--minima-highlight-gs-background-color);
    font-style: var(--minima-highlight-gs-font-style);
    font-weight: var(--minima-highlight-gs-font-weight); }
  .highlight .gu {
    color: var(--minima-highlight-gu-color);
    background-color: var(--minima-highlight-gu-background-color);
    font-style: var(--minima-highlight-gu-font-style);
    font-weight: var(--minima-highlight-gu-font-weight); }
  .highlight .gt {
    color: var(--minima-highlight-gt-color);
    background-color: var(--minima-highlight-gt-background-color);
    font-style: var(--minima-highlight-gt-font-style);
    font-weight: var(--minima-highlight-gt-font-weight); }
  .highlight .kc {
    color: var(--minima-highlight-kc-color);
    background-color: var(--minima-highlight-kc-background-color);
    font-style: var(--minima-highlight-kc-font-style);
    font-weight: var(--minima-highlight-kc-font-weight); }
  .highlight .kd {
    color: var(--minima-highlight-kd-color);
    background-color: var(--minima-highlight-kd-background-color);
    font-style: var(--minima-highlight-kd-font-style);
    font-weight: var(--minima-highlight-kd-font-weight); }
  .highlight .kp {
    color: var(--minima-highlight-kp-color);
    background-color: var(--minima-highlight-kp-background-color);
    font-style: var(--minima-highlight-kp-font-style);
    font-weight: var(--minima-highlight-kp-font-weight); }
  .highlight .kr {
    color: var(--minima-highlight-kr-color);
    background-color: var(--minima-highlight-kr-background-color);
    font-style: var(--minima-highlight-kr-font-style);
    font-weight: var(--minima-highlight-kr-font-weight); }
  .highlight .kt {
    color: var(--minima-highlight-kt-color);
    background-color: var(--minima-highlight-kt-background-color);
    font-style: var(--minima-highlight-kt-font-style);
    font-weight: var(--minima-highlight-kt-font-weight); }
  .highlight .m {
    color: var(--minima-highlight-m-color);
    background-color: var(--minima-highlight-m-background-color);
    font-style: var(--minima-highlight-m-font-style);
    font-weight: var(--minima-highlight-m-font-weight); }
  .highlight .s {
    color: var(--minima-highlight-s-color);
    background-color: var(--minima-highlight-s-background-color);
    font-style: var(--minima-highlight-s-font-style);
    font-weight: var(--minima-highlight-s-font-weight); }
  .highlight .na {
    color: var(--minima-highlight-na-color);
    background-color: var(--minima-highlight-na-background-color);
    font-style: var(--minima-highlight-na-font-style);
    font-weight: var(--minima-highlight-na-font-weight); }
  .highlight .nb {
    color: var(--minima-highlight-nb-color);
    background-color: var(--minima-highlight-nb-background-color);
    font-style: var(--minima-highlight-nb-font-style);
    font-weight: var(--minima-highlight-nb-font-weight); }
  .highlight .nc {
    color: var(--minima-highlight-nc-color);
    background-color: var(--minima-highlight-nc-background-color);
    font-style: var(--minima-highlight-nc-font-style);
    font-weight: var(--minima-highlight-nc-font-weight); }
  .highlight .no {
    color: var(--minima-highlight-no-color);
    background-color: var(--minima-highlight-no-background-color);
    font-style: var(--minima-highlight-no-font-style);
    font-weight: var(--minima-highlight-no-font-weight); }
  .highlight .ni {
    color: var(--minima-highlight-ni-color);
    background-color: var(--minima-highlight-ni-background-color);
    font-style: var(--minima-highlight-ni-font-style);
    font-weight: var(--minima-highlight-ni-font-weight); }
  .highlight .ne {
    color: var(--minima-highlight-ne-color);
    background-color: var(--minima-highlight-ne-background-color);
    font-style: var(--minima-highlight-ne-font-style);
    font-weight: var(--minima-highlight-ne-font-weight); }
  .highlight .nf {
    color: var(--minima-highlight-nf-color);
    background-color: var(--minima-highlight-nf-background-color);
    font-style: var(--minima-highlight-nf-font-style);
    font-weight: var(--minima-highlight-nf-font-weight); }
  .highlight .nn {
    color: var(--minima-highlight-nn-color);
    background-color: var(--minima-highlight-nn-background-color);
    font-style: var(--minima-highlight-nn-font-style);
    font-weight: var(--minima-highlight-nn-font-weight); }
  .highlight .nt {
    color: var(--minima-highlight-nt-color);
    background-color: var(--minima-highlight-nt-background-color);
    font-style: var(--minima-highlight-nt-font-style);
    font-weight: var(--minima-highlight-nt-font-weight); }
  .highlight .nv {
    color: var(--minima-highlight-nv-color);
    background-color: var(--minima-highlight-nv-background-color);
    font-style: var(--minima-highlight-nv-font-style);
    font-weight: var(--minima-highlight-nv-font-weight); }
  .highlight .ow {
    color: var(--minima-highlight-ow-color);
    background-color: var(--minima-highlight-ow-background-color);
    font-style: var(--minima-highlight-ow-font-style);
    font-weight: var(--minima-highlight-ow-font-weight); }
  .highlight .w {
    color: var(--minima-highlight-w-color);
    background-color: var(--minima-highlight-w-background-color);
    font-style: var(--minima-highlight-w-font-style);
    font-weight: var(--minima-highlight-w-font-weight); }
  .highlight .mf {
    color: var(--minima-highlight-mf-color);
    background-color: var(--minima-highlight-mf-background-color);
    font-style: var(--minima-highlight-mf-font-style);
    font-weight: var(--minima-highlight-mf-font-weight); }
  .highlight .mh {
    color: var(--minima-highlight-nh-color);
    background-color: var(--minima-highlight-nh-background-color);
    font-style: var(--minima-highlight-nh-font-style);
    font-weight: var(--minima-highlight-nh-font-weight); }
  .highlight .mi {
    color: var(--minima-highlight-mi-color);
    background-color: var(--minima-highlight-mi-background-color);
    font-style: var(--minima-highlight-mi-font-style);
    font-weight: var(--minima-highlight-mi-font-weight); }
  .highlight .mo {
    color: var(--minima-highlight-mo-color);
    background-color: var(--minima-highlight-mo-background-color);
    font-style: var(--minima-highlight-mo-font-style);
    font-weight: var(--minima-highlight-mo-font-weight); }
  .highlight .sb {
    color: var(--minima-highlight-sb-color);
    background-color: var(--minima-highlight-sb-background-color);
    font-style: var(--minima-highlight-sb-font-style);
    font-weight: var(--minima-highlight-sb-font-weight); }
  .highlight .sc {
    color: var(--minima-highlight-sc-color);
    background-color: var(--minima-highlight-sc-background-color);
    font-style: var(--minima-highlight-sc-font-style);
    font-weight: var(--minima-highlight-sc-font-weight); }
  .highlight .sd {
    color: var(--minima-highlight-sd-color);
    background-color: var(--minima-highlight-sd-background-color);
    font-style: var(--minima-highlight-sd-font-style);
    font-weight: var(--minima-highlight-sd-font-weight); }
  .highlight .s2 {
    color: var(--minima-highlight-s2-color);
    background-color: var(--minima-highlight-s2-background-color);
    font-style: var(--minima-highlight-s2-font-style);
    font-weight: var(--minima-highlight-s2-font-weight); }
  .highlight .se {
    color: var(--minima-highlight-se-color);
    background-color: var(--minima-highlight-se-background-color);
    font-style: var(--minima-highlight-se-font-style);
    font-weight: var(--minima-highlight-se-font-weight); }
  .highlight .sh {
    color: var(--minima-highlight-sh-color);
    background-color: var(--minima-highlight-sh-background-color);
    font-style: var(--minima-highlight-sh-font-style);
    font-weight: var(--minima-highlight-sh-font-weight); }
  .highlight .si {
    color: var(--minima-highlight-si-color);
    background-color: var(--minima-highlight-si-background-color);
    font-style: var(--minima-highlight-si-font-style);
    font-weight: var(--minima-highlight-si-font-weight); }
  .highlight .sx {
    color: var(--minima-highlight-sx-color);
    background-color: var(--minima-highlight-sx-background-color);
    font-style: var(--minima-highlight-sx-font-style);
    font-weight: var(--minima-highlight-sx-font-weight); }
  .highlight .sr {
    color: var(--minima-highlight-sr-color);
    background-color: var(--minima-highlight-sr-background-color);
    font-style: var(--minima-highlight-sr-font-style);
    font-weight: var(--minima-highlight-sr-font-weight); }
  .highlight .s1 {
    color: var(--minima-highlight-s1-color);
    background-color: var(--minima-highlight-s1-background-color);
    font-style: var(--minima-highlight-s1-font-style);
    font-weight: var(--minima-highlight-s1-font-weight); }
  .highlight .ss {
    color: var(--minima-highlight-ss-color);
    background-color: var(--minima-highlight-ss-background-color);
    font-style: var(--minima-highlight-ss-font-style);
    font-weight: var(--minima-highlight-ss-font-weight); }
  .highlight .bp {
    color: var(--minima-highlight-bp-color);
    background-color: var(--minima-highlight-bp-background-color);
    font-style: var(--minima-highlight-bp-font-style);
    font-weight: var(--minima-highlight-bp-font-weight); }
  .highlight .vc {
    color: var(--minima-highlight-vc-color);
    background-color: var(--minima-highlight-vc-background-color);
    font-style: var(--minima-highlight-vc-font-style);
    font-weight: var(--minima-highlight-vc-font-weight); }
  .highlight .vg {
    color: var(--minima-highlight-vg-color);
    background-color: var(--minima-highlight-vg-background-color);
    font-style: var(--minima-highlight-vg-font-style);
    font-weight: var(--minima-highlight-vg-font-weight); }
  .highlight .vi {
    color: var(--minima-highlight-vi-color);
    background-color: var(--minima-highlight-vi-background-color);
    font-style: var(--minima-highlight-vi-font-style);
    font-weight: var(--minima-highlight-vi-font-weight); }
  .highlight .il {
    color: var(--minima-highlight-il-color);
    background-color: var(--minima-highlight-il-background-color);
    font-style: var(--minima-highlight-il-font-style);
    font-weight: var(--minima-highlight-il-font-weight); }

/* begin initialize.scss */
:root {
  --minima-base-font-family: -apple-system, system-ui, BlinkMacSystemFont, "Segoe UI", "Segoe UI Emoji", "Segoe UI Symbol", "Apple Color Emoji", Roboto, Helvetica, Arial, sans-serif ;
  --minima-code-font-family: "Menlo", "Inconsolata", "Consolas", "Roboto Mono", "Ubuntu Mono", "Liberation Mono", "Courier New", monospace;
  --minima-base-font-size: 16px ;
  --minima-base-font-weight: 400 ;
  --minima-small-font-size: calc(var(--minima-base-font-size) * 0.875) ;
  --minima-base-line-height: 1.5 ;
  --minima-spacing-unit: 30px ;
  --minima-table-text-align: left ; }

:root {
  --minima-content-width: 800px; }

/*
// Width of the content area
*/
@media screen and (min-width: 600px) {
  /* on-medium = on-palm */
  .site-nav {
    position: static;
    float: right;
    border: none;
    background-color: inherit; }
  .site-nav label[for="nav-trigger"] {
    display: none; }
  .site-nav .menu-icon {
    display: none; }
  .site-nav input ~ .trigger {
    display: block; }
  .site-nav .page-link {
    display: inline;
    padding: 0;
    margin-left: auto; }
    .site-nav .page-link:not(:last-child) {
      margin-right: 20px; }
  .footer-col-wrapper {
    display: flex; }
  .footer-col {
    width: calc(100% - (var(--minima-spacing-unit) / 2 ));
    padding: 0 calc(var(--minima-spacing-unit) * .5); }
    .footer-col:first-child {
      padding-right: calc(var(--minima-spacing-unit) * .5);
      padding-left: 0; }
    .footer-col:last-child {
      padding-right: 0;
      padding-left: calc(var(--minima-spacing-unit) * .5); } }

:root {
  --minima-wrapper-max-width: calc( var(--minima-content-width) - (var(--minima-spacing-unit)));
  --minima-wrapper-padding-left-right: calc(var(--minima-spacing-unit) * .5);
  --minima-post-content-h1-font-size: 2.625rem;
  --minima-post-content-h2-font-size: 1.75rem;
  --minima-post-content-h3-font-size: 1.375rem;
  --minima-footer-col1-width: calc(50% - (var(--minima-spacing-unit) / 2));
  --minima-footer-col2-width: calc(50% - (var(--minima-spacing-unit) / 2));
  --minima-footer-col3-width: calc(50% - (var(--minima-spacing-unit) / 2)); }

@media screen and (min-width: 800px) {
  :root {
    --minima-wrapper-max-width: calc( var(--minima-content-width) - (var(--minima-spacing-unit) * 2));
    --minima-wrapper-padding-left-right: var(--minima-spacing-unit);
    --minima-one-half-width: calc(50% - (var(--minima-spacing-unit) / 2 ));
    --minima-post-content-h1-font-size: 2.625rem;
    --minima-post-content-h2-font-size: 2rem;
    --minima-post-content-h3-font-size: 1.625rem;
    --minima-footer-col1-width: calc(35% - (var(--minima-spacing-unit) / 2));
    --minima-footer-col1-width: calc(20% - (var(--minima-spacing-unit) / 2 ));
    --minima-footer-col1-width: calc(45% - (var(--minima-spacing-unit) / 2 )); } }

@media screen and (max-width: 600px) {
  /* on-palm */
  :root {
    --minima-site-title-padding-right: 45px; } }

@media screen and (max-width: 800px) {
  /* on-laptop */
  :root {
    --minima-table-display: block;
    --minima-table-overflow-x: auto;
    --minima-table-webkit-overflow-scrolling: touch;
    --minima-table-ms-overflow-style: -ms-autohiding-scrollbar; } }

/*
// Syntax highlighting styles should be adjusted appropriately for every "skin"
// List of tokens: https://github.com/rouge-ruby/rouge/wiki/List-of-tokens
// Some colors come from Material Theme Darker:
// https://github.com/material-theme/vsc-material-theme/blob/master/scripts/generator/settings/specific/darker-hc.ts
// https://github.com/material-theme/vsc-material-theme/blob/master/scripts/generator/color-set.ts
// ----------------------------------------------------------------------------
// Use media queries like this:
// @include media-query($on-palm) {
//   .wrapper {
//     padding-right: $spacing-unit / 2;
//     padding-left: $spacing-unit / 2;
//   }
// }
// Notice the following mixin uses max-width, in a deprecated, desktop-first
// approach, whereas media queries used elsewhere now use min-width.

// Import pre-styling-overrides hook and style-partials.
*/
/* begin custom-styles.scss
// Placeholder to allow overriding predefined variables smoothly.
*/
/* begin _base.scss */
html {
  font-size: var(--minima-base-font-size); }

/**
 * Reset some basic elements
 */
body, h1, h2, h3, h4, h5, h6,
p, blockquote, pre, hr,
dl, dd, ol, ul, figure {
  margin: 0;
  padding: 0; }

/**
 * Basic styling
 */
body {
  font: var(--minima-base-font-weight) var(--minima-base-font-size)/var(--minima-base-line-height) var(--minima-base-font-family);
  color: var(--minima-text-color);
  background-color: var(--minima-background-color);
  -webkit-text-size-adjust: 100%;
  -webkit-font-feature-settings: "kern" 1;
  -moz-font-feature-settings: "kern" 1;
  -o-font-feature-settings: "kern" 1;
  font-feature-settings: "kern" 1;
  font-kerning: normal;
  display: flex;
  min-height: 100vh;
  flex-direction: column;
  overflow-wrap: break-word; }

/**
 * Set `margin-bottom` to maintain vertical rhythm
 */
h1, h2, h3, h4, h5, h6,
p, blockquote, pre,
ul, ol, dl, figure,
.highlight {
  margin-bottom: calc(var(--minima-spacing-unit) * .5); }

hr {
  margin-top: var(--minima-spacing-unit);
  margin-bottom: var(--minima-spacing-unit); }

/**
 * `main` element
 */
main {
  display: block;
  /* Default value of `display` of `main` element is 'inline' in IE 11. */ }

/**
 * Images
 */
img {
  max-width: 100%;
  vertical-align: middle; }

/**
 * Figures
 */
figure > img {
  display: block; }

figcaption {
  font-size: var(--minima-small-font-size); }

/**
 * Lists
 */
ul, ol {
  margin-left: var(--minima-spacing-unit); }

li > ul,
li > ol {
  margin-bottom: 0; }

/**
 * Headings
 */
h1, h2, h3, h4, h5, h6 {
  font-weight: var(--minima-base-font-weight); }

/**
 * Links
 */
a {
  color: var(--minima-link-base-color);
  text-decoration: none; }
  a:visited {
    color: var(--minima-link-visited-color); }
  a:hover {
    color: var(--minima-link-hover-color);
    text-decoration: underline; }
  .social-media-list a:hover, .pagination a:hover {
    text-decoration: none; }
    .social-media-list a:hover .username, .pagination a:hover .username {
      text-decoration: underline; }

/**
 * Blockquotes
 */
blockquote {
  color: var(--minima-brand-color);
  border-left: 4px solid var(--minima-border-color-01);
  padding-left: calc(var(--minima-spacing-unit) * .5);
  font-size: 1.125rem;
  font-style: italic; }
  blockquote > :last-child {
    margin-bottom: 0; }
  blockquote i, blockquote em {
    font-style: normal; }

/**
 * Code formatting
 */
pre,
code {
  font-family: var(--minima-code-font-family);
  font-size: 0.9375em;
  border: 1px solid var(--minima-border-color-01);
  border-radius: 3px;
  background-color: var(--minima-code-background-color); }

code {
  padding: 1px 5px; }

pre {
  padding: 8px 12px;
  overflow-x: auto; }
  pre > code {
    border: 0;
    padding-right: 0;
    padding-left: 0; }

.highlight {
  border-radius: 3px;
  background: var(--minima-code-background-color); }
  .highlighter-rouge .highlight {
    background: var(--minima-code-background-color); }

/**
 * Wrapper
 */
.wrapper {
  max-width: var(--minima-wrapper-max-width);
  margin-right: auto;
  margin-left: auto;
  padding-right: var(--minima-wrapper-padding-left-right);
  padding-left: var(--minima-wrapper-padding-left-right); }

/**
 * Clearfix
 */
.wrapper:after {
  content: "";
  display: table;
  clear: both; }

/**
 * Icons
 */
.orange {
  color: #f66a0a; }

.grey {
  color: #828282; }

.svg-icon {
  width: 1.25em;
  height: 1.25em;
  display: inline-block;
  fill: currentColor;
  vertical-align: text-bottom; }

/**
 * Tables
 */
table {
  margin-bottom: var(--minima-spacing-unit);
  width: 100%;
  text-align: var(--minima-table-text-align);
  color: var(--minima-table-text-color);
  border-collapse: collapse;
  border: 1px solid var(--minima-table-border-color);
  display: var(--minima-table-display);
  overflow-x: var(--minima-table-overflow-x);
  -webkit-overflow-scrolling: var(--minima-table-webkit-overflow-scrolling);
  -ms-overflow-style: var(--minima-table-ms-overflow-style); }
  table tr:nth-child(even) {
    background-color: var(--minima-table-zebra-color); }
  table th, table td {
    padding: calc(var(--minima-spacing-unit) * 33.3333333333 * .01) calc(var(--minima-spacing-unit) * .5); }
  table th {
    background-color: var(--minima-table-header-bg-color);
    border: 1px solid var(--minima-table-header-border); }
  table td {
    border: 1px solid var(--minima-table-border-color); }

/* begin _layout.scss */
/**
 * Site header
 */
.site-header {
  border-top: 5px solid var(--minima-border-color-03);
  border-bottom: 1px solid var(--minima-border-color-01);
  min-height: calc(var(--minima-spacing-unit) * 1.865);
  line-height: calc(var(--minima-base-line-height) * var(--minima-base-font-size) * 2.25);
  /*
  // Positioning context for the mobile navigation icon
  */
  position: relative; }

.site-title {
  font-size: 1.625rem;
  font-weight: 300;
  letter-spacing: -1px;
  margin-bottom: 0;
  float: left;
  padding-right: var(--minima-site-title-padding-right); }
  .site-title, .site-title:visited {
    color: var(--minima-site-title-color); }

.site-nav {
  position: absolute;
  top: 9px;
  right: calc(var(--minima-spacing-unit) * .5);
  background-color: var(--minima-background-color);
  border: 1px solid var(--minima-border-color-01);
  border-radius: 5px;
  text-align: right; }
  .site-nav .nav-trigger {
    display: none; }
  .site-nav .menu-icon {
    float: right;
    width: 36px;
    height: 26px;
    line-height: 0;
    padding-top: 10px;
    text-align: center; }
    .site-nav .menu-icon > svg path {
      fill: var(--minima-border-color-03); }
  .site-nav label[for="nav-trigger"] {
    display: block;
    float: right;
    width: 36px;
    height: 36px;
    z-index: 2;
    cursor: pointer; }
  .site-nav input ~ .trigger {
    clear: both;
    display: none; }
  .site-nav input:checked ~ .trigger {
    display: block;
    padding-bottom: 5px; }
  .site-nav .page-link {
    color: var(--minima-text-color);
    line-height: var(--minima-base-line-height);
    display: block;
    padding: 5px 10px;
    /*
    // Gaps between nav items, but not on the last one
    */
    margin-left: 20px; }
    .site-nav .page-link:not(:last-child) {
      margin-right: 0; }

/**
 * Site footer
 */
.site-footer {
  border-top: 1px solid var(--minima-border-color-01);
  padding: var(--minima-spacing-unit) 0; }

.footer-heading {
  font-size: 1.125rem;
  margin-bottom: calc(var(--minima-spacing-unit) * .5); }

.feed-subscribe .svg-icon {
  padding: 5px 5px 2px 0; }

.contact-list,
.social-media-list,
.pagination {
  list-style: none;
  margin-left: 0; }

.footer-col-wrapper,
.social-links {
  font-size: 0.9375rem;
  color: var(--minima-brand-color); }

.footer-col {
  margin-bottom: calc(var(--minima-spacing-unit) * .5); }

.footer-col-1 {
  width: var(--minima-footer-col1-width); }

.footer-col-2 {
  width: var(--minima-footer-col2-width); }

.footer-col-3 {
  width: var(--minima-footer-col3-width); }

/**
 * Page content
 */
.page-content {
  padding: var(--minima-spacing-unit) 0;
  flex: 1 0 auto; }

.page-heading {
  font-size: 2rem; }

.post-list-heading {
  font-size: 1.75rem; }

.post-list {
  margin-left: 0;
  list-style: none; }
  .post-list > li {
    margin-bottom: var(--minima-spacing-unit); }

.post-meta {
  font-size: var(--minima-small-font-size);
  color: var(--minima-brand-color); }

.post-link {
  display: block;
  font-size: 1.5rem; }

/**
 * Posts
 */
.post-header {
  margin-bottom: var(--minima-spacing-unit); }

.post-title,
.post-content h1 {
  font-size: var(--minima-post-content-h1-font-size);
  letter-spacing: -1px;
  line-height: 1.15; }

.post-content {
  margin-bottom: var(--minima-spacing-unit); }
  .post-content h1, .post-content h2, .post-content h3, .post-content h4, .post-content h5, .post-content h6 {
    margin-top: var(--minima-spacing-unit); }
  .post-content h2 {
    font-size: var(--minima-post-content-h2-font-size); }
  .post-content h3 {
    font-size: var(--minima-post-content-h3-font-size); }
  .post-content h4 {
    font-size: 1.25rem; }
  .post-content h5 {
    font-size: 1.125rem; }
  .post-content h6 {
    font-size: 1.0625rem; }

.social-media-list, .pagination {
  display: table;
  margin: 0 auto; }
  .social-media-list li, .pagination li {
    float: left;
    margin: 5px 10px 5px 0; }
    .social-media-list li:last-of-type, .pagination li:last-of-type {
      margin-right: 0; }
    .social-media-list li a, .pagination li a {
      display: block;
      padding: 10px 12px;
      border: 1px solid var(--minima-border-color-01); }
      .social-media-list li a:hover, .pagination li a:hover {
        border-color: var(--minima-border-color-02); }

/**
 * Pagination navbar
 */
.pagination {
  margin-bottom: var(--minima-spacing-unit); }
  .pagination li a, .pagination li div {
    min-width: 41px;
    text-align: center;
    box-sizing: border-box; }
  .pagination li div {
    display: block;
    padding: calc(var(--minima-spacing-unit) * .25);
    border: 1px solid transparent; }
    .pagination li div.pager-edge {
      color: var(--minima-border-color-01);
      border: 1px dashed; }

/**
 * Grid helpers
 */
.one-half {
  width: var(--minima-one-half-width); }

/* begin custom-variables.scss
// Placeholder to allow defining custom styles that override everything else.
// (Use `_sass/minima/custom-variables.scss` to override variable defaults)
*/
'''
