#!/usr/bin/env python3
"""Render a digest markdown file as an HTML email.

Email clients strip <style> blocks unpredictably, so every rule is inlined and
the layout is table-based. Produces digest_YYYY-MM-DD.html next to the source.
"""
import argparse
import datetime as dt
import html
import pathlib
import re
import sys

INK = "#14171a"
MUTED = "#5b6570"
FAINT = "#8a939c"
ACCENT = "#26485f"
RULE = "#e6e8eb"
PAGE_BG = "#f4f6f7"
CARD_BG = "#ffffff"
AMBER_BG = "#fdf6e3"
AMBER_INK = "#8a6100"
AMBER_RULE = "#e8d9ae"

SANS = ("-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,"
        "Helvetica,Arial,sans-serif")
SERIF = "Georgia,'Iowan Old Style','Times New Roman',serif"

# Section heading -> (display label, accent treatment)
SECTION_META = {
    "TOP PAPERS TODAY": ("Top papers today", "The five worth reading first"),
    "TIER A — ALL NEW NEUROSCIENCE": ("Tier A — all new neuroscience", None),
    "NEURODEGENERATION & AGING — TOP 5": ("Neurodegeneration & aging", None),
    "PREPRINTS": ("Preprints", "Not peer reviewed — interpret accordingly"),
    "NOW PUBLISHED": ("Now published", None),
}

PREPRINT_TAG = "[PREPRINT — NOT PEER REVIEWED]"


def md_inline(text):
    """Convert the inline markdown the digest actually uses."""
    out = html.escape(text, quote=False)
    out = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", out)
    out = re.sub(r"(?<!\w)\*(.+?)\*(?!\w)", r"<em>\1</em>", out)
    out = re.sub(r"`(.+?)`", r"<code>\1</code>", out)
    # <sup> survives html.escape as literal text; restore it.
    out = out.replace("&lt;sup&gt;", "<sup>").replace("&lt;/sup&gt;", "</sup>")
    out = re.sub(r"(https://doi\.org/\S+)",
                 rf'<a href="\1" style="color:{ACCENT};text-decoration:none">\1</a>',
                 out)
    return out


def parse(md):
    """Split the digest into sections of papers.

    Returns (meta_lines, [(section_title, [paper, ...]), ...]).
    """
    lines = md.split("\n")
    title_line = next((l for l in lines if l.startswith("# ")), "")
    meta = [l.strip() for l in lines[:8]
            if l.startswith("*") and not l.startswith("**")]

    sections, cur_sec, cur_paper = [], None, None

    def flush_paper():
        nonlocal cur_paper
        if cur_paper and cur_sec is not None:
            cur_sec[1].append(cur_paper)
        cur_paper = None

    pending_preprint = False
    for raw in lines:
        line = raw.rstrip()
        if line.startswith("## "):
            flush_paper()
            cur_sec = (line[3:].strip(), [])
            sections.append(cur_sec)
            pending_preprint = False
        elif line.startswith("### "):
            flush_paper()
            cur_paper = {"title": line[4:].strip(), "byline": "", "fields": [],
                         "link": None, "preprint": pending_preprint}
            pending_preprint = False
        elif line.strip() == f"**{PREPRINT_TAG}**":
            pending_preprint = True
        elif cur_paper is not None and line.strip():
            m = re.match(r"\*\*(DOI|Link):\*\*\s*(\S+)", line.strip())
            if m:
                cur_paper["link"] = m.group(2)
                continue
            m = re.match(r"\*\*(.+?):\*\*\s*(.*)", line.strip())
            if m and m.group(1) in ("Why it matters", "Key findings",
                                    "Model/system & primary method",
                                    "Model system & primary method"):
                cur_paper["fields"].append((m.group(1), m.group(2)))
            elif not cur_paper["byline"] and line.strip().startswith("**"):
                cur_paper["byline"] = line.strip()
            elif line.strip().startswith("---"):
                # horizontal rule between papers, not prose
                continue
            elif cur_paper["fields"]:
                # continuation of the previous field
                k, v = cur_paper["fields"][-1]
                cur_paper["fields"][-1] = (k, f"{v} {line.strip()}")
        elif cur_sec is not None and line.strip() and cur_paper is None:
            if not line.startswith("---") and not line.startswith("#"):
                cur_sec[1].append({"prose": line.strip()})
    flush_paper()
    return title_line, meta, sections


def render_byline(byline):
    """`**First & Last | Journal**` -> authors in muted text, journal as a pill."""
    # `**First & Last | Journal**` optionally followed by an italic aside.
    m = re.match(r"^\*\*(.+?)\*\*\s*(.*)$", byline.strip())
    if m:
        inner, trailing = m.group(1), m.group(2)
    else:
        inner, trailing = byline.strip().strip("*"), ""
    if "|" in inner:
        authors, journal = inner.rsplit("|", 1)
    else:
        authors, journal = inner, ""
    bits = []
    if journal.strip():
        bits.append(
            f'<span style="display:inline-block;background:{PAGE_BG};'
            f'border:1px solid {RULE};border-radius:3px;padding:2px 7px;'
            f'font-size:12px;font-weight:600;color:{ACCENT};'
            f'letter-spacing:.01em">{html.escape(journal.strip())}</span>'
        )
    if authors.strip():
        bits.append(f'<span style="color:{MUTED};font-size:13px">'
                    f'{md_inline(authors.strip())}</span>')
    if trailing.strip():
        bits.append(f'<span style="color:{FAINT};font-size:12px">'
                    f'{md_inline(trailing.strip())}</span>')
    return (f'<div style="margin:0 0 14px;line-height:1.9">'
            + " &nbsp;".join(bits) + "</div>")


def render_paper(paper, number=None):
    if "prose" in paper:
        return (f'<p style="margin:0;font-family:{SANS};font-size:15px;'
                f'color:{MUTED}">{md_inline(paper["prose"])}</p>')

    pre = paper.get("preprint")
    bg = AMBER_BG if pre else CARD_BG
    border = AMBER_RULE if pre else RULE

    head = ""
    if pre:
        head = (f'<div style="font-size:11px;font-weight:700;'
                f'letter-spacing:.09em;text-transform:uppercase;color:{AMBER_INK};'
                f'margin:0 0 10px">Preprint · not peer reviewed</div>')

    num = ""
    if number:
        num = (f'<span style="display:inline-block;width:24px;height:24px;'
               f'line-height:24px;text-align:center;background:{ACCENT};'
               f'color:#fff;border-radius:12px;font-size:12px;'
               f'font-weight:700;margin-right:9px;vertical-align:2px">{number}</span>')

    title = (f'<h3 style="margin:0 0 9px;font-family:{SERIF};font-size:19px;'
             f'line-height:1.32;font-weight:700;color:{INK}">'
             f'{num}{md_inline(paper["title"])}</h3>')

    body = ""
    for label, value in paper["fields"]:
        short = "Model & method" if label.startswith("Model") else label
        body += (
            f'<div style="margin:0 0 11px">'
            f'<div style="font-size:11px;font-weight:700;'
            f'letter-spacing:.08em;text-transform:uppercase;color:{FAINT};'
            f'margin:0 0 3px">{html.escape(short)}</div>'
            f'<div style="font-size:14.5px;line-height:1.62;'
            f'color:{INK}">{md_inline(value)}</div></div>'
        )

    link = ""
    if paper.get("link"):
        url = html.escape(paper["link"], quote=True)
        link = (f'<div style="margin:13px 0 0;padding-top:11px;'
                f'border-top:1px solid {border}">'
                f'<a href="{url}" style="font-size:12.5px;'
                f'color:{ACCENT};text-decoration:none;word-break:break-all">'
                f'{html.escape(paper["link"])}</a></div>')

    return (
        f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
        f'style="border-collapse:separate;margin:0 0 16px"><tr><td '
        f'style="background:{bg};border:1px solid {border};border-radius:7px;'
        f'padding:20px 22px;font-family:{SANS}">{head}{title}{render_byline(paper["byline"])}'
        f'{body}{link}</td></tr></table>'
    )


def render(md):
    title_line, meta, sections = parse(md)

    m = re.match(r"#\s*Neuro digest\s*—\s*(\S+)\s*—\s*(\d+)\s*papers", title_line)
    date_str, count = (m.group(1), m.group(2)) if m else ("", "")
    try:
        pretty_date = dt.date.fromisoformat(date_str).strftime("%A, %B %-d, %Y")
    except ValueError:
        pretty_date = date_str

    parts = [
        f'<div style="background:{PAGE_BG};padding:26px 12px;">',
        f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
        f'style="max-width:660px;margin:0 auto;border-collapse:collapse"><tr><td>',
        # masthead
        f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
        f'style="border-collapse:separate;margin:0 0 22px"><tr><td '
        f'style="background:{ACCENT};border-radius:7px;padding:24px 24px 20px">'
        f'<div style="font-family:{SANS};font-size:11px;font-weight:700;'
        f'letter-spacing:.16em;text-transform:uppercase;color:#a8c4d4;'
        f'margin:0 0 7px">Neuro digest</div>'
        f'<div style="font-family:{SERIF};font-size:24px;font-weight:700;'
        f'color:#ffffff;line-height:1.25">{html.escape(pretty_date)}</div>'
        f'<div style="font-family:{SANS};font-size:13px;color:#c3d7e2;'
        f'margin:8px 0 0">{html.escape(count)} new papers and preprints</div>'
        f'</td></tr></table>',
    ]

    if meta:
        notes = "<br>".join(md_inline(x.strip("*")) for x in meta)
        parts.append(
            f'<div style="font-family:{SANS};font-size:12px;line-height:1.65;'
            f'color:{FAINT};margin:0 0 24px;padding:0 3px">{notes}</div>'
        )

    for sec_title, papers in sections:
        label, sub = SECTION_META.get(sec_title, (sec_title.title(), None))
        parts.append(
            f'<div style="margin:30px 0 15px;border-bottom:2px solid {ACCENT};'
            f'padding:0 0 7px">'
            f'<span style="font-family:{SANS};font-size:13px;font-weight:700;'
            f'letter-spacing:.1em;text-transform:uppercase;color:{ACCENT}">'
            f'{html.escape(label)}</span>'
            + (f'<span style="font-family:{SANS};font-size:12px;color:{FAINT};'
               f'float:right;padding-top:2px">{html.escape(sub)}</span>' if sub else "")
            + "</div>"
        )
        numbered = sec_title == "TOP PAPERS TODAY"
        for i, paper in enumerate(papers, 1):
            parts.append(render_paper(paper, number=i if numbered else None))

    parts.append(
        f'<div style="font-family:{SANS};font-size:11.5px;color:{FAINT};'
        f'text-align:center;margin:30px 0 6px;padding-top:16px;'
        f'border-top:1px solid {RULE}">'
        f'Sources: PubMed (filtered by entry date), bioRxiv, medRxiv.'
        f'</div>'
    )
    parts.append("</td></tr></table></div>")

    return (f'<html><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width,initial-scale=1">'
            f'</head><body style="margin:0;padding:0;background:{PAGE_BG}">'
            + "".join(parts) + "</body></html>")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("digest", help="path to digest_YYYY-MM-DD.md")
    args = ap.parse_args()

    src = pathlib.Path(args.digest)
    out = src.with_suffix(".html")
    out.write_text(render(src.read_text()))
    print(f"wrote {out} ({out.stat().st_size:,} bytes)", file=sys.stderr)


if __name__ == "__main__":
    main()
