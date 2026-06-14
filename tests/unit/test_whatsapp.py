"""Tests for the WhatsApp adapter's HMAC signature verification."""
import os
import sys

# Put the whatsapp_adapter service on sys.path FIRST.
_HERE = os.path.dirname(os.path.abspath(__file__))
_SERVICE_ROOT = os.path.abspath(os.path.join(_HERE, "..", "..", "..", "services", "whatsapp_adapter"))
if _SERVICE_ROOT not in sys.path:
    sys.path.insert(0, _SERVICE_ROOT)

from app.services.inbound_service import verify_signature


def test_verify_signature_no_secret_allows_all():
    body = b'{"k":"v"}'
    sig = "anything"
    assert verify_signature(body, sig, "") is True


def test_verify_signature_correct():
    import hmac, hashlib
    secret = "topsecret"
    body = b'{"k":"v"}'
    expected = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    assert verify_signature(body, expected, secret) is True


def test_verify_signature_incorrect():
    assert verify_signature(b"hello", "deadbeef", "topsecret") is False


def test_verify_signature_empty_signature_with_secret():
    assert verify_signature(b"hello", "", "topsecret") is False
