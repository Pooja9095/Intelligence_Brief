import os, json, uuid, contextlib, asyncio, atexit
from typing import Any, Optional, List
from dataclasses import dataclass
from duckduckgo_search import DDGS
from openai import AsyncOpenAI

_client = None

# Return a global AsyncOpenAI client (singleton style)
def get_client():
    global _client
    if _client is None:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise RuntimeError("Missing GROQ_API_KEY. Set it in .env or environment.")
        _client = AsyncOpenAI(api_key=api_key, base_url="https://api.groq.com/openai/v1")
        atexit.register(lambda: asyncio.get_event_loop().run_until_complete(_client.close()))
    return _client

# Generate unique trace IDs
def gen_trace_id() -> str:
    return uuid.uuid4().hex

# Simple tracing context manager (logs start and end)
@contextlib.contextmanager
def trace(name: str, trace_id: Optional[str] = None):
    print(f"[trace start] {name} id={trace_id or gen_trace_id()}")
    try:
        yield
    finally:
        print(f"[trace end] {name}")

@dataclass
class ModelSettings:
    tool_choice: Optional[str] = None

class Result:
    def __init__(self, text: str):
        self.final_output = text
     # Parse output into a Pydantic model, fallback to {"markdown": "..."} if schema fits
    def final_output_as(self, model_cls):
        """
        Try to parse JSON into the requested Pydantic model.
        Fallback to {"markdown": "..."} ONLY if the target model is a brief with a single 'markdown' field.
        Otherwise, raise the original error.
        """
        try:
            data = _extract_json(self.final_output)
            return model_cls.model_validate(data)
        except Exception as first_err:
            
            try:
                fields = getattr(model_cls, "model_fields", {})
                if isinstance(fields, dict) and set(fields.keys()) == {"markdown"}:
                    return model_cls.model_validate({"markdown": self.final_output})
            except Exception:
                pass
            
            raise first_err
# Try to extract JSON from text, even if wrapped in ```json blocks
def _extract_json(txt: str) -> Any:
    s = txt.strip()
    if s.startswith("```"):
      
        s = s.strip("`")
        if s.lower().startswith("json"):
            s = s[4:].lstrip()
    try:
        return json.loads(s)
    except Exception:
        pass
     # Fallback: regex search for JSON-like substrings
    import re
    candidates = re.findall(r'(\{.*\}|\[.*\])', s, re.S)
    for cand in candidates:
        try:
            return json.loads(cand)
        except Exception:
            continue
    raise ValueError("Could not parse JSON from model output")

class WebSearchTool:
    # Wrapper around DuckDuckGo search
    def __init__(self, search_context_size: str = "medium", max_results: int = 8, timelimit: str = "w", mode: str = "news"):
        self.max_results = max_results
        self.timelimit = timelimit
        self.mode = mode
    async def run(self, query: str) -> List[dict]:
        # Perform search in a thread (non-blocking)
        def _do_search(q: str, k: int, tl: str, mode: str):
            with DDGS() as ddgs:
                if mode == "news":
                    hits = ddgs.news(q, max_results=k, timelimit=tl) or []
                else:
                    hits = ddgs.text(q, max_results=k, timelimit=tl) or []
            return hits
        hits = await asyncio.to_thread(_do_search, query, self.max_results, self.timelimit, self.mode)
        # Normalize results
        norm = []
        for h in hits:
            norm.append({
                "title": (h.get("title") or "").strip(),
                "href": (h.get("url") or h.get("href") or "").strip(),
                "body": (h.get("body") or h.get("excerpt") or "").strip(),
                "date": (h.get("date") or "").strip(),
            })
        return norm

# Extract search query if input starts with "Search term:"
def _pick_query_from(text: str) -> str:
    for line in text.splitlines():
        if line.lower().startswith("search term:"):
            return line.split(":", 1)[1].strip()
    return text.strip()

# Format search hits for model input
def _format_hits(hits: List[dict]) -> str:
    lines = []
    for h in hits[:10]:
        title = h.get("title","").strip()
        href = h.get("href","").strip()
        body = h.get("body","").strip()
        date = h.get("date","").strip()
        lines.append(f"- {title}\n  URL: {href}\n  Date: {date}\n  Snippet: {body}")
    return "\n".join(lines)

class Agent:
    # Represents an agent with instructions + optional tools + output schema
    def __init__(self, name: str, instructions: str, model: str,
                 tools: Optional[List[Any]] = None,
                 output_type: Optional[Any] = None,
                 model_settings: Optional[ModelSettings] = None,
                 temperature: float = 0.3,
                 strict_json: bool = False):
        self.name = name
        self.instructions = instructions
        self.model = model
        self.tools = tools or []
        self.output_type = output_type
        self.model_settings = model_settings or ModelSettings()
        self.temperature = temperature
        self.strict_json = strict_json

class Runner:
    # Executes an agent: run tools, send prompt to model, handle JSON enforcement
    @staticmethod
    async def run(agent: Agent, user_input: str) -> Result:
        client = get_client()
        tool_results_text = ""
        # Run web search tools if present
        web_tools = [t for t in agent.tools if isinstance(t, WebSearchTool)]
        if web_tools:
            query = _pick_query_from(user_input)
            if query:
                try:
                    hits = await web_tools[0].run(query)
                    tool_results_text = _format_hits(hits)
                except Exception as e:
                    tool_results_text = f"(web search failed: {e})"
        # Build system + user messages
        system = agent.instructions
        user = user_input
        if tool_results_text:
            user += "\n\nWeb search results (use only these URLs):\n" + tool_results_text
        # If agent expects JSON, ask model to return JSON
        wants_json = agent.output_type is not None
        response_format = {"type": "json_object"} if wants_json else None
        if wants_json and "json" not in system.lower():
            system += "\n\nReturn a valid JSON object. Output ONLY json."

        # First call to model
        resp = await client.chat.completions.create(
            model=agent.model,
            messages=[{"role":"system","content":system},
                      {"role":"user","content":user}],
            temperature=agent.temperature if not wants_json else min(agent.temperature, 0.5),
            response_format=response_format,
        )
        text = resp.choices[0].message.content.strip()
        # Handle strict JSON fallback
        if wants_json:

            brief_style = False
            try:
                fields = getattr(agent.output_type, "model_fields", {})
                brief_style = isinstance(fields, dict) and set(fields.keys()) == {"markdown"}
            except Exception:
                brief_style = False

            if agent.strict_json or not brief_style:
                try:
                    _ = _extract_json(text)
                except Exception:
                     # Retry with stricter system prompt
                    strict_system = system + "\n\nIMPORTANT: Output ONLY a single valid JSON object matching the expected schema. No prose, no extra text."
                    resp2 = await client.chat.completions.create(
                        model=agent.model,
                        messages=[{"role":"system","content":strict_system},
                                  {"role":"user","content":user}],
                        temperature=min(agent.temperature, 0.3),
                        response_format=response_format,
                    )
                    text = resp2.choices[0].message.content.strip()

        return Result(text)
