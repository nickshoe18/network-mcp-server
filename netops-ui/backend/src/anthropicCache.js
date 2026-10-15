// Prompt-caching helpers (https://platform.claude.com/docs/en/build-with-claude/prompt-caching).
// System prompts and tool definitions are identical across every call a given mode makes, and
// within one multi-turn loop the message history only ever grows — both are ideal cache targets.
// Without this, every turn of every investigation re-billed the full system prompt, tool
// definitions, and the entire accumulated conversation at full input price, every single time.

export function cachedSystem(text) {
  return [{ type: "text", text, cache_control: { type: "ephemeral" } }];
}

export function cachedTools(tools) {
  if (tools.length === 0) return tools;
  return tools.map((t, i) => (i === tools.length - 1 ? { ...t, cache_control: { type: "ephemeral" } } : t));
}

// Returns a copy of `messages` with a single cache breakpoint on the last content block of the
// last message — call this only when building the request to send, never store the result back
// into the running message array, so each turn gets exactly one breakpoint instead of
// accumulating one per turn (the API allows at most 4 breakpoints per request, across
// tools + system + messages combined).
export function withCacheBreakpoint(messages) {
  if (messages.length === 0) return messages;
  const last = messages[messages.length - 1];
  const content = typeof last.content === "string"
    ? [{ type: "text", text: last.content }]
    : last.content.map(b => ({ ...b }));
  if (content.length === 0) return messages;
  content[content.length - 1] = { ...content[content.length - 1], cache_control: { type: "ephemeral" } };
  return [...messages.slice(0, -1), { ...last, content }];
}
