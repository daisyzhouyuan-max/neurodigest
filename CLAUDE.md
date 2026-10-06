# neurodigest

Daily neuroscience research digest. The scheduled routine's full workflow lives in
`ROUTINE_PROMPT.md`; `fetch_sources.py`, `diagrams.py` and `render_email.py` do the
retrieval, figures and email rendering.

## Writing the digest

The digest is a reader-facing document for a neuroscientist studying neurodegeneration
and brain aging. It is not a log of how the run went.

- **No meta-commentary about the pipeline.** Never write sentences in the digest about
  what could not be fetched, resolved or reached — e.g. "the published title was not
  resolvable from PubMed", "crossref was unreachable from this environment", "the
  abstract could not be retrieved because…". Process caveats belong in the run summary
  reported back in chat, never in the digest or the email.
- **NOW PUBLISHED:** resolve the published title and journal when you can. When the
  title will not resolve, simply list the preprint title, the journal and the DOI, and
  stop there — no explanation of the failure.
- Omit missing fields rather than filling them in, and never fabricate a title, author,
  DOI or finding. Omitting quietly is correct; narrating the omission is not.
- A genuine scientific limitation of a *study* (small n, cross-sectional, mouse-only
  causal evidence) is different and should be stated in a clause — that is about the
  paper, not about the pipeline.
