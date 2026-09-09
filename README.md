# neurodigest

Daily neuroscience research digest, weekdays at 12:00 UTC (8 AM EDT / 7 AM EST).

Emphasis on neurodegeneration, neurodegenerative disease, brain aging, disease
mechanisms, and translational research.

## Contents

- `digest_YYYY-MM-DD.md` — the daily digest
- `seen_papers.json` — deduplication state across runs; also drives
  preprint→publication tracking
- `fetch_sources.py` — source fetcher (PubMed E-utilities, bioRxiv, medRxiv)
- `render_email.py` — renders a digest markdown file to an HTML email
- `diagrams.py` — builds the schematic figures embedded for Top Papers (see
  Figures below)

## Sources

**Tier A** (no neurodegeneration filter, any substantive neuroscience): Nature,
Science, Cell, Nature Neuroscience, Neuron, Nature Medicine, Science
Translational Medicine, Nature Aging, Cell Stem Cell, Immunity.

**Tier B** (neurodegeneration/aging topic filter): Molecular Neurodegeneration,
Acta Neuropathologica, Brain, Alzheimer's & Dementia, Annals of Neurology, The
Lancet Neurology, Movement Disorders, Neurology, Journal of Neuroscience, Nature
Communications, PNAS, Science Advances, Cell Reports, Nature Methods, Nature
Protocols, Nature Biotechnology.

**Preprints:** bioRxiv (Neuroscience, plus adjacent categories when substantively
neuroscience-related) and medRxiv (Neurology).

PubMed is filtered by **entry/creation date** (`edat`), not publication date,
since publication dates lag entry substantially. Monday runs look back 72 hours;
Tuesday–Friday look back 24.

## Running manually

```bash
python3 fetch_sources.py              # today, automatic window
python3 fetch_sources.py --date 2026-08-26 --days 3
```

Writes `candidates.json`, which is then summarized into the digest.

## Figures

Every Top Paper gets a schematic figure (a generic boxes-and-arrows flow, not
a copy of the journal's own figure — those are copyrighted and usually
unreachable for brand-new papers). Build them each day like this:

1. For each Top Paper, write a small JSON spec: `title`, `doi`, an optional
   `subtitle`, 2-4 `steps` (`{"title", "sub": [...], "color"}` — color is one
   of `blue/green/amber/teal/coral/gray` in `diagrams.py`'s `PALETTE`), and a
   one-line `caption`. Keep box titles to ~28 chars and each `sub` line to
   ~32 chars in a 2-box row (a solo full-width row, used for a 3rd/lone step,
   allows roughly double that) — `diagrams.py` prints a layout warning to
   stderr for anything too long instead of silently overflowing.
2. Collect the day's specs into one JSON list and render:
   ```bash
   python3 diagrams.py figures --spec /path/to/todays_figs.json
   ```
   This writes `figures/<name>.svg` and `figures/<name>.png` for each spec.
   Prefix `name` with the date (e.g. `2026-09-09-fig1-bonemarrow`) — the
   directory is flat and shared across every day's digest.
3. Add each `doi -> "<name>.png"` entry to the `FIGURES` dict near the top of
   `render_email.py`, then re-run `render_email.py` on the digest — it embeds
   `<img>` tags for any Top Paper whose DOI is in that map.
4. Commit the new PNGs/SVGs and the updated `render_email.py` alongside the
   digest. **Images are hosted from this repo's `main` branch
   (`raw.githubusercontent.com/.../main/figures/...`) — they render as
   broken images in the email until this branch is merged to `main`.**

Rendering uses a headless Chromium to rasterize the SVG
(`DIGEST_CHROME` env var to override the auto-detected binary path) and
Pillow to crop the result — on this specific Chromium build, screenshots
silently clip ~90px short of the requested `--window-size` height, so
`diagrams.py` requests extra height and crops back down to the true figure
size; don't remove that padding/crop step.

To add a one-off, hand-laid-out figure instead of the daily template, write
a `fig_*()` function (see the five originals in `diagrams.py`) and add it to
the `FIGURES` dict at module level — significantly more effort per figure,
reserve it for a figure worth bespoke layout.
