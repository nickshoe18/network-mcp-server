"""Elicitation middleware and handler for write tool confirmation.

The ElicitationMiddleware runs at session init to enable write tools
based on config flags and detect client elicitation support.

The elicitation_handler function is called by individual write tools
to get user confirmation. Behavior depends on config and client:
- DISABLE_ELICITATION=true: auto-accept, no confirmation
- Client supports elicitation: show confirmation prompt dialog
- Client lacks elicitation: decline and instruct AI to ask user in chat

``confirm_gated_invoke`` is a second, newer confirmation path -- the
universal confirmation gate for tools that explicitly opt in via the
``requires_confirmation`` tag (ported from upstream `nowireless4u/
hpe-networking-mcp`, closing a real self-authorization bypass: some MCP
clients silently auto-accept an empty-schema elicitation prompt, letting
a write proceed with no visible confirmation). Unlike upstream, this is
NOT wired to fail-closed on an unclassified tool (``spec.capability is
None``) -- almost none of this codebase's ~2000 existing tools carry a
``capability`` classification, so treating that as "needs confirmation"
would suddenly gate every read tool too. Only tools that explicitly carry
``requires_confirmation`` in their tags go through this gate; everything
else keeps using its existing ``confirm_write``/``elicitation_handler``
call, unaffected.
"""

import json as _json

import mcp.types
from fastmcp import Context
from fastmcp.client.elicitation import ElicitResult
from fastmcp.server.elicitation import (
    AcceptedElicitation,
    CancelledElicitation,
    DeclinedElicitation,
)
from fastmcp.server.middleware import Middleware, MiddlewareContext
from fastmcp.tools.tool import ToolResult
from loguru import logger
from mcp.shared.exceptions import McpError

from hpe_networking_mcp.middleware.response_envelope import _build_envelope
from hpe_networking_mcp.platforms._common.tool_registry import REGISTRIES, ToolSpec
from hpe_networking_mcp.redaction.safe_summary import is_sensitive_key as _is_sensitive_key

_PARAM_SUMMARY_MAX_LEN = 300


def _sanitized_param_summary(params: dict | None) -> str:
    """Render a compact, redacted view of invocation params for the prompt.

    The human must see WHAT they are approving (target IDs, payload fields),
    not just the tool name -- but never secret values, and never unbounded
    payload dumps. Sensitive keys are redacted by name at any nesting depth,
    the bookkeeping ``confirmed`` flag is dropped, and the rendering is
    length-capped.
    """
    if not params:
        return "(no parameters)"

    def scrub(value):
        if isinstance(value, dict):
            return {k: ("***" if _is_sensitive_key(k) else scrub(v)) for k, v in value.items() if k != "confirmed"}
        if isinstance(value, list):
            return [scrub(v) for v in value]
        return value

    rendered = _json.dumps(scrub(params), separators=(", ", ": "), ensure_ascii=False, default=str)
    if len(rendered) > _PARAM_SUMMARY_MAX_LEN:
        rendered = rendered[: _PARAM_SUMMARY_MAX_LEN - 1] + "…"
    return rendered


def _find_registry_spec(tool_name: str) -> ToolSpec | None:
    """Return the platform ``ToolSpec`` for a tool name, or ``None``.

    Only registry-managed **platform** tools live in ``REGISTRIES``. The
    per-platform meta-tools (``<platform>_list_tools`` / ``_get_tool_schema`` /
    ``_invoke_tool``), the code-mode ``execute`` + discovery tools, and the
    cross-platform statics (``health`` / ``site_*`` / ``translate_*``) are
    registered with ``@mcp.tool`` OUTSIDE the registry, so they return
    ``None`` here and are NOT gated by ``on_call_tool``. That is correct:
    ``_invoke_tool`` and the translate-apply tools carry their own in-body
    ``confirm_gated_invoke`` and dispatch the target directly (never
    re-entering middleware), so gating them here too would double-prompt;
    the rest are reads/discovery/sandbox and must not prompt.
    """
    for registry in REGISTRIES.values():
        spec = registry.get(tool_name)
        if spec is not None:
            return spec
    return None


class ElicitationMiddleware(Middleware):
    async def on_call_tool(
        self,
        context: MiddlewareContext[mcp.types.CallToolRequestParams],
        call_next,
    ) -> ToolResult:
        """Structural confirmation gate at the ``tools/call`` layer.

        A tool called DIRECTLY by name -- which the code-mode sandbox allows --
        never goes through a platform's ``_invoke_tool`` dispatcher, so a tool
        that only relies on ``confirm_gated_invoke`` inside that dispatcher
        would bypass confirmation entirely. This gates the direct path
        structurally: any registry ``ToolSpec`` carrying the
        ``requires_confirmation`` tag prompts before it runs, exactly like the
        dispatcher. Every other tool (no tag) passes through unchanged --
        see ``_find_registry_spec`` and the module docstring for why this does
        NOT fail-closed on an unclassified tool.
        """
        tool_name = getattr(context.message, "name", None)
        ctx = context.fastmcp_context
        spec = _find_registry_spec(tool_name) if tool_name else None

        if spec is not None and ctx is not None and "requires_confirmation" in spec.tags:
            params = dict(getattr(context.message, "arguments", None) or {})
            summary = (spec.description or spec.category or "no description")[:120]
            gate = await confirm_gated_invoke(
                ctx,
                f"{spec.platform} tool '{tool_name}' ({summary})",
                params,
            )
            if gate is not None:
                envelope = _build_envelope(
                    ok=False,
                    data=gate,
                    status=403,
                    message=gate.get("message"),
                    tool=tool_name or "unknown",
                    platform=spec.platform,
                )
                return ToolResult(content=gate.get("message", ""), structured_content=envelope)

            if "confirmed" in params:
                cleaned = {k: v for k, v in params.items() if k != "confirmed"}
                new_message = context.message.model_copy(update={"arguments": cleaned})
                context = context.copy(message=new_message)

        return await call_next(context)  # type: ignore[no-any-return]

    async def on_initialize(
        self,
        context: MiddlewareContext[mcp.types.InitializeRequest],
        call_next,
    ) -> mcp.types.InitializeResult | None:
        result = await call_next(context)
        ctx = context.fastmcp_context
        if ctx is None:
            return result  # type: ignore[return-value]

        try:
            config = ctx.lifespan_context.get("config")
        except Exception:
            config = None

        if config is None:
            return result  # type: ignore[return-value]

        mist_write = config.enable_mist_write_tools
        central_write = config.enable_central_write_tools
        clearpass_write = config.enable_clearpass_write_tools
        greenlake_write = config.enable_greenlake_write_tools
        apstra_write = config.enable_apstra_write_tools
        axis_write = config.enable_axis_write_tools
        aos8_write = config.enable_aos8_write_tools
        uxi_write = config.enable_uxi_write_tools
        any_write = (
            mist_write
            or central_write
            or clearpass_write
            or greenlake_write
            or apstra_write
            or axis_write
            or aos8_write
            or uxi_write
        )

        if not any_write:
            return result  # type: ignore[return-value]

        # Determine confirmation mode
        if config.disable_elicitation:
            await ctx.set_state("elicitation_mode", "disabled")
            logger.warning("Elicitation: DISABLE_ELICITATION=true — write tools will execute without confirmation")
        else:
            client_supports = False
            try:
                caps = context.message.params.capabilities
                if caps is not None and caps.elicitation is not None:
                    client_supports = True
            except Exception:
                pass

            if client_supports:
                await ctx.set_state("elicitation_mode", "prompt")
                logger.debug("Elicitation: client supports elicitation prompts")
            else:
                await ctx.set_state("elicitation_mode", "chat_confirm")
                logger.info(
                    "Elicitation: client does not support elicitation — "
                    "write tools will require AI to confirm with user in chat"
                )

        # Enable write tools
        if mist_write:
            await ctx.enable_components(tags={"mist_write", "mist_write_delete"}, components={"tool"})
        if central_write:
            await ctx.enable_components(tags={"central_write_delete"}, components={"tool"})
        if clearpass_write:
            await ctx.enable_components(tags={"clearpass_write_delete"}, components={"tool"})
        if greenlake_write:
            await ctx.enable_components(tags={"greenlake_write", "greenlake_write_delete"}, components={"tool"})
        if apstra_write:
            await ctx.enable_components(tags={"apstra_write", "apstra_write_delete"}, components={"tool"})
        if axis_write:
            await ctx.enable_components(tags={"axis_write", "axis_write_delete"}, components={"tool"})
        if aos8_write:
            await ctx.enable_components(tags={"aos8_write", "aos8_write_delete"}, components={"tool"})
        if uxi_write:
            await ctx.enable_components(tags={"uxi_write", "uxi_write_delete"}, components={"tool"})
        logger.info(
            "Elicitation: write tools enabled (mist=%s, central=%s, clearpass=%s, greenlake=%s, "
            "apstra=%s, axis=%s, aos8=%s, uxi=%s)",
            mist_write,
            central_write,
            clearpass_write,
            greenlake_write,
            apstra_write,
            axis_write,
            aos8_write,
            uxi_write,
        )

        return result  # type: ignore[return-value]


async def confirm_gated_invoke(
    ctx: Context,
    description: str,
    params: dict | None,
) -> dict | None:
    """Universal confirmation gate for tools carrying ``requires_confirmation``.

    Called directly from a tool's own body (translate_config_apply,
    translate_wlan_apply) or from ``ElicitationMiddleware.on_call_tool`` /
    a platform's ``_invoke_tool`` dispatcher for registry tools tagged
    ``requires_confirmation``.

    The decision sequence:

    1. ``DISABLE_ELICITATION=true`` -> auto-accept (operator opt-out).
    2. Attempt a REAL ``ctx.elicit()`` prompt with a REQUIRED ``approve``
       boolean schema. Only an explicit ``approve=true`` proceeds;
       decline/cancel/approve-false return structured results. The required
       field closes a real safety gap: an empty-schema elicitation prompt is
       silently auto-accepted by some clients, letting a write proceed with
       no visible confirmation; a missing ``approve`` now fails closed.
    3. Only when the prompt RAISES (client genuinely cannot present one) is
       ``confirmed=true`` honored as the popup-less chat fallback. An AI
       cannot self-authorize while a human-facing prompt is available.
    4. A bare ``DeclinedElicitation`` result (as opposed to an explicit
       ``approve=false`` answer) is treated the same way as step 3, NOT as a
       real decline -- confirmed empirically against a real client that
       renders no UI at all and returns this as its silent default. The
       explicit ``AcceptedElicitation(data=False)`` and ``CancelledElicitation``
       results remain real, final signals. This still never lets
       ``confirmed=true`` bypass on a first attempt; it only substitutes the
       channel a human's real approval arrives through (chat text instead of
       a rendered dialog) for clients whose elicitation support is broken in
       this specific way.

    Args:
        ctx: FastMCP context of the invoke call.
        description: Human-readable description of the tool invocation.
        params: The raw params dict passed to the invoke (read-only; the
            ``confirmed`` flag is consumed from here for the fallback path).

    Returns:
        ``None`` when the invocation may proceed; otherwise a structured
        ``{"status": "confirmation_required" | "declined" | "cancelled", ...}``
        dict the caller should return as the tool result.
    """
    try:
        config = ctx.lifespan_context.get("config")
    except Exception:
        config = None
    if config is not None and config.disable_elicitation:
        logger.debug("Gate: auto-accepting (DISABLE_ELICITATION) — {}", description)
        return None

    param_summary = _sanitized_param_summary(params)
    prompt = f"Confirm: {description}\nParams: {param_summary}"
    try:
        # Required boolean response schema rather than the deprecated
        # ``response_type=None`` (empty-object) form -- see module docstring.
        result = await ctx.elicit(
            prompt,
            bool,  # type: ignore[arg-type]
            response_title="Approve",
            response_description="Approve this action? Must be set to true to proceed.",
        )
    except McpError as e:
        # Only the specific no-capability signal opens the fallback path.
        error = getattr(e, "error", None)
        code = getattr(error, "code", None)
        message = (getattr(error, "message", None) or str(e)).lower()
        is_no_capability = code == -32601 or "elicitation not supported" in message
        if not is_no_capability:
            logger.error(
                "Gate: MCP-layer elicitation failure (code={}, {}) — failing closed for {}",
                code,
                message[:120],
                description,
            )
            return {
                "status": "confirmation_unavailable",
                "message": (
                    f"{description} requires user confirmation, but the confirmation prompt failed "
                    "at the MCP layer. The action was NOT performed. Retry later, or have the "
                    "operator set DISABLE_ELICITATION=true if confirmations must be bypassed "
                    "deliberately."
                ),
            }
        # ONLY here does confirmed=true carry authority — the human-in-chat fallback.
        if params and params.get("confirmed") is True:
            logger.info("Gate: client lacks elicitation — honoring confirmed=true for {}", description)
            return None
        return {
            "status": "confirmation_required",
            "message": (
                f"{description} requires user confirmation and this client cannot show a "
                f"confirmation prompt. Params: {param_summary}. Confirm with the user in chat, "
                'then re-invoke with "confirmed": true.'
            ),
        }
    except Exception as e:
        # Any OTHER failure (handler crash, serialization bug, framework
        # regression) is NOT a license to skip confirmation — fail closed.
        logger.error(
            "Gate: elicitation failed unexpectedly ({}: {}) — failing closed for {}", type(e).__name__, e, description
        )
        return {
            "status": "confirmation_unavailable",
            "message": (
                f"{description} requires user confirmation, but the confirmation prompt failed "
                f"unexpectedly ({type(e).__name__}). The action was NOT performed. Retry later, "
                "or have the operator set DISABLE_ELICITATION=true if confirmations must be "
                "bypassed deliberately."
            ),
        }

    match result:
        case AcceptedElicitation(data=True):
            return None
        case AcceptedElicitation():
            # The human was shown the required approve/deny field and explicitly
            # answered false -- a real, deliberate rejection. Final.
            return {"status": "declined", "message": "Action not approved (approve was not set to true)."}
        case DeclinedElicitation():
            # Ambiguous by construction: some clients return this when a human
            # genuinely dismissed the prompt, but at least one real client
            # (confirmed empirically) returns it as the SDK default when NO
            # prompt was ever rendered at all -- the human never saw anything.
            # A genuine deliberate "no" already took the AcceptedElicitation(data=False)
            # branch above, so a bare Declined here is treated as "we don't know
            # whether a human actually saw this" rather than a real decline.
            # Fall through to the same popup-less chat-confirm relay the legacy
            # confirm_write()/elicitation_handler() path already uses for clients
            # with no elicitation capability at all -- describe the action in
            # plain chat text and require a fresh confirmed=true re-invocation.
            # This never lets confirmed=true bypass on a first attempt; it only
            # substitutes the channel a human's real "yes" arrives through.
            if params and params.get("confirmed") is True:
                logger.info("Gate: client returned bare Declined — honoring confirmed=true for {}", description)
                return None
            return {
                "status": "confirmation_required",
                "message": (
                    f"{description} requires user confirmation. This client did not render a visible "
                    f"confirmation prompt. Params: {param_summary}. Confirm with the user in chat, "
                    'then re-invoke with "confirmed": true.'
                ),
            }
        case CancelledElicitation():
            # Cancellation is a distinct, explicit user action in the elicitation
            # protocol (not the "nothing happened" default) -- treat as real.
            return {"status": "cancelled", "message": "Action cancelled by user."}
        case _:
            return {"status": "cancelled", "message": "Action cancelled (unrecognized elicitation result)."}


async def confirm_write(
    ctx: Context,
    message: str,
    *,
    chat_confirm_hint: str | None = None,
) -> dict | None:
    """High-level write-tool confirmation helper.

    Most write tools were carrying nearly-identical ``_confirm`` helpers that
    wrapped :func:`elicitation_handler` and turned the returned action into the
    canonical ``{"status": ..., "message": ...}`` dict shape. This helper
    consolidates that boilerplate (#148).

    Args:
        ctx: FastMCP context.
        message: Human-readable description of what the tool is about to do.
            Passed verbatim to the elicitation prompt.
        chat_confirm_hint: Optional replacement for the default "call again
            with confirmed=true" message returned when the client cannot
            present an elicitation prompt. Useful for tools whose parameter
            name isn't ``confirmed``.

    Returns:
        ``None`` if the user accepted (or elicitation is disabled) — caller
        proceeds. A dict with ``status`` of ``confirmation_required``,
        ``declined``, or ``cancelled`` if not — caller should return the dict
        as the tool result.
    """
    result = await elicitation_handler(message=message, ctx=ctx)
    if result.action == "accept":
        return None
    if result.action == "cancel":
        return {"status": "cancelled", "message": "Action cancelled by user."}
    # decline
    mode = await ctx.get_state("elicitation_mode")
    if mode == "chat_confirm":
        hint = chat_confirm_hint or (
            f"{message} — please confirm with the user before proceeding, then "
            "call this tool again with confirmed=true."
        )
        return {"status": "confirmation_required", "message": hint}
    return {"status": "declined", "message": "Action declined by user."}


async def elicitation_handler(message: str, ctx: Context) -> ElicitResult:
    """Get user confirmation before a write operation.

    Returns:
        ElicitResult with action "accept", "decline", or "cancel".
        On "decline" when chat confirmation is needed, the calling tool
        should return a confirmation request message to the AI.
    """
    mode = await ctx.get_state("elicitation_mode")

    # DISABLE_ELICITATION=true — skip all confirmation
    if mode == "disabled":
        logger.debug("Elicitation: auto-accepting (disabled) — {}", message)
        return ElicitResult(action="accept")

    # Client supports elicitation — show prompt dialog
    if mode == "prompt":
        try:
            logger.debug("Elicitation: prompting user — {}", message)
            result = await ctx.elicit(message, response_type=None)
            match result:
                case AcceptedElicitation():
                    return ElicitResult(action="accept")
                case DeclinedElicitation():
                    return ElicitResult(action="decline")
                case CancelledElicitation():
                    return ElicitResult(action="cancel")
                case _:
                    return ElicitResult(action="cancel")
        except Exception:
            logger.warning("Elicitation: prompt failed, falling through to chat confirm")

    # Client lacks elicitation — tell AI to ask the user in chat
    logger.debug("Elicitation: chat confirmation required — {}", message)
    return ElicitResult(action="decline")
