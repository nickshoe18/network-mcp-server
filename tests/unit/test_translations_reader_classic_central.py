"""Tests for the Classic Central CLI parser + VLAN reader.

Validated against two REAL config dumps captured live from the source
tenant (see project memory: "Classic Central -> New Central group-config
translation") -- "Wayne Enterprises" (359 lines, holds actual VLAN/WLAN/
AAA/role config) and "default" (103 lines, mostly-empty baseline with
different construct types: arm, airgroupservice, multi-port enet
bindings). Using two independently-shaped real samples, not one, is the
whole point -- the parser must be generic, not tuned to a single tenant's
config (see project memory's explicit design requirement).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from hpe_networking_mcp.translations.canonical.vlan import CanonicalNamedVlan
from hpe_networking_mcp.translations.canonical.wlan import (
    AuthSourceKind,
    Cipher,
    FastRoam,
    ForwardMode,
    KeyMgmt,
    VlanMode,
    WpaVersion,
)
from hpe_networking_mcp.translations.readers.classic_central import (
    blocks_by_keyword,
    classic_central_read_ap_uplink,
    classic_central_read_named_vlan,
    classic_central_read_policy,
    classic_central_read_skeletal_role,
    classic_central_read_wlan,
    has_flag,
    parse_cli_blocks,
    prop,
    prop_all,
    prop_str,
)

pytestmark = pytest.mark.unit

_FIXTURES = Path(__file__).parent / "fixtures" / "classic_central"


def _load(name: str) -> list[str]:
    return json.loads((_FIXTURES / name).read_text())


@pytest.fixture(scope="module")
def wayne_lines() -> list[str]:
    return _load("wayne_enterprises_ap_cli.json")


@pytest.fixture(scope="module")
def default_lines() -> list[str]:
    return _load("default_group_ap_cli.json")


class TestParseCliBlocksOnRealData:
    def test_wayne_enterprises_parses_without_error(self, wayne_lines):
        blocks = parse_cli_blocks(wayne_lines)
        assert len(blocks) > 0
        # every line became part of some block -- no silent total failure
        assert all(isinstance(b["keyword"], str) and b["keyword"] for b in blocks)

    def test_default_group_parses_without_error(self, default_lines):
        blocks = parse_cli_blocks(default_lines)
        assert len(blocks) > 0

    def test_single_word_keyword(self, wayne_lines):
        blocks = parse_cli_blocks(wayne_lines)
        vlan_blocks = blocks_by_keyword(blocks, "vlan")
        assert len(vlan_blocks) == 4
        names = {b["args"][0] for b in vlan_blocks}
        assert names == {"Users", "Aruba", "Servers", "IoT"}

    def test_two_word_keyword(self, wayne_lines):
        blocks = parse_cli_blocks(wayne_lines)
        ssid_blocks = blocks_by_keyword(blocks, "wlan ssid-profile")
        assert len(ssid_blocks) == 3
        names = {b["args"][0] for b in ssid_blocks}
        assert names == {"Wayne Enterprises", "Aruba Air Pass", "Visitor Test"}

    def test_three_word_keyword_not_swallowed_by_two_word_prefix(self, wayne_lines):
        """'wlan access-list route' must NOT be parsed as 'wlan access-rule'-shaped
        (a real risk: both start with 'wlan access-')."""
        blocks = parse_cli_blocks(wayne_lines)
        route_blocks = blocks_by_keyword(blocks, "wlan access-list route")
        assert len(route_blocks) == 1
        assert route_blocks[0]["args"] == ["default policy"]
        # and plain "wlan access-rule" blocks are unaffected
        rule_blocks = blocks_by_keyword(blocks, "wlan access-rule")
        assert len(rule_blocks) >= 10

    def test_repeated_properties_preserved_in_order(self, wayne_lines):
        blocks = parse_cli_blocks(wayne_lines)
        guest_rule = next(b for b in blocks_by_keyword(blocks, "wlan access-rule") if b["args"] == ["Test_#guest#_"])
        rules = prop_all(guest_rule, "rule")
        assert len(rules) == 8  # 8 "rule ..." lines under this block, none dropped
        assert rules[0][:2] == ["alias", "licdn.com"]

    def test_netdestination_repeated_name_properties(self, wayne_lines):
        blocks = parse_cli_blocks(wayne_lines)
        netdest = blocks_by_keyword(blocks, "netdestination")[0]
        names = prop_all(netdest, "name")
        assert len(names) == 7
        assert ["iprofiles.apple.com"] in names

    def test_blank_name_block_still_parses(self, wayne_lines):
        """'rf dot11g-radio-profile ' (trailing space, no name) must parse to
        an empty args list, not crash or merge into the wrong block."""
        blocks = parse_cli_blocks(wayne_lines)
        blank = [b for b in blocks_by_keyword(blocks, "rf dot11g-radio-profile") if not b["args"]]
        assert len(blank) == 1
        assert prop(blank[0], "max-tx-power") == ["22"]

    def test_bare_flag_property(self, wayne_lines):
        blocks = parse_cli_blocks(wayne_lines)
        ssid = next(b for b in blocks_by_keyword(blocks, "wlan ssid-profile") if b["args"] == ["Aruba Air Pass"])
        assert has_flag(ssid, "dot11r")
        assert has_flag(ssid, "enable")
        assert not has_flag(ssid, "not-a-real-property")

    def test_quoted_value_with_embedded_space_kept_as_one_token(self, wayne_lines):
        blocks = parse_cli_blocks(wayne_lines)
        candidates = blocks_by_keyword(blocks, "hotspot anqp-venue-name-profile")
        hs_profile = next(b for b in candidates if b["args"] == ["Gemini"])
        assert prop_str(hs_profile, "venue-name") == "Wayne Manor"

    def test_scalar_directive_with_no_children_is_a_valid_empty_block(self, wayne_lines):
        """'ntp-server us.pool.ntp.org' has zero indented children -- a bare
        one-line directive is a legitimate block with empty properties."""
        blocks = parse_cli_blocks(wayne_lines)
        ntp = blocks_by_keyword(blocks, "ntp-server")
        assert len(ntp) == 1
        assert ntp[0]["args"] == ["us.pool.ntp.org"]
        assert ntp[0]["properties"] == {}

    def test_default_group_construct_types_not_seen_in_wayne_enterprises(self, default_lines):
        """Confirms generality: constructs absent from the other fixture still
        parse correctly by shape alone (no hardcoded name list)."""
        blocks = parse_cli_blocks(default_lines)
        assert blocks_by_keyword(blocks, "arm")
        assert blocks_by_keyword(blocks, "airgroupservice")
        assert len(blocks_by_keyword(blocks, "airgroupservice")) == 2
        # multiple distinct single-word keywords for numbered enet bindings
        for n in range(5):
            assert blocks_by_keyword(blocks, f"enet{n}-port-profile")

    def test_same_construct_different_args_across_fixtures(self, wayne_lines, default_lines):
        """The same block type appears with different arg counts/values in each
        fixture -- confirms the parser isn't tuned to one shape."""
        wayne_clock = blocks_by_keyword(parse_cli_blocks(wayne_lines), "clock")[0]
        default_clock = blocks_by_keyword(parse_cli_blocks(default_lines), "clock")[0]
        assert wayne_clock["args"] == ["timezone", "Central-America", "-6", "0"]
        assert default_clock["args"] == ["timezone", "none", "0", "0"]

    def test_unrecognized_multiword_construct_degrades_to_single_word_keyword(self):
        """A hypothetical never-seen 2-word command falls back to a single-word
        keyword rather than raising -- safe degradation, not a crash."""
        blocks = parse_cli_blocks(["totally unknown-thing-nobody-has-seen", "  some-property value"])
        assert len(blocks) == 1
        assert blocks[0]["keyword"] == "totally"
        assert blocks[0]["args"] == ["unknown-thing-nobody-has-seen"]
        assert prop(blocks[0], "some-property") == ["value"]

    def test_indented_line_before_any_header_is_skipped_not_crashed(self):
        blocks = parse_cli_blocks(["  orphan-property value", "vlan Users 60"])
        assert len(blocks) == 1
        assert blocks[0]["keyword"] == "vlan"

    def test_blank_lines_ignored(self):
        blocks = parse_cli_blocks(["vlan Users 60", "", "   ", "vlan Aruba 20"])
        assert len(blocks) == 2


class TestClassicCentralReadNamedVlan:
    def test_reads_real_wayne_enterprises_vlans(self, wayne_lines):
        blocks = parse_cli_blocks(wayne_lines)
        vlan_blocks = blocks_by_keyword(blocks, "vlan")
        canon_by_name = {}
        for b in vlan_blocks:
            c = classic_central_read_named_vlan(b)
            canon_by_name[c.vlan_name] = c

        assert canon_by_name["Users"] == CanonicalNamedVlan(vlan_name="Users", alias_name="users", vlan_ids=["60"])
        assert canon_by_name["Aruba"].vlan_ids == ["20"]
        assert canon_by_name["IoT"].vlan_ids == ["50"]

    def test_alias_name_defaults_to_lowercase(self):
        block = {"keyword": "vlan", "args": ["Servers", "30"], "properties": {}}
        canon = classic_central_read_named_vlan(block)
        assert canon.alias_name == "servers"

    def test_alias_name_override(self):
        block = {"keyword": "vlan", "args": ["Servers", "30"], "properties": {}}
        canon = classic_central_read_named_vlan(block, alias_name="custom-alias")
        assert canon.alias_name == "custom-alias"

    def test_missing_id_defaults_to_empty_list(self):
        block = {"keyword": "vlan", "args": ["OnlyName"], "properties": {}}
        canon = classic_central_read_named_vlan(block)
        assert canon.vlan_ids == []


class TestClassicCentralReadWlan:
    def _ssid_block(self, wayne_lines, name: str) -> dict:
        blocks = parse_cli_blocks(wayne_lines)
        return next(b for b in blocks_by_keyword(blocks, "wlan ssid-profile") if b["args"] == [name])

    def _auth_servers(self, wayne_lines) -> list[dict]:
        return blocks_by_keyword(parse_cli_blocks(wayne_lines), "wlan auth-server")

    def test_wpa3_personal_ssid(self, wayne_lines):
        ssid = self._ssid_block(wayne_lines, "Wayne Enterprises")
        canon = classic_central_read_wlan(ssid, auth_servers=self._auth_servers(wayne_lines))

        assert canon.ssid == "Wayne Enterprises"
        assert canon.profile_name == "Wayne Enterprises"
        assert canon.enabled is True
        assert canon.security.key_mgmt == KeyMgmt.SAE
        assert canon.security.wpa_version == WpaVersion.WPA3
        assert canon.security.cipher == Cipher.AES_CCM
        assert canon.vlan.mode == VlanMode.NAMED
        assert canon.vlan.name == "Users"
        assert canon.performance.dtim == 10
        assert canon.performance.max_clients == 64
        assert canon.forward == ForwardMode.BRIDGED

    def test_masked_psk_never_propagated(self, wayne_lines):
        """The API returns 'wpa-passphrase ********' -- must become None, never
        the literal mask string (that would silently ship a garbage secret)."""
        ssid = self._ssid_block(wayne_lines, "Wayne Enterprises")
        canon = classic_central_read_wlan(ssid, auth_servers=self._auth_servers(wayne_lines))
        assert canon.security.psk is None

    def test_wpa3_enterprise_ssid_with_radius(self, wayne_lines):
        ssid = self._ssid_block(wayne_lines, "Aruba Air Pass")
        canon = classic_central_read_wlan(ssid, auth_servers=self._auth_servers(wayne_lines))

        assert canon.security.key_mgmt == KeyMgmt.ENTERPRISE
        assert canon.security.wpa_version == WpaVersion.WPA3
        assert canon.security.auth_source.kind == AuthSourceKind.RADIUS_GROUP
        assert canon.security.auth_source.ref == "naw1"
        assert canon.security.radius is not None
        assert len(canon.security.radius.auth_servers) == 1
        server = canon.security.radius.auth_servers[0]
        assert server.host == "naw1.cloudguest.central.arubanetworks.com"
        assert server.port == 1812
        assert len(canon.security.radius.acct_servers) == 1
        assert canon.security.radius.acct_servers[0].port == 1813
        # naw1 carries a bare 'radsec' flag, not 'rfc3576' -- no CoA server expected
        assert canon.security.radius.coa == []
        assert canon.performance.fast_roam == FastRoam.DOT11R

    def test_radius_secret_unmasked_to_none(self, wayne_lines):
        """ClearPass auth-server has 'key ********' -- must not leak the mask."""
        ssid = self._ssid_block(wayne_lines, "Aruba Air Pass")
        auth_servers = self._auth_servers(wayne_lines)
        clearpass = next(b for b in auth_servers if b["args"] == ["ClearPass"])
        assert prop_str(clearpass, "key") == "********"  # confirm the raw fixture really has the mask

        # Build a WLAN referencing ClearPass directly to exercise the unmask path.
        ssid_referencing_clearpass = dict(ssid)
        ssid_referencing_clearpass["properties"] = dict(ssid["properties"])
        ssid_referencing_clearpass["properties"]["auth-server"] = [["ClearPass"]]
        canon = classic_central_read_wlan(ssid_referencing_clearpass, auth_servers=auth_servers)
        assert canon.security.radius.auth_servers[0].secret is None

    def test_rfc3576_flag_produces_coa_server(self, wayne_lines):
        """ClearPass has a bare 'rfc3576' flag + 'cppm-rfc3576-port 5999' -- CoA
        server should be built at that explicit port."""
        auth_servers = self._auth_servers(wayne_lines)
        clearpass = next(b for b in auth_servers if b["args"] == ["ClearPass"])
        assert has_flag(clearpass, "rfc3576")
        assert prop_str(clearpass, "cppm-rfc3576-port") == "5999"

        ssid = {
            "keyword": "wlan ssid-profile",
            "args": ["Test"],
            "properties": {"opmode": [["wpa2-aes"]], "auth-server": [["ClearPass"]], "enable": [[]]},
        }
        canon = classic_central_read_wlan(ssid, auth_servers=auth_servers)
        assert len(canon.security.radius.coa) == 1
        assert canon.security.radius.coa[0].port == 5999

    def test_guest_ssid_open_with_captive_portal(self, wayne_lines):
        ssid = self._ssid_block(wayne_lines, "Visitor Test")
        canon = classic_central_read_wlan(ssid, auth_servers=self._auth_servers(wayne_lines))

        assert canon.security.key_mgmt == KeyMgmt.OPEN
        assert canon.portal_deferred is True  # 'captive-portal external profile ...' -> deferred, not dropped

    def test_captive_portal_disable_is_not_deferred(self, wayne_lines):
        ssid = self._ssid_block(wayne_lines, "Wayne Enterprises")  # has 'captive-portal disable'
        canon = classic_central_read_wlan(ssid, auth_servers=self._auth_servers(wayne_lines))
        assert canon.portal_deferred is False

    def test_disabled_ssid_when_enable_flag_absent(self):
        ssid = {"keyword": "wlan ssid-profile", "args": ["X"], "properties": {"opmode": [["opensystem"]]}}
        canon = classic_central_read_wlan(ssid, auth_servers=[])
        assert canon.enabled is False

    def test_unknown_opmode_falls_back_to_open(self):
        """A never-seen opmode string must degrade to OPEN, not raise -- generality."""
        ssid = {"keyword": "wlan ssid-profile", "args": ["X"], "properties": {"opmode": [["some-future-opmode"]]}}
        canon = classic_central_read_wlan(ssid, auth_servers=[])
        assert canon.security.key_mgmt == KeyMgmt.OPEN

    def test_missing_auth_server_reference_is_ignored_not_crashed(self):
        ssid = {
            "keyword": "wlan ssid-profile",
            "args": ["X"],
            "properties": {"opmode": [["wpa2-aes"]], "auth-server": [["DoesNotExist"]]},
        }
        canon = classic_central_read_wlan(ssid, auth_servers=[])
        assert canon.security.radius is None


class TestClassicCentralReadPolicy:
    def _access_rule(self, wayne_lines, name: str) -> dict:
        blocks = parse_cli_blocks(wayne_lines)
        return next(b for b in blocks_by_keyword(blocks, "wlan access-rule") if b["args"] == [name])

    def test_simple_permit_any_any(self, wayne_lines):
        block = self._access_rule(wayne_lines, "employee")
        canon = classic_central_read_policy(block)

        assert canon.name == "employee"
        assert canon.association == "ASSOCIATION_ROLE"
        assert len(canon.rules) == 1
        rule = canon.rules[0]
        assert rule["condition"]["source"] == {"type": "ADDRESS_ROLE", "role-list": ["employee"]}
        assert rule["condition"]["destination"] == {"type": "ADDRESS_ANY"}
        assert rule["condition"]["rule-type"] == "RULE_ANY"
        assert rule["action"] == {"type": "ACTION_ALLOW"}
        assert canon.unmapped_actions == []

    def test_alias_deny_rule(self, wayne_lines):
        """'Wayne Enterprises' access-rule: alias-deny then any-permit -- also
        confirms non-'rule' properties (bare 'utf8' flag) don't leak into rules."""
        block = self._access_rule(wayne_lines, "Wayne Enterprises")
        canon = classic_central_read_policy(block)

        assert len(canon.rules) == 2
        deny_rule = canon.rules[0]
        assert deny_rule["condition"]["destination"] == {"type": "ADDRESS_ALIAS", "net-group": "apple-mdm"}
        assert deny_rule["action"] == {"type": "ACTION_DENY"}
        assert canon.rules[1]["action"] == {"type": "ACTION_ALLOW"}

    def test_masterip_and_tcp_port_rule(self):
        block = {
            "keyword": "wlan access-rule",
            "args": ["wired-SetMeUp"],
            "properties": {"rule": [["masterip", "0.0.0.0", "match", "tcp", "80", "80", "permit"]]},
        }
        canon = classic_central_read_policy(block)
        rule = canon.rules[0]
        assert rule["condition"]["destination"] == {
            "type": "ADDRESS_HOST",
            "host-address": {"host-ipv4-address": "0.0.0.0"},
        }
        assert rule["condition"]["rule-type"] == "RULE_TCP"
        assert rule["condition"]["ip-header"] == {"protocol": "IP_TCP"}
        assert rule["condition"]["transport-fields"] == {"destination-port": {"operator": "COMPARISON_EQ", "min": 80}}

    def test_guest_role_many_alias_rules(self, wayne_lines):
        block = self._access_rule(wayne_lines, "Test_#guest#_")
        canon = classic_central_read_policy(block)
        assert len(canon.rules) == 8  # all 8 real rule lines present, none dropped
        assert all(r["action"] == {"type": "ACTION_ALLOW"} for r in canon.rules)
        first = canon.rules[0]
        assert first["condition"]["destination"] == {"type": "ADDRESS_ALIAS", "net-group": "licdn.com"}
        assert first["condition"]["rule-type"] == "RULE_TCP"

    def test_unmapped_action_fails_closed_to_deny(self):
        """A never-seen action word must become ACTION_DENY and be flagged --
        never a silent ACTION_ALLOW fall-through (the security-inverting bug
        class this whole design guards against)."""
        block = {
            "keyword": "wlan access-rule",
            "args": ["X"],
            "properties": {"rule": [["any", "any", "match", "any", "any", "any", "some-future-action"]]},
        }
        canon = classic_central_read_policy(block)
        assert canon.rules[0]["action"] == {"type": "ACTION_DENY"}
        assert canon.unmapped_actions == ["some-future-action"]

    def test_malformed_rule_line_skipped_not_crashed(self):
        block = {
            "keyword": "wlan access-rule",
            "args": ["X"],
            "properties": {"rule": [["not-a-real-rule-shape"], ["any", "any", "match", "any", "any", "any", "permit"]]},
        }
        canon = classic_central_read_policy(block)
        assert len(canon.rules) == 1  # the malformed line was skipped, not crashed on

    def test_no_rules_produces_empty_policy(self):
        block = {"keyword": "wlan access-rule", "args": ["Empty"], "properties": {}}
        canon = classic_central_read_policy(block)
        assert canon.rules == []
        assert canon.unmapped_actions == []


class TestClassicCentralReadSkeletalRole:
    def test_role_with_vlan(self, wayne_lines):
        blocks = parse_cli_blocks(wayne_lines)
        block = next(b for b in blocks_by_keyword(blocks, "wlan access-rule") if b["args"] == ["Cloud-Faculty"])
        canon = classic_central_read_skeletal_role(block)

        assert canon.kind == "skeletal_role"
        assert canon.profile_type == "roles"
        assert canon.name == "Cloud-Faculty"
        assert canon.body == {"name": "Cloud-Faculty", "vlan": "60"}

    def test_role_without_vlan(self, wayne_lines):
        blocks = parse_cli_blocks(wayne_lines)
        block = next(b for b in blocks_by_keyword(blocks, "wlan access-rule") if b["args"] == ["employee"])
        canon = classic_central_read_skeletal_role(block)
        assert canon.body == {"name": "employee"}


class TestClassicCentralReadApUplink:
    def test_real_wayne_enterprises_uplink(self, wayne_lines):
        blocks = parse_cli_blocks(wayne_lines)
        uplink = blocks_by_keyword(blocks, "uplink")[0]
        canon = classic_central_read_ap_uplink(uplink, name="Wayne Enterprises")

        assert canon.kind == "ap_uplink"
        assert canon.profile_type == "ap-uplinks"
        assert canon.name == "Wayne Enterprises"
        assert canon.body == {
            "name": "Wayne Enterprises",
            "preemption": {"enable": True},
            "failover": {"pkt-lost-cnt": 10, "pkt-send-freq": 30, "vpn-timeout": 180},
        }

    def test_no_preemption_flag_omits_preemption_block(self):
        uplink = {
            "keyword": "uplink",
            "args": [],
            "properties": {"failover-vpn-timeout": [["180"]]},
        }
        canon = classic_central_read_ap_uplink(uplink, name="X")
        assert "preemption" not in canon.body
        assert canon.body["failover"] == {"vpn-timeout": 180}

    def test_no_failover_settings_omits_failover_block(self):
        uplink = {"keyword": "uplink", "args": [], "properties": {"preemption": [[]]}}
        canon = classic_central_read_ap_uplink(uplink, name="X")
        assert "failover" not in canon.body
        assert canon.body["preemption"] == {"enable": True}

    def test_empty_uplink_block_produces_bare_name_body(self):
        uplink = {"keyword": "uplink", "args": [], "properties": {}}
        canon = classic_central_read_ap_uplink(uplink, name="Empty")
        assert canon.body == {"name": "Empty"}
