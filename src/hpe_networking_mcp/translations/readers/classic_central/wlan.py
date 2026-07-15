"""Classic Central → canonical WLAN reader.

Builds a ``CanonicalWlan`` from one ``wlan ssid-profile`` block plus the
``wlan auth-server`` blocks it references by name (joined here, same
pattern as the AOS 8 reader's virtual_ap → ssid_prof/aaa_prof/server_group
join). Unlike AOS 8, Instant's ssid-profile is already the merged
essid+opmode+auth-server record -- no separate profile-join step needed
for those fields.

Bridged-only (confirmed for this deployment): ``forward`` is always
``ForwardMode.BRIDGED``, no gateway-cluster/tunnel resolution attempted.

Secrets: the API pre-masks ``wpa-passphrase``/``key`` as literal
``"********"`` -- this reader always treats that literal as "not
available" (``None``), never propagates it as a real secret. Operators
must set the real PSK/shared-secret manually post-migration; there is no
way to recover it from this source.

Known gaps (not modeled -- reasonable field mappings weren't confirmed,
so they're left at the canonical model's defaults rather than guessed):
Isolation/Rates/Wmm nuances, RF-band selection, RadSec-specific transport
settings. Revisit if/when a real Central push surfaces a concrete need.
"""

from __future__ import annotations

from hpe_networking_mcp.translations.canonical.wlan import (
    AuthSource,
    AuthSourceKind,
    CanonicalWlan,
    Cipher,
    CoaServer,
    FastRoam,
    ForwardMode,
    KeyMgmt,
    Performance,
    RadiusConfig,
    RadiusServer,
    Security,
    Vlan,
    VlanMode,
    WpaVersion,
)
from hpe_networking_mcp.translations.readers.classic_central._cli_parser import CliBlock, has_flag, prop_all, prop_str

_MASKED = "********"

# Instant ssid-profile opmode -> neutral (key_mgmt, wpa_version, cipher) triplet.
# Same underlying ArubaOS vocabulary as AOS 8's table (readers/aos8/wlan.py) --
# kept as its own copy since the two source platforms' reader modules are
# independent and this project doesn't share tables cross-platform.
_OPMODE_TO_TRIPLET: dict[str, tuple[KeyMgmt, WpaVersion, Cipher]] = {
    "opensystem": (KeyMgmt.OPEN, WpaVersion.NONE, Cipher.NONE),
    "enhanced-open": (KeyMgmt.OWE, WpaVersion.NONE, Cipher.NONE),
    "static-wep": (KeyMgmt.WEP_STATIC, WpaVersion.NONE, Cipher.WEP),
    "dynamic-wep": (KeyMgmt.WEP_DYNAMIC, WpaVersion.NONE, Cipher.WEP),
    "wpa-aes": (KeyMgmt.ENTERPRISE, WpaVersion.WPA, Cipher.AES_CCM),
    "wpa-tkip": (KeyMgmt.ENTERPRISE, WpaVersion.WPA, Cipher.TKIP),
    "wpa-psk-aes": (KeyMgmt.PSK, WpaVersion.WPA, Cipher.AES_CCM),
    "wpa-psk-tkip": (KeyMgmt.PSK, WpaVersion.WPA, Cipher.TKIP),
    "wpa2-aes": (KeyMgmt.ENTERPRISE, WpaVersion.WPA2, Cipher.AES_CCM),
    "wpa2-tkip": (KeyMgmt.ENTERPRISE, WpaVersion.WPA2, Cipher.TKIP),
    "wpa2-psk-aes": (KeyMgmt.PSK, WpaVersion.WPA2, Cipher.AES_CCM),
    "wpa2-psk-tkip": (KeyMgmt.PSK, WpaVersion.WPA2, Cipher.TKIP),
    "wpa3-sae-aes": (KeyMgmt.SAE, WpaVersion.WPA3, Cipher.AES_CCM),
    "wpa3-aes-ccm-128": (KeyMgmt.ENTERPRISE, WpaVersion.WPA3, Cipher.AES_CCM),
    "wpa3-aes-gcm-256": (KeyMgmt.ENTERPRISE, WpaVersion.WPA3, Cipher.GCM_256),
    "wpa3-cnsa": (KeyMgmt.ENTERPRISE, WpaVersion.WPA3, Cipher.CNSA),
    "mpsk-aes": (KeyMgmt.MPSK, WpaVersion.WPA2, Cipher.AES_CCM),
}

_DEFAULT_AUTH_PORT = 1812
_DEFAULT_ACCT_PORT = 1813
_DEFAULT_COA_PORT = 3799


def _unmask(value: str | None) -> str | None:
    """Never propagate the API's own redaction literal as a real secret."""
    if value is None or value == _MASKED:
        return None
    return value


def _radius(auth_server_names: list[str], auth_servers_by_name: dict[str, CliBlock]) -> RadiusConfig | None:
    auth: list[RadiusServer] = []
    acct: list[RadiusServer] = []
    coa: list[CoaServer] = []
    for name in auth_server_names:
        block = auth_servers_by_name.get(name)
        if block is None:
            continue
        host = prop_str(block, "ip") or ""
        secret = _unmask(prop_str(block, "key"))
        auth_port = prop_str(block, "port")
        auth.append(RadiusServer(host=host, port=int(auth_port) if auth_port else _DEFAULT_AUTH_PORT, secret=secret))
        acct_port = prop_str(block, "acctport")
        if acct_port:
            acct.append(RadiusServer(host=host, port=int(acct_port), secret=secret))
        if has_flag(block, "rfc3576"):
            coa_port = prop_str(block, "cppm-rfc3576-port")
            coa.append(CoaServer(ip=host, port=int(coa_port) if coa_port else _DEFAULT_COA_PORT, secret=secret))
    if not (auth or acct or coa):
        return None
    return RadiusConfig(auth_servers=auth, acct_servers=acct, coa=coa)


def _security(ssid: CliBlock, auth_servers_by_name: dict[str, CliBlock]) -> Security:
    opmode = prop_str(ssid, "opmode") or "opensystem"
    km, wpa, cipher = _OPMODE_TO_TRIPLET.get(opmode, (KeyMgmt.OPEN, WpaVersion.NONE, Cipher.NONE))
    sec = Security(key_mgmt=km, wpa_version=wpa, cipher=cipher)

    if km in (KeyMgmt.PSK, KeyMgmt.SAE):
        sec.psk = _unmask(prop_str(ssid, "wpa-passphrase"))

    auth_server_names = [v[0] for v in prop_all(ssid, "auth-server") if v]
    if km == KeyMgmt.ENTERPRISE and auth_server_names:
        sec.auth_source = AuthSource(kind=AuthSourceKind.RADIUS_GROUP, ref=auth_server_names[0])
        sec.radius = _radius(auth_server_names, auth_servers_by_name)
    return sec


def _vlan(ssid: CliBlock) -> Vlan:
    name = prop_str(ssid, "vlan")
    if not name:
        return Vlan(mode=VlanMode.NONE)
    return Vlan(mode=VlanMode.NAMED, name=name)


def classic_central_read_wlan(
    ssid: CliBlock,
    *,
    auth_servers: list[CliBlock] | None = None,
) -> CanonicalWlan:
    """Build a ``CanonicalWlan`` from one ``wlan ssid-profile`` block.

    Args:
        ssid: a block with ``keyword == "wlan ssid-profile"``.
        auth_servers: candidate ``wlan auth-server`` blocks from the same
            group config (joined by name via the ssid's ``auth-server``
            property/-ies).
    """
    as_by_name = {b["args"][0]: b for b in (auth_servers or []) if b.get("args")}

    essid = prop_str(ssid, "essid") or (ssid.get("args") or [""])[0]
    profile_name = (ssid.get("args") or [essid])[0]
    captive_portal = prop_str(ssid, "captive-portal")

    return CanonicalWlan(
        ssid=essid,
        profile_name=profile_name,
        enabled=has_flag(ssid, "enable"),
        security=_security(ssid, as_by_name),
        vlan=_vlan(ssid),
        performance=Performance(
            dtim=int(v) if (v := prop_str(ssid, "dtim-period")) else None,
            max_clients=int(v) if (v := prop_str(ssid, "max-clients-threshold")) else None,
            idle_timeout=int(v) if (v := prop_str(ssid, "inactivity-timeout")) else None,
            fast_roam=FastRoam.DOT11R if has_flag(ssid, "dot11r") else FastRoam.NONE,
        ),
        forward=ForwardMode.BRIDGED,
        portal_deferred=bool(captive_portal and captive_portal != "disable"),
    )
