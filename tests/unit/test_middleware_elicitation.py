"""Unit tests for ``confirm_gated_invoke``'s elicitation-result handling.

Covers the fix for the VS Code MCP client gap: a bare ``DeclinedElicitation``
(the SDK default when no prompt is actually rendered) must be treated as
"ask in chat" (``confirmation_required``), not as a real human decline —
while an explicit ``AcceptedElicitation(data=False)`` or a ``Cancelled``
result must still be treated as final, real signals.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastmcp.server.elicitation import (
    AcceptedElicitation,
    CancelledElicitation,
    DeclinedElicitation,
)
from mcp.shared.exceptions import McpError
from mcp.types import ErrorData

from hpe_networking_mcp.middleware.elicitation import confirm_gated_invoke


def _make_ctx(*, elicit_result=None, elicit_side_effect=None, disable_elicitation: bool = False) -> MagicMock:
    ctx = MagicMock()
    config = MagicMock()
    config.disable_elicitation = disable_elicitation
    ctx.lifespan_context = {"config": config}
    if elicit_side_effect is not None:
        ctx.elicit = AsyncMock(side_effect=elicit_side_effect)
    else:
        ctx.elicit = AsyncMock(return_value=elicit_result)
    return ctx


@pytest.mark.unit
@pytest.mark.asyncio
class TestConfirmGatedInvoke:
    async def test_disable_elicitation_auto_accepts(self):
        ctx = _make_ctx(disable_elicitation=True)
        result = await confirm_gated_invoke(ctx, "do a thing", {})
        assert result is None
        ctx.elicit.assert_not_called()

    async def test_explicit_approve_true_proceeds(self):
        ctx = _make_ctx(elicit_result=AcceptedElicitation(data=True))
        result = await confirm_gated_invoke(ctx, "do a thing", {})
        assert result is None

    async def test_explicit_approve_false_is_a_real_final_decline(self):
        ctx = _make_ctx(elicit_result=AcceptedElicitation(data=False))
        result = await confirm_gated_invoke(ctx, "do a thing", {"confirmed": True})
        assert result == {"status": "declined", "message": "Action not approved (approve was not set to true)."}

    async def test_cancelled_is_a_real_final_signal(self):
        ctx = _make_ctx(elicit_result=CancelledElicitation())
        result = await confirm_gated_invoke(ctx, "do a thing", {"confirmed": True})
        assert result == {"status": "cancelled", "message": "Action cancelled by user."}

    async def test_bare_declined_first_attempt_asks_in_chat_not_declined(self):
        """The core fix: nothing rendered (bare Declined) must not be a final decline."""
        ctx = _make_ctx(elicit_result=DeclinedElicitation())
        result = await confirm_gated_invoke(ctx, "do a thing", {})
        assert result is not None
        assert result["status"] == "confirmation_required"
        assert "confirmed" in result["message"]

    async def test_bare_declined_with_confirmed_true_proceeds(self):
        """After the human confirms in chat, re-invoking with confirmed=true proceeds."""
        ctx = _make_ctx(elicit_result=DeclinedElicitation())
        result = await confirm_gated_invoke(ctx, "do a thing", {"confirmed": True})
        assert result is None

    async def test_no_capability_error_falls_back_to_confirmed_true(self):
        error = ErrorData(code=-32601, message="elicitation not supported")
        ctx = _make_ctx(elicit_side_effect=McpError(error))
        result = await confirm_gated_invoke(ctx, "do a thing", {"confirmed": True})
        assert result is None

    async def test_no_capability_error_without_confirmed_asks_for_it(self):
        error = ErrorData(code=-32601, message="elicitation not supported")
        ctx = _make_ctx(elicit_side_effect=McpError(error))
        result = await confirm_gated_invoke(ctx, "do a thing", {})
        assert result["status"] == "confirmation_required"

    async def test_other_mcp_error_fails_closed(self):
        error = ErrorData(code=-32000, message="some other MCP failure")
        ctx = _make_ctx(elicit_side_effect=McpError(error))
        result = await confirm_gated_invoke(ctx, "do a thing", {"confirmed": True})
        assert result["status"] == "confirmation_unavailable"

    async def test_unexpected_exception_fails_closed(self):
        ctx = _make_ctx(elicit_side_effect=RuntimeError("boom"))
        result = await confirm_gated_invoke(ctx, "do a thing", {"confirmed": True})
        assert result["status"] == "confirmation_unavailable"
