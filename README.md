# Intelligence Brief

Ask a question about a company or sector and get a short, clean research summary with sources, driven by a compact, agent-orchestrated research pipeline. A planner agent derives scope, timeframe, and intent from the user query; a search agent invokes a web search tool to retrieve recent, credible sources; a ranker filters and prioritizes results by relevance, domain quality, and recency; and a writer agent produces the final brief with a clearly attributed Sources section. Responsibility is modular and delegated, tool use is isolated to the search agent, and strict structured outputs reduce cost and minimize factual error.

Check it out live here: [Intelligence Brief on Hugging Face Spaces](https://huggingface.co/spaces/Pooja-Nigam/Intelligence_Brief)

---

## Features

- **Focused Web Research**: Builds smart search queries (company/sector, recency, intent terms like layoffs, launch, earnings).
- **Fresh & Credible Sources**: Prefers recent links (2025 / last 30 days) and reputable domains (e.g., SEC, Reuters, Bloomberg, WSJ, FT, CNBC).
- **Tight Summaries (≤220 words)**: Clear and factual.
- **Brief Writer**: Turns findings into a short, friendly “Intelligence Brief” with a Sources section.
- **Email the Brief**: Send the final brief to your inbox via SendGrid.
- **Cost Controls**: Caps queries, concurrency, and sources to avoid surprise bills.

**Guardrails / Anti-hallucination**
- Uses **only** the URLs returned by the search tool (no invented links).
- Adds an **evidence note** if there isn’t a good mix of official + independent sources.
- Normalizes dates and favors recent items.
- Enforces **strict JSON** on intermediate agents to reduce format drift.

---

## Tools & Libraries Used

- Python 3.x  
- [Gradio](https://gradio.app/) – web UI and HF Space runtime  
- [OpenAI API](https://platform.openai.com/) – model calls (gpt-4o-mini in code)  
- [DuckDuckGo Search](https://pypi.org/project/duckduckgo-search/) – news/text search  
- [Pydantic](https://docs.pydantic.dev/) – typed schemas for agent outputs  
- [python-dotenv](https://pypi.org/project/python-dotenv/) – local environment variables  
- [SendGrid](https://sendgrid.com/) – email delivery  
- [markdown](https://pypi.org/project/Markdown/) – render brief markdown to HTML for email

---

## Usage

### Run locally

1. Clone the repo:
```bash
git clone https://github.com/Pooja-Nigam/Research_Briefs.git
cd Research_Briefs
```
2. Create & activate a venv:
```bash
python -m venv .venv
```
### Windows:
```bash
.\.venv\Scripts\activate
```
### macOS/Linux:
```bash
source .venv/bin/activate
```
3. Install requirements:
```bash
pip install -r requirements.txt
``` 
4. Create a .env (this file is ignored by git):
```bash
OPENAI_API_KEY=sk-...
SENDGRID_API_KEY=SG-...
FROM_EMAIL=you@yourdomain.com   # must be a verified sender in SendGrid 
```
5. Run the app:
```bash
python app.py
```
## License

MIT License  

Copyright (c) 2025 Pooja Nigam  

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:  

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.  

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
