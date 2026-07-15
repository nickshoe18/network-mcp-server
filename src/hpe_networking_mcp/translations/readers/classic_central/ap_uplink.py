"""Classic Central → canonical AP-uplink reader.

Confirmed against the real New Central config-model schema
(``platforms/central/_config_payload_schemas.json``, schema key
``ap-uplink``; also exposed as ``central_get_ap_uplink`` /
``central_manage_ap_uplink`` in ``platforms/central/tools/interfaces.py``):
a library ``ap-uplinks/{name}`` object with a ``preemption {enable,
interval}`` block and a ``failover {enable, ip, pkt-lost-cnt,
pkt-send-freq, timeout, vpn-timeout}`` block -- both present, under
slightly different names, in Instant's ``uplink`` block:

    uplink
      preemption
      enforce none
      failover-internet-pkt-lost-cnt 10
      failover-internet-pkt-send-freq 30
      failover-vpn-timeout 180

Reuses ``CanonicalCentralProfile`` + the existing generic
``central_write_profile`` writer -- same shape as the skeletal-role kind,
no new writer needed. ``ap-uplinks`` is a bare library resource with no
name of its own in the source (Instant's ``uplink`` block takes no
arguments), so the caller supplies one.

Not mapped: Instant's top-level ``enforce none`` doesn't correspond to
any top-level ``ap-uplink`` field in the confirmed schema (``enforce`` only
appears nested under ``ethernet-1``/``ethernet-2``/``lte-modem``, which
this reader doesn't attempt to populate since Instant's uplink block
doesn't carry per-interface data) -- dropped rather than guessed.
"""

from __future__ import annotations

from typing import Any

from hpe_networking_mcp.translations.canonical.auth import CanonicalCentralProfile
from hpe_networking_mcp.translations.readers.classic_central._cli_parser import CliBlock, has_flag, prop_str

_AP_UPLINKS_PROFILE_TYPE = "ap-uplinks"


def classic_central_read_ap_uplink(uplink: CliBlock, *, name: str) -> CanonicalCentralProfile:
    """Build a Central ``ap-uplink`` profile from one Instant ``uplink`` block.

    Args:
        uplink: a block with ``keyword == "uplink"``.
        name: the profile name -- Instant's ``uplink`` block is bare
            (no args), so the caller must supply one (e.g. the group name).
    """
    body: dict[str, Any] = {"name": name}

    if has_flag(uplink, "preemption"):
        body["preemption"] = {"enable": True}

    failover: dict[str, Any] = {}
    pkt_lost = prop_str(uplink, "failover-internet-pkt-lost-cnt")
    pkt_freq = prop_str(uplink, "failover-internet-pkt-send-freq")
    vpn_timeout = prop_str(uplink, "failover-vpn-timeout")
    if pkt_lost:
        failover["pkt-lost-cnt"] = int(pkt_lost)
    if pkt_freq:
        failover["pkt-send-freq"] = int(pkt_freq)
    if vpn_timeout:
        failover["vpn-timeout"] = int(vpn_timeout)
    if failover:
        body["failover"] = failover

    return CanonicalCentralProfile(kind="ap_uplink", profile_type=_AP_UPLINKS_PROFILE_TYPE, name=name, body=body)
