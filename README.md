# Email Validation API 🚀

[![Live](https://img.shields.io/badge/Live-brightgreen)](https://verify-mail.rabahdj.online)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-blue?logo=fastapi)](https://fastapi.tiangolo.com)
[![RapidAPI](https://img.shields.io/badge/RapidAPI-listed-0055DA)](https://rapidapi.com/rabahdjebbes6-VpFXFzqdF1R/api/email-validation-api32)
[![License: MIT](https://img.shields.io/badge/License-MIT-green)](LICENSE)

![Email Validation API](docs/thumbnail.png)

**A production email validation API that checks syntax, MX records, SMTP deliverability and disposable domains, and returns a confidence score.**
Use it to block fake and throwaway sign-ups, clean mailing lists and reduce bounce rates.

## 🔗 Live

- 🌐 **Website**: https://verify-mail.rabahdj.online
- 📖 **Interactive docs (Swagger)**: https://verify-mail.rabahdj.online/docs
- 🏪 **RapidAPI**: https://rapidapi.com/rabahdjebbes6-VpFXFzqdF1R/api/email-validation-api32

## ✨ Checks

| Check | What it does | Score |
|---|---|---|
| Syntax | Validates the address format | +0.4 |
| MX records | Confirms the domain can receive email (DNS lookup) | +0.4 |
| SMTP (`full` mode) | Asks the mail server whether the mailbox exists | +0.2 |
| Disposable | Flags known throwaway domains (Mailinator, YOPmail, …) | score set to 0 |

An address is `valid` when its score is **≥ 0.6**.

## 📡 Usage

**`POST /validate`**

```bash
curl -X POST https://verify-mail.rabahdj.online/validate \
  -H "Content-Type: application/json" \
  -d '{"email": "john@example.com", "depth": "full"}'
```

`depth` is `basic` (syntax + MX + disposable, fast) or `full` (adds the SMTP check).

**Response**

```json
{
  "valid": true,
  "score": 1.0,
  "checks": {
    "syntax": true,
    "mx": ["mx1.example.com."],
    "smtp": "250",
    "disposable": false
  },
  "suggestion": null
}
```

**`GET /ping`** returns service status and version.

## 🛠️ Run locally

```bash
pip install -r requirements.txt
python main.py            # serves on http://localhost:8001
```

Open http://localhost:8001/docs for the interactive API docs.

## 🧱 Tech stack

Python · FastAPI · Pydantic · dnspython · smtplib · Uvicorn

## 👨‍💻 Author

**Rabah Djebbes** – Software & Automation Engineer
[LinkedIn](https://www.linkedin.com/in/rabahdjebbes) · [GitHub](https://github.com/rabahdj2002) · Rabahwork@gmail.com

## 📄 License

MIT – see [LICENSE](LICENSE).
