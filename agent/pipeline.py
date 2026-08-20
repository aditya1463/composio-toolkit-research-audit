"""
Composio toolkit research pipeline.

This mirrors, line for line, the logic that ran live inside Composio's
COMPOSIO_REMOTE_WORKBENCH sandbox (accessed via the Composio MCP connector)
to research all 100 apps. It uses the `web_search` and `invoke_llm` helpers
that Composio's workbench provides natively.

To run standalone outside the workbench, swap `web_search`/`invoke_llm` for
your own implementations (e.g. wrapping the Composio Python SDK's tool
execution for a search-capable toolkit, plus any LLM client).
"""

import json
import re
import os
import concurrent.futures

SCHEMA_PROMPT = """You are a precise API/auth researcher. Given raw web search results about a software app's developer API, extract ONLY facts supported by the text below and return STRICT JSON (no markdown fences, no commentary) matching exactly this shape:

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

App: {app_name} ({hint})
Category: {category}

SEARCH RESULTS:
{search_text}

Rules:
- If search results are thin or contradictory, use "unclear"/"low-confidence" rather than guessing.
- mcp_status "official-mcp" ONLY if search results explicitly mention an official MCP server from the vendor.
- Return ONLY the JSON object.
"""


def research_app(app, web_search, invoke_llm):
    q1 = f"{app['app']} API authentication developer docs OAuth API key"
    q2 = f"{app['app']} API pricing free tier self-serve access developer account"
    r1, e1 = web_search(q1)
    r2, e2 = web_search(q2)
    combined = ((r1 or "") + "\n---\n" + (r2 or ""))[:12000]
    prompt = SCHEMA_PROMPT.format(
        app_name=app["app"], hint=app["hint"], category=app["category"],
        search_text=combined,
    )
    resp, err = invoke_llm(prompt)
    if err:
        return {"id": app["id"], "app": app["app"], "category": app["category"], "error": err}
    cleaned = re.sub(r"^```json\s*|\s*```$", "", resp.strip())
    try:
        parsed = json.loads(cleaned)
    except Exception as e:
        return {"id": app["id"], "app": app["app"], "category": app["category"],
                 "error": f"parse_fail: {e}", "raw": cleaned[:500]}
    parsed["id"] = app["id"]
    parsed["app"] = app["app"]
    parsed["category"] = app["category"]
    return parsed


def run_pipeline(apps, web_search, invoke_llm, checkpoint_path, batch_size=20, max_workers=8):
    if os.path.exists(checkpoint_path):
        with open(checkpoint_path) as f:
            all_results = json.load(f)
    else:
        all_results = {}

    for start in range(0, len(apps), batch_size):
        batch = apps[start:start + batch_size]
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as ex:
            futures = {ex.submit(research_app, a, web_search, invoke_llm): a for a in batch}
            for fut in concurrent.futures.as_completed(futures):
                a = futures[fut]
                try:
                    res = fut.result()
                except Exception as e:
                    res = {"id": a["id"], "app": a["app"], "category": a["category"], "error": str(e)}
                all_results[str(a["id"])] = res
        with open(checkpoint_path, "w") as f:
            json.dump(all_results, f)
        print(f"Checkpoint: {len(all_results)}/{len(apps)} apps done")

    return [all_results[str(a["id"])] for a in apps]


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--apps", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    # In the Composio workbench these are provided natively as globals.
    # Outside the workbench, wire these up to your own Composio SDK client / LLM client.
    from composio_workbench_shim import web_search, invoke_llm  # user-provided

    with open(args.apps) as f:
        apps = json.load(f)

    results = run_pipeline(apps, web_search, invoke_llm, checkpoint_path=args.out)
    with open(args.out, "w") as f:
        json.dump(results, f, indent=2)
    print(f"Done: {len(results)} apps written to {args.out}")
