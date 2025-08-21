# Intelligence Brief – Research Summaries

Ask a question about a **company** or **sector** and get a short, clean **Intelligence Brief** with sources. The app plans focused web searches, summarizes what it finds, and writes a readable brief.

Check it out live here: [Intelligence Brief on Hugging Face Spaces](https://huggingface.co/spaces/Pooja-Nigam/Intelligence_Brief)

---

## Features

- **Focused Web Research**: Builds smart search queries (company/sector, recency, intent terms like layoffs, launch, earnings).
- **Fresh & Credible Sources**: Prefers recent links (2025 / last 30 days) and reputable domains (e.g., SEC, Reuters, Bloomberg, WSJ, FT, CNBC).
- **Tight Summaries (≤220 words)**: Clear and factual, no fluff.
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

2. Create & activate a venv:
```bash
python -m venv .venv
# Windows:
.\.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate ```

3. Install requirements:
```bash
pip install -r requirements.txt ```

4. Create a .env (this file is ignored by git):
   ```bash
   OPENAI_API_KEY=sk-...
   SENDGRID_API_KEY=SG-...
   FROM_EMAIL=you@yourdomain.com   # must be a verified sender in SendGrid ```

5. Run the app:
```bash
python app.py ``` 
