import { useState, useRef, useCallback } from "react";

export function useChat() {
  const [messages, setMessages]       = useState([]);
  const [streaming, setStreaming]     = useState(false);
  const [activeTools, setActiveTools] = useState([]);
  const abortRef = useRef(null);

  const send = useCallback(async (userText) => {
    if (streaming || !userText.trim()) return;
    const userMsg = { role: "user", content: userText, id: Date.now() };
    const history = [...messages, userMsg].map(({ role, content }) => ({ role, content }));
    setMessages(prev => [...prev, userMsg]);
    setStreaming(true);
    setActiveTools([]);

    const assistantId = Date.now() + 1;
    setMessages(prev => [...prev, { role: "assistant", content: "", id: assistantId, streaming: true }]);
    abortRef.current = new AbortController();

    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ messages: history }),
        signal: abortRef.current.signal,
      });

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buf = "";
      let lastEvent = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buf += decoder.decode(value, { stream: true });
        const lines = buf.split("\n");
        buf = lines.pop();

        for (const line of lines) {
          if (line.startsWith("event: ")) { lastEvent = line.slice(7).trim(); continue; }
          if (!line.startsWith("data: ")) continue;
          try {
            const data = JSON.parse(line.slice(6));
            if (lastEvent === "text" && data.text)
              setMessages(prev => prev.map(m => m.id === assistantId ? { ...m, content: m.content + data.text } : m));
            if (lastEvent === "tool_start" && data.name)
              setActiveTools(prev => [...prev, data.name]);
            if (lastEvent === "tool_end" && data.name)
              setActiveTools(prev => prev.filter(n => n !== data.name));
            if (lastEvent === "done")
              setMessages(prev => prev.map(m => m.id === assistantId ? { ...m, streaming: false } : m));
          } catch {}
        }
      }
    } catch (e) {
      if (e.name !== "AbortError")
        setMessages(prev => prev.map(m => m.id === assistantId ? { ...m, content: "Error: " + e.message, streaming: false, error: true } : m));
    } finally {
      setStreaming(false);
      setActiveTools([]);
      setMessages(prev => prev.map(m => m.id === assistantId ? { ...m, streaming: false } : m));
    }
  }, [messages, streaming]);

  const stop  = () => abortRef.current?.abort();
  const clear = () => { setMessages([]); setStreaming(false); };

  return { messages, streaming, activeTools, send, stop, clear };
}
