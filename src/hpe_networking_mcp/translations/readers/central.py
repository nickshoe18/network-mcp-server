"""Central → canonical WLAN reader.

Inverts the Central ``wlan-ssids`` writer: reads a Central WLAN profile (as
returned by ``GET network-config/v1alpha1/wlan-ssids/{name}``) back into a
platform-neutral ``CanonicalWlan`` so it can be written to another platform
(e.g. Mist) by that platform's writer.

RADIUS is resolved by walking the referenced ``auth-server-group`` →
``server-group`` → ``auth-servers`` (supplied as reader context), so the canonical
carries the actual servers — the Mist writer needs them inline. An
``auth-server-address`` that matches a defined ``ALIAS_AUTH_SERVER_ADDRESS`` alias
is mapped back to a ``{{var}}`` host. Assignment is rebuilt from the WLAN's
``config-assignments`` (context) via scope-id → name/type.
"""

from __future__ import annotations

import re
from typing import Any

from hpe_networking_mcp.translations.canonical.wlan import (
    Assignment,
    AuthSource,
    AuthSourceKind,
    CanonicalWlan,
    Cipher,
    CoaServer,
    FastRoam,
    ForwardMode,
    Isolation,
    KeyMgmt,
    MpskSource,
    Performance,
    RadiusConfig,
    RadiusServer,
    Rates,
    Security,
    Vlan,
    VlanMode,
    Wmm,
    WpaVersion,
)

# Central opmode enum → neutral (key_mgmt, wpa_version, cipher) triplet.
_OPMODE_TO_TRIPLET: dict[str, tuple[KeyMgmt, WpaVersion, Cipher]] = {
    "OPEN": (KeyMgmt.OPEN, WpaVersion.NONE, Cipher.NONE),
    "ENHANCED_OPEN": (KeyMgmt.OWE, WpaVersion.NONE, Cipher.NONE),
    "STATIC_WEP": (KeyMgmt.WEP_STATIC, WpaVersion.NONE, Cipher.WEP),
    "DYNAMIC_WEP": (KeyMgmt.WEP_DYNAMIC, WpaVersion.NONE, Cipher.WEP),
    "WPA_PERSONAL": (KeyMgmt.PSK, WpaVersion.WPA, Cipher.AES_CCM),
    "WPA2_PERSONAL": (KeyMgmt.PSK, WpaVersion.WPA2, Cipher.AES_CCM),
    "BOTH_WPA_WPA2_PSK": (KeyMgmt.PSK, WpaVersion.WPA_WPA2, Cipher.AES_CCM),
    "WPA3_SAE": (KeyMgmt.SAE, WpaVersion.WPA3, Cipher.AES_CCM),
    "WPA_ENTERPRISE": (KeyMgmt.ENTERPRISE, WpaVersion.WPA, Cipher.AES_CCM),
    "WPA2_ENTERPRISE": (KeyMgmt.ENTERPRISE, WpaVersion.WPA2, Cipher.AES_CCM),
    "BOTH_WPA_WPA2_DOT1X": (KeyMgmt.ENTERPRISE, WpaVersion.WPA_WPA2, Cipher.AES_CCM),
    "WPA3_ENTERPRISE_CCM_128": (KeyMgmt.ENTERPRISE, WpaVersion.WPA3, Cipher.AES_CCM),
    "WPA3_ENTERPRISE_GCM_256": (KeyMgmt.ENTERPRISE, WpaVersion.WPA3, Cipher.GCM_256),
    "WPA3_ENTERPRISE_CNSA": (KeyMgmt.ENTERPRISE, WpaVersion.WPA3, Cipher.CNSA),
    "WPA2_MPSK_AES": (KeyMgmt.MPSK, WpaVersion.WPA2, Cipher.AES_CCM),
    "WPA2_MPSK_LOCAL": (KeyMgmt.MPSK, WpaVersion.WPA2, Cipher.AES_CCM),
}

_FORWARD_FROM_CENTRAL = {
    "FORWARD_MODE_BRIDGE": ForwardMode.BRIDGED,
    "FORWARD_MODE_L2": ForwardMode.TUNNELED,
    "FORWARD_MODE_MIXED": ForwardMode.HYBRID,
}

# Central legacy basic-rates → neutral per-band template (inverse of the writer).
_RATES_FROM_CENTRAL: dict[tuple[str, ...], str] = {
    ("RATE_1MB", "RATE_2MB"): "compatible",
    ("RATE_12MB",): "no-legacy",
    ("RATE_24MB",): "high-density",
}

# The Central system NAC server-group — a WLAN referencing it is NAC-backed.
_NAC_GROUPS = {"sys_central_nac"}

_IPV4 = re.compile(r"^\d{1,3}(\.\d{1,3}){3}$")


def _is_literal_host(addr: str) -> bool:
    """True if ``addr`` is an IP/FQDN literal (not an alias reference)."""
    if _IPV4.match(addr):
        return True
    # an FQDN has a dot and no spaces; a bare alias name typically has neither
    return "." in addr and " " not in addr


def _index(records: list[dict] | None, *keys: str) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for r in records or []:
        if not isinstance(r, dict):
            continue
        for k in keys:
            if r.get(k):
                out[r[k]] = r
                break
    return out


def _alias_names(aliases: list[dict] | None) -> set[str]:
    return {
        a["name"]
        for a in aliases or []
        if isinstance(a, dict) and a.get("name") and a.get("type") == "ALIAS_AUTH_SERVER_ADDRESS"
    }


def _host(addr: str | None, alias_names: set[str]) -> str:
    """Map an auth-server-address back to a literal or a ``{{var}}`` alias ref."""
    if not addr:
        return ""
    if addr in alias_names or not _is_literal_host(addr):
        return f"{{{{{addr}}}}}"
    return addr


def _radius(group_name: str, server_groups: dict, auth_servers: dict, alias_names: set[str]) -> RadiusConfig | None:
    group = server_groups.get(group_name)
    if not group:
        return None
    auth: list[RadiusServer] = []
    acct: list[RadiusServer] = []
    coa: list[CoaServer] = []
    for member in group.get("servers") or []:
        rec = auth_servers.get(member.get("server-name", ""))
        if not rec:
            continue
        host = _host(rec.get("auth-server-address"), alias_names)
        secret = (rec.get("shared-secret-config") or {}).get("plaintext-value")
        mode = rec.get("radius-server-mode", "AUTH_ONLY")
        if mode in ("AUTH_ONLY", "AUTH_AND_COA"):
            auth.append(RadiusServer(host=host, port=rec.get("auth-port"), secret=secret))
        if rec.get("acct-port"):
            acct.append(RadiusServer(host=host, port=rec.get("acct-port"), secret=secret))
        if rec.get("dynamic-authorization-enable") or mode in ("COA_ONLY", "AUTH_AND_COA"):
            coa.append(CoaServer(ip=host, port=rec.get("dynamic-authorization-port"), secret=secret))
    if not (auth or acct or coa):
        return None
    return RadiusConfig(auth_servers=auth, acct_servers=acct, coa=coa)


def _security(wlan: dict, server_groups: dict, auth_servers: dict, alias_names: set[str]) -> Security:
    km, wpa, cipher = _OPMODE_TO_TRIPLET.get(wlan.get("opmode", "OPEN"), (KeyMgmt.OPEN, WpaVersion.NONE, Cipher.NONE))
    sec = Security(key_mgmt=km, wpa_version=wpa, cipher=cipher)
    sec.wpa2_wpa3_transition = bool(wlan.get("wpa3-transition-mode-enable"))
    sec.mac_auth = bool(wlan.get("mac-authentication"))

    ps = wlan.get("personal-security") or {}
    if km in (KeyMgmt.PSK, KeyMgmt.SAE) and ps.get("wpa-passphrase"):
        sec.psk = ps["wpa-passphrase"]
    if km == KeyMgmt.MPSK:
        sec.mpsk_source = MpskSource.CLOUD if ps.get("mpsk-cloud-auth") else MpskSource.LOCAL

    group_name = wlan.get("auth-server-group")
    if km == KeyMgmt.ENTERPRISE or sec.mac_auth:
        if group_name in _NAC_GROUPS:
            sec.auth_source = AuthSource(kind=AuthSourceKind.NAC, ref=group_name)
        else:
            sec.auth_source = AuthSource(kind=AuthSourceKind.RADIUS_GROUP, ref=group_name)
            if group_name:
                sec.radius = _radius(group_name, server_groups, auth_servers, alias_names)
    return sec


def _vlan(wlan: dict) -> Vlan:
    sel = wlan.get("vlan-selector")
    if sel == "NAMED_VLAN" and wlan.get("vlan-name"):
        return Vlan(mode=VlanMode.NAMED, name=wlan["vlan-name"])
    if sel == "VLAN_RANGES":
        rng = wlan.get("vlan-id-range") or []
        if rng:
            try:
                return Vlan(mode=VlanMode.ID, id=int(str(rng[0])))
            except (ValueError, TypeError):
                return Vlan(mode=VlanMode.NONE)
    return Vlan(mode=VlanMode.NONE)


def _rates(wlan: dict) -> Rates:
    def tmpl(key: str) -> str | None:
        rates = tuple((wlan.get(key) or {}).get("basic-rates") or [])
        return _RATES_FROM_CENTRAL.get(rates)

    return Rates(band_24=tmpl("g-legacy-rates"), band_5=tmpl("a-legacy-rates"))


def _assignment(profile: str, assignments: list[dict] | None) -> Assignment:
    a = Assignment()
    for row in assignments or []:
        if row.get("profile-type") != "wlan-ssids" or row.get("profile-instance") != profile:
            continue
        st = row.get("scope-type")
        name = row.get("scope-name")
        if st == "GLOBAL":
            a.org_wide = True
        elif st == "SITE" and name:
            a.sites.append(name)
        elif st == "SITE_COLLECTION" and name:
            a.site_collections.append(name)
        elif st == "DEVICE_COLLECTION" and name:
            a.device_groups.append(name)
    return a


def central_read_wlan(
    wlan: dict[str, Any],
    *,
    server_groups: list[dict] | None = None,
    auth_servers: list[dict] | None = None,
    aliases: list[dict] | None = None,
    assignments: list[dict] | None = None,
) -> CanonicalWlan:
    """Build a ``CanonicalWlan`` from a Central ``wlan-ssids`` profile + context.

    Args:
        wlan: the Central WLAN body (``GET .../wlan-ssids/{name}``).
        server_groups: Central ``server-groups`` records (for the RADIUS walk).
        auth_servers: Central ``auth-servers`` records (host/secret/ports).
        aliases: Central ``aliases`` records (to detect ``{{var}}`` hosts).
        assignments: this profile's ``config-assignments`` rows (scope-name/-type).
    """
    sg_by = _index(server_groups, "name")
    as_by = _index(auth_servers, "name")
    alias_names = _alias_names(aliases)

    essid_obj = wlan.get("essid") or {}
    ssid = essid_obj.get("alias") if essid_obj.get("use-alias") else essid_obj.get("name")
    profile = wlan.get("ssid") or ssid or ""

    p = Performance(
        dtim=wlan.get("dtim-period"),
        max_clients=wlan.get("max-clients-threshold"),
        idle_timeout=wlan.get("inactivity-timeout"),
        fast_roam=FastRoam.DOT11R if wlan.get("dot11r") else FastRoam.NONE,
    )
    eht = wlan.get("extremely-high-throughput")
    if isinstance(eht, dict) and "enable" in eht:
        p.wifi7_11be = bool(eht["enable"])

    return CanonicalWlan(
        ssid=ssid or profile,
        profile_name=profile,
        enabled=bool(wlan.get("enable", True)),
        hidden=bool(wlan.get("hide-ssid", False)),
        security=_security(wlan, sg_by, as_by, alias_names),
        vlan=_vlan(wlan),
        rates=_rates(wlan),
        performance=p,
        isolation=Isolation(
            client_isolation=bool(wlan.get("client-isolation", False)),
            limit_bcast=bool(wlan.get("deny-inter-user-bridging", False)),
            arp_filter=wlan.get("broadcast-filter-ipv4") == "BCAST_FILTER_ARP",
        ),
        wmm=Wmm(
            enabled=bool((wlan.get("wmm-cfg") or {}).get("enable", True)),
            uapsd=bool((wlan.get("wmm-cfg") or {}).get("uapsd", True)),
        ),
        forward=_FORWARD_FROM_CENTRAL.get(wlan.get("forward-mode", "FORWARD_MODE_BRIDGE"), ForwardMode.BRIDGED),
        assignment=_assignment(profile, assignments),
    )
