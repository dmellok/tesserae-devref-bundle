"""devref_egress, worked example of the network-egress capability.

The manifest declares ``requires: ["network:api.github.com"]`` so the
host's socket hook (see ``app/capabilities.py``) allows connections to
that one host and refuses every other. The widget's demo option flips
between an allowed URL and one pointed at a different host so a
reviewer can see both the happy path and the ``CapabilityDenied``
error surface in the cell renderer.

For widget authors reading this as a reference: the only thing you
need to do to opt into the contract is add the ``requires`` array.
You don't import the capability module, you don't wrap your fetches,
you don't pass any context. The host runs your ``fetch()`` inside a
scope that already knows your allowlist.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any

ALLOWED_URL = "https://api.github.com/zen"
DENIED_URL = "https://httpbin.org/uuid"

USER_AGENT = "tesserae/devref_egress (+contract demo)"


def _request(url: str) -> tuple[str, str | None]:
    """GET ``url`` with a short timeout, return ``(body, content_type)``.

    The function makes no attempt to handle CapabilityDenied
    specifically. Whatever the host raises, we let bubble out and the
    caller maps to a cell-level error so the gallery row reads as a
    real failure rather than a silent pass."""
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT}, method="GET")
    with urllib.request.urlopen(req, timeout=8) as resp:
        return resp.read().decode("utf-8", errors="replace"), resp.headers.get("Content-Type")


def fetch(
    options: dict[str, Any], settings: dict[str, Any], *, ctx: dict[str, Any]
) -> dict[str, Any]:
    del settings, ctx
    choice = options.get("demo_url") or "allowed"
    if choice == "denied":
        url = DENIED_URL
        scenario = "denied"
    else:
        url = ALLOWED_URL
        scenario = "allowed"

    try:
        body, ctype = _request(url)
    except urllib.error.HTTPError as err:
        return {
            "scenario": scenario,
            "url": url,
            "error": f"HTTP {err.code}: {err.reason}",
        }
    except Exception as err:
        return {
            "scenario": scenario,
            "url": url,
            "error": f"{type(err).__name__}: {err}",
        }

    payload: str
    if ctype and "json" in ctype.lower():
        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            payload = body
    else:
        payload = body.strip()

    return {
        "scenario": scenario,
        "url": url,
        "payload": payload,
    }
