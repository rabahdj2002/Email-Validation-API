import difflib
import os
import smtplib
import socket
from datetime import datetime, timezone
from typing import List, Literal, Optional

import dns.exception
import dns.resolver
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from email_validator import EmailNotValidError
from email_validator import validate_email as parse_email
from pydantic import BaseModel, EmailStr, Field

DNS_TIMEOUT_SECONDS = float(os.getenv("DNS_TIMEOUT_SECONDS", "3"))
SMTP_TIMEOUT_SECONDS = float(os.getenv("SMTP_TIMEOUT_SECONDS", "10"))
SMTP_HELO_HOST = os.getenv("SMTP_HELO_HOST", "email-validation-api.local")
SMTP_UNAVAILABLE = "unavailable"


app = FastAPI(title="Email Validation API", version="1.1.0")

class EmailRequest(BaseModel):
    email: EmailStr = Field(..., description="Email to validate")
    depth: Literal["basic", "full"] = Field("basic", description="'basic' (syntax, MX, disposable) or 'full' (adds SMTP)")

class ValidationChecks(BaseModel):
    syntax: bool
    mx: List[str] = Field(default_factory=list)
    smtp: Optional[str] = Field(None, description="SMTP RCPT reply code, or 'unavailable' if no mail server could be reached")
    disposable: bool = False

class ValidationResult(BaseModel):
    valid: bool
    score: float
    checks: ValidationChecks
    suggestion: Optional[str] = None

@app.get("/ping")
async def ping():
    return {"status": "ok", "version": app.version, "timestamp": datetime.now(timezone.utc).isoformat()}

@app.get("/", response_class=HTMLResponse)
async def root():
    readme_html = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Email Validation API</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: -apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Oxygen,Ubuntu,Cantarell,'Open Sans','Helvetica Neue',sans-serif; 
            max-width: 900px; margin: 0 auto; padding: 2rem; line-height: 1.6; color: #333; background: #fafafa; 
        }
        .header { text-align: center; margin-bottom: 2rem; }
        .badge { display: inline-block; padding: 0.25rem 0.5rem; margin: 0 0.25rem; border-radius: 20px; font-size: 0.8rem; font-weight: 500; }
        .live { background: #28a745; color: white; }
        .fastapi { background: #009485; color: white; }
        h1 { color: #1f70c2; margin-bottom: 0.5rem; font-size: 2.5rem; }
        h2 { color: #1f70c2; margin: 2rem 0 1rem 0; }
        pre, code { background: #2d3748; color: #a0aec0; padding: 0.5rem; border-radius: 5px; font-family: 'Fira Code', monospace; }
        pre { padding: 1rem; overflow-x: auto; }
        table { border-collapse: collapse; width: 100%; margin: 1rem 0; background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        th, td { border: 1px solid #e2e8f0; padding: 1rem; text-align: left; }
        th { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; }
        .endpoint { background: #1a202c; padding: 1.5rem; border-radius: 8px; margin: 1rem 0; }
        .features { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 1rem; }
        .feature { background: white; padding: 1.5rem; border-radius: 8px; text-align: center; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .metric { font-size: 1.2rem; font-weight: bold; color: #1f70c2; }
        footer { text-align: center; margin-top: 3rem; padding-top: 2rem; border-top: 1px solid #e2e8f0; color: #666; }
    </style>
</head>
<body>
    <div class="header">
        <h1>Email Validation API 🚀</h1>
        <p><span class="badge fastapi">FastAPI</span> | Built by <strong>Rabah Djebbes</strong> - Automation Engineering</p>
    </div>

    <h2>✨ API Endpoints</h2>
    <div class="endpoint">
        <h3>📖 Interactive Docs: <a href="/docs">/docs</a></h3>
        <h3>🔍 Health Check: <a href="/ping">/ping</a></h3>
    </div>

    <h2>✅ Features</h2>
    <div class="features">
        <div class="feature">✅ Syntax (RFC 5322)</div>
        <div class="feature">✅ MX Records</div>
        <div class="feature">✅ SMTP Verify</div>
        <div class="feature">✅ Disposable Block</div>
        <div class="feature">✅ Confidence Score</div>
        <div class="feature">✅ Typo Suggestions</div>
    </div>

    <h2>🧪 Test Results</h2>
    <table>
        <tr><th>Email</th><th>Result</th><th>Score</th></tr>
        <tr><td>support@docker.com</td><td>✅ PASS</td><td>1.0</td></tr>
        <tr><td>rabahwork@gmail.com</td><td>✅ PASS</td><td>1.0</td></tr>
        <tr><td>test@yopmail.com</td><td>❌ FAIL</td><td>0.00</td></tr>
    </table>

    <footer>
        <p><a href="/docs">Swagger UI</a> | <a href="https://github.com/rabahdj2002/Email-Validation-API">Source on GitHub</a> | Made by Rabah Djebbes</p>
    </footer>
</body>
</html>
    """
    return HTMLResponse(content=readme_html, status_code=200)

DISPOSABLE_DOMAINS = {
    "yopmail.com", "tempmail.org", "guerrillamail.com", "10minutemail.com",
    "mailinator.com", "sharklasers.com", "getnada.com", "33mail.com",
    "temp-mail.org", "trashmail.com", "maildrop.cc", "dispostable.com",
    "throwawaymail.com", "fakeinbox.com", "mintemail.com", "mohmal.com",
    "emailondeck.com", "tempail.com", "burnermail.io", "spamgourmet.com",
}

COMMON_DOMAINS = [
    "gmail.com", "yahoo.com", "outlook.com", "hotmail.com", "icloud.com",
    "live.com", "aol.com", "proton.me", "protonmail.com", "yandex.com", "gmx.com", "mail.com",
]


def suggest_domain(domain: str) -> Optional[str]:
    """Closest well-known domain for a likely typo, e.g. 'gmial.com' -> 'gmail.com'."""
    if domain in COMMON_DOMAINS:
        return None
    match = difflib.get_close_matches(domain, COMMON_DOMAINS, n=1, cutoff=0.8)
    return match[0] if match else None


def resolve_mx(domain: str) -> List[str]:
    """MX hosts ordered by preference; empty if the domain has none or DNS fails."""
    resolver = dns.resolver.Resolver()
    resolver.lifetime = DNS_TIMEOUT_SECONDS
    try:
        answers = resolver.resolve(domain, "MX")
    except (dns.exception.DNSException, OSError):
        return []
    records = sorted(answers, key=lambda r: r.preference)
    return [str(r.exchange).rstrip(".") for r in records if str(r.exchange) not in (".", "")]


def smtp_check(email: str, mx_hosts: List[str]) -> str:
    """RCPT TO reply code from the first reachable MX host, or 'unavailable'."""
    for host in mx_hosts:
        try:
            with smtplib.SMTP(host, 25, timeout=SMTP_TIMEOUT_SECONDS) as server:
                server.helo(SMTP_HELO_HOST)
                server.mail(f"verify@{SMTP_HELO_HOST}")
                code, _ = server.rcpt(email)
                return str(code)
        except (smtplib.SMTPException, socket.timeout, OSError):
            continue
    return SMTP_UNAVAILABLE


@app.post("/validate", response_model=ValidationResult, summary="Validate Email")
def validate_email(request: EmailRequest):
    # Sync on purpose: FastAPI runs it in a worker thread, so slow DNS/SMTP never blocks other requests.
    email = request.email
    domain = email.rsplit("@", 1)[1].lower()
    checks = ValidationChecks(syntax=True)  # EmailStr already rejected bad syntax with HTTP 422
    score = 0.4
    try:
        parsed = parse_email(email, check_deliverability=False)
        ascii_domain, ascii_email = parsed.ascii_domain, parsed.ascii_email
    except EmailNotValidError:
        ascii_domain, ascii_email = domain, None

    # DNS and SMTP need the IDNA (punycode) form, e.g. gießen.de -> xn--gieen-nqa.de
    checks.mx = resolve_mx(ascii_domain)
    if checks.mx:
        score += 0.4

    checks.disposable = domain in DISPOSABLE_DOMAINS

    if request.depth == "full" and checks.mx and not checks.disposable:
        # A non-ASCII mailbox name needs SMTPUTF8, which this check does not speak.
        checks.smtp = smtp_check(ascii_email, checks.mx) if ascii_email else SMTP_UNAVAILABLE
        if checks.smtp.startswith("2"):
            score += 0.2
        elif checks.smtp.startswith("5"):
            score = min(score, 0.4)  # the mail server rejected this mailbox

    if checks.disposable:
        score = 0.0

    return ValidationResult(
        valid=score >= 0.6,
        score=round(score, 2),
        checks=checks,
        suggestion=None if checks.disposable else suggest_domain(domain),
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8001")))
