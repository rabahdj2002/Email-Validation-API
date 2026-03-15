# Email Validation API 🚀

[![Live](https://img.shields.io/badge/Live-brightgreen)](https://verify-mail.rabahdj.online)
 [![FastAPI](https://img.shields.io/badge/FastAPI-0.115-blue?logo=fastapi)](https://fastapi.tiangolo.com)

**Production email validation API** - Syntax, MX, SMTP, disposable detection.

## 🔗 Live API
- 🌐 **Website**: https://verify-mail.rabahdj.online
- 📖 **Docs**: https://verify-mail.rabahdj.online/docs  
- 🏪 **RapidAPI**: https://rapidapi.com/rabahdjebbes6-VpFXFzqdF1R/api/email-validation-api32

## 🚀 Quick Start

```bash
curl -X POST https://verify-mail.rabahdj.online/validate/email \
  -H "Content-Type: application/json" \
  -d '{"email": "test@gmail.com"}'
📊 Response
json
{"valid": true, "score": 0.9, "checks": {"syntax": true, "mx": [], "disposable": false}}
By Rabah Djebbes - Automation Engineering
⭐ Star if useful!