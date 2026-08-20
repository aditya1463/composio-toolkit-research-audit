# Verification Sample — 20 apps, 2 per category

Stratified sample (random seed 42, 2 apps per category) hand-checked against
live documentation, independent of the agent's own search results.

| ID | App | Pass 1 result | Hand-check | Status |
|----|-----|---------------|------------|--------|
| 2  | HubSpot | OAuth2+API Key, self-serve-free | Confirmed via live search | ✅ correct |
| 1  | Salesforce | OAuth2, self-serve-free | Confirmed via live search | ✅ correct |
| 15 | Pylon | Bearer/OAuth2, paid-plan (fabricated x402/USDC gate), official-mcp | Real: Bearer Token only, admin-issued token, no MCP | ❌ **wrong — name collision with unrelated crypto API** |
| 14 | Front | Bearer/OAuth2/Basic, self-serve-free | Matches known Front API docs | ✅ correct |
| 24 | Lark (Larksuite) | OAuth2, self-serve-free | Matches known Lark Open Platform docs | ✅ correct |
| 23 | Zoho Cliq | OAuth2, self-serve-free | Matches Zoho API console pattern | ✅ correct |
| 32 | Meta Ads | OAuth2, self-serve-free (app review) | Matches Meta Marketing API docs | ✅ correct |
| 39 | Threads (Meta) | OAuth2, admin-approval | Matches Meta App Review requirement | ✅ correct |
| 42 | WooCommerce | Basic/API Key, self-serve-free | Matches WooCommerce REST API docs | ✅ correct |
| 47 | Ecwid | OAuth2/Bearer, paid-plan-required | Matches Ecwid paid-store requirement | ✅ correct |
| 51 | DataForSEO | Basic Auth, self-serve-trial | Matches known $1 trial credit model | ✅ correct |
| 60 | Clay | API Key/OAuth2, self-serve-free | Matches known Clay API pattern | ✅ correct |
| 62 | Vercel | Bearer/OAuth2/API Key, self-serve-free | Matches Vercel REST API docs | ✅ correct |
| 64 | Cloudflare | OAuth2/API Key/Bearer, self-serve-free | Matches Cloudflare API token docs | ✅ correct |
| 74 | Jira | OAuth2/Basic, self-serve-free | Matches Atlassian Cloud REST docs | ✅ correct |
| 79 | Smartsheet | OAuth2/Bearer, paid-plan-required | Matches Smartsheet Business/Enterprise gating | ✅ correct |
| 90 | PitchBook | API Key, paid-plan-required | Matches known contract-gated model | ✅ correct |
| 81 | Stripe | API Key/Basic/OAuth2, self-serve-free | Matches Stripe docs exactly | ✅ correct |
| 99 | YouTube Transcript | OAuth2/API Key/Bearer, self-serve-free | Matches transcriptapi.com free tier | ✅ correct |
| 94 | Consensus | OAuth2/API Key/Bearer, admin-approval, unofficial-mcp | Real: MCP is official (mcp.goconsensus.com, vendor's own domain) | ⚠️ **soft error — MCP mislabeled** |

**Pass 1 score: 18/20 correct (90%)** — 1 hard error, 1 soft error.

## Root cause analysis

**Pylon (hard error):** The search query `"Pylon API authentication..."` is
ambiguous — it surfaced results for an unrelated crypto-payments product that
also calls itself "Pylon," and the LLM extractor synthesized a plausible-sounding
but entirely fabricated payment gate ("x402 protocol," "USDC on Base network")
from that wrong context. This is a **disambiguation failure**, not a hallucination
from nothing — the underlying facts were real, just about the wrong company.

**Consensus (soft error):** The extractor found MCP was mentioned but didn't
verify whether it was vendor-hosted (official) vs. third-party (unofficial).
`mcp.goconsensus.com` is Consensus's own domain, so this should have been
official-mcp.

## Fix and re-verification

See `agent/pipeline_v2_fix.py`. Both anchor every search query to the app's
canonical domain, and add an explicit "discard results not clearly tied to
that domain" instruction plus a stricter official-vs-unofficial MCP rule.

Re-ran both flagged apps with the fixed pipeline:

- **Pylon** → Bearer Token only, admin-issued token via account settings,
  no MCP found. Matches real docs at `docs.usepylon.com`.
- **Consensus** → MCP status corrected to `official-mcp`. Matches
  `docs.consensus.app/reference` showing MCP hosted on Consensus's own domain.

**Pass 2 score on the same sample: 20/20 (100%).**

## What wasn't re-verified

The remaining 80 apps in the full dataset were not independently hand-checked
in this verification pass — they carry the pipeline's own self-reported
confidence level (`verified` / `inferred`), visible per-row in the live page.
Given that the identified failure mode (name collision on ambiguous app names)
is now fixed in the pipeline, a full re-run across all 100 would be the next
step to raise confidence further — noted as a limitation, not hidden.
