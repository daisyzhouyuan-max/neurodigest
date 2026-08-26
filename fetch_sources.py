#!/usr/bin/env python3
"""Fetch candidate papers for the daily neuroscience digest.

Queries PubMed (E-utilities) and bioRxiv/medRxiv, applies journal/category
filters, drops anything already in seen_papers.json, and writes the surviving
candidates to candidates.json for summarization.

Filtering by PubMed *entry* date (edat), not publication date.
"""
import argparse
import datetime as dt
import json
import pathlib
import re
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
RXIV = "https://api.biorxiv.org/details/{server}/{start}/{end}/{cursor}"
UA = {"User-Agent": "neuro-digest/1.0 (mailto:daisy.zhou@yale.edu)"}

HERE = pathlib.Path(__file__).parent

TIER_A_JOURNALS = (
    '"Nature"[ta] OR "Science"[ta] OR "Cell"[ta] OR "Nat Neurosci"[ta] OR '
    '"Neuron"[ta] OR "Nat Med"[ta] OR "Sci Transl Med"[ta] OR "Nat Aging"[ta] OR '
    '"Cell Stem Cell"[ta] OR "Immunity"[ta]'
)
NEURO_TERMS = (
    "neuroscience OR neurobiology OR nervous system OR neurological OR neural OR "
    "brain OR neuron OR synapse OR glia OR astrocyte OR microglia OR oligodendrocyte OR "
    "spinal cord OR cerebral OR hippocampus OR cortex OR cerebellum OR thalamus OR "
    "basal ganglia OR blood-brain barrier OR neurodegeneration OR Alzheimer OR Parkinson OR "
    "dementia OR neuroinflammation OR neuropathy OR epilepsy OR stroke OR neuroimmune OR "
    "electrophysiology OR optogenetics OR connectome"
)
B1_JOURNALS = (
    '"Mol Neurodegener"[ta] OR "Acta Neuropathol"[ta] OR "Brain"[ta] OR '
    '"Alzheimers Dement"[ta] OR "Ann Neurol"[ta] OR "Lancet Neurol"[ta] OR '
    '"Mov Disord"[ta] OR "Neurology"[ta]'
)
B2_JOURNALS = (
    '"J Neurosci"[ta] OR "Nat Commun"[ta] OR "Proc Natl Acad Sci U S A"[ta] OR '
    '"Sci Adv"[ta] OR "Cell Rep"[ta] OR "Nat Methods"[ta] OR "Nat Protoc"[ta] OR '
    '"Nat Biotechnol"[ta]'
)
NEURODEG_TERMS = (
    'neurodegeneration OR neurodegenerative OR "brain aging" OR Alzheimer OR Parkinson OR '
    'dementia OR ALS OR "motor neuron" OR Huntington OR tau OR amyloid OR "alpha-synuclein" OR '
    'TDP-43 OR prion OR neuroinflammation OR microglia OR astrocyte OR "protein aggregation" OR '
    'proteostasis OR autophagy OR "neuronal death" OR "neuronal vulnerability" OR ferroptosis OR '
    'necroptosis OR "blood-brain barrier" OR neurovascular OR meningeal OR glymphatic OR '
    'lymphatic OR biomarker OR neuropathology OR cerebrospinal OR neuroimmune OR myelin OR '
    'oligodendrocyte OR synapse OR neuroprotection'
)

# Editorial/administrative material carries no findings to summarize.
SKIP_PUBTYPES = {
    "Editorial", "Comment", "News", "Correction", "Published Erratum",
    "Retraction of Publication", "Retracted Publication", "Biography",
    "Newspaper Article", "Patient Education Handout",
}

RXIV_PRIMARY = {"neuroscience"}
RXIV_SECONDARY = {"cell biology", "bioinformatics", "systems biology",
                  "genomics", "molecular biology", "genetics"}

# Used only to shortlist secondary-category preprints; final relevance is a
# judgement call made during summarization.
NEURO_RE = re.compile(
    r"\b(neuro\w*|brain|cortic\w*|cortex|hippocamp\w*|synap\w*|neuron\w*|glia\w*|"
    r"astrocyt\w*|microglia\w*|oligodendrocyt\w*|myelin\w*|axon\w*|dendrit\w*|"
    r"alzheimer\w*|parkinson\w*|dementia|huntington\w*|amyotrophic|\bALS\b|tauopath\w*|"
    r"amyloid\w*|synuclein\w*|TDP-43|prion\w*|cerebrospinal|glymphatic|meninge\w*|"
    r"blood-brain|nervous system|spinal cord|motor neuron|cognit\w*|neural)\b",
    re.I,
)
AGING_RE = re.compile(r"\b(aging|ageing|senescen\w*|lifespan|healthspan|geroscience)\b", re.I)


def get(url, retries=3):
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=90) as r:
                return r.read()
        except Exception as exc:
            if attempt == retries - 1:
                raise
            print(f"    retry {attempt + 1} after {exc}", file=sys.stderr)
            time.sleep(2 * (attempt + 1))


def esearch(term, mindate, maxdate):
    url = EUTILS + "esearch.fcgi?" + urllib.parse.urlencode({
        "db": "pubmed", "retmode": "json", "retmax": "300",
        "datetype": "edat", "mindate": mindate, "maxdate": maxdate, "term": term,
    })
    res = json.loads(get(url))["esearchresult"]
    return res.get("idlist", []), int(res.get("count", 0))


def _author_name(a):
    fore, last = a.findtext("ForeName"), a.findtext("LastName")
    if last:
        return " ".join(x for x in (fore, last) if x)
    return a.findtext("CollectiveName")


def efetch(pmids):
    """Fetch article records in batches, returning parsed dicts."""
    out = []
    for i in range(0, len(pmids), 100):
        batch = pmids[i:i + 100]
        url = EUTILS + "efetch.fcgi?" + urllib.parse.urlencode(
            {"db": "pubmed", "retmode": "xml", "id": ",".join(batch)})
        root = ET.fromstring(get(url))
        for art in root.findall(".//PubmedArticle"):
            pubtypes = [p.text for p in art.findall(".//PublicationType") if p.text]
            if any(p in SKIP_PUBTYPES for p in pubtypes):
                continue

            doi = None
            for e in art.findall(".//ELocationID"):
                if e.get("EIdType") == "doi":
                    doi = e.text
            if not doi:
                for aid in art.findall(".//ArticleId"):
                    if aid.get("IdType") == "doi":
                        doi = aid.text

            authors = [n for n in (_author_name(a)
                                   for a in art.findall(".//AuthorList/Author")) if n]
            # Structured abstracts split across labelled sections; keep the labels.
            parts = []
            for t in art.findall(".//Abstract/AbstractText"):
                label = t.get("Label")
                text = "".join(t.itertext()).strip()
                parts.append(f"{label}: {text}" if label else text)

            title_el = art.find(".//ArticleTitle")
            out.append({
                "pmid": art.findtext(".//MedlineCitation/PMID"),
                "doi": doi,
                "title": "".join(title_el.itertext()).strip() if title_el is not None else None,
                "journal": art.findtext(".//Journal/ISOAbbreviation"),
                "first_author": authors[0] if authors else None,
                "last_author": authors[-1] if len(authors) > 1 else None,
                "n_authors": len(authors),
                "abstract": " ".join(parts),
                "pubtypes": pubtypes,
            })
        time.sleep(0.5)
    return out


def fetch_rxiv(server, start, end):
    """Page through the rXiv detail API (~30 records/page), newest version wins."""
    by_doi, cursor, total = {}, 0, None
    while True:
        data = json.loads(get(RXIV.format(server=server, start=start, end=end, cursor=cursor)))
        msg = (data.get("messages") or [{}])[0]
        if msg.get("status") != "ok":
            break
        if total is None:
            total = int(msg.get("total", 0))
            print(f"  {server}: {total} preprints in window", file=sys.stderr)
        coll = data.get("collection", [])
        if not coll:
            break
        for item in coll:
            prev = by_doi.get(item["doi"])
            if prev is None or float(item.get("version", 1)) >= float(prev.get("version", 1)):
                by_doi[item["doi"]] = item
        cursor += len(coll)
        if total is not None and cursor >= total:
            break
        time.sleep(0.3)
    return list(by_doi.values())


def rxiv_relevant(item, server):
    cat = (item.get("category") or "").lower()
    blob = f"{item.get('title', '')} {item.get('abstract', '')}"
    if server == "medrxiv":
        return cat == "neurology" and (NEURO_RE.search(blob) or AGING_RE.search(blob))
    if cat in RXIV_PRIMARY:
        return True
    if cat in RXIV_SECONDARY:
        return bool(NEURO_RE.search(blob))
    return False


def norm_rxiv(item, server):
    authors = [a.strip() for a in (item.get("authors") or "").split(";") if a.strip()]
    return {
        "doi": item.get("doi"),
        "title": (item.get("title") or "").strip(),
        "server": server,
        "category": item.get("category"),
        "first_author": authors[0] if authors else None,
        "last_author": authors[-1] if len(authors) > 1 else None,
        "abstract": (item.get("abstract") or "").strip(),
        "date": item.get("date"),
        "version": item.get("version"),
        "published": item.get("published") or None,
        "link": f"https://doi.org/{item.get('doi')}",
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", help="digest date YYYY-MM-DD (default: today)")
    ap.add_argument("--days", type=int, help="override lookback window in days")
    args = ap.parse_args()

    today = dt.date.fromisoformat(args.date) if args.date else dt.date.today()
    # Monday reaches back through the weekend to Friday.
    days = args.days if args.days else (3 if today.weekday() == 0 else 1)
    start = today - dt.timedelta(days=days)

    pm_min, pm_max = start.strftime("%Y/%m/%d"), today.strftime("%Y/%m/%d")
    rx_min, rx_max = start.isoformat(), today.isoformat()
    print(f"Window: {rx_min} .. {rx_max} ({days}d, {today:%A})", file=sys.stderr)

    seen_path = HERE / "seen_papers.json"
    seen = json.loads(seen_path.read_text()) if seen_path.exists() else {"papers": []}
    seen_ids = set()
    for p in seen.get("papers", []):
        seen_ids.update(str(v).lower() for v in (p.get("doi"), p.get("pmid")) if v)

    def is_new(rec):
        return not any(str(v).lower() in seen_ids
                       for v in (rec.get("doi"), rec.get("pmid")) if v)

    result = {"date": today.isoformat(), "window_days": days,
              "window": [rx_min, rx_max], "errors": []}
    claimed = set()  # a paper belongs to exactly one section

    searches = [
        ("tier_a", f"({TIER_A_JOURNALS}) AND ({NEURO_TERMS})"),
        ("tier_b1", f"({B1_JOURNALS})"),
        ("tier_b2", f"({B2_JOURNALS}) AND ({NEURODEG_TERMS})"),
    ]
    for key, term in searches:
        try:
            ids, count = esearch(term, pm_min, pm_max)
            print(f"  {key}: {count} hits", file=sys.stderr)
            time.sleep(0.5)
            recs = efetch(ids) if ids else []
            kept = []
            for r in recs:
                key_id = (r.get("doi") or r.get("pmid") or "").lower()
                if key_id in claimed or not is_new(r):
                    continue
                claimed.add(key_id)
                kept.append(r)
            result[key] = kept
            print(f"  {key}: {len(kept)} new after dedup/pubtype filter", file=sys.stderr)
        except Exception as exc:
            result[key] = []
            result["errors"].append(f"PubMed {key}: {exc}")
            print(f"  {key} FAILED: {exc}", file=sys.stderr)

    for server in ("biorxiv", "medrxiv"):
        try:
            items = fetch_rxiv(server, rx_min, rx_max)
            kept = []
            for it in items:
                if not rxiv_relevant(it, server):
                    continue
                rec = norm_rxiv(it, server)
                key_id = (rec.get("doi") or "").lower()
                if key_id in claimed or not is_new(rec):
                    continue
                claimed.add(key_id)
                kept.append(rec)
            result[server] = kept
            print(f"  {server}: {len(kept)} relevant new preprints", file=sys.stderr)
        except Exception as exc:
            result[server] = []
            result["errors"].append(f"{server}: {exc}")
            print(f"  {server} FAILED: {exc}", file=sys.stderr)

    # Preprints from earlier digests that have since been peer reviewed.
    now_published = []
    tracked = [p for p in seen.get("papers", []) if p.get("section") == "preprint"]
    for p in tracked:
        doi = p.get("doi")
        if not doi or not doi.startswith("10.1101"):
            continue
        try:
            data = json.loads(get(f"https://api.biorxiv.org/details/{p.get('server', 'biorxiv')}/{doi}"))
            for item in data.get("collection", []):
                if item.get("published") and item["published"].lower() != "na":
                    now_published.append({"preprint": p, "published_doi": item["published"]})
                    break
            time.sleep(0.3)
        except Exception as exc:
            result["errors"].append(f"pub-check {doi}: {exc}")
    result["now_published"] = now_published

    out = HERE / "candidates.json"
    out.write_text(json.dumps(result, indent=2))
    counts = {k: len(v) for k, v in result.items() if isinstance(v, list) and k != "errors"}
    print(f"\nWrote {out}\n  {counts}", file=sys.stderr)
    if result["errors"]:
        print(f"  errors: {result['errors']}", file=sys.stderr)


if __name__ == "__main__":
    main()
