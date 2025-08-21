import os
import random
import sendgrid
import markdown
from sendgrid.helpers.mail import Email, Mail, Content, To

# Friendly openers 
OPENERS = [
    "Thanks for taking a moment — I pulled together a short brief I hope is useful.",
    "Appreciate you reading this — I did some digging and wrapped up the key points.",
    "Thanks for checking this out — here’s a clear summary so you can skim and get the picture.",
    "Thanks for your time — I gathered the highlights so it’s easy to follow.",
    "Grateful you’re interested — here’s a quick brief without the extra noise.",
    "Thanks for reading — I’ve put the main points in one place.",
    "Appreciate your interest — here’s a short, straight-to-the-point brief."
]

def build_email_html(topic: str, markdown_body: str) -> str:
    opener = random.choice(OPENERS)
    body_html = markdown.markdown(markdown_body, extensions=["extra", "sane_lists"])
    return f"""
    <html>
      <head>
        <meta charset="utf-8" />
        <style>
          body {{
            font-family: -apple-system, Segoe UI, Roboto, Arial, sans-serif;
            line-height: 1.6;
            background-color: #f9fafb; margin: 0; padding: 0;
          }}
          .container {{
            max-width: 700px; margin: 20px auto; padding: 24px;
            background: #ffffff; border-radius: 12px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
          }}
          .header {{ font-size: 22px; font-weight: bold; color: #2563eb; margin-bottom: 12px; }}
          .opener {{ font-size: 15px; color: #444; margin-bottom: 20px; }}
          .card {{
            padding: 16px; border-left: 4px solid #2563eb;
            background: #f9f9ff; border-radius: 8px;
            font-size: 14px; color: #111827;
          }}
          h1, h2, h3 {{ font-weight: bold; color: #111; }}
          h1 {{ font-size: 20px; margin-top: 20px; }}
          h2 {{ font-size: 18px; margin-top: 16px; }}
          h3 {{ font-size: 16px; margin-top: 12px; }}
          ul {{ margin: 8px 0 8px 20px; }}
          .footer {{ margin-top: 20px; font-size: 14px; color: #444; }}
          .signoff {{ margin-top: 30px; font-size: 14px; color: #111; }}
        </style>
      </head>
      <body>
        <div class="container">
          <div class="opener">Hi there,<br><br>{opener}</div>
          <div class="card">
            <p><strong>Topic:</strong> {topic}</p>
            {body_html}
          </div>
          <div class="signoff">
            Warm regards,<br><strong>Pooja N</strong>
          </div>
          <div class="footer"><em>Sent via tiny Gradio app ✨</em></div>
        </div>
      </body>
    </html>
    """

def send_email(subject: str, html_body: str, to_email: str):
    api_key = os.getenv("SENDGRID_API_KEY")
    FROM_EMAIL = os.getenv("FROM_EMAIL", "")
    if not api_key:
        return False, "Missing SENDGRID_API_KEY in .env"
    try:
        sg = sendgrid.SendGridAPIClient(api_key=api_key)
        mail = Mail(
            from_email=Email(FROM_EMAIL),
            to_emails=To(to_email),
            subject=subject,
            html_content=Content("text/html", html_body)
        ).get()
        resp = sg.client.mail.send.post(request_body=mail)
        return (200 <= resp.status_code < 300), f"status={resp.status_code}"
    except Exception as e:
        return False, str(e)
