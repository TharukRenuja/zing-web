import re, os, json, urllib.request

def slugify(text):
    text = text.lower()
    text = re.sub(r'[^a-z0-9\s\u4e00-\u9fff-]', '', text)
    text = re.sub(r'[\s]+', '-', text)
    text = re.sub(r'-+', '-', text)
    return text.strip('-')

def fix_link(url):
    if url.endswith('.md') or '.md#' in url:
        url = url.lower().replace('.md', '.html')
    elif (url.endswith('.html') or '.html#' in url) and not url.startswith('http'):
        url = url.lower()
    return url

def inline_format(text):
    code_spans = []
    def save_code(m):
        code_spans.append(m.group(1))
        return f'\x00CODE{len(code_spans)-1}\x00'
    text = re.sub(r'`([^`]+)`', save_code, text)
    text = re.sub(r'!\[([^\]]*)\]\(([^)]+)\)', r'<img src="\2" alt="\1">', text)
    text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', lambda m: f'<a href="{fix_link(m.group(2))}" rel="noopener noreferrer">{m.group(1)}</a>', text)
    text = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'(?<!\*)\*([^*]+)\*(?!\*)', r'<em>\1</em>', text)
    text = re.sub(r'~~([^~]+)~~', r'<del>\1</del>', text)
    for i, cs in enumerate(code_spans):
        text = text.replace(f'\x00CODE{i}\x00', f'<code>{cs}</code>')
    return text

def consume_code(lines, i):
    lang = lines[i].lstrip()[3:].strip()
    indent = len(lines[i]) - len(lines[i].lstrip())
    buf = []
    i += 1
    while i < len(lines):
        stripped = lines[i].lstrip()
        if stripped.startswith('```'):
            i += 1
            break
        if indent > 0 and len(lines[i]) >= indent:
            buf.append(lines[i][indent:] + '\n')
        else:
            buf.append(lines[i] + '\n')
        i += 1
    return f'<div class="code-block"><button class="copy-btn" onclick="copyCode(this)"><i class="fa-regular fa-copy"></i> Copy</button><pre><code>{"".join(buf)}</code></pre></div>', i

def md_to_html(md):
    lines = md.split('\n')
    html = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if not line.strip():
            i += 1
            continue
        if line.lstrip().startswith('```'):
            code_html, i = consume_code(lines, i)
            html.append(code_html)
            continue
        if re.match(r'^[-*_]{3,}\s*$', line):
            html.append('<hr>')
            i += 1
            continue

        # Inline anchor tag before heading
        am = re.match(r'^<a\s+id="([^"]+)"\s*/?>\s*</a>\s*$', line.strip())
        if am:
            aid = am.group(1)
            i += 1
            if i < len(lines) and re.match(r'^(#{1,6})\s+', lines[i]):
                hm = re.match(r'^(#{1,6})\s+(.+)$', lines[i])
                level = len(hm.group(1))
                text = inline_format(hm.group(2))
                html.append(f'<h{level} id="{aid}">{text}</h{level}>')
                i += 1
                continue
            else:
                html.append(f'<a id="{aid}"></a>')
                continue

        # Headings
        hm = re.match(r'^(#{1,6})\s+(.+)$', line)
        if hm:
            level = len(hm.group(1))
            text = hm.group(2)
            ain = re.search(r'<a\s+id="([^"]+)"\s*/?>\s*</a>\s*', text)
            if ain:
                aid = ain.group(1)
                text = re.sub(r'<a\s+id="[^"]+"\s*/?>\s*</a>\s*', '', text).strip()
            else:
                aid = slugify(text)
            html.append(f'<h{level} id="{aid}">{inline_format(text)}</h{level}>')
            i += 1
            continue

        # GFM Alerts
        al = re.match(r'>\s*\[!(\w+)\]\s*$', line)
        if al:
            atype = al.group(1).upper()
            i += 1
            qlines = []
            while i < len(lines):
                ql = lines[i]
                if ql.startswith('> '):
                    qlines.append(ql[2:].strip())
                    i += 1
                elif ql.strip() == '>':
                    i += 1
                else:
                    break
            content = '\n'.join(qlines)
            content = inline_format(content)
            html.append(f'<div class="callout callout-{atype.lower()}"><strong class="callout-title">{atype}</strong> {content}</div>')
            continue

        # Multi-line blockquote
        if line.startswith('> ') and not re.match(r'>\s*\[!\w+\]', line):
            qlines = []
            while i < len(lines) and (lines[i].startswith('> ') or lines[i].strip() == '>'):
                if lines[i].strip() == '>':
                    i += 1
                    continue
                qlines.append(lines[i][2:].strip())
                i += 1
            content = ' '.join(qlines)
            content = inline_format(content)
            html.append(f'<blockquote><p>{content}</p></blockquote>')
            continue

        # Tables
        if '|' in line and line.strip().startswith('|'):
            rows = []
            while i < len(lines) and '|' in lines[i] and lines[i].strip().startswith('|'):
                rows.append(lines[i])
                i += 1
            html.append(convert_table(rows))
            continue

        # Lists (ordered and unordered) — stack-based recursive nesting
        def is_list_item(ln):
            return bool(re.match(r'^(\s*)(?:\d+\.|[-*+])\s+', ln))

        def item_indent(ln):
            m = re.match(r'^(\s*)', ln)
            return len(m.group(1)) if m else 0

        def item_tag(ln):
            stripped = ln.lstrip()
            return 'ol' if re.match(r'^\d+\.\s+', stripped) else 'ul'

        def item_text_content(ln):
            return re.sub(r'^\s*(?:\d+\.|[-*+])\s+', '', ln)

        def consume_list(lines, start, base_indent):
            i = start
            tag = item_tag(lines[i])
            parts = [f'<{tag}>']
            while i < len(lines):
                ln = lines[i]
                if not ln.strip():
                    j = i + 1
                    while j < len(lines) and not lines[j].strip():
                        j += 1
                    if j < len(lines) and is_list_item(lines[j]) and item_indent(lines[j]) >= base_indent:
                        i = j
                        continue
                    break
                if not is_list_item(ln):
                    break
                ind = item_indent(ln)
                if ind < base_indent:
                    break
                if ind > base_indent:
                    nested_html, i = consume_list(lines, i, ind)
                    parts.append(nested_html)
                    continue
                if parts[-1] != f'<{tag}>':
                    parts.append('</li>')
                text = inline_format(item_text_content(ln))
                parts.append(f'<li>{text}')
                i += 1
                while i < len(lines):
                    cont = lines[i]
                    if not cont.strip():
                        j = i + 1
                        while j < len(lines) and not lines[j].strip():
                            j += 1
                        if j < len(lines):
                            cind = item_indent(lines[j]) if is_list_item(lines[j]) else (len(lines[j]) - len(lines[j].lstrip()))
                            if cind > base_indent:
                                i = j
                                continue
                        break
                    s = cont.lstrip()
                    cind = len(cont) - len(s)
                    if is_list_item(cont) and item_indent(cont) > base_indent:
                        nested_html, i = consume_list(lines, i, item_indent(cont))
                        parts.append(nested_html)
                    elif is_list_item(cont) and item_indent(cont) == base_indent:
                        break
                    elif cind > base_indent and s.startswith('```'):
                        ch, i = consume_code(lines, i)
                        parts.append(ch)
                    elif cind > base_indent and s.startswith('> '):
                        parts.append(f'<blockquote>{inline_format(s[2:])}</blockquote>')
                        i += 1
                    elif cind > base_indent and s.strip():
                        parts.append(f'<p>{inline_format(s)}</p>')
                        i += 1
                    else:
                        break
            if parts and parts[-1] != f'<{tag}>':
                parts.append('</li>')
            parts.append(f'</{tag}>')
            return '\n'.join(parts), i

        if is_list_item(line):
            base = item_indent(line)
            list_html, i = consume_list(lines, i, base)
            html.append(list_html)
            continue

        # Paragraph
        para = []
        while i < len(lines) and lines[i].strip():
            if lines[i].lstrip().startswith('```'):
                break
            text = inline_format(lines[i].rstrip())
            if lines[i].endswith('  '):
                text += '<br>'
            para.append(text)
            i += 1
        if para:
            html.append(f'<p>{" ".join(para)}</p>')
        if i < len(lines) and lines[i].lstrip().startswith('```'):
            code_html, i = consume_code(lines, i)
            html.append(code_html)
    return '\n'.join(html)

def convert_table(rows):
    if len(rows) < 2:
        return ''
    header = rows[0]
    data = rows[2:]
    cols = [c.strip() for c in header.split('|')]
    if cols and not cols[0]: cols = cols[1:]
    if cols and not cols[-1]: cols = cols[:-1]
    html_s = '<div class="table-wrap"><table>\n<thead>\n<tr>'
    for c in cols:
        html_s += f'<th>{inline_format(c)}</th>'
    html_s += '</tr>\n</thead>\n<tbody>\n'
    for row in data:
        cells = [c.strip() for c in row.split('|')]
        if cells and not cells[0]: cells = cells[1:]
        if cells and not cells[-1]: cells = cells[:-1]
        if not any(c for c in cells):
            continue
        html_s += '<tr>'
        for c in cells:
            html_s += f'<td>{inline_format(c)}</td>'
        html_s += '</tr>\n'
    html_s += '</tbody>\n</table></div>'
    return html_s

SECTION_ORDER = {'Getting Started': 0, 'Basics': 0, 'Guides': 1, 'Internals': 2, 'Reference': 3}

FALLBACK_TITLES = {
    'getting-started': 'Getting Started', 'architecture': 'Architecture',
    'download-engine': 'Download Engine', 'cli': 'CLI Reference',
    'daemon': 'Daemon Mode', 'gui': 'GUI Overview',
    'browser-extension': 'Browser Extension', 'tui': 'Terminal UI',
    'installation': 'Installation', 'pipe-mode': 'Pipe Mode',
    'config': 'Configuration',
}

FALLBACK_SECTIONS = {
    'getting-started': 'Basics', 'architecture': 'Basics', 'installation': 'Basics',
    'download-engine': 'Guides', 'cli': 'Guides', 'daemon': 'Guides', 'gui': 'Guides',
    'browser-extension': 'Guides', 'tui': 'Guides', 'pipe-mode': 'Guides',
    'config': 'Reference',
}

FALLBACK_ORDER = {
    'getting-started': 1, 'architecture': 2, 'installation': 3,
    'download-engine': 1, 'cli': 2, 'daemon': 3, 'gui': 4,
    'browser-extension': 5, 'tui': 6, 'pipe-mode': 7,
    'config': 1,
}

FALLBACK_DESC = {
    'getting-started': 'Install and run zing for the first time.',
    'architecture': 'How zing is organized: workspace structure, crate dependencies, data flow, and design decisions.',
    'download-engine': 'How zing downloads files: adaptive connections, segment allocation, work stealing, retry logic, and mirror fallback.',
    'cli': 'Full zing CLI reference. Every command, flag, and config option explained.',
    'daemon': 'Run zing as a background daemon with JSON-RPC over Unix socket or TCP. Manage downloads remotely.',
    'gui': 'Overview of the Tauri v2 GUI: main window, add download, settings, confirm dialogs, and theme system.',
    'browser-extension': 'Capture downloads from Chrome and Firefox directly into zing via Native Messaging.',
    'tui': 'Terminal UI built with ratatui: task list, per-connection detail, block map, and log panel.',
    'installation': 'Install zing from pre-built binaries or build from source.',
    'pipe-mode': 'Pipe URLs from stdin to zing for scripted workflows.',
    'config': 'Complete configuration reference for zing: all fields, defaults, and examples.',
}

FALLBACK_KEYWORDS = {
    'getting-started': 'zing install, download manager setup, Rust cargo install, HTTP download tool',
    'architecture': 'zing architecture, workspace structure, Rust crates, download manager design',
    'download-engine': 'zing download engine, adaptive connections, segmented downloads, work stealing, retry logic',
    'cli': 'zing CLI, command line reference, download manager commands, flags and options',
    'daemon': 'zing daemon, background service, JSON-RPC, Unix socket, TCP server',
    'gui': 'zing GUI, Tauri v2, desktop application, download manager interface, theme system',
    'browser-extension': 'zing browser extension, Chrome extension, Firefox extension, Native Messaging',
    'tui': 'zing TUI, terminal UI, ratatui, terminal download manager, block map visualization',
    'installation': 'zing installation, download manager setup, binary download, cargo install',
    'pipe-mode': 'zing pipe mode, stdin, scripted downloads, batch downloads',
    'config': 'zing configuration, settings reference, config file format, download options',
}

def parse_metadata(md):
    m = re.match(r'^\s*<!--\s*(.*?)-->\s*', md, re.DOTALL)
    if not m:
        return {}
    meta = {}
    for line in m.group(1).split('\n'):
        line = line.strip()
        kv = re.match(r'(\w+):\s*(.*)', line)
        if kv:
            meta[kv.group(1).lower()] = kv.group(2).strip()
    return meta

def load_pages(docs_dir):
    pages = []
    for fname in sorted(os.listdir(docs_dir)):
        if not fname.endswith('.md') or fname.lower() == 'readme.md':
            continue
        slug = fname.replace('.md', '').lower()
        with open(os.path.join(docs_dir, fname)) as f:
            md = f.read()
        meta = parse_metadata(md)
        title = meta.get('title', FALLBACK_TITLES.get(slug, slug.replace('-', ' ').title()))
        section = meta.get('section', FALLBACK_SECTIONS.get(slug, 'Guides'))
        order = int(meta.get('order', FALLBACK_ORDER.get(slug, 99)))
        desc = meta.get('desc', FALLBACK_DESC.get(slug, f'zing documentation - {title}'))
        keywords = meta.get('keywords', FALLBACK_KEYWORDS.get(slug, 'zing, download manager, Rust, HTTP'))
        pages.append((slug, title, section, order, desc, keywords, fname))
    pages.sort(key=lambda p: (SECTION_ORDER.get(p[2], 99), p[3]))
    return pages

def sidebar(pages, slug):
    groups = {}
    for p in pages:
        section = p[2]
        if section == 'Getting Started':
            section = 'Basics'
        groups.setdefault(section, []).append((p[0], p[1]))
    lines = []
    for section in ['Basics', 'Guides', 'Internals', 'Reference']:
        if section not in groups and section != 'Basics':
            continue
        lines.append('<div class="sidebar-group">')
        lines.append(f'<div class="sidebar-heading">{section}</div>')
        if section == 'Basics':
            active = ' active' if slug == 'get-started' else ''
            lines.append(f'<a href="get-started.html" class="sidebar-link{active}">Get Started</a>')
        for href, label in groups.get(section, []):
            active = ' active' if href == slug else ''
            lines.append(f'<a href="{href}.html" class="sidebar-link{active}">{label}</a>')
        lines.append('</div>')
    return '\n'.join(lines)

def nav_buttons(pages, slug):
    slugs = [p[0] for p in pages]
    labels = {p[0]: p[1] for p in pages}
    try:
        idx = slugs.index(slug)
    except ValueError:
        return ''
    prev_link = next_link = ''
    if idx > 0:
        p = slugs[idx - 1]
        prev_link = f'<a href="{p}.html" class="doc-nav-btn doc-nav-prev">\u2190 {labels[p]}</a>'
    if idx < len(slugs) - 1:
        n = slugs[idx + 1]
        next_link = f'<a href="{n}.html" class="doc-nav-btn doc-nav-next">{labels[n]} \u2192</a>'
    return f'<div class="doc-nav-buttons">{prev_link}{next_link}</div>'

def breadcrumb(pages, slug):
    m = {p[0]: (p[2], p[1]) for p in pages}
    if slug not in m:
        return '<span>Docs</span>'
    section, label = m[slug]
    parts = ['<span>Docs</span>']
    if section != label:
        parts.append('<span class="bc-sep">/</span>')
        parts.append(f'<span class="bc-section">{section}</span>')
    parts.append('<span class="bc-sep">/</span>')
    parts.append(f'<span class="bc-label">{label}</span>')
    return ''.join(parts)

def make_page(title, body, slug, nav_template, footer_template, pages, is_index=False):
    s = sidebar(pages, slug)
    nav_btns = nav_buttons(pages, slug)
    bc_html = breadcrumb(pages, slug)
    seo = {}
    for p in pages:
        if p[0] == slug:
            seo = {'desc': p[4], 'keywords': p[5]}
            break
    desc = seo.get('desc', f'zing documentation - {title}')
    keywords = seo.get('keywords', 'zing, download manager, Rust, HTTP')

    nav_html = nav_template.replace('{{FEATURES_HREF}}', '/#features').replace('{{DOCS_STYLE}}', 'style="color:var(--accent)"')
    footer_html = footer_template

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <meta name="description" content="{desc}">
  <meta name="keywords" content="{keywords}">
  <title>{title} - zing Docs</title>
  <meta property="og:title" content="{title} - zing Docs">
  <meta property="og:description" content="{desc}">
  <meta property="og:url" content="https://zing.tharuk.pro/docs/{slug}.html">
  <meta property="og:type" content="website">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="{title} - zing Docs">
  <meta name="twitter:description" content="{desc}">
  <link rel="canonical" href="https://zing.tharuk.pro/docs/{slug}.html">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;700&display=swap" rel="stylesheet">
  <link rel="icon" href="/assets/favicon.ico">
  <link rel="apple-touch-icon" href="/assets/favicon.ico">
  <link rel="stylesheet" href="../style.css">
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">
  <style>
    nav .nav-inner {{ max-width: none; }}
    .docs-layout {{
      display: flex; min-height: calc(100vh - 64px);
    }}
    .sidebar {{
      width: 300px; flex-shrink: 0;
      border-right: 1px solid var(--border);
      background: var(--bg-elevated);
      overflow-y: auto;
      position: sticky; top: 64px; height: calc(100vh - 64px);
    }}
    .sidebar-inner {{
      padding: 0;
      position: relative;
      width: 100%;
      min-width: 0;
    }}
    .sidebar-group {{
      margin-bottom: 0;
    }}
    .sidebar-heading {{
      font-family: var(--mono); font-size: 0.7rem; font-weight: 700;
      text-transform: uppercase; letter-spacing: 0.08em;
      color: var(--accent); padding: 1rem 1rem 0.25rem;
    }}
    .sidebar-link {{
      display: block; padding: 0.5rem 1rem;
      font-size: 0.9rem; color: var(--muted);
      text-decoration: none; border-radius: 0;
      transition: all 0.1s;
    }}
    .sidebar-link:hover {{
      color: var(--text); background: var(--bg-card);
    }}
    .sidebar-link.active {{
      color: var(--accent); background: rgba(79,142,247,0.08);
      font-weight: 600;
    }}
    .sidebar-content {{
      flex: 1; min-width: 0;
      padding: 2rem 2rem 4rem;
      max-width: none;
    }}
    .sidebar-content h1 {{
      font-family: var(--mono); font-size: clamp(1.5rem, 2.5vw, 2rem);
      font-weight: 700; letter-spacing: -0.03em; color: var(--text);
      margin-bottom: 1.5rem; padding-bottom: 0.75rem;
      border-bottom: 1px solid var(--border);
    }}
    .sidebar-content h2 {{
      font-family: var(--mono); font-size: 1.25rem; font-weight: 700;
      color: var(--accent); margin: 2rem 0 0.75rem;
      letter-spacing: -0.02em;
    }}
    .sidebar-content h2:target {{
      border-left: 3px solid var(--accent);
      padding-left: 0.75rem;
    }}
    .sidebar-content h3 {{
      font-family: var(--mono); font-size: 1rem; font-weight: 600;
      color: var(--accent-light); margin: 1.5rem 0 0.5rem;
    }}
    .sidebar-content h3:target {{
      border-left: 2px solid var(--accent);
      padding-left: 0.5rem;
    }}
    .sidebar-content p {{
      color: var(--muted); line-height: 1.7; margin-bottom: 1rem;
    }}
    .sidebar-content strong {{ color: var(--text); }}
    .sidebar-content a {{
      color: var(--accent); text-decoration: none;
      word-break: break-word; overflow-wrap: anywhere;
    }}
    .sidebar-content a:hover {{ text-decoration: underline; }}
    .sidebar-content code {{
      font-family: var(--mono); font-size: 0.82rem;
      background: var(--bg-card); padding: 0.15rem 0.4rem;
      border-radius: 4px; color: var(--accent);
      word-break: break-word; overflow-wrap: anywhere;
    }}
    .sidebar-content pre {{
      background: var(--bg-elevated); border: 1px solid var(--border);
      border-radius: 8px; padding: 1rem; overflow-x: auto;
      margin-bottom: 1rem;
    }}
    .sidebar-content pre code {{
      background: none; padding: 0; font-size: 0.78rem;
      color: var(--text); line-height: 1.6;
    }}
    .code-block {{
      position: relative;
    }}
    .code-block:hover .copy-btn {{
      opacity: 1;
    }}
    .copy-btn {{
      position: absolute; top: 0.5rem; right: 0.5rem;
      background: var(--bg-card); border: 1px solid var(--border);
      color: var(--muted); font-size: 0.7rem;
      font-family: var(--sans); padding: 0.2rem 0.5rem;
      border-radius: 4px; cursor: pointer;
      opacity: 0; transition: opacity 0.15s; z-index: 1;
      display: inline-flex; align-items: center; gap: 0.25rem;
    }}
    .copy-btn:hover {{
      color: var(--accent); border-color: var(--accent);
    }}
    @media (max-width: 768px) {{
      .copy-btn {{ opacity: 1; }}
    }}
    .sidebar-content ul, .sidebar-content ol {{
      color: var(--muted); line-height: 1.7;
      margin-bottom: 1rem; padding-left: 1.25rem;
    }}
    .sidebar-content li {{ margin-bottom: 0.25rem; }}
    .sidebar-content li > .code-block {{ margin-top: 0.5rem; }}
    .sidebar-content blockquote {{
      border-left: 3px solid var(--accent); background: var(--bg-card);
      padding: 0.75rem 1rem; margin-bottom: 1rem;
      border-radius: 0 6px 6px 0;
      color: var(--text); font-size: 0.9rem;
    }}
    .sidebar-content blockquote p {{ color: var(--text); margin-bottom: 0; }}
    .sidebar-content hr {{
      border: none; border-top: 1px solid var(--border); margin: 2rem 0;
    }}
    .table-wrap {{
      overflow-x: auto;
      -webkit-overflow-scrolling: touch;
      margin-bottom: 1.5rem;
    }}
    .table-wrap table {{
      width: max-content;
      min-width: 100%;
      margin-bottom: 0;
    }}
    .sidebar-content table {{
      width: max-content; min-width: 100%;
      border-collapse: collapse; font-size: 0.85rem;
      margin-bottom: 1.5rem;
    }}
    .sidebar-content th {{
      font-family: var(--mono); font-size: 0.72rem; font-weight: 700;
      text-transform: uppercase; letter-spacing: 0.06em;
      padding: 0.75rem 1rem; text-align: left; color: var(--muted);
      border-bottom: 1px solid var(--border); background: var(--bg-card);
      white-space: nowrap;
    }}
    .sidebar-content td {{
      padding: 0.75rem 1rem; border-bottom: 1px solid var(--border);
      color: var(--muted);
      white-space: normal; word-break: normal;
      overflow-wrap: break-word; max-width: 300px;
    }}
    .sidebar-content img {{
      max-width: 100%; border-radius: 8px; border: 1px solid var(--border);
      margin: 1rem 0;
    }}
    .sidebar-content details {{
      background: var(--bg-elevated); border: 1px solid var(--border);
      border-radius: 8px; padding: 1rem; margin-bottom: 1rem;
    }}
    .sidebar-content summary {{
      font-family: var(--mono); font-size: 0.85rem;
      cursor: pointer; color: var(--accent);
    }}
    .callout {{
      border-left: 4px solid var(--accent);
      background: var(--bg-card); padding: 0.75rem 1rem;
      margin-bottom: 1rem; border-radius: 0 6px 6px 0;
      font-size: 0.9rem; color: var(--text);
    }}
    .callout-title {{
      font-family: var(--mono); font-size: 0.72rem;
      text-transform: uppercase; letter-spacing: 0.06em;
      display: block; margin-bottom: 0.25rem;
    }}
    .callout-note {{ border-left-color: var(--accent); }}
    .callout-note .callout-title {{ color: var(--accent); }}
    .callout-tip {{ border-left-color: var(--green); }}
    .callout-tip .callout-title {{ color: var(--green); }}
    .callout-warning {{ border-left-color: #f59e0b; }}
    .callout-warning .callout-title {{ color: #f59e0b; }}
    .callout-caution {{ border-left-color: #f59e0b; }}
    .callout-caution .callout-title {{ color: #f59e0b; }}
    .callout-important {{ border-left-color: #ef4444; }}
    .callout-important .callout-title {{ color: #ef4444; }}
    .doc-nav-buttons {{
      display: flex; justify-content: space-between; gap: 1rem;
      margin: 2rem 0 1rem;
    }}
    .doc-nav-btn {{
      padding: 0.5rem 1rem; border-radius: 8px;
      font-family: var(--sans); font-size: 0.82rem; font-weight: 500;
      text-decoration: none; color: var(--muted);
      border: 1px solid var(--border);
      transition: all 0.15s; max-width: 50%;
    }}
    .doc-nav-btn:hover {{
      color: var(--text); border-color: var(--muted);
    }}
    .doc-nav-next {{
      margin-left: auto; text-align: right;
    }}
    .doc-nav-prev {{
      text-align: left;
    }}
    .doc-copyright {{
      font-size: 0.78rem; color: var(--border-hover);
      padding-top: 1rem; border-top: 1px solid var(--border);
      margin-top: 1.5rem; text-align: center;
    }}
    .doc-copyright a {{
      color: var(--border-hover); text-decoration: none;
    }}
    .doc-copyright a:hover {{
      color: var(--muted);
    }}
    .nav-overlay {{
      display: none; position: fixed;
      top: 64px; left: 0; right: 0; bottom: 0;
      background: rgba(0,0,0,0.5); z-index: 199;
    }}
    .nav-overlay.active {{ display: block; }}

    .sidebar-close {{
      display: none;
      position: absolute; top: 0.5rem; right: 1rem;
      background: none; border: none;
      color: var(--muted); font-size: 1.5rem;
      cursor: pointer; padding: 0.25rem 0.5rem;
      line-height: 1; border-radius: 4px;
    }}
    .sidebar-close:hover {{
      color: var(--text); background: var(--bg-card);
    }}

    .doc-breadcrumb {{
      display: none;
      position: sticky;
      top: 64px;
      z-index: 50;
      align-items: center;
      gap: 0.5rem;
      padding: 0.5rem 1rem;
      background: var(--bg-elevated);
      border-bottom: 1px solid var(--border);
      font-size: 0.78rem;
      color: var(--muted);
      user-select: none;
      cursor: pointer;
    }}
    .doc-breadcrumb .bc-sep {{
      color: var(--border-hover);
    }}
    .doc-breadcrumb .bc-section {{
      color: var(--text);
    }}
    .doc-breadcrumb .bc-label {{
      color: var(--accent);
    }}
    @media (max-width: 768px) {{
      .sidebar {{
        display: flex;
        position: fixed; top: 64px; left: 0;
        width: 300px; height: calc(100dvh - 64px); z-index: 200;
        border-right: 1px solid var(--border);
        transform: translateX(-100%);
        transition: transform 0.25s ease;
        box-shadow: 4px 0 12px rgba(0,0,0,0.2);
      }}
      .sidebar.open {{ transform: translateX(0); }}
      .sidebar-close {{ display: block; }}
      .sidebar-content {{ padding: 1.5rem 1rem 3rem; }}
      .doc-breadcrumb {{ display: flex; }}
      .docs-layout {{ flex-direction: column; }}
      .sidebar-content th,
      .sidebar-content td {{
        padding: 0.5rem 0.5rem;
        font-size: 0.78rem;
      }}
    }}
  </style>
  <script src="/assets/js/theme-init.js"></script>
</head>
<body>
  {nav_html}
  <div class="nav-overlay" id="sidebar-overlay"></div>

  <div class="doc-breadcrumb" id="sidebar-toggle" role="button" tabindex="0" aria-label="Toggle docs navigation">
    <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" style="flex-shrink:0">
      <rect x="3" y="3" width="18" height="18" rx="2"/>
      <line x1="9" y1="3" x2="9" y2="21"/>
    </svg>
    {bc_html}
  </div>

  <div class="docs-layout">
    <aside class="sidebar" id="sidebar">
      <div class="sidebar-inner">
        <button class="sidebar-close" id="sidebar-close" aria-label="Close sidebar">&times;</button>
{s}
      </div>
    </aside>
    <div class="sidebar-content">
{body}
{nav_btns}
      <p class="doc-copyright">{footer_html}</p>
    </div>
  </div>

  <script src="/assets/js/theme.js"></script>
  <script src="/assets/js/docs.js"></script>
</body>
</html>'''

def fix_img_paths(html):
    return re.sub(r'Documentation/resources/', r'assets/resources/', html)

def fetch_latest_release():
    try:
        url = 'https://api.github.com/repos/TharukRenuja/zing/releases?per_page=5'
        req = urllib.request.Request(url)
        token = os.environ.get('GITHUB_TOKEN')
        if token:
            req.add_header('Authorization', f'Bearer {token}')
        with urllib.request.urlopen(req, timeout=10) as resp:
            releases = json.loads(resp.read())
    except Exception:
        return None

    if not releases:
        return None

    latest = releases[0]
    version = latest.get('tag_name', 'v0.3.0')
    date = latest.get('published_at', '2026-08-17')[:10]
    body = latest.get('body', '')
    changelog = md_to_html(body) if body else '<p>No changelog available.</p>'
    changelog = re.sub(r'<div class="code-block"><button class="copy-btn"[^>]*>.*?</button>', '', changelog)
    changelog = changelog.replace('</div><pre><code>', '<pre><code>')

    older_rows = []
    for r in releases[1:]:
        tag = r.get('tag_name', '')
        rd = r.get('published_at', '')[:10]
        rn = r.get('name', tag)
        base = f'https://github.com/TharukRenuja/zing/releases/download/{tag}'
        info = f'https://github.com/TharukRenuja/zing/releases/tag/{tag}'
        older_rows.append(
            f'<tr><td>{rn}</td><td>{rd}</td><td class="dl-cell"><div class="dl-links">'
            f'<a href="{base}/zing-{tag}-aarch64-linux.tar.gz" class="dl-secondary" title="Linux ARM"><i class="fa-brands fa-linux"></i> arm</a>'
            f'<a href="{base}/zing-{tag}-x86_64-linux.tar.gz" class="dl-secondary" title="Linux x86"><i class="fa-brands fa-linux"></i> x86</a>'
            f'<a href="{base}/zing-{tag}-x86_64-mac.dmg" class="dl-secondary" title="macOS Intel"><i class="fa-brands fa-apple"></i> intel</a>'
            f'<a href="{base}/zing-{tag}-aarch64-mac.dmg" class="dl-secondary" title="macOS Silicon"><i class="fa-brands fa-apple"></i> silicon</a>'
            f'<a href="{base}/zing-{tag}-windows.msi" class="dl-secondary" title="Windows"><i class="fa-brands fa-windows"></i> universal</a>'
            f'</div></td><td><a href="{info}" class="dl-secondary dl-info" title="Release info" target="_blank" rel="noopener noreferrer"><i class="fa-solid fa-circle-info"></i></a></td></tr>'
        )
    older_html = (
        '<div class="table-wrap"><table><thead><tr><th>Version</th><th>Date</th><th class="dl-header">Downloads</th></tr></thead><tbody>'
        + '\n'.join(older_rows)
        + '</tbody></table></div>'
        if older_rows else ''
    )

    return {
        'version': version,
        'date': date,
        'changelog': changelog,
        'older_html': older_html,
    }


def build_downloads_page(root, nav_template, footer_template):
    dl_nav = nav_template.replace('{{FEATURES_HREF}}', '/#features').replace('{{DOCS_STYLE}}', '')
    dl_nav = dl_nav.replace('<a href="/downloads">Downloads</a>', '<a href="/downloads" class="active">Downloads</a>')
    release_info = fetch_latest_release()
    if release_info:
        version = release_info['version']
        date = release_info['date']
        changelog = release_info['changelog']
        older_html = release_info['older_html']
    else:
        version = 'v0.3.0'
        date = '2026-08-17'
        changelog = md_to_html('No changelog available.')
        older_html = ''
    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
  <meta name="description" content="Download zing - a modern HTTP download manager for Linux, macOS, and Windows.">
  <title>Downloads - zing</title>
  <meta property="og:title" content="Downloads - zing">
  <meta property="og:description" content="Download zing for Linux, macOS, and Windows.">
  <meta property="og:url" content="https://zing.tharuk.pro/downloads">
  <meta property="og:type" content="website">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="Downloads - zing">
  <meta name="twitter:description" content="Download zing for Linux, macOS, and Windows.">
  <link rel="canonical" href="https://zing.tharuk.pro/downloads">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link rel="dns-prefetch" href="https://github.com">
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;700&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="/style.css">
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">
  <link rel="icon" href="/assets/favicon.ico">
  <link rel="apple-touch-icon" href="/assets/favicon.ico">
  <script src="/assets/js/theme-init.js"></script>
</head>
<body>
<!--NAV_START-->
{dl_nav}
<!--NAV_END-->
<main>
  <section class="download-hero">
    <div class="container">
      <div class="section-label">Downloads</div>
      <h1>Get zing</h1>
      <p class="section-desc">Free, open source, and available on Linux, macOS, and Windows.</p>
      <div class="dl-version">{version}</div>
      <div class="dl-cards">
        <div class="dl-card">
          <div class="dl-card-icon">
            <i class="fa-brands fa-linux"></i>
          </div>
          <h3 class="dl-card-title">Linux</h3>
          <p class="dl-card-desc">Static binary for any Linux distribution. Zero dependencies.</p>
          <div class="dl-dropdown">
            <a href="https://github.com/TharukRenuja/zing/releases/latest" class="btn btn-primary dl-dropdown-trigger" rel="noopener noreferrer">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
               Download {version}
               <svg class="dl-chevron" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="6 9 12 15 18 9"/></svg>
             </a>
             <div class="dl-dropdown-menu">
               <a href="https://github.com/TharukRenuja/zing/releases/latest" class="dl-dropdown-item" rel="noopener noreferrer">
                 <i class="fa-solid fa-microchip"></i> x86_64
               </a>
               <a href="https://github.com/TharukRenuja/zing/releases/latest" class="dl-dropdown-item" rel="noopener noreferrer">
                 <i class="fa-solid fa-microchip"></i> aarch64
               </a>
             </div>
           </div>
         </div>
         <div class="dl-card">
           <div class="dl-card-icon">
             <i class="fa-brands fa-apple"></i>
           </div>
           <h3 class="dl-card-title">macOS</h3>
           <p class="dl-card-desc">Universal binary for Apple Silicon and Intel Macs.</p>
           <div class="dl-dropdown">
             <a href="https://github.com/TharukRenuja/zing/releases/latest" class="btn btn-primary dl-dropdown-trigger" rel="noopener noreferrer">
               <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
               Download {version}
               <svg class="dl-chevron" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="6 9 12 15 18 9"/></svg>
            </a>
            <div class="dl-dropdown-menu">
              <a href="https://github.com/TharukRenuja/zing/releases/latest" class="dl-dropdown-item" rel="noopener noreferrer">
                <i class="fa-brands fa-apple"></i> Intel (x86_64)
              </a>
              <a href="https://github.com/TharukRenuja/zing/releases/latest" class="dl-dropdown-item" rel="noopener noreferrer">
                <i class="fa-brands fa-apple"></i> Apple Silicon (aarch64)
              </a>
            </div>
          </div>
        </div>
        <div class="dl-card">
          <div class="dl-card-icon">
            <i class="fa-brands fa-windows"></i>
          </div>
          <h3 class="dl-card-title">Windows</h3>
          <p class="dl-card-desc">Pre-built executable for Windows 10+ with daemon service support.</p>
          <a href="https://github.com/TharukRenuja/zing/releases/latest" class="btn btn-primary" rel="noopener noreferrer">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
            Download {version}
          </a>
        </div>
      </div>
    </div>
  </section>

  <section class="section">
    <div class="container">
      <div class="section-label">Browser Extension</div>
      <h2>One-click capture</h2>
      <p class="section-desc">Install the zing Interceptor extension and every download automatically goes through zing. Filter by file type or domain.</p>
      <div class="ext-downloads">
        <div class="ext-downloads-info">
          <h3 style="margin:0 0 0.5rem;font-size:1rem">Features</h3>
          <ul style="list-style:none;padding:0">
            <li style="color:var(--muted);font-size:0.9rem;padding:0.35rem 0;padding-left:1.25rem;position:relative"><span style="position:absolute;left:0;top:0.65rem;width:6px;height:6px;border-radius:50%;background:var(--accent)"></span>Chrome and Firefox via Native Messaging</li>
            <li style="color:var(--muted);font-size:0.9rem;padding:0.35rem 0;padding-left:1.25rem;position:relative"><span style="position:absolute;left:0;top:0.65rem;width:6px;height:6px;border-radius:50%;background:var(--accent)"></span>File type and domain-based interception filters</li>
            <li style="color:var(--muted);font-size:0.9rem;padding:0.35rem 0;padding-left:1.25rem;position:relative"><span style="position:absolute;left:0;top:0.65rem;width:6px;height:6px;border-radius:50%;background:var(--accent)"></span>Configurable connections, concurrent tasks, and speed limits</li>
            <li style="color:var(--muted);font-size:0.9rem;padding:0.35rem 0;padding-left:1.25rem;position:relative"><span style="position:absolute;left:0;top:0.65rem;width:6px;height:6px;border-radius:50%;background:var(--accent)"></span>Stats dashboard with intercepted, ignored, and detected counts</li>
          </ul>
        </div>
        <div class="ext-downloads-cards">
          <div class="dl-card">
            <div class="dl-card-icon"><i class="fa-brands fa-chrome"></i></div>
            <h3 class="dl-card-title">Chrome</h3>
            <p class="dl-card-desc">Install from Chrome WebStore.</p>
            <a href="https://github.com/TharukRenuja/zing/releases" class="btn btn-primary" rel="noopener noreferrer">
              <i class="fa-solid fa-puzzle-piece"></i>
              Install
            </a>
          </div>
          <div class="dl-card">
            <div class="dl-card-icon"><i class="fa-brands fa-firefox-browser"></i></div>
            <h3 class="dl-card-title">Firefox</h3>
            <p class="dl-card-desc">Install from Firefox Add-ons.</p>
            <a href="https://github.com/TharukRenuja/zing/releases" class="btn btn-primary" rel="noopener noreferrer">
              <i class="fa-solid fa-puzzle-piece"></i>
              Install
            </a>
          </div>
        </div>
      </div>
    </div>
  </section>

  <div class="divider"></div>

  <section class="section">
    <div class="container">
      <div class="section-label">Install from source</div>
      <h2>Build it yourself</h2>
      <p class="section-desc">zing is written in Rust. Clone the repo and build with cargo.</p>
      <div class="build-terminal">
        <div><span class="terminal-prompt">$ </span><span style="color:var(--text)">git clone https://github.com/TharukRenuja/zing.git</span></div>
        <div><span class="terminal-prompt">$ </span><span style="color:var(--text)">cd zing</span></div>
        <div><span class="terminal-prompt">$ </span><span style="color:var(--text)">cargo build --release</span></div>
        <div><span class="terminal-prompt">$ </span><span style="color:var(--text)">cp target/release/zing /usr/local/bin/</span></div>
      </div>
    </div>
  </section>

  <div class="divider"></div>

  <section class="section">
    <div class="container">
      <div class="section-label">Changelog</div>
      <h2>{version}</h2>
      <div class="changelog-wrap">
        <div class="changelog" id="changelog-body">
          {changelog}
        </div>
        <button class="changelog-toggle" id="changelog-toggle" onclick="document.getElementById('changelog-body').classList.toggle('expanded');this.textContent=this.textContent==='Show changelog'?'Hide changelog':'Show changelog'">Show changelog</button>
      </div>
    </div>
  </section>

  <div class="divider"></div>

  <section class="section">
    <div class="container">
      <div class="section-label">Older Versions</div>
      <h2>Previous releases</h2>
      {older_html}
    </div>
  </section>
</main>

<!--FOOTER_START-->
<footer>
  <div class="container">
    <p>{footer_template}</p>
  </div>
</footer>
<!--FOOTER_END-->

<script src="/assets/js/docs.js"></script>
<script src="/assets/js/theme.js"></script>
</body>
</html>'''
    with open(os.path.join(root, 'downloads.html'), 'w') as f:
        f.write(html)
    print("OK: downloads.html")

def generate_sitemap(root):
    base = 'https://zing.tharuk.pro'
    today = '2026-08-17'
    priorities = {
        'index.html': ('/', 1.0),
        'downloads.html': ('/downloads.html', 0.9),
        '404.html': ('/404.html', 0.1),
    }
    doc_priorities = {
        'getting-started': 0.9, 'architecture': 0.8,
        'download-engine': 0.7, 'cli-reference': 0.7, 'daemon': 0.7, 'gui': 0.7,
        'browser-extension': 0.6, 'tui': 0.6,
        'troubleshooting': 0.6, 'configuration': 0.6,
    }
    urls = [(loc, pri) for fname, (loc, pri) in priorities.items()]
    urls += [(f'/docs/{slug}.html', pri) for slug, pri in doc_priorities.items()]
    lines = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for loc, pri in urls:
        lines.append('  <url>')
        lines.append(f'    <loc>{base}{loc}</loc>')
        lines.append(f'    <lastmod>{today}</lastmod>')
        lines.append(f'    <changefreq>monthly</changefreq>')
        lines.append(f'    <priority>{pri}</priority>')
        lines.append('  </url>')
    lines.append('</urlset>')
    with open(os.path.join(root, 'sitemap.xml'), 'w') as f:
        f.write('\n'.join(lines) + '\n')
    print("OK: sitemap.xml")

if __name__ == '__main__':
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    docs_dir = os.path.join(root, 'docs/content')
    out_dir = os.path.join(root, 'docs')

    with open(os.path.join(root, '_nav.html')) as f:
        nav_template = f.read()
    with open(os.path.join(root, '_footer.html')) as f:
        footer_template = f.read()

    pages = load_pages(docs_dir)

    for slug, title, section, order, desc, keywords, fname in pages:
        path = os.path.join(docs_dir, fname)
        if not os.path.exists(path):
            print(f"SKIP: {fname} not found")
            continue
        with open(path) as f:
            md = f.read()
        md = re.sub(r'^\s*<!--.*?-->\s*', '', md, flags=re.DOTALL)
        body = md_to_html(md)
        body = fix_img_paths(body)
        slug = fname.replace('.md', '').lower()
        page = make_page(title, body, slug, nav_template, footer_template, pages)
        out_path = os.path.join(out_dir, slug + '.html')
        with open(out_path, 'w') as f:
            f.write(page)
        print(f"OK: {slug}.html")

    # Stamp index.html
    index_path = os.path.join(root, 'index.html')
    with open(index_path) as f:
        index_html = f.read()
    index_nav = nav_template.replace('{{FEATURES_HREF}}', '#features').replace('{{DOCS_STYLE}}', '')
    index_html = re.sub(
        r'<!--NAV_START-->.*?<!--NAV_END-->',
        f'<!--NAV_START-->\n{index_nav}\n<!--NAV_END-->',
        index_html,
        flags=re.DOTALL
    )
    release_info = fetch_latest_release()
    if release_info:
        version = release_info['version']
        index_html = re.sub(
            r'(<div class="hero-badge"><span></span>)v[^<]+( · Open Source</div>)',
            lambda m: f'{m.group(1)}{version}{m.group(2)}',
            index_html,
        )
        index_html = re.sub(
            r'("softwareVersion"\s*:\s*")v?[^"\n]+(",)',
            lambda m: f'{m.group(1)}{version.lstrip("v")}{m.group(2)}',
            index_html,
        )
    index_html = index_html.replace('{{FOOTER}}', footer_template)
    with open(index_path, 'w') as f:
        f.write(index_html)
    print("OK: index.html")

    # Generate downloads.html
    build_downloads_page(root, nav_template, footer_template)

    # Generate 404.html
    four04_nav = nav_template.replace('{{FEATURES_HREF}}', '/#features').replace('{{DOCS_STYLE}}', '')
    four04_html = f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <meta name="description" content="Page not found - zing">
  <title>404 - zing</title>
  <meta property="og:title" content="404 - zing">
  <meta property="og:description" content="Page not found">
  <meta property="og:url" content="https://zing.tharuk.pro/404.html">
  <meta property="og:type" content="website">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="404 - zing">
  <meta name="twitter:description" content="Page not found">
  <link rel="canonical" href="https://zing.tharuk.pro/404.html">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;700&display=swap" rel="stylesheet">
  <link rel="icon" href="/assets/favicon.ico">
  <link rel="apple-touch-icon" href="/assets/favicon.ico">
  <link rel="stylesheet" href="/style.css">
  <script src="/assets/js/theme-init.js"></script>
</head>
<body>
{four04_nav}
  <main style="display:flex;flex-direction:column;align-items:center;justify-content:center;min-height:calc(100vh - 64px - 80px);padding:2rem;text-align:center">
    <h1 style="font-size:4rem;font-family:var(--mono);color:var(--muted);margin-bottom:0.5rem">404</h1>
    <p style="color:var(--muted);font-size:1rem;margin-bottom:2rem;max-width:400px">The page you're looking for doesn't exist.</p>
    <div style="display:flex;gap:0.75rem;flex-wrap:wrap;justify-content:center">
      <a href="/" class="btn btn-primary">Go Home</a>
      <a href="/docs/" class="btn btn-ghost">Browse Docs</a>
    </div>
  </main>
  <footer>
    <p>{footer_template}</p>
  </footer>
</body>
</html>'''
    with open(os.path.join(root, '404.html'), 'w') as f:
        f.write(four04_html)
    print("OK: 404.html")

    generate_sitemap(root)
