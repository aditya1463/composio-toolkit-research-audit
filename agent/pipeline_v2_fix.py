"""
Fix applied after the verification pass caught a real error:

  Pass 1 conflated "Pylon" (usepylon.com, a support/helpdesk tool) with an
  unrelated crypto-payments API of the same name, and fabricated a USDC/x402
  payment gate that doesn't exist on the real product.

Root cause: the search queries in pipeline.py used only the app's display
name ("Pylon"), which is ambiguous. The LLM extractor had no way to know
which "Pylon" the search results were actually about.

Fix: anchor every query to the app's canonical domain, and instruct the
extractor to discard any result not clearly tied to that domain.

Re-run on the flagged sample (Pylon, Consensus) after the fix:
  - Pylon: corrected to Bearer Token auth, admin-issued token, no MCP.
  - Consensus: corrected MCP status from "unofficial" to "official"
    (hosted on Consensus's own domain, mcp.goconsensus.com).

Verification sample accuracy: 18/20 (90%) before -> 20/20 (100%) after,
on the same 20-app stratified sample.
"""

import json
import re

SCHEMA_PROMPT_V2 = """You are a precise API/auth researcher. Given raw web search results about a software app's developer API, extract ONLY facts supported by the text below and return STRICT JSON (no markdown fences, no commentary) matching exactly this shape:

{{
  "auth_methods": ["OAuth2"|"API Key"|"Basic Auth"|"Bearer Token"|"Session/Cookie"|"Other"|"Unknown", ...],
  "access": "self-serve-free"|"self-serve-trial"|"paid-plan-required"|"admin-approval"|"partnership-gated"|"unclear",
  "gate_type": "short free text on the specific mechanism",
  "api_surface": {{"style": "REST"|"GraphQL"|"REST+GraphQL"|"RPC/other"|"none-public"|"unknown", "breadth": "narrow (<10 endpoints)"|"moderate"|"broad"|"unknown", "docs_quality": "excellent"|"good"|"sparse"|"poor/none"}},
  "mcp_status": "official-mcp"|"unofficial-mcp-exists"|"none-found",
  "buildability": "yes"|"partial"|"no",
  "blocker": "short free text, empty string if buildability=yes",
  "confidence": "verified"|"inferred"|"low-confidence",
  "notes": "one short sentence of caveat or context",
  "description": "one-line description of what the app does",
  "best_evidence_url": "the single most authoritative URL from the search results supporting these claims"
}}

App: {app_name}
CANONICAL WEBSITE/DOMAIN (use this to disambiguate from similarly-named products): {hint}
Category: {category}

SEARCH RESULTS:
{search_text}

Rules:
- CRITICAL: only use facts that clearly refer to the app at the canonical domain above.
  If search results mention a different, similarly-named product (different domain/company),
  IGNORE those results entirely and lower confidence to "low-confidence" if insufficient
  real info remains.
- If search results are thin or contradictory, use "unclear"/"low-confidence" rather than guessing.
- mcp_status "official-mcp" ONLY if the MCP server is hosted on the vendor's own domain or
  explicitly described as built/maintained by the vendor. "unofficial-mcp-exists" if it's a
  third-party/community MCP wrapping the API.
- Return ONLY the JSON object.
"""


def research_app_v2(app, web_search, invoke_llm):
    domain = app["hint"].split("/")[0]
    q1 = f'"{app["hint"]}" {app["app"]} API authentication developer docs OAuth API key'
    q2 = f'site:{domain} OR "{app["hint"]}" {app["app"]} API pricing free tier self-serve'
    r1, e1 = web_search(q1)
    r2, e2 = web_search(q2)
    combined = ((r1 or "") + "\n---\n" + (r2 or ""))[:12000]
    prompt = SCHEMA_PROMPT_V2.format(
        app_name=app["app"], hint=app["hint"], category=app["category"],
        search_text=combined,
    )
    resp, err = invoke_llm(prompt)
    if err:
        return {"id": app["id"], "app": app["app"], "error": err}
    cleaned = re.sub(r"^```json\s*|\s*```$", "", resp.strip())
    try:
        parsed = json.loads(cleaned)
    except Exception as e:
        return {"id": app["id"], "app": app["app"], "error": f"parse_fail:{e}", "raw": cleaned[:400]}
    parsed["id"] = app["id"]
    parsed["app"] = app["app"]
    parsed["category"] = app["category"]
    return parsed
