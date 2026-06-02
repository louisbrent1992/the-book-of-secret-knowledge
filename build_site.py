#!/usr/bin/env python3
"""Parse README.md and generate an organized, searchable webpage of links."""
import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).parent
README = ROOT / "README.md"

# The curated-link collection lives between the first chapter (CLI Tools)
# and the start of "Shell One-liners" (which is code, not links).
START_LINE = 111   # "#### CLI Tools"
END_LINE = 1660    # last line before "#### Shell One-liners"

LINK_RE = re.compile(
    r'<a\s+href="([^"]+)"\s*>(.*?)</a>\s*-?\s*(.*?)(?:<br\s*/?>|$)',
    re.IGNORECASE,
)
TAG_RE = re.compile(r"<[^>]+>")


def strip_tags(s: str) -> str:
    return TAG_RE.sub("", s).strip()


def parse():
    lines = README.read_text(encoding="utf-8").splitlines()
    chapters = []          # list of {name, slug, sections:[{name, links:[...]}]}
    cur_chapter = None
    cur_section = None

    for i, raw in enumerate(lines, start=1):
        if i < START_LINE or i > END_LINE:
            continue
        line = raw.rstrip()

        m = re.match(r"^####\s+(.*)$", line)            # chapter
        if m:
            title = re.sub(r"\s*&nbsp;.*$", "", m.group(1)).strip()
            cur_chapter = {"name": title, "slug": slug(title), "sections": []}
            chapters.append(cur_chapter)
            cur_section = None
            continue

        m = re.match(r"^#{5,6}\s+(.*)$", line)           # section / subsection
        if m and cur_chapter is not None:
            title = m.group(1)
            title = re.sub(r":[a-z_]+:", "", title)      # drop emoji shortcodes
            title = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", title)  # md links -> text
            title = title.replace("&nbsp;", " ").strip()
            cur_section = {"name": title, "links": []}
            cur_chapter["sections"].append(cur_section)
            continue

        if "<a href" not in line or cur_chapter is None:
            continue

        # Ensure links land in a section (some chapters open links directly).
        if cur_section is None:
            cur_section = {"name": "", "links": []}
            cur_chapter["sections"].append(cur_section)

        for url, name_raw, desc_raw in LINK_RE.findall(line):
            name = strip_tags(name_raw)
            unavailable = "<b>*</b>" in desc_raw or desc_raw.strip().endswith("*")
            desc = strip_tags(desc_raw).rstrip("*").strip()
            if not name:
                continue
            cur_section["links"].append({
                "name": name,
                "url": url,
                "desc": desc,
                "unavailable": unavailable,
            })

    # Drop empty sections / chapters.
    for ch in chapters:
        ch["sections"] = [s for s in ch["sections"] if s["links"]]
    chapters = [c for c in chapters if c["sections"]]
    return chapters


def slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def domain(url: str) -> str:
    m = re.match(r"https?://([^/]+)/?", url)
    return m.group(1).lower().lstrip("www.") if m else url


def render(chapters):
    total = sum(len(s["links"]) for c in chapters for s in c["sections"])
    data_json = json.dumps(chapters, ensure_ascii=False)

    nav = "\n".join(
        f'        <li><a href="#{c["slug"]}">{html.escape(c["name"])}'
        f' <span class="ncount">{sum(len(s["links"]) for s in c["sections"])}</span></a></li>'
        for c in chapters
    )

    return TEMPLATE.format(total=total, nchapters=len(chapters), nav=nav, data=data_json)


TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>The Book of Secret Knowledge — Links</title>
<style>
  :root {{
    --bg: #0d1117; --panel: #161b22; --panel2: #1c2330; --border: #283040;
    --text: #c9d1d9; --muted: #8b949e; --accent: #58a6ff; --accent2: #2ea043;
    --warn: #d29922;
  }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0; font: 15px/1.55 -apple-system, BlinkMacSystemFont, "Segoe UI",
    Roboto, Helvetica, Arial, sans-serif; background: var(--bg); color: var(--text);
  }}
  a {{ color: var(--accent); text-decoration: none; }}
  a:hover {{ text-decoration: underline; }}
  .layout {{ display: flex; min-height: 100vh; }}
  /* Sidebar */
  aside {{
    width: 260px; flex: 0 0 260px; background: var(--panel); border-right: 1px solid var(--border);
    position: sticky; top: 0; height: 100vh; overflow-y: auto; padding: 22px 16px;
  }}
  aside h1 {{ font-size: 17px; margin: 0 0 4px; color: #fff; }}
  aside .tag {{ color: var(--muted); font-size: 12px; margin-bottom: 18px; }}
  aside ul {{ list-style: none; margin: 0; padding: 0; }}
  aside li a {{
    display: flex; justify-content: space-between; align-items: center; gap: 8px;
    padding: 6px 10px; border-radius: 6px; color: var(--text); font-size: 13.5px;
  }}
  aside li a:hover {{ background: var(--panel2); text-decoration: none; }}
  .ncount {{ background: var(--panel2); color: var(--muted); font-size: 11px;
    padding: 1px 7px; border-radius: 10px; }}
  /* Main */
  main {{ flex: 1; min-width: 0; padding: 24px 32px 80px; max-width: 1100px; }}
  .topbar {{ position: sticky; top: 0; background: rgba(13,17,23,.92);
    backdrop-filter: blur(6px); padding: 16px 0 14px; margin-bottom: 8px; z-index: 5;
    border-bottom: 1px solid var(--border); }}
  #search {{ width: 100%; padding: 12px 16px; font-size: 15px; color: var(--text);
    background: var(--panel); border: 1px solid var(--border); border-radius: 10px; }}
  #search:focus {{ outline: none; border-color: var(--accent); }}
  .stats {{ color: var(--muted); font-size: 12.5px; margin-top: 8px; }}
  h2.chapter {{ font-size: 22px; color: #fff; margin: 38px 0 4px;
    padding-bottom: 8px; border-bottom: 2px solid var(--border); scroll-margin-top: 90px; }}
  h3.section {{ font-size: 14px; text-transform: uppercase; letter-spacing: .06em;
    color: var(--accent); margin: 24px 0 12px; }}
  .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(290px, 1fr)); gap: 12px; }}
  .card {{ background: var(--panel); border: 1px solid var(--border); border-radius: 10px;
    padding: 13px 15px; transition: border-color .15s, transform .15s; }}
  .card:hover {{ border-color: var(--accent); transform: translateY(-1px); }}
  .card .name {{ font-weight: 600; font-size: 14.5px; }}
  .card .name a {{ color: #e6edf6; }}
  .card .domain {{ font-size: 11.5px; color: var(--muted); margin-top: 2px;
    word-break: break-all; }}
  .card .desc {{ font-size: 13px; color: var(--text); margin-top: 7px; }}
  .card.unavail {{ opacity: .6; }}
  .badge {{ font-size: 10px; color: var(--warn); border: 1px solid var(--warn);
    border-radius: 4px; padding: 0 4px; margin-left: 6px; vertical-align: middle; }}
  mark {{ background: #bb8009; color: #fff; border-radius: 2px; padding: 0 1px; }}
  .empty {{ color: var(--muted); padding: 40px 0; text-align: center; display: none; }}
  footer {{ color: var(--muted); font-size: 12px; margin-top: 50px;
    border-top: 1px solid var(--border); padding-top: 18px; }}
  @media (max-width: 780px) {{
    aside {{ display: none; }} main {{ padding: 18px; }}
  }}
</style>
</head>
<body>
<div class="layout">
  <aside>
    <h1>📕 Secret Knowledge</h1>
    <div class="tag">{total} curated links · {nchapters} chapters</div>
    <ul>
{nav}
    </ul>
  </aside>
  <main>
    <div class="topbar">
      <input id="search" type="search" placeholder="Search {total} links by name, description, or domain…" autocomplete="off">
      <div class="stats" id="stats"></div>
    </div>
    <div id="content"></div>
    <div class="empty" id="empty">No links match your search.</div>
    <footer>
      Generated from <a href="https://github.com/trimstray/the-book-of-secret-knowledge">the-book-of-secret-knowledge</a> README · links open in a new tab.
    </footer>
  </main>
</div>
<script>
const DATA = {data};

function domain(url) {{
  try {{ return new URL(url).hostname.replace(/^www\./, ''); }}
  catch (e) {{ return url; }}
}}
function esc(s) {{
  return s.replace(/[&<>"]/g, c => ({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}}[c]));
}}
function highlight(s, q) {{
  if (!q) return esc(s);
  const i = s.toLowerCase().indexOf(q);
  if (i < 0) return esc(s);
  return esc(s.slice(0, i)) + '<mark>' + esc(s.slice(i, i + q.length)) + '</mark>' + esc(s.slice(i + q.length));
}}

const content = document.getElementById('content');
const stats = document.getElementById('stats');
const empty = document.getElementById('empty');

function render(q) {{
  q = q.trim().toLowerCase();
  let shown = 0, frag = '';
  for (const ch of DATA) {{
    let chHtml = '', chCount = 0;
    for (const sec of ch.sections) {{
      const matches = sec.links.filter(l =>
        !q || l.name.toLowerCase().includes(q) ||
        l.desc.toLowerCase().includes(q) ||
        domain(l.url).includes(q));
      if (!matches.length) continue;
      chCount += matches.length;
      if (sec.name) chHtml += `<h3 class="section">${{esc(sec.name)}}</h3>`;
      chHtml += '<div class="grid">';
      for (const l of matches) {{
        chHtml += `<div class="card${{l.unavailable ? ' unavail' : ''}}">
          <div class="name"><a href="${{esc(l.url)}}" target="_blank" rel="noopener">${{highlight(l.name, q)}}</a>${{l.unavailable ? '<span class="badge">offline?</span>' : ''}}</div>
          <div class="domain">${{esc(domain(l.url))}}</div>
          ${{l.desc ? `<div class="desc">${{highlight(l.desc, q)}}</div>` : ''}}
        </div>`;
      }}
      chHtml += '</div>';
    }}
    if (chCount) {{
      shown += chCount;
      frag += `<h2 class="chapter" id="${{ch.slug}}">${{esc(ch.name)}}</h2>` + chHtml;
    }}
  }}
  content.innerHTML = frag;
  empty.style.display = shown ? 'none' : 'block';
  stats.textContent = q ? `${{shown}} result${{shown === 1 ? '' : 's'}} for "${{q}}"` : '';
}}

const search = document.getElementById('search');
let t;
search.addEventListener('input', () => {{ clearTimeout(t); t = setTimeout(() => render(search.value), 120); }});
render('');
</script>
</body>
</html>
"""


def main():
    chapters = parse()
    out = render(chapters)
    (ROOT / "index.html").write_text(out, encoding="utf-8")
    total = sum(len(s["links"]) for c in chapters for s in c["sections"])
    print(f"Wrote index.html: {len(chapters)} chapters, {total} links")
    for c in chapters:
        n = sum(len(s['links']) for s in c['sections'])
        print(f"  {c['name']}: {n} links across {len(c['sections'])} sections")


if __name__ == "__main__":
    main()
