#!/usr/bin/env python3
"""Convert a blog post's markdown into clean HTML suitable for pasting into the Zhihu editor.

Usage: python3 tools/md2zhihu.py content/posts/xxx.md [--base https://bryanzhang.github.io] > out.html

Handles the subset of markdown used in this blog: paragraphs, **bold**, `code`, fenced code,
images, blockquotes, ordered/unordered lists, headings, <autolinks>, [text](url), and
the {{< series-nav >}} shortcode (dropped). Front matter is parsed for title/url slug.
"""
import html
import re
import sys
from pathlib import Path

base = "https://bryanzhang.github.io"
args = [a for a in sys.argv[1:]]
if "--base" in args:
    i = args.index("--base"); base = args[i + 1]; del args[i:i + 2]
src = Path(args[0]).read_text(encoding="utf-8")

fm, body = re.match(r"^---\n(.*?)\n---\n(.*)$", src, re.S).groups()
title = re.search(r'^title:\s*"?(.*?)"?\s*$', fm, re.M).group(1)
slug = Path(args[0]).stem
post_url = f"{base}/posts/{slug}/"

body = re.sub(r"\{\{<.*?>\}\}", "", body)


def inline(t):
    t = html.escape(t, quote=False)
    t = re.sub(r"&lt;(https?://[^&]+)&gt;", r'<a href="\1">\1</a>', t)
    t = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", lambda m: f'<a href="{abs_url(m.group(2))}">{m.group(1)}</a>', t)
    t = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", t)
    t = re.sub(r"`([^`]+)`", r"<code>\1</code>", t)
    return t


def abs_url(u):
    return base + u if u.startswith("/") else u


out = []
lines = body.split("\n")
i = 0
while i < len(lines):
    ln = lines[i]
    if ln.startswith("```"):
        j = i + 1
        buf = []
        while j < len(lines) and not lines[j].startswith("```"):
            buf.append(lines[j]); j += 1
        out.append("<pre>" + html.escape("\n".join(buf)) + "</pre>")
        i = j + 1; continue
    m = re.match(r"^!\[([^\]]*)\]\(([^)]+)\)\s*$", ln)
    if m:
        out.append(f'<p><img src="{abs_url(m.group(2))}" alt="{html.escape(m.group(1))}"></p>')
        i += 1; continue
    m = re.match(r"^(#{1,6})\s+(.*)$", ln)
    if m:
        lvl = min(len(m.group(1)) + 1, 3)
        out.append(f"<h{lvl}>{inline(m.group(2))}</h{lvl}>")
        i += 1; continue
    if ln.startswith(">"):
        buf = []
        while i < len(lines) and lines[i].startswith(">"):
            buf.append(lines[i][1:].strip()); i += 1
        out.append("<blockquote>" + inline(" ".join(buf)) + "</blockquote>")
        continue
    m = re.match(r"^(\d+)\.\s+(.*)$", ln)
    if m or ln.startswith("- "):
        tag = "ol" if m else "ul"
        buf = []
        while i < len(lines) and (re.match(r"^\d+\.\s+", lines[i]) or lines[i].startswith("- ")):
            buf.append(re.sub(r"^(\d+\.|-)\s+", "", lines[i])); i += 1
        out.append(f"<{tag}>" + "".join(f"<li>{inline(x)}</li>" for x in buf) + f"</{tag}>")
        continue
    if ln.strip() == "":
        i += 1; continue
    buf = [ln]
    i += 1
    while i < len(lines) and lines[i].strip() and not re.match(r"^(```|!\[|#|>|\d+\.\s|- )", lines[i]):
        buf.append(lines[i]); i += 1
    joined = buf[0]
    for nxt in buf[1:]:
        # 中文行之间直接拼接，避免出现多余空格
        cjk = lambda ch: "\u3000" <= ch <= "\u9fff" or "\uff00" <= ch <= "\uffef"
        sep = "" if (joined and nxt and (cjk(joined[-1]) or cjk(nxt[0]))) else " "
        joined += sep + nxt
    out.append("<p>" + inline(joined) + "</p>")

out.append(f'<p>原文发布于 <a href="{post_url}">{post_url}</a>，以此为准。</p>')
sys.stdout.write(f"<!-- title: {title} -->\n" + "\n".join(out) + "\n")
