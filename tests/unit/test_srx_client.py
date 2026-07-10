"""Unit tests for SRXClient — session lifecycle, show-command gating, retry, aclose().

PyEZ's ``Device`` does blocking SSH/NETCONF I/O, so it's mocked out
entirely here (no real network calls) — ``client.py``'s ``Device`` import
is patched with a stand-in whose ``.open()``/``.cli()``/``.close()`` are
plain synchronous mocks, matching what ``asyncio.to_thread()`` expects.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from jnpr.junos.exception import ConnectError, RpcError

from hpe_networking_mcp.config import SRXSecrets
from hpe_networking_mcp.platforms.srx.client import (
    SRXClient,
    SRXConnectionError,
    format_srx_error,
)


def _make_secrets(**overrides) -> SRXSecrets:
    base = {
        "host": "srx.test",
        "port": 830,
        "username": "admin",
        "password": "secret",
    }
    base.update(overrides)
    return SRXSecrets(**base)


def _make_mock_device(facts: dict | None = None) -> MagicMock:
    dev = MagicMock()
    dev.connected = False

    def _open():
        dev.connected = True

    dev.open.side_effect = _open
    dev.facts = facts or {"hostname": "srx1", "model": "SRX300", "version": "21.4R1", "serialnumber": "AB1234"}
    dev.cli.return_value = "show output text"
    return dev


@pytest.mark.unit
class TestSRXClientSession:
    async def test_get_facts_opens_session_with_configured_credentials(self):
        mock_dev = _make_mock_device()
        with patch("hpe_networking_mcp.platforms.srx.client.Device", return_value=mock_dev) as mock_device_cls:
            client = SRXClient(_make_secrets(host="srx.example.com", port=830, username="admin", password="secret"))
            facts = await client.get_facts()

        mock_device_cls.assert_called_once()
        _, kwargs = mock_device_cls.call_args
        assert kwargs["host"] == "srx.example.com"
        assert kwargs["port"] == 830
        assert kwargs["user"] == "admin"
        assert kwargs["password"] == "secret"
        mock_dev.open.assert_called_once()
        assert facts == mock_dev.facts

    async def test_session_reused_across_calls(self):
        mock_dev = _make_mock_device()
        with patch("hpe_networking_mcp.platforms.srx.client.Device", return_value=mock_dev) as mock_device_cls:
            client = SRXClient(_make_secrets())
            await client.get_facts()
            await client.get_facts()

        assert mock_device_cls.call_count == 1
        assert mock_dev.open.call_count == 1

    async def test_session_reopened_if_disconnected(self):
        mock_dev = _make_mock_device()
        with patch("hpe_networking_mcp.platforms.srx.client.Device", return_value=mock_dev) as mock_device_cls:
            client = SRXClient(_make_secrets())
            await client.get_facts()
            mock_dev.connected = False
            await client.get_facts()

        assert mock_device_cls.call_count == 2
        assert mock_dev.open.call_count == 2


@pytest.mark.unit
class TestSRXClientShow:
    async def test_rejects_non_show_command_without_opening_session(self):
        with patch("hpe_networking_mcp.platforms.srx.client.Device") as mock_device_cls:
            client = SRXClient(_make_secrets())
            with pytest.raises(SRXConnectionError, match="Only 'show' commands"):
                await client.show("delete interfaces ge-0/0/0")
        mock_device_cls.assert_not_called()

    async def test_show_calls_cli_with_warning_false(self):
        mock_dev = _make_mock_device()
        with patch("hpe_networking_mcp.platforms.srx.client.Device", return_value=mock_dev):
            client = SRXClient(_make_secrets())
            result = await client.show("show configuration security policies")

        mock_dev.cli.assert_called_once_with("show configuration security policies", warning=False)
        assert result == "show output text"

    async def test_show_is_case_insensitive_on_prefix(self):
        mock_dev = _make_mock_device()
        with patch("hpe_networking_mcp.platforms.srx.client.Device", return_value=mock_dev):
            client = SRXClient(_make_secrets())
            await client.show("SHOW version")
        mock_dev.cli.assert_called_once()

    async def test_show_retries_once_on_rpc_error(self):
        mock_dev_1 = _make_mock_device()
        mock_dev_1.cli.side_effect = RpcError()
        mock_dev_2 = _make_mock_device()
        mock_dev_2.cli.return_value = "recovered output"

        with patch(
            "hpe_networking_mcp.platforms.srx.client.Device",
            side_effect=[mock_dev_1, mock_dev_2],
        ) as mock_device_cls:
            client = SRXClient(_make_secrets())
            result = await client.show("show version")

        assert mock_device_cls.call_count == 2
        assert result == "recovered output"


@pytest.mark.unit
class TestSRXClientLifecycle:
    async def test_aclose_closes_open_session(self):
        mock_dev = _make_mock_device()
        with patch("hpe_networking_mcp.platforms.srx.client.Device", return_value=mock_dev):
            client = SRXClient(_make_secrets())
            await client.get_facts()
            await client.aclose()

        mock_dev.close.assert_called_once()

    async def test_aclose_without_open_session_is_a_noop(self):
        client = SRXClient(_make_secrets())
        await client.aclose()  # must not raise

    async def test_health_check_returns_facts_subset(self):
        mock_dev = _make_mock_device(
            facts={"hostname": "starkwanedge", "model": "SRX300", "version": "21.4R1", "serialnumber": "XYZ"}
        )
        with patch("hpe_networking_mcp.platforms.srx.client.Device", return_value=mock_dev):
            client = SRXClient(_make_secrets())
            result = await client.health_check()

        assert result == {"hostname": "starkwanedge", "model": "SRX300", "version": "21.4R1"}


@pytest.mark.unit
class TestFormatSRXError:
    def test_connect_error(self):
        # ConnectError.__repr__ dereferences dev.hostname when a msg is set,
        # so a real construction always passes the Device instance -- a bare
        # stand-in with a .hostname attribute mirrors that, not dev=None.
        fake_dev = MagicMock()
        fake_dev.hostname = "srx.test"
        exc = ConnectError(dev=fake_dev, msg="unreachable")
        formatted = format_srx_error(exc)
        assert formatted["status_code"] == 0
        assert "NETCONF connection failed" in formatted["message"]

    def test_srx_connection_error(self):
        exc = SRXConnectionError("Only 'show' commands are permitted, got: 'delete x'")
        formatted = format_srx_error(exc)
        assert "Only 'show' commands" in formatted["message"]

    def test_generic_exception(self):
        exc = RuntimeError("boom")
        formatted = format_srx_error(exc)
        assert formatted["status_code"] == 0
        assert "boom" in formatted["message"]
