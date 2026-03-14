from fastapi import FastAPI
from pydantic import BaseModel, EmailStr
import re
import dns.resolver
import smtplib
from typing import Dict, List, Optional
from typing import Dict, Any

app = FastAPI(title="Email Validation API")

DISPOSABLE_DOMAINS = {
    "tempmail.org", "guerrillamail.com", "10minutemail.com", 
    "mailinator.com", "yopmail.com", "sharklasers.com"
}

class EmailRequest(BaseModel):
    email: EmailStr
    depth: str = "basic"

class ValidationResult(BaseModel):
    valid: bool
    score: float
    checks: Dict[str, Any]
    suggestion: Optional[str] = None

def syntax_check(email: str) -> bool:
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email, re.IGNORECASE))

async def mx_check(domain: str) -> List[str]:
    try:
        mx_records = dns.resolver.resolve(domain, 'MX')
        return [str(r.exchange).rstrip('.') for r in mx_records]
    except:
        return []

async def smtp_check(email: str, mx_servers: List[str]) -> str:
    if not mx_servers:
        return "no_mx"
    
    domain = email.split('@')[1]
    for mx in mx_servers[:2]:
        try:
            server = smtplib.SMTP(timeout=5)
            server.set_debuglevel(0)
            server.connect(mx, 25)
            server.helo("example.com")
            server.mail("test@example.com")
            code, _ = server.rcpt(email)
            server.quit()
            return "250" if code == 250 else f"{code}"
        except:
            continue
    return "timeout"

@app.post("/validate", response_model=ValidationResult)
async def validate_email(req: EmailRequest) -> ValidationResult:
    email = req.email.lower()
    domain = email.split('@')[1]
    
    checks = {"syntax": syntax_check(email)}
    score = 0.3 if checks["syntax"] else 0.0
    
    if checks["syntax"]:
        mx_servers = await mx_check(domain)
        checks["mx"] = mx_servers
        if mx_servers:
            score += 0.3
            
            if req.depth == "full":
                smtp_result = await smtp_check(email, mx_servers)
                checks["smtp"] = smtp_result
                score += 0.4 if smtp_result == "250" else 0.1
        
        checks["disposable"] = domain in DISPOSABLE_DOMAINS
        if checks["disposable"]:
            score = 0.0
    
    return ValidationResult(
        valid=score >= 0.8,
        score=round(score, 2),
        checks=checks
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
