from pydantic import BaseModel, Field
from agents import Agent, ModelSettings, WebSearchTool

# Each search result item captured from the web
class SourceItem(BaseModel):
    title: str = Field(...)
    url: str = Field(...)
    date: str | None = None

# Final structured summary per query
class SearchSummary(BaseModel):
    summary: str = Field(description="<=220 words, tight and factual.")
    sources: list[SourceItem] = Field(description="Only use links from the provided web results.")

# Instruction block to control hallucinations and enforce reliability
INSTRUCTIONS = (
    "You will receive 'Web search results (use only these URLs):' formatted as:\n"
    "- <title>\n  URL: <url>\n  Date: <date>\n  Snippet: <text>\n"
    "Output ONLY json as {\"summary\":\"...\",\"sources\":[{\"title\":\"...\",\"url\":\"...\",\"date\":\"...\"}, ...]}.\n"
    "\n"
    "Ground rules:\n"
    "- Use ONLY the URLs provided. No invented links or facts.\n"
    "- Prefer 2025 items; allow late 2024 if 2025 is scarce. Ignore 2023 and older unless the user explicitly asks for history.\n"
    "- Keep the summary ≤220 words, factual, and directly answers the user’s query with concrete names, products, dates, or figures when present.\n"
    "- If results mix homonyms (same name, different entities), pick ONE and state that focus briefly in the first sentence; exclude the others.\n"
    "- If there are too few recent items, say so briefly in the summary rather than guessing.\n"
    "- Return 3–6 distinct sources from the provided list, deduped by URL.\n"
)

# Agent setup: ensures strict JSON, requires tool usage, small temperature for factual outputs
search_agent_instance = Agent(
    name="SearchAgent",
    instructions=INSTRUCTIONS,
    tools=[WebSearchTool(max_results=10, timelimit="w", mode="news")],
    model="llama-3.3-70b-versatile",
    model_settings=ModelSettings(tool_choice="required"),
    output_type=SearchSummary,
    temperature=0.2,  # low randomness = more factual
    strict_json=True, # enforces JSON only, prevents free-text hallucination
)
