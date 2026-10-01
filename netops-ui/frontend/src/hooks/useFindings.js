import { useState, useEffect } from "react";

export function useFindings(intervalMs = 15000) {
  const [findings, setFindings] = useState([]);
  const [loading, setLoading] = useState(true);

  const fetch_ = async () => {
    try {
      const res = await fetch("/api/findings");
      const data = await res.json();
      setFindings(data?.data ?? []);
    } catch {
      // stay on the last known list — a transient fetch failure isn't worth surfacing here
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetch_();
    const id = setInterval(fetch_, intervalMs);
    return () => clearInterval(id);
  }, [intervalMs]);

  return { findings, loading, refetch: fetch_ };
}
