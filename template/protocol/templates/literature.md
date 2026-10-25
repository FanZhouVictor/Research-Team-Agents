---
citekey: {citekey}
title: {title}
authors: [{authors}]
year: {year}
venue: {venue}
doi: {doi}
arxiv: {arxiv}
pdf: literature/pdf/{citekey}.pdf
relevance: {relevance}          # core | supporting | background | not-useful
bears-on: [{question_ids}]
readers:
  - {person: {person}, agent: {agent}, date: {date}, read: full-text}   # read: full-text | abstract-only | skimmed
code: {code}
data: {data}
related: [{citekeys}]
---

## Summary
≤150 words, own words: problem, method, data, main result.
<!-- Template note, not copied into new files. Every edit of the summary appends a trail line:
revised: <date> <person>/<agent> — <why>
Refine by adding detail or fixing an error; never shorten or remove what another reader wrote. -->

## Why it matters here
One or two lines tying the paper to the project. If relevance is not-useful: say why,
so nobody spends an hour rediscovering that.

## Claims for this project
<!-- Template note, not copied into new files. One bullet per claim, in your own words. A claim
without a where is not written. Format:
- <the claim>
  - where: <section, table, figure or page>
  - bears on: <question id> — supports
  - kind: result                 # result | method | dataset | definition | limitation
  - basis: stated by paper       # or: inferred by <agent>
  - by: <person> · <agent> · <date>
  - verified-by: —
  - disputed-by: —
-->

## Notes
<!-- Template note, not copied into new files. Entry format:
- <date> · <person> · <agent>: <note>
-->

## BibTeX
```bibtex
@article{{citekey}, ...}
```
