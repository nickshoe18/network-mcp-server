"""Central → canonical reader tests.

Cover the opmode→triplet inverse, essid (literal + alias), VLAN, the RADIUS walk
(auth-server-group → server-group → auth-servers, incl. AUTH_AND_COA), the
alias→{{var}} host mapping, NAC detection (sys_central_nac), and assignment
rebuilt from config-assignment rows.
"""

from __future__ import annotations

import pytest

from hpe_networking_mcp.translations.canonical.wlan import (
    AuthSourceKind,
    Cipher,
    ForwardMode,
    KeyMgmt,
    MpskSource,
    VlanMode,
    WpaVersion,
)
from hpe_networking_mcp.translations.readers.central import central_read_wlan

pytestmark = pytest.mark.unit


def _wlan(**kw):
    base = {"ssid": "CORP", "essid": {"name": "CORP", "use-alias": False}, "opmode": "OPEN"}
    base.update(kw)
    return base


@pytest.mark.parametrize(
    "opmode,km,wpa,cipher",
    [
        ("OPEN", KeyMgmt.OPEN, WpaVersion.NONE, Cipher.NONE),
        ("ENHANCED_OPEN", KeyMgmt.OWE, WpaVersion.NONE, Cipher.NONE),
        ("STATIC_WEP", KeyMgmt.WEP_STATIC, WpaVersion.NONE, Cipher.WEP),
        ("WPA2_PERSONAL", KeyMgmt.PSK, WpaVersion.WPA2, Cipher.AES_CCM),
        ("BOTH_WPA_WPA2_PSK", KeyMgmt.PSK, WpaVersion.WPA_WPA2, Cipher.AES_CCM),
        ("WPA3_SAE", KeyMgmt.SAE, WpaVersion.WPA3, Cipher.AES_CCM),
        ("WPA2_ENTERPRISE", KeyMgmt.ENTERPRISE, WpaVersion.WPA2, Cipher.AES_CCM),
        ("WPA3_ENTERPRISE_GCM_256", KeyMgmt.ENTERPRISE, WpaVersion.WPA3, Cipher.GCM_256),
        ("WPA2_MPSK_AES", KeyMgmt.MPSK, WpaVersion.WPA2, Cipher.AES_CCM),
    ],
)
def test_opmode_inverse(opmode, km, wpa, cipher) -> None:
    c = central_read_wlan(_wlan(opmode=opmode))
    assert c.security.key_mgmt == km
    assert c.security.wpa_version == wpa
    assert c.security.cipher == cipher


def test_essid_literal_vs_alias() -> None:
    lit = central_read_wlan(_wlan(essid={"name": "CORP", "use-alias": False}))
    assert lit.ssid == "CORP"
    al = central_read_wlan(_wlan(ssid="PROF", essid={"alias": "CORP-ALIAS", "use-alias": True}))
    assert al.ssid == "CORP-ALIAS"
    assert al.profile_name == "PROF"


def test_forward_and_vlan_inverse() -> None:
    c = central_read_wlan(
        _wlan(**{"forward-mode": "FORWARD_MODE_L2", "vlan-selector": "VLAN_RANGES", "vlan-id-range": ["150"]})
    )
    assert c.forward == ForwardMode.TUNNELED
    assert c.vlan.mode == VlanMode.ID
    assert c.vlan.id == 150
    named = central_read_wlan(_wlan(**{"vlan-selector": "NAMED_VLAN", "vlan-name": "CORP"}))
    assert named.vlan.mode == VlanMode.NAMED
    assert named.vlan.name == "CORP"


def test_mpsk_cloud_detected() -> None:
    c = central_read_wlan(_wlan(opmode="WPA2_MPSK_AES", **{"personal-security": {"mpsk-cloud-auth": True}}))
    assert c.security.key_mgmt == KeyMgmt.MPSK
    assert c.security.mpsk_source == MpskSource.CLOUD


def test_radius_walk_auth_acct_coa() -> None:
    wlan = _wlan(opmode="WPA2_ENTERPRISE", **{"auth-server-group": "CORP_nac"})
    sgs = [{"name": "CORP_nac", "type": "RADIUS", "servers": [{"server-name": "CORP_nac_1", "position": 1}]}]
    ass = [
        {
            "name": "CORP_nac_1",
            "auth-server-address": "10.1.1.5",
            "auth-port": 1812,
            "acct-port": 1813,
            "radius-server-mode": "AUTH_AND_COA",
            "dynamic-authorization-enable": True,
            "dynamic-authorization-port": 3799,
            "shared-secret-config": {"plaintext-value": "s"},
        }
    ]
    c = central_read_wlan(wlan, server_groups=sgs, auth_servers=ass)
    assert c.security.auth_source.kind == AuthSourceKind.RADIUS_GROUP
    r = c.security.radius
    assert [s.host for s in r.auth_servers] == ["10.1.1.5"]
    assert [s.host for s in r.acct_servers] == ["10.1.1.5"]
    assert [x.ip for x in r.coa] == ["10.1.1.5"]


def test_alias_host_maps_back_to_variable() -> None:
    wlan = _wlan(opmode="WPA2_ENTERPRISE", **{"auth-server-group": "CORP_nac"})
    sgs = [{"name": "CORP_nac", "servers": [{"server-name": "CORP_nac_1"}]}]
    ass = [{"name": "CORP_nac_1", "auth-server-address": "RADIUS_PRIMARY", "auth-port": 1812}]
    aliases = [{"name": "RADIUS_PRIMARY", "type": "ALIAS_AUTH_SERVER_ADDRESS"}]
    c = central_read_wlan(wlan, server_groups=sgs, auth_servers=ass, aliases=aliases)
    assert c.security.radius.auth_servers[0].host == "{{RADIUS_PRIMARY}}"


def test_nac_group_detected_as_nac() -> None:
    wlan = _wlan(opmode="WPA2_ENTERPRISE", **{"auth-server-group": "sys_central_nac"})
    c = central_read_wlan(wlan)
    assert c.security.auth_source.kind == AuthSourceKind.NAC
    assert c.security.radius is None


def test_assignment_from_config_assignments() -> None:
    assigns = [
        {"profile-type": "wlan-ssids", "profile-instance": "CORP", "scope-type": "GLOBAL", "scope-name": "GLOBAL"},
        {"profile-type": "wlan-ssids", "profile-instance": "CORP", "scope-type": "SITE", "scope-name": "HOME"},
        {"profile-type": "wlan-ssids", "profile-instance": "OTHER", "scope-type": "SITE", "scope-name": "NOPE"},
    ]
    c = central_read_wlan(_wlan(), assignments=assigns)
    assert c.assignment.org_wide is True
    assert c.assignment.sites == ["HOME"]
