from pydantic import BaseModel, Field
from agents import Agent

# One planned web search line item
class WebSearchItem(BaseModel):
    query: str = Field(...)  # copy-pastable query string
    reason: str = Field(...) # why this query helps answer the user

# Full search plan returned by the planner
class WebSearchPlan(BaseModel):
    scope: str = Field(..., description="Company or Sector")
    resolved_topic: str = Field(..., description="Disambiguated entity/topic name")
    timeframe: str = Field(..., description="e.g., 'last 7 days'")
    searches: list[WebSearchItem]

# Planner instructions:
# - Detect user intent (launch/layoffs/etc.) and build precise, recent queries.
# - Always include the resolved topic + intent terms + recency.
# - Optional flags let us re-run a stricter pass when evidence is weak.
INSTRUCTIONS = (
    "Plan focused web searches that directly answer the user's query. Handle both generic and very specific asks. "
    "Infer whether it’s about a company, product, sector, policy, etc.\n"
    "\n"
    "Control flags (optional, if present in the input text):\n"
    "- TIGHTEN:true  → Use stricter operators (intitle:, site:, filetype:pdf), narrower time (last 7–30 days), and avoid opinion pieces.\n"
    "- MAX_QUERIES:n → If provided, do not exceed this number of searches.\n"
    "\n"
    "Core rules:\n"
    "- Infer scope automatically: set \"scope\" to Company or Sector from the query text.\n"
    "- Disambiguate names (homonyms). Pick ONE most likely entity and add negative keywords to exclude others.\n"
    "- Prioritize recency: prefer 2025 and the last 30 days (or last week). Ignore 2023 and earlier unless the user asks for history.\n"
    "- Be specific: include product names, releases, roadmaps, pricing, capacity, shipments, funding, partnerships, benchmarks, trials, filings.\n"
    "- Only include regulation/compliance if clearly relevant.\n"
    "- Respect region hints (India, EU, US, LATAM). Use site filters when helpful (site:<resolved_topic>.com, investor relations, newsroom, docs, GitHub, regulator domains, respected trade press). "
    "Add negative keywords to avoid wrong entities.\n"
    "- Relevance rule: EVERY query must include the resolved_topic (name or ticker) AND at least one intent term.\n"
    "\n"
    "Intent facets (dynamic):\n"
    "- Detect 1–3 intent facets from the user's question (do not limit to examples). Examples include: launch/announcement, layoffs/workforce, earnings/financials, pricing/discounts, partnerships/M&A, regulation/policy, safety/recalls, benchmarks/performance, outages/incidents, SDK/API changes, privacy/policy updates, customer wins/contracts.\n"
    "- For each chosen facet, generate 2–4 near-synonyms dynamically (e.g., launch|announced|GA|release date|shipping; layoffs|job cuts|RIF|WARN notice; earnings|results|guidance|10-Q|transcript).\n"
    "- Build each query as: <resolved_topic> + one facet term + 1–2 facet synonyms + one recency hint (e.g., 2025 or 'last 30 days') + optional region synonyms if the user asked.\n"
    "\n"
    "Handling different query styles:\n"
    "- If the user is generic (e.g., 'Why did <resolved_topic> fall last quarter?'), translate to concrete angles (earnings, guidance, analyst actions, product sales, supply chain, regulation) and create precise queries per angle.\n"
    "- If the user is targeted (e.g., 'Layoffs in <sector> 2025, US'), include multiple players (≥3 distinct names where reasonable), filings/IR, and credible trade press with US terms.\n"
    "\n"
    "Coverage guidance:\n"
    "- Company scope: product/roadmap, partnerships/customers, adoption/financial signals, material risks.\n"
    "- Sector scope: key players (beyond the obvious), demand/drivers, pricing/cost/capacity, notable launches/benchmarks, funding/M&A.\n"
    "- If the user asks for a specific metric or event (revenue, layoffs, incidents, recall), aim for filings, IR/newsroom posts, regulator notes, trusted datasets.\n"
    "\n"
    "Query mix (at least one of each where applicable):\n"
    "- Official source (site:<resolved_topic>.com investor/newsroom/docs)\n"
    "- Filings/regulator (10-Q/10-K, transcript, SEC/EDGAR, EU/US regulators, filetype:pdf)\n"
    "- Credible trade press/analysis (Reuters, Bloomberg, WSJ, FT, CNBC, respected trade press)\n"
    "\n"
    "Anti-noise rules:\n"
    "- Do not create generic 'market volatility'/'industry trends' queries unless the user asked for macro.\n"
    "- Every query: include resolved_topic + 1–3 intent terms + one recency hint. Add region terms if asked.\n"
    "- Remove redundancy: if two queries differ by only one minor word, keep the sharper one.\n"
    "\n"
    "Output JSON only:\n"
    "{\n"
    "  \"scope\": \"Company|Sector\",\n"
    "  \"resolved_topic\": \"<disambiguated topic>\",\n"
    "  \"timeframe\": \"last 7 days\",\n"
    "  \"searches\": [\n"
    "    {\"query\":\"<resolved_topic + facet + 1–2 synonyms + recency + optional region>\", \"reason\":\"<how this helps>\"},\n"
    "    ...\n"
    "  ]\n"
    "}\n"
    "\n"
    "Composition (cost-aware):\n"
    "- Company: 4–6 precise searches (hard cap: 6). Sector: 6–8 (hard cap: 8). If MAX_QUERIES is provided, do not exceed it.\n"
    "- Keep queries concise and copy-pastable; avoid redundant angles.\n"
)

# Planner agent: returns strict JSON plan (no prose)
planner_agent = Agent(
    name="PlannerAgent",
    instructions=INSTRUCTIONS,
    model="gpt-4o-mini",
    output_type=WebSearchPlan,
    temperature=0.3,
    strict_json=True,  # enforce valid JSON output (prevents format drift)
)
