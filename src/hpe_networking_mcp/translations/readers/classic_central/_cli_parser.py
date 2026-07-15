"""Generic Aruba Instant/IAP CLI-line parser for Classic Central group config.

``GET /configuration/v1/ap_cli/{group_name}`` (see
``platforms/classic_central/tools/group_config.py``) returns a group's entire
shared config as an array of CLI-style text lines: a 2-space indentation
level distinguishes a block header (e.g. ``vlan Users 60``,
``wlan ssid-profile "Wayne Enterprises"``) from its properties (e.g.
``  max-tx-power 19``, repeated ``  rule ...`` lines).

This parser is deliberately generic — it groups lines into blocks by shape
alone (indentation + a keyword-prefix table), not by hardcoding any
tenant's specific profile/VLAN/role names. A block whose keyword isn't in
the multi-word prefix table below still parses cleanly (falls back to a
single-word keyword) — it just won't match any per-kind reader's filter,
which is the correct behavior for constructs intentionally out of scope
(e.g. Hotspot 2.0/Passpoint, IoT radio profiles) or genuinely unknown
config this parser has never seen. Every real construct observed across
two independent groups in the source tenant ("Wayne Enterprises" — 359
lines — and "default" — 103 lines) parses correctly with this shape;
that variety (not just one config sample) is what "generic" is checked
against here — see the project memory for a full account.

Blocks are plain dicts (not a custom class) so they can flow unchanged as
``source_record`` across the MCP tool boundary into
``translate_config_preview``/``apply``, which require a JSON-serializable
``dict``.
"""

from __future__ import annotations

import shlex
from typing import Any, TypedDict

# Known multi-word command prefixes, longest first so e.g. "wlan access-list
# route" (3 words) is tried before "wlan access-rule" (2 words) would ever
# wrongly consume it. Anything not listed here falls back to a single-word
# keyword — safe degradation, not a parse failure.
_MULTI_WORD_PREFIXES: tuple[tuple[str, ...], ...] = tuple(
    sorted(
        [
            ("wlan", "access-list", "route"),
            ("wlan", "ssid-profile"),
            ("wlan", "auth-server"),
            ("wlan", "access-rule"),
            ("wlan", "mpsk-local"),
            ("wlan", "captive-portal"),
            ("wlan", "external-captive-portal"),
            ("rf", "dot11g-radio-profile"),
            ("rf", "dot11a-radio-profile"),
            ("rf", "dot11a-secondary-radio-profile"),
            ("rf", "dot11-6ghz-radio-profile"),
            ("hotspot", "anqp-nai-realm-profile"),
            ("hotspot", "anqp-venue-name-profile"),
            ("hotspot", "anqp-3gpp-profile"),
            ("hotspot", "anqp-ip-addr-avail-profile"),
            ("hotspot", "anqp-domain-name-profile"),
            ("hotspot", "h2qp-oper-name-profile"),
            ("hotspot", "hs-profile"),
            ("iot", "radio-profile"),
        ],
        key=len,
        reverse=True,
    )
)


class CliBlock(TypedDict):
    """One parsed CLI block. Plain dict shape -- JSON-serializable."""

    keyword: str
    args: list[str]
    properties: dict[str, list[list[str]]]


def _split_keyword(tokens: list[str]) -> tuple[str, list[str]]:
    for prefix in _MULTI_WORD_PREFIXES:
        n = len(prefix)
        if tuple(tokens[:n]) == prefix:
            return " ".join(prefix), tokens[n:]
    return tokens[0], tokens[1:]


def _tokenize(line: str) -> list[str]:
    """Quote-aware split -- ``shlex`` keeps ``"Wayne Enterprises"`` as one token."""
    try:
        return shlex.split(line.strip())
    except ValueError:
        # Unbalanced quotes (malformed/truncated line) -- fall back to a naive
        # split rather than dropping the line entirely.
        return line.strip().split()


def parse_cli_blocks(lines: list[str]) -> list[CliBlock]:
    """Parse an ``ap_cli`` line array into a list of generic CLI blocks.

    A non-indented line always starts a new block (even a bare flag like
    ``dpi`` or a scalar directive like ``ntp-server us.pool.ntp.org`` --
    those just end up with empty ``properties``). Every subsequent
    indented line becomes a property of the current block until the next
    non-indented line. Duplicate property keys (e.g. multiple ``rule``
    lines under one ``wlan access-rule`` block) are preserved in order,
    not overwritten -- ``properties`` maps each key to a list of
    value-token-lists.
    """
    blocks: list[CliBlock] = []
    current: CliBlock | None = None
    for raw_line in lines:
        if not raw_line.strip():
            continue
        if raw_line.startswith(" "):
            if current is None:
                continue  # indented line with no preceding header -- skip defensively
            tokens = _tokenize(raw_line)
            if not tokens:
                continue
            key, rest = tokens[0], tokens[1:]
            current["properties"].setdefault(key, []).append(rest)
        else:
            tokens = _tokenize(raw_line)
            if not tokens:
                continue
            keyword, args = _split_keyword(tokens)
            current = {"keyword": keyword, "args": args, "properties": {}}
            blocks.append(current)
    return blocks


def blocks_by_keyword(blocks: list[CliBlock], keyword: str) -> list[CliBlock]:
    """All blocks matching an exact keyword (e.g. ``'vlan'``, ``'wlan ssid-profile'``)."""
    return [b for b in blocks if b["keyword"] == keyword]


def prop(block: CliBlock, key: str, default: list[str] | None = None) -> list[str] | None:
    """First value-token-list for ``key`` on this block, or ``default``."""
    values = block["properties"].get(key)
    return values[0] if values else default


def prop_all(block: CliBlock, key: str) -> list[list[str]]:
    """Every value-token-list for ``key`` (repeatable properties like ``rule``)."""
    return block["properties"].get(key, [])


def has_flag(block: CliBlock, key: str) -> bool:
    """True if ``key`` appears as a property at all (bare flags like ``enable``)."""
    return key in block["properties"]


def prop_str(block: CliBlock, key: str, default: str | None = None) -> str | None:
    """Convenience: first token of the first value-list for ``key``, joined if quoted-multi-word."""
    values = prop(block, key)
    if values is None:
        return default
    return " ".join(values) if values else default


def as_dict(block: CliBlock) -> dict[str, Any]:
    """Identity helper -- ``CliBlock`` is already a plain dict; documents intent at call sites."""
    return dict(block)
