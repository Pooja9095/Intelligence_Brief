import random
import gradio as gr
from dotenv import load_dotenv
from research_manager import ResearchManager
from emailer import send_email, build_email_html
import re

from sessions import (
    new_session_id, add_session, get_session, increment_questions,
    reached_limit, is_admin, ADMIN_SESSION_ID, MAX_QUESTIONS
)

# Regex for validating emails
EMAIL_REGEX = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,63}$")

# Block disposable email domains (avoid spam/testers)
DISPOSABLE_DOMAINS = {
    "mailinator.com","10minutemail.com","guerrillamail.com","temp-mail.org",
    "yopmail.com","trashmail.com","sharklasers.com","burnermail.io"
}

# Example questions shown in the UI
examples = [
    "Why is Tesla investing in AI chips?",
    "What led Apple’s stock to fall last quarter?",
    "How is Amazon entering healthcare?",
    "Which startups are shaping the EV battery sector?",
    "Is Bolt expanding into new markets in 2025?",
    "What’s happening in agriculture tech this year?",
    "Who are the major players in fintech right now?",
]

# Load environment variables (API keys, etc.)
load_dotenv(override=True)
manager = ResearchManager()

async def run(topic: str, state: dict):
    state = state or {}

    if topic.strip().lower() == "/admin":
        state["session_id"] = ADMIN_SESSION_ID
        yield "🛡️ Admin mode enabled for this session.", state
        return

    # 2) Ensure we have a session_id
    session_id = state.get("session_id")
    if session_id is None:
        session_id = new_session_id()
        add_session(session_id)
        state["session_id"] = session_id

    # 3) Enforce limit for non-admin sessions
    if not is_admin(session_id):
        if get_session(session_id) is None:
            add_session(session_id)

        if reached_limit(session_id):
            yield f"⛔ Thanks for giving Intelligence Brief a try! You’ve reached the {MAX_QUESTIONS}-question limit for this session.", state
            return
        else:
            increment_questions(session_id)

    # 4) Guard for empty input
    if not topic.strip():
        yield "Please enter a topic."
        return

    # 5) Execute your existing pipeline
    async for chunk in manager.run(topic):
        yield chunk, state

# Validate email + send the generated brief
def email_brief(topic: str, last_md: str, to_email: str):
    to_email = (to_email or "").strip()
    if not last_md.strip():
        return "Generate a brief first."

    if not EMAIL_REGEX.fullmatch(to_email):
        return "Please enter a valid email address (e.g., name@example.com)."

    try:
        domain = to_email.split("@", 1)[1].lower()
    except Exception:
        return "Please enter a valid email address."

    if domain in DISPOSABLE_DOMAINS:
        return "Disposable email domains aren’t supported. Please use a regular email."

    html = build_email_html(topic, last_md)
    ok, msg = send_email(subject=f"Brief: {topic[:60]}", html_body=html, to_email=to_email)
    return "✅ Email sent!" if ok else f"❌ Email failed: {msg}"

# Random placeholder suggestion for textbox
def _pick_placeholder():
    return gr.update(placeholder=random.choice(examples))

# Build Gradio UI
with gr.Blocks(theme=gr.themes.Default(primary_hue="sky")) as ui:
    gr.Markdown("# Intelligence Brief")
    gr.Markdown("Ask about a company or an industry → get a concise research brief with sources → optional email.")
    
    state = gr.State({})

    topic = gr.Textbox(
        label="Ask a question",
        placeholder="Type your question here...",  
        lines=2,
    )
    ui.load(fn=_pick_placeholder, inputs=None, outputs=topic)

 # Button logic
    run_btn = gr.Button("Generate", variant="primary")
    email_btn = gr.Button("Email me")
    send_to = gr.Textbox(label="Enter your email", placeholder="name@example.com", visible=False)
    send_btn = gr.Button("Send", visible=False)
    output = gr.Markdown(value="")

    run_btn.click(fn=run, inputs=[topic, state], outputs=[output, state], queue=True)
    email_btn.click(lambda: [gr.update(visible=True), gr.update(visible=True)], inputs=None, outputs=[send_to, send_btn])
    send_btn.click(fn=email_brief, inputs=[topic, output, send_to], outputs=output)

# Launch app
if __name__ == "__main__":
    ui.launch()

