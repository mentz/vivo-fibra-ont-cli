"""Small, model-independent helpers for the HTML served by ONT web UIs.

The helpers deliberately avoid a full HTML parser: the CGIs emit stable,
hand-written markup and the original tool already matched it with regular
expressions. Keeping the helpers here lets model modules share them without
depending on each other.
"""

from __future__ import annotations

import html
import re


def form_block(page: str, form_name: str) -> str:
    """Return the markup of ``<form name="form_name">...</form>``."""
    m = re.search(
        rf'<form[^>]*name="{re.escape(form_name)}".*?</form>',
        page, re.S | re.I,
    )
    return m.group(0) if m else ""


def select_block(page: str, select_id: str) -> str:
    m = re.search(
        rf'<select[^>]*id="{re.escape(select_id)}"[^>]*>(.*?)</select>',
        page, re.S | re.I,
    )
    return m.group(1) if m else ""


def selected_value(page: str, select_id: str) -> str | None:
    block = select_block(page, select_id)
    m = re.search(r'<option[^>]*value="([^"]*)"[^>]*\bselected\b', block, re.I)
    if m:
        return html.unescape(m.group(1))
    m = re.search(r'<option[^>]*\bselected\b[^>]*value="([^"]*)"', block, re.I)
    return html.unescape(m.group(1)) if m else None


def input_value(page: str, input_id: str) -> str | None:
    m = re.search(
        rf'<input[^>]*id="{re.escape(input_id)}"[^>]*value="([^"]*)"',
        page, re.I,
    )
    if not m:
        m = re.search(
            rf'<input[^>]*value="([^"]*)"[^>]*id="{re.escape(input_id)}"',
            page, re.I,
        )
    return html.unescape(m.group(1)) if m else None


def input_checked(page: str, name: str, value: str) -> bool:
    for m in re.finditer(rf'<input[^>]*name="{re.escape(name)}"[^>]*>', page, re.I):
        tag = m.group(0)
        if (re.search(rf'value="{re.escape(value)}"', tag, re.I)
                and re.search(r"\bchecked\b", tag, re.I)):
            return True
    return False


def radio_checked(page: str, form_name: str, radio_name: str, value: str) -> bool:
    block = form_block(page, form_name)
    if not block:
        return False
    m = re.search(
        rf'<input[^>]*name="{re.escape(radio_name)}"[^>]*value="{re.escape(value)}"[^>]*>',
        block, re.I,
    )
    return bool(m and re.search(r"\bchecked\b", m.group(0), re.I))


def js_var(page: str, name: str) -> str | None:
    m = re.search(rf'var\s+{re.escape(name)}\s*=\s*"([^"]*)"', page)
    return m.group(1) if m else None


def public_key(page: str) -> str:
    m = re.search(
        r'ID="PublicKey" value="(-----BEGIN PUBLIC KEY-----.*?-----END PUBLIC KEY-----)"',
        page, re.S,
    )
    if not m:
        raise RuntimeError("public key not found in wireless page")
    return m.group(1)
