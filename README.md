# Composio Toolkit Research Audit — 100 Apps

**Live page:** `site/index.html` (see submission for deployed link)
**Data:** `data/research_final.json` — 100 records, schema in `data/schema.json`

## What this is

A research pipeline that audits an app's auth model, self-serve vs. gated access,
API surface, and MCP status — the same judgment call Composio makes before building
a toolkit — run across 100 apps automatically instead of by hand.

## How the research actually ran

This was **not** simulated. It ran live inside Composio's own `COMPOSIO_REMOTE_WORKBENCH`
tool — a real Python sandbox exposed through the Composio MCP connector, with built-in
`web_search` and `invoke_llm` helpers. See `agent/pipeline.py` for the exact logic that
executed.

1. Loaded all 100 apps (id, name, category, canonical domain hint).
2. For each app: two targeted `web_search` calls (auth/docs, pricing/self-serve terms).
3. Fed combined search results + a strict JSON schema prompt to `invoke_llm` for
   structured extraction — never freeform text.
4. Ran in parallel batches of 20 (`ThreadPoolExecutor`), checkpointed to disk after
   every batch so a failure never loses prior work.
5. Result: 100/100 apps processed, 0 pipeline errors, 93 self-flagged "verified"
   confidence, 7 self-flagged "inferred" (thin source material).

## Verification methodology

A stratified sample of 20 apps (2 per category) was **independently hand-checked**
against live documentation, separately from the agent's own search results.

- **Pass 1: 18/20 correct (90%).** One hard error (Pylon — the agent conflated
  `usepylon.com`, a support/helpdesk tool, with an unrelated crypto-payments API
  sharing the same name, and fabricated a USDC/x402 payment gate that doesn't exist).
  One soft error (Consensus's MCP server is official, hosted on Consensus's own
  domain — pass 1 mislabeled it unofficial).
- **Fix:** anchored every search query to the app's canonical domain, and instructed
  the extractor to discard any search result not clearly tied to that domain. Also
  tightened the official-vs-unofficial MCP rule to require vendor-domain hosting.
- **Pass 2: 20/20 correct (100%)** on the same sample, re-run with the fixed pipeline
  (`agent/pipeline_v2_fix.py`).

The other 80 records were **not** independently hand-verified in this pass — they
carry the pipeline's own self-reported confidence rating (`verified` / `inferred`),
visible per-row in the findings table. This is stated plainly rather than implied
away, per the assignment's honesty requirement.

## Where a human was needed

- Designing the schema (what fields matter, what "buildability" even means).
- Diagnosing *why* the agent got Pylon wrong (name collision, not a model failure
  in isolation) rather than just re-running until it looked right.
- Writing and validating the actual fix (domain-anchoring), not just re-prompting.
- Choosing the verification sample to be stratified across categories rather than random,
  so a systemic issue in one category couldn't hide.
- All narrative/pattern synthesis in the final page.

## Repo structure

```
data/
  schema.json           # the JSON shape every record follows
  research_pass1.json   # raw first-pass agent output, 100 records
  research_final.json   # pass1 + verification corrections applied, used by the page
  01-crm-sales.json     # early manual proof-of-concept batch (superseded by pipeline)
agent/
  pipeline.py            # the exact research_app() logic used in the live run
  pipeline_v2_fix.py      # the domain-anchored fix, validated on Pylon/Consensus
verification/
  sample.md               # the 20-app stratified sample and hand-check notes
site/
  index.html              # the single-page case study (self-contained, no build step)
```

## Running it yourself

The pipeline requires a Composio API key with access to `COMPOSIO_REMOTE_WORKBENCH`
(or equivalent web_search + LLM tool access). It cannot run from a network-restricted
sandbox — it needs to reach Composio's backend directly.

```bash
export COMPOSIO_API_KEY=your_key_here
python agent/pipeline.py --apps data/apps_list.json --out data/research_pass1.json
python agent/pipeline_v2_fix.py --in data/research_pass1.json --out data/research_final.json
```

The site (`site/index.html`) is fully static — open it directly, no server needed.
It embeds `data/research_final.json` inline so it's viewable offline.
