import asyncio
import datetime
from urllib.parse import urlparse
from agents import Runner, trace, gen_trace_id
from planner_agent import planner_agent, WebSearchPlan, WebSearchItem
from search_agent import search_agent_instance, SearchSummary
from intel_agent import intel_agent, IntelBundle

# Limits and weights
MAX_SOURCES = 3           # Max number of sources included in final brief 
MAX_CONCURRENCY = 5       # Max number of parallel searches 
MAX_TOTAL_QUERIES = 6     # Cap on planned search queries 

# Trust weights for domains
DOMAIN_WEIGHTS = {
    "sec.gov": 2.5,
    "reuters.com": 1.8,
    "bloomberg.com": 1.8,
    "wsj.com": 1.7,
    "ft.com": 1.7,
    "cnbc.com": 1.6,
    "marketwatch.com": 1.4,
    "seekingalpha.com": 1.2,
    "forbes.com": 1.1,
}

RECENCY_DAYS_DEFAULT = 180  # Default lookback window

class ResearchManager:
    async def run(self, topic: str):
        trace_id = gen_trace_id()
        try:
            with trace("Intel Research", trace_id=trace_id):
                
                yield "🔎 Planning searches…"
                plan = await self._plan(topic)

                # Deduplicate and trim queries
                unique_items = self._dedupe_queries(plan.searches or [])[:MAX_TOTAL_QUERIES]
                yield f"🌐 Searching the web ({len(unique_items)} queries)…"
                summaries, failed = await self._search_all(unique_items)
                if failed:
                    yield f"ℹ️ {failed} quer{'y' if failed == 1 else 'ies'} failed; continuing with the rest."

                if not summaries:
                    yield "⚠️ No recent credible sources found. Try a narrower query."
                    return

                merged_sources, source_meta = self._merge_sources(plan, summaries)
                
                # If not enough good sources, retry with tightened plan
                if len(merged_sources) < 2:
                    yield "🔧 Tightening queries for better evidence…"
                    tightened_inp = (
                        f"TIGHTEN:true\n"
                        f"MAX_QUERIES:{MAX_TOTAL_QUERIES}\n"
                        f"Topic: {topic}\n"
                        f"Goal: Plan searches for an Intelligence Brief."
                    )
                    tplan_res = await Runner.run(planner_agent, tightened_inp)
                    tplan = tplan_res.final_output_as(WebSearchPlan)
                    t_items = self._dedupe_queries(tplan.searches or [])[:MAX_TOTAL_QUERIES]
                    yield f"🌐 Searching the web ({len(t_items)} queries)…"
                    summaries, failed2 = await self._search_all(t_items)
                    if failed2:
                        yield f"ℹ️ {failed2} quer{'y' if failed2 == 1 else 'ies'} failed in tighten pass."
                    if not summaries:
                        yield "⚠️ Still not enough recent credible sources after tightening."
                        return

                    plan = tplan  
                    merged_sources, source_meta = self._merge_sources(plan, summaries)

                yield "🧠 Writing brief…"
                bundle = await self._write(plan, summaries, merged_sources, source_meta)

                yield "✅ Done. See sources below."
                yield bundle.markdown
        except Exception as e:
            yield f"❌ Error: {e}"

    async def _plan(self, topic: str) -> WebSearchPlan:
        inp = f"Topic: {topic}\nGoal: Plan searches for an Intelligence Brief."
        res = await Runner.run(planner_agent, inp)
        return res.final_output_as(WebSearchPlan)

    def _dedupe_queries(self, items: list[WebSearchItem]) -> list[WebSearchItem]:
        seen, out = set(), []
        for it in items:
            key = (getattr(it, "query", "") or "").strip().lower()
            if key and key not in seen:
                seen.add(key)
                out.append(it)
        return out

    async def _search_all(self, items: list[WebSearchItem]) -> tuple[list[SearchSummary], int]:
        sem = asyncio.Semaphore(MAX_CONCURRENCY)
        failed = 0

        async def do(item: WebSearchItem):
            nonlocal failed
            q = f"Search term: {item.query}\nReason for searching: {item.reason}"
            async with sem:
                try:
                    res = await Runner.run(search_agent_instance, q)
                    return res.final_output_as(SearchSummary)
                except Exception:
                    failed += 1
                    return None

        tasks = [asyncio.create_task(do(s)) for s in items]
        results: list[SearchSummary] = []
        try:
            for t in asyncio.as_completed(tasks):
                r = await t
                if r:
                    results.append(r)
            return results, failed
        finally:
            for t in tasks:
                if not t.done():
                    t.cancel()

    def _parse_dt(self, s: str | None):
        """Parse many date formats and normalize to *naive UTC* so comparisons never mix aware/naive."""
        if not s:
            return None
        s = s.strip()
        fmts = [
            "%Y-%m-%d",
            "%Y-%m-%dT%H:%M:%S%z",
            "%Y-%m-%dT%H:%M:%S.%f%z",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%dT%H:%M:%S.%f",
            "%b %d, %Y",
            "%B %d, %Y",
            "%Y/%m/%d",
        ]
        dt = None
        for fmt in fmts:
            try:
                dt = datetime.datetime.strptime(s, fmt)
                break
            except Exception:
                pass
        if dt is None:
            try:
            
                t = s[:-1] if s.endswith("Z") else s
                dt = datetime.datetime.fromisoformat(t)
            except Exception:
                return None

        if dt.tzinfo is not None:
            dt = dt.astimezone(datetime.timezone.utc).replace(tzinfo=None)
        return dt

    def _domain_weight(self, url: str) -> float:
        try:
            host = urlparse(url).netloc.lower()
            if host in DOMAIN_WEIGHTS:
                return DOMAIN_WEIGHTS[host]
            parts = host.split(".")
            if len(parts) >= 2:
                apex = ".".join(parts[-2:])
                return DOMAIN_WEIGHTS.get(apex, 1.0)
        except Exception:
            pass
        return 1.0

    def _contains_topic(self, text: str, topic: str) -> bool:
        return topic.lower() in (text or "").lower()

    def _is_official(self, url: str, topic: str) -> bool:
        """Heuristic: company site / investor subdomain / regulator (e.g., sec.gov)."""
        host = (urlparse(url).netloc or "").lower()
        if not host:
            return False
        if host.endswith("sec.gov"):
            return True
        if "investor" in host or "ir." in host:
            return True
    
        return topic.replace(" ", "").lower() in host

    def _is_independent(self, url: str) -> bool:
        host = (urlparse(url).netloc or "").lower()
        for apex in ("reuters.com", "bloomberg.com", "wsj.com", "ft.com", "cnbc.com", "marketwatch.com"):
            if host.endswith(apex):
                return True
        return False

    def _relevance_score(
        self,
        topic: str,
        title: str,
        url: str,
        dt: datetime.datetime | None,
        timeframe_days: int | None,
    ) -> float:
        score = 0.0
        if self._contains_topic(title, topic):
            score += 2.0
        if self._contains_topic(url, topic):
            score += 1.0

        score *= self._domain_weight(url)

        window_days = timeframe_days or RECENCY_DAYS_DEFAULT
        if dt:
            
            age_days = (datetime.datetime.utcnow() - dt).days
            if age_days <= window_days:
                score += max(0.0, 1.5 - (age_days / window_days))
        return score

    def _merge_sources(self, plan: WebSearchPlan, summaries: list[SearchSummary]) -> tuple[list[dict], dict]:
        """
        Merge, de-dup, and pick top by relevance (topic + domain + recency).
        Also return meta flags for evidence quality.
        """
        seen, candidates = set(), []
        topic = getattr(plan, "resolved_topic", "") or ""

        tf_window_days = None
        tf = getattr(plan, "timeframe", None)
        if tf:
            import re
            m = re.search(r'(\d+)\s*day', tf.lower())
            if m:
                try:
                    tf_window_days = int(m.group(1))
                except Exception:
                    tf_window_days = None

        for s in summaries or []:
            for src in (getattr(s, "sources", None) or []):
                url = (getattr(src, "url", "") or "").strip()
                if not url or url in seen:
                    continue
                seen.add(url)
                title = getattr(src, "title", "") or "Untitled"
                date_str = getattr(src, "date", "") or ""
                dt = self._parse_dt(date_str)  # normalized to naive UTC
                score = self._relevance_score(topic, title, url, dt, tf_window_days)
                candidates.append({
                    "title": title,
                    "url": url,
                    "date": date_str,
                    "dt": dt,
                    "score": score,
                })

        candidates.sort(key=lambda x: (x["score"], x["dt"] or datetime.datetime.min), reverse=True)
        top = candidates[:MAX_SOURCES]

        has_official = any(self._is_official(c["url"], topic) for c in top)
        has_indep = any(self._is_independent(c["url"]) for c in top)
        meta = {"has_official": has_official, "has_indep": has_indep}
        return top, meta

    async def _write(
        self,
        plan: WebSearchPlan,
        summaries: list[SearchSummary],
        merged_sources: list[dict] | None = None,
        source_meta: dict | None = None,
    ) -> IntelBundle:
        timeframe_text = (getattr(plan, "timeframe", None) or
                          ("Up to " + datetime.datetime.now().strftime("%B %Y")))

        if merged_sources is None or source_meta is None:
            merged_sources, source_meta = self._merge_sources(plan, summaries)

        src_lines = [f"- {s['title']} | {s['url']} | {s['date']}" for s in merged_sources]

        compact = []
        for s in summaries:
            sm = getattr(s, "summary", None)
            if sm:
                compact.append(f"- {sm}")

        evidence_note = ""
        if not source_meta.get("has_official", False) or not source_meta.get("has_indep", False):
            evidence_note = "Limited official/independent source mix in the recent window; interpret with caution."

        inp = (
            f"resolved_topic: {plan.resolved_topic}\n"
            f"scope: {plan.scope}\n"
            f"timeframe_text: {timeframe_text}\n"
            + (f"evidence_note: {evidence_note}\n" if evidence_note else "")
            + "ProvidedSources:\n" + "\n".join(src_lines) + "\n\n"
            + "SearchSummaries:\n" + "\n".join(compact) + "\n"
        )

        res = await Runner.run(intel_agent, inp)
        return res.final_output_as(IntelBundle)

