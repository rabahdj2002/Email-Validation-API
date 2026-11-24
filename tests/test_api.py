import smtplib
from types import SimpleNamespace

import dns.resolver
import pytest
from fastapi.testclient import TestClient

import main

client = TestClient(main.app)


@pytest.fixture
def dns_records(monkeypatch):
    """Fake MX lookups: map domain -> list of MX hosts (missing domain -> no MX)."""
    records = {}
    monkeypatch.setattr(main, "resolve_mx", lambda domain: records.get(domain, []))
    return records


@pytest.fixture
def smtp_reply(monkeypatch):
    reply = {"code": "250", "calls": 0}

    def fake(email, hosts):
        reply["calls"] += 1
        return reply["code"]

    monkeypatch.setattr(main, "smtp_check", fake)
    return reply


def validate(email, depth="basic"):
    return client.post("/validate", json={"email": email, "depth": depth})


def test_ping():
    body = client.get("/ping").json()
    assert body["status"] == "ok" and body["version"] == main.app.version


def test_home_and_docs_render():
    assert client.get("/").status_code == 200
    assert client.get("/docs").status_code == 200


def test_valid_domain_basic(dns_records, smtp_reply):
    dns_records["example.com"] = ["mx1.example.com"]
    body = validate("ana@example.com").json()
    assert body == {
        "valid": True, "score": 0.8, "suggestion": None,
        "checks": {"syntax": True, "mx": ["mx1.example.com"], "smtp": None, "disposable": False},
    }
    assert smtp_reply["calls"] == 0


def test_domain_without_mx_is_invalid(dns_records):
    body = validate("ana@no-mail.example").json()
    assert body["valid"] is False and body["score"] == 0.4 and body["checks"]["mx"] == []


@pytest.mark.parametrize("payload", [{"email": "not-an-email"}, {"email": "a@b.com", "depth": "deep"}, {}])
def test_bad_input_is_422(payload):
    assert client.post("/validate", json=payload).status_code == 422


def test_full_mode_accepted_mailbox(dns_records, smtp_reply):
    dns_records["example.com"] = ["mx1.example.com"]
    body = validate("ana@example.com", "full").json()
    assert body["score"] == 1.0 and body["checks"]["smtp"] == "250"


def test_full_mode_rejected_mailbox_is_invalid(dns_records, smtp_reply):
    dns_records["example.com"] = ["mx1.example.com"]
    smtp_reply["code"] = "550"
    body = validate("ghost@example.com", "full").json()
    assert body["valid"] is False and body["checks"]["smtp"] == "550"


def test_full_mode_unreachable_smtp_keeps_basic_result(dns_records, smtp_reply):
    dns_records["example.com"] = ["mx1.example.com"]
    smtp_reply["code"] = main.SMTP_UNAVAILABLE
    body = validate("ana@example.com", "full").json()
    assert body["valid"] is True and body["score"] == 0.8


def test_disposable_scores_zero_even_in_full_mode(dns_records, smtp_reply):
    dns_records["yopmail.com"] = ["mx.yopmail.com"]
    body = validate("x@yopmail.com", "full").json()
    assert body["valid"] is False and body["score"] == 0.0 and body["checks"]["disposable"] is True
    assert smtp_reply["calls"] == 0
    assert body["suggestion"] is None


def test_international_domain_is_looked_up_in_punycode(dns_records, smtp_reply):
    dns_records["xn--gieen-nqa.de"] = ["mx.xn--gieen-nqa.de"]
    dns_records["giessen.de"] = ["mx.giessen.de"]
    body = validate("ana@gießen.de", "full").json()
    assert body["checks"]["mx"] == ["mx.xn--gieen-nqa.de"] and body["checks"]["smtp"] == "250"


def test_non_ascii_mailbox_skips_smtp(dns_records, smtp_reply):
    dns_records["example.com"] = ["mx1.example.com"]
    body = validate("jösé@example.com", "full").json()
    assert body["checks"]["smtp"] == main.SMTP_UNAVAILABLE and body["valid"] is True
    assert smtp_reply["calls"] == 0


def test_typo_suggestion(dns_records):
    assert validate("ana@gmial.com").json()["suggestion"] == "gmail.com"
    dns_records["gmail.com"] = ["gmail-smtp-in.l.google.com"]
    assert validate("ana@gmail.com").json()["suggestion"] is None


def test_resolve_mx_orders_by_preference(monkeypatch):
    answers = [SimpleNamespace(preference=20, exchange="mx2.example.com."), SimpleNamespace(preference=5, exchange="mx1.example.com.")]
    monkeypatch.setattr(dns.resolver.Resolver, "resolve", lambda self, domain, rtype: answers)
    assert main.resolve_mx("example.com") == ["mx1.example.com", "mx2.example.com"]


def test_resolve_mx_handles_dns_errors(monkeypatch):
    def fail(self, domain, rtype):
        raise dns.resolver.NXDOMAIN()
    monkeypatch.setattr(dns.resolver.Resolver, "resolve", fail)
    assert main.resolve_mx("missing.example") == []


class FakeSMTP:
    reachable = {"mx2.example.com"}

    def __init__(self, host, port, timeout):
        if host not in self.reachable:
            raise OSError("connection refused")

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def helo(self, name):
        pass

    def mail(self, sender):
        pass

    def rcpt(self, email):
        return 250, b"OK"


def test_smtp_check_falls_back_to_next_mx(monkeypatch):
    monkeypatch.setattr(smtplib, "SMTP", FakeSMTP)
    assert main.smtp_check("ana@example.com", ["mx1.example.com", "mx2.example.com"]) == "250"


def test_smtp_check_reports_unavailable_instead_of_rejected(monkeypatch):
    monkeypatch.setattr(smtplib, "SMTP", FakeSMTP)
    assert main.smtp_check("ana@example.com", ["mx1.example.com"]) == main.SMTP_UNAVAILABLE
