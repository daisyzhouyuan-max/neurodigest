#!/usr/bin/env python3
"""Build review-paper-style schematics for the digest's top papers.

Journal figures are copyrighted and mostly unreachable for brand-new papers
(not yet deposited in PMC, publisher sites behind auth), so these are original
diagrams drawn from the reported findings. Self-contained SVG with hardcoded
colours — no external CSS — rendered to PNG via headless Chrome for email.

Two ways to add a figure:
  1. One-off, hand-laid-out: write a fig_*() function (see the five originals
     below) and add it to FIGURES.
  2. Daily, templated: build a JSON spec (see fig_flow_from_spec / --spec)
     with a title, subtitle, model/system, and a short ordered list of
     mechanism steps — one call renders a generic boxes-and-arrows flow
     without hand-placing coordinates. This is the one to reuse every day.
"""
import json
import pathlib
import shutil
import subprocess
import sys
import textwrap

W = 570                      # fits the email card's inner width


def find_chrome():
    env = __import__("os").environ.get("DIGEST_CHROME")
    if env and pathlib.Path(env).exists():
        return env
    candidates = [
        "/opt/pw-browsers/chromium",
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        shutil.which("chromium"),
        shutil.which("chromium-browser"),
        shutil.which("google-chrome"),
    ]
    for c in candidates:
        if c and pathlib.Path(c).exists():
            return c
    raise RuntimeError(
        "No headless Chrome/Chromium found. Set DIGEST_CHROME to a binary path."
    )


CHROME = find_chrome()
FONT = "Helvetica,Arial,sans-serif"

INK, MUTED, FAINT = "#14171a", "#5b6570", "#8a939c"
RULE, ACCENT = "#d9dde0", "#26485f"

# fill, stroke, text — muted enough to sit inside a white card
PALETTE = {
    "blue":  ("#E9F1FA", "#7FA8CE", "#123C63"),
    "green": ("#EDF4E3", "#9CBE74", "#31570F"),
    "amber": ("#FBF1DF", "#DFBA7C", "#6E4309"),
    "teal":  ("#E5F4EF", "#86C6AE", "#0D5843"),
    "coral": ("#FAEEEA", "#DFA792", "#7E3418"),
    "gray":  ("#F1F2F1", "#BFC2C0", "#3B3E3D"),
}

# Helvetica advance widths, measured empirically at these sizes.
CH_TITLE, CH_SUB = 7.6, 6.3


def esc(s):
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


class Fig:
    def __init__(self, height):
        self.h = height
        self.parts = []
        self.warnings = []

    def add(self, s):
        self.parts.append(s)

    def text(self, x, y, s, size=12, weight=400, fill=MUTED, anchor="start"):
        self.add(f'<text x="{x}" y="{y}" font-family="{FONT}" font-size="{size}" '
                 f'font-weight="{weight}" fill="{fill}" text-anchor="{anchor}">{esc(s)}</text>')

    def box(self, x, y, w, h, title, sub=(), color="gray", center=False):
        fill, stroke, ink = PALETTE[color]
        self.add(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="5" '
                 f'fill="{fill}" stroke="{stroke}" stroke-width="1"/>')
        if isinstance(sub, str):
            sub = [sub]
        # vertically centre the title + subtitle block
        block = 15 + 14 * len(sub)
        ty = y + (h - block) / 2 + 12
        tx = x + w / 2 if center else x + 13
        anchor = "middle" if center else "start"
        avail = w - (16 if center else 26)

        if len(title) * CH_TITLE > avail:
            self.warnings.append(f'title overflows ({len(title)*CH_TITLE:.0f}>{avail}): "{title}"')
        self.text(tx, ty, title, size=13, weight=600, fill=ink, anchor=anchor)
        for i, line in enumerate(sub):
            if len(line) * CH_SUB > avail:
                self.warnings.append(f'sub overflows ({len(line)*CH_SUB:.0f}>{avail}): "{line}"')
            self.text(tx, ty + 15 + i * 14, line, size=11, fill=ink, anchor=anchor)

    def frame(self, x, y, w, h, label):
        self.add(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="7" fill="none" '
                 f'stroke="{RULE}" stroke-width="1" stroke-dasharray="4 4"/>')
        self.text(x + 13, y + 17, label, size=10.5, weight=600, fill=FAINT)

    def arrow(self, x1, y1, x2, y2, color=None):
        c = color or "#9aa3a8"
        self.add(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{c}" '
                 f'stroke-width="1.2" marker-end="url(#a)"/>')

    def dashline(self, x1, y1, x2, y2):
        self.add(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{RULE}" '
                 f'stroke-width="1" stroke-dasharray="3 3"/>')

    def caption(self, y, s, color="teal"):
        fill, stroke, ink = PALETTE[color]
        self.add(f'<rect x="16" y="{y}" width="{W-32}" height="34" rx="5" '
                 f'fill="{fill}" stroke="{stroke}" stroke-width="1"/>')
        if len(s) * CH_SUB > W - 60:
            self.warnings.append(f'caption overflows: "{s}"')
        self.text(W / 2, y + 22, s, size=11.5, weight=600, fill=ink, anchor="middle")

    def svg(self, title, desc):
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{self.h}" '
            f'viewBox="0 0 {W} {self.h}" role="img">'
            f'<title>{esc(title)}</title><desc>{esc(desc)}</desc>'
            f'<defs><marker id="a" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" '
            f'markerHeight="6" orient="auto-start-reverse">'
            f'<path d="M2 1L8 5L2 9" fill="none" stroke="context-stroke" stroke-width="1.5" '
            f'stroke-linecap="round" stroke-linejoin="round"/></marker></defs>'
            f'<rect width="{W}" height="{self.h}" fill="#ffffff"/>'
            + "".join(self.parts) + "</svg>"
        )


# ---------------------------------------------------------------- diagrams

def fig_oligodendrocyte():
    """Craig & Miron, Nature Medicine."""
    f = Fig(330)
    f.text(16, 24, "Oligodendrocyte NRF2 and the rate of cognitive aging", 13, 700, INK)

    f.frame(16, 38, W - 32, 128, "HUMAN — POST-MORTEM WHITE MATTER (ASSOCIATION)")
    f.box(30, 58, 232, 44, "NRF2 downregulated", ["In oligodendrocytes"], "blue")
    f.box(30, 110, 232, 44, "Altered myelin structure", ["Thicker sheaths, smaller axons"], "blue")
    f.box(320, 84, 224, 44, "Worse cognitive trajectory", ["Individual rate of decline"], "gray")
    f.arrow(266, 80, 314, 100)
    f.arrow(266, 132, 314, 112)

    f.frame(16, 178, W - 32, 92, "MOUSE — OLIGODENDROCYTE-SPECIFIC Nrf2 KNOCKOUT (CAUSAL TEST)")
    f.box(30, 198, 232, 48, "Aged Nrf2 cKO", ["Knockout restricted to", "oligodendrocytes"], "green")
    f.box(320, 198, 224, 48, "Phenocopies human", ["Same white matter pathology,", "blunted cognitive gain"], "green")
    f.arrow(266, 222, 314, 222)

    f.caption(282, "NRF2 in oligodendrocytes — a tractable target for cognitive aging")
    return f, ("Oligodendrocyte NRF2 and cognitive aging",
               "Human white matter associates NRF2 loss and altered myelin with faster cognitive "
               "decline; oligodendrocyte-specific Nrf2 knockout in aged mice reproduces the pathology.")


def fig_abeta():
    """Kostylev & Strittmatter, Nature Communications."""
    f = Fig(336)
    f.text(16, 24, "Receptor-bound amyloid-β is a filament, not a separate oligomer", 13, 700, INK)

    f.box(16, 40, 150, 44, "AD brain tissue", ["Post-mortem"], "gray")
    f.box(188, 40, 210, 44, "PrP-antagonist elution", ["Releases receptor-bound pool"], "blue")
    f.box(420, 40, 134, 44, "Cryo-EM", ["To homogeneity"], "blue")
    f.arrow(170, 62, 184, 62)
    f.arrow(402, 62, 416, 62)

    f.frame(16, 100, W - 32, 132, "TWO POOLS FROM THE SAME BRAIN, COMPARED")
    f.box(30, 120, 244, 96, "Receptor-bound Aβ",
          ["65 nm filaments; ~10× more", "abundant than free Aβ", "Two S-shaped monomers per rung"], "coral")
    f.box(296, 120, 248, 96, "Plaque filaments",
          ["Same overall fold, but differ in", "subunit tilt, N-terminal shape,", "length and seeding"], "gray")
    f.dashline(285, 132, 285, 204)

    f.box(16, 244, W - 32, 42, "Filament tips bind PrP and drive synapse loss in human neurons",
          [], "amber", center=True)

    f.caption(294, "Synaptotoxicity tracks short filament ends, not a distinct oligomer")
    return f, ("Receptor-bound amyloid-beta filament structure",
               "Receptor-bound amyloid-beta eluted from AD brain forms 65 nm filaments ten times more "
               "abundant than free amyloid-beta, resembling plaque filaments but distinguishable by "
               "subunit tilt, N-terminal conformation, length and seeding.")


def fig_macaque():
    """Ruff & Cohen, PNAS."""
    f = Fig(322)
    f.text(16, 24, "Early Alzheimer pathology disrupts coordination, not tuning", 13, 700, INK)
    f.text(16, 42, "Macaque model, longitudinal recordings (n = 2 animals)", 11, 400, FAINT)

    y = 58
    rows = [
        ("Molecular pathology", "Confined to regions giving feedback to visual cortex", "amber", "affected"),
        ("Single-neuron tuning", "Feature encoding and tuning remain stable", "green", "preserved"),
        ("Population coordination", "Declines within and between visual and parietal cortex", "coral", "disrupted"),
        ("Visually guided behaviour", "Less consistent, more variable exploration", "coral", "disrupted"),
    ]
    for i, (title, sub, color, tag) in enumerate(rows):
        top = y + i * 56
        f.box(16, top, 400, 46, title, [sub], color)
        fill, stroke, ink = PALETTE["green" if tag == "preserved" else
                                    ("amber" if tag == "affected" else "coral")]
        f.add(f'<rect x="432" y="{top+12}" width="122" height="22" rx="11" '
              f'fill="{fill}" stroke="{stroke}" stroke-width="1"/>')
        f.text(493, top + 27, tag.upper(), size=10, weight=700, fill=ink, anchor="middle")
        if i < len(rows) - 1:
            f.arrow(216, top + 46, 216, top + 54)

    f.caption(282, "Methylphenidate transiently restored behavioural organisation")
    return f, ("Neuronal population organization in a macaque Alzheimer model",
               "Across levels, molecular pathology and single-neuron tuning are spared while population "
               "coordination and behaviour degrade, indicating a selective loss of coordination.")


def fig_aria():
    """Kang & Seo, Alzheimer's & Dementia."""
    f = Fig(330)
    f.text(16, 24, "APOE-guided lecanemab dosing separates two ARIA axes", 13, 700, INK)
    f.text(16, 42, "508 patients, eight Korean centres, MRI surveillance", 11, 400, FAINT)

    f.box(160, 58, 250, 44, "APOE-guided dose escalation", ["Cmax target set by ε4 dose"], "blue", center=True)
    f.arrow(230, 104, 150, 126)
    f.arrow(340, 104, 420, 126)

    f.box(16, 130, 262, 96, "ARIA-E  (oedema)",
          ["Driven by APOE ε4 dose", "ε4/ε4 vs non-carrier OR 3.25", "vs 8.49 and 8.32 historically"], "teal")
    f.box(292, 130, 262, 96, "ARIA-H  (haemosiderin)",
          ["Driven by baseline vessel burden:", "microbleeds, WMH, age, ε4 dose", "Not attenuated by dosing"], "coral")

    f.box(16, 240, W - 32, 46, "Non-randomised comparison with historical cohorts",
          ["Compatible with, but not proof of, attenuation"], "gray", center=True)
    f.caption(296, "A dual-axis safety model that still needs a randomised test")
    return f, ("APOE-guided lecanemab dosing and ARIA",
               "Under genotype-guided dosing, ARIA-E tracked APOE e4 dose with a shallower gradient than "
               "historical cohorts, while ARIA-H tracked pre-existing cerebrovascular burden.")


def fig_ttr():
    """Zheng & Shi, Nature Communications."""
    f = Fig(300)
    f.text(16, 24, "Amyloid structures from living patients, via biopsy", 13, 700, INK)

    f.box(16, 44, 196, 56, "Ten ATTRv patients", ["Nine distinct mutations", "heterozygous carriers"], "blue")
    f.box(232, 44, 150, 56, "Biopsy tissue", ["Muscle and vitreous", "from living donors"], "blue")
    f.box(402, 44, 152, 56, "Cryo-EM", ["19 structures", "at 1.9–3.4 Å"], "blue")
    f.arrow(216, 72, 228, 72)
    f.arrow(386, 72, 398, 72)

    f.frame(16, 116, W - 32, 96, "DEEP-LEARNING ANALYSIS OF CRYO-EM DENSITY")
    f.box(30, 136, 236, 62, "Mutant vs wild-type TTR", ["Assigned semi-quantitatively", "within individual fibrils"], "amber")
    f.box(300, 136, 244, 62, "Composition tracks onset age", ["Which species nucleates may", "set clinical timing"], "amber")
    f.arrow(270, 167, 294, 167)

    f.caption(226, "Biopsy workflow opens living-patient tissue to amyloid structural biology")
    return f, ("Biopsy-derived transthyretin fibril structures",
               "Cryo-EM of biopsy tissue from ten living ATTRv patients yielded nineteen fibril structures; "
               "deep-learning density analysis assigned mutant versus wild-type composition, which tracked "
               "age of disease onset.")


def fig_flow_from_spec(spec):
    """Generic template: a short chain of labeled boxes with arrows, built
    from a plain dict instead of hand-placed coordinates. This is the one to
    reuse every day for Top Papers — write the content (title, 2-4 steps,
    caption), not the layout.

    Rows hold at most 2 boxes (2-column text needs ~30 chars/title to avoid
    overflowing at this card width); a step left over after pairing gets a
    full-width row of its own — a natural shape for "input + mechanism ->
    outcome". So: 2 steps = one row of 2; 3 steps = a row of 2 then a
    full-width row of 1; 4 steps = two rows of 2.

    spec keys:
      title    figure headline (top of card)
      subtitle optional line under the headline (e.g. species/cohort size)
      steps    2-4 dicts: {"title": str, "sub": [str, ...], "color": str}
               color is one of PALETTE's keys (blue/green/amber/teal/coral/gray)
               keep title <=28 chars and each sub line <=32 chars in a
               2-box row; a solo full-width row allows roughly 2x that.
      caption  optional one-line takeaway (<=75 chars), shown in a colored
               bar at the bottom
      caption_color  optional, default "teal"
      desc     optional longer alt-text description (falls back to caption/title)
    """
    title = spec["title"]
    subtitle = spec.get("subtitle")
    steps = spec["steps"]
    caption = spec.get("caption")
    caption_color = spec.get("caption_color", "teal")

    n = len(steps)
    if not 2 <= n <= 4:
        raise ValueError(f"fig_flow_from_spec needs 2-4 steps, got {n}")

    box_h, gap = 78, 28
    y0 = 58 if subtitle else 40
    rows = [steps[:2]] if n == 2 else \
           [steps[:2], steps[2:]] if n in (3, 4) else [steps]
    body_h = box_h * len(rows) + gap * (len(rows) - 1)
    caption_h = 46 if caption else 0
    h = y0 + body_h + (24 if caption else 10) + caption_h

    f = Fig(h)
    f.text(16, 24, title, 13, 700, INK)
    if subtitle:
        f.text(16, 42, subtitle, 11, 400, FAINT)

    def place_row(row, y):
        count = len(row)
        bw = (W - 32 - (count - 1) * gap) / count
        xs = [16 + i * (bw + gap) for i in range(count)]
        for x, step in zip(xs, row):
            f.box(x, y, bw, box_h, step["title"], step.get("sub", []),
                  step.get("color", "gray"), center=(count == 1))
        for i in range(count - 1):
            f.arrow(xs[i] + bw, y + box_h / 2, xs[i + 1], y + box_h / 2)
        return xs, bw

    y = y0
    row_geoms = []
    for row in rows:
        xs, bw = place_row(row, y)
        row_geoms.append((xs, bw))
        y += box_h + gap
    y_end = y - gap

    if len(rows) == 2:
        (xs1, bw1), (xs2, bw2) = row_geoms
        y1_bottom, y2_top = y0 + box_h, y0 + box_h + gap
        if len(rows[1]) == 1:
            # two boxes converging into one outcome below — aim at two
            # distinct points so the arrows form a funnel, not an X
            target_mid = xs2[0] + bw2 / 2
            f.arrow(xs1[0] + bw1 / 2, y1_bottom, target_mid - 50, y2_top)
            f.arrow(xs1[-1] + bw1 / 2, y1_bottom, target_mid + 50, y2_top)
        else:
            # 2x2 grid: each column flows straight down
            for x1, x2 in zip(xs1, xs2):
                f.arrow(x1 + bw1 / 2, y1_bottom, x2 + bw2 / 2, y2_top)

    if caption:
        f.caption(y_end + 20, caption, caption_color)

    return f, (title, spec.get("desc", caption or title))


FIGURES = {
    "fig1-oligodendrocyte": fig_oligodendrocyte,
    "fig2-abeta": fig_abeta,
    "fig3-macaque": fig_macaque,
    "fig4-aria": fig_aria,
    "fig5-ttr": fig_ttr,
}


SCALE = 2
# Headless Chrome's screenshot viewport comes up ~90px shorter than the
# requested --window-size height on this build (confirmed by direct test:
# content past that point is silently clipped, not just cropped at a
# sensible boundary). Request extra height as a safety margin, then crop
# the PNG back down to the true figure size with Pillow.
HEIGHT_PAD = 150


def _render_fig(name, fig, title, desc, outdir):
    svg = fig.svg(title, desc)
    (outdir / f"{name}.svg").write_text(svg)

    html = f'<html><body style="margin:0;background:#fff">{svg}</body></html>'
    tmp = outdir / f"{name}.html"
    tmp.write_text(html)
    png = outdir / f"{name}.png"
    subprocess.run(
        [CHROME, "--headless", "--disable-gpu", "--no-sandbox",
         f"--force-device-scale-factor={SCALE}", "--hide-scrollbars",
         f"--window-size={W},{fig.h + HEIGHT_PAD}",
         f"--screenshot={png}", tmp.as_uri()],
        capture_output=True, timeout=120,
    )
    tmp.unlink()

    if png.exists():
        try:
            from PIL import Image
        except ImportError:
            subprocess.run([sys.executable, "-m", "pip", "install", "-q", "pillow"],
                            check=True)
            from PIL import Image
        im = Image.open(png)
        im.crop((0, 0, W * SCALE, fig.h * SCALE)).save(png)

    ok = png.exists()
    size = png.stat().st_size if ok else 0
    print(f"{name:24} {'ok' if ok else 'FAILED':6} {size:>8,} bytes  h={fig.h}")
    return fig.warnings


def render(outdir, builders=None):
    outdir = pathlib.Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    problems = []

    for name, builder in (builders or FIGURES).items():
        fig, (title, desc) = builder()
        for w in _render_fig(name, fig, title, desc, outdir):
            problems.append(f"{name}: {w}")

    if problems:
        print("\nLAYOUT WARNINGS", file=sys.stderr)
        for p in problems:
            print("  " + textwrap.shorten(p, 150), file=sys.stderr)
    else:
        print("\nno layout warnings")
    return problems


def render_specs(spec_path, outdir):
    """Render today's Top Papers figures from a JSON file: a list of specs,
    each matching fig_flow_from_spec's input plus a required "name" (used as
    the output filename stem) and optional "doi" (for your own bookkeeping
    when wiring the result into render_email.py's FIGURES map — this function
    does not touch render_email.py itself)."""
    specs = json.loads(pathlib.Path(spec_path).read_text())
    builders = {s["name"]: (lambda s=s: fig_flow_from_spec(s)) for s in specs}
    return render(outdir, builders)


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("outdir", nargs="?", default="figures")
    p.add_argument("--spec", help="JSON spec file for render_specs() (daily figures)")
    args = p.parse_args()
    outdir = pathlib.Path(__file__).parent / args.outdir
    if args.spec:
        render_specs(args.spec, outdir)
    else:
        render(outdir)
