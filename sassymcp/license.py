"""SassyMCP License — Offline-first tier gating with HMAC-signed keys.

License keys are HMAC-SHA256 signed JSON payloads. Validated locally on startup.
Optional weekly online check handles Stripe cancellations.

Tiers:
  free      — core, meta, github_quick, persona, setup (22 tools)
  pro       — free + all productivity/automation groups (255 tools)
  forensics — security_audit, registry (additive, stacks with any tier)
"""

import base64
import hashlib
import hmac
import json
import logging
import os
import time
from pathlib import Path

logger = logging.getLogger("sassymcp.license")

LICENSE_FILE = Path.home() / ".sassymcp" / "license.json"
VALIDATE_URL = "https://sassyconsultingllc.com/api/license/validate"

_SIGNING_SECRET = os.environ.get("SASSYMCP_LICENSE_SECRET", "sassy-mcp-v1-signing-key-change-me")

TIER_GROUPS = {
    "free": [
        "core", "meta", "github_quick", "persona", "setup",
    ],
    "pro": [
        "core", "meta", "github_quick", "persona", "setup",
        "infrastructure", "utility", "selfmod", "memory",
        "github_full", "android", "v020", "linux", "system",
    ],
    "forensics": [
        "security_audit_full", "registry_full",
    ],
}

ALWAYS_ALLOWED = {"core", "meta", "github_quick", "persona", "setup"}


def _sign_payload(payload: dict) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hmac.new(
        _SIGNING_SECRET.encode(), canonical.encode(), hashlib.sha256
    ).hexdigest()


def _verify_signature(payload: dict, signature: str) -> bool:
    expected = _sign_payload(payload)
    return hmac.compare_digest(expected, signature)


def generate_license_key(email: str, tier: str, days_valid: int = 30) -> dict:
    payload = {
        "email": email,
        "tier": tier,
        "created": time.time(),
        "expires": time.time() + (days_valid * 86400),
    }
    signature = _sign_payload(payload)
    key_data = {
        **payload,
        "signature": signature,
    }
    key_b64 = base64.urlsafe_b64encode(json.dumps(key_data).encode()).decode()
    return {
        "key": f"sassy_{tier}_{key_b64}",
        "raw": key_data,
    }


def parse_license_key(key_string: str) -> dict | None:
    try:
        parts = key_string.split("_", 2)
        if len(parts) != 3 or parts[0] != "sassy":
            return None
        b64_data = parts[2]
        raw = json.loads(base64.urlsafe_b64decode(b64_data + "=="))
        return raw
    except Exception:
        return None


def validate_license(key_string: str = None) -> dict:
    if key_string is None:
        if not LICENSE_FILE.exists():
            return {"valid": False, "tier": "free", "reason": "no_license_file"}
        try:
            data = json.loads(LICENSE_FILE.read_text())
            key_string = data.get("key", "")
        except Exception:
            return {"valid": False, "tier": "free", "reason": "corrupt_license_file"}

    parsed = parse_license_key(key_string)
    if not parsed:
        return {"valid": False, "tier": "free", "reason": "invalid_key_format"}

    signature = parsed.pop("signature", "")
    email = parsed.get("email", "")
    tier = parsed.get("tier", "free")
    expires = parsed.get("expires", 0)

    if not _verify_signature(parsed, signature):
        return {"valid": False, "tier": "free", "reason": "invalid_signature"}

    if expires < time.time():
        return {"valid": False, "tier": "free", "email": email, "reason": "expired",
                "expired_at": expires}

    return {"valid": True, "tier": tier, "email": email, "expires": expires}


def save_license(key_string: str) -> dict:
    result = validate_license(key_string)
    if not result["valid"]:
        return result

    LICENSE_FILE.parent.mkdir(parents=True, exist_ok=True)
    LICENSE_FILE.write_text(json.dumps({
        "key": key_string,
        "email": result.get("email", ""),
        "tier": result["tier"],
        "expires": result["expires"],
        "activated_at": time.time(),
    }, indent=2))

    logger.info(f"License activated: tier={result['tier']}, email={result.get('email')}")
    return result


def remove_license():
    if LICENSE_FILE.exists():
        LICENSE_FILE.unlink()
        logger.info("License removed — downgraded to free tier")


def get_allowed_groups() -> set[str]:
    result = validate_license()
    tier = result.get("tier", "free")

    allowed = set(TIER_GROUPS.get("free", []))

    if result.get("valid") and tier in TIER_GROUPS:
        allowed.update(TIER_GROUPS[tier])

    if LICENSE_FILE.exists():
        try:
            data = json.loads(LICENSE_FILE.read_text())
            if data.get("forensics_key"):
                forensics_result = validate_license(data["forensics_key"])
                if forensics_result.get("valid"):
                    allowed.update(TIER_GROUPS.get("forensics", []))
        except Exception:
            pass

    logger.info(f"License tier: {tier} ({'valid' if result.get('valid') else 'free'}) — {len(allowed)} groups allowed")
    return allowed


async def weekly_validation_check():
    if not LICENSE_FILE.exists():
        return

    try:
        data = json.loads(LICENSE_FILE.read_text())
        key = data.get("key", "")
        last_check = data.get("last_online_check", 0)

        if time.time() - last_check < 604800:
            return

        import httpx
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(VALIDATE_URL, params={"key": key})
        if resp.status_code == 200:
            remote = resp.json()
            if not remote.get("valid"):
                logger.warning(f"Remote license check failed: {remote.get('reason')}")
                if remote.get("reason") == "revoked":
                    remove_license()
                    logger.warning("License revoked by server — downgraded to free tier")

        data["last_online_check"] = time.time()
        LICENSE_FILE.write_text(json.dumps(data, indent=2))

    except Exception as e:
        logger.debug(f"Weekly license check failed (non-fatal): {e}")
