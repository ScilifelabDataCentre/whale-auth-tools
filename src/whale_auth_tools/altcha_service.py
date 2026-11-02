"""ALTCHA v2 challenge and verification helpers."""

from datetime import datetime, timedelta, timezone
import secrets

from altcha import create_challenge, verify_solution

from whale_auth_tools.settings import Settings


def generate_secrets() -> dict[str, str]:
    """Generate independent high-entropy HMAC secrets for ALTCHA v2."""

    return {
        "hmacSecret": secrets.token_urlsafe(48),
        "hmacKeySecret": secrets.token_urlsafe(48),
    }


def create_altcha_challenge(settings: Settings) -> dict:
    """Create an official signed ALTCHA v2 challenge for ALTCHA clients."""

    expires_at = datetime.now(timezone.utc) + timedelta(seconds=settings.altcha_ttl_seconds)
    challenge = create_challenge(
        algorithm=settings.altcha_algorithm,
        cost=settings.altcha_cost,
        expires_at=expires_at,
        hmac_secret=settings.altcha_hmac_secret,
        hmac_key_secret=settings.altcha_hmac_key_secret,
    )
    return challenge.to_dict()


def verify_altcha_payload(payload: str, settings: Settings) -> dict[str, bool | float | str | None]:
    """Verify a base64 ALTCHA v2 payload without logging its contents."""

    verification = verify_solution(
        payload,
        settings.altcha_hmac_secret,
        hmac_key_secret=settings.altcha_hmac_key_secret,
    )
    return {
        "verified": verification.verified,
        "expired": verification.expired,
        "invalidSignature": verification.invalid_signature,
        "invalidSolution": verification.invalid_solution,
        "time": verification.time,
        "error": verification.error,
    }
