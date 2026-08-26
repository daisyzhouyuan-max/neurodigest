# neurodigest

Daily neuroscience research digest, weekdays at 12:00 UTC (8 AM EDT / 7 AM EST).

Emphasis on neurodegeneration, neurodegenerative disease, brain aging, disease
mechanisms, and translational research.

## Contents

- `digest_YYYY-MM-DD.md` — the daily digest
- `seen_papers.json` — deduplication state across runs; also drives
  preprint→publication tracking
- `fetch_sources.py` — source fetcher (PubMed E-utilities, bioRxiv, medRxiv)

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
