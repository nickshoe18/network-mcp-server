import { useState, useEffect } from "react";

const PLATFORM_META = {
  mist:      { label: "Juniper Mist",   color: "#1B8C6E" },
  central:   { label: "Aruba Central",  color: "#185FA5" },
  greenlake: { label: "HPE GreenLake",  color: "#BA7517" },
  clearpass: { label: "ClearPass",      color: "#534AB7" },
  axis:      { label: "Aruba Axis",     color: "#993C1D" },
  uxi:       { label: "UXI",            color: "#3B6D11" },
};

export function usePlatformHealth(intervalMs = 30000) {
  const [health, setHealth]   = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState(null);

  const fetch_ = async () => {
    try {
      const res  = await fetch("/api/health");
      const data = await res.json();
      setHealth(data);
      setError(null);
    } catch (e) {
      setError("Cannot reach backend");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetch_();
    const id = setInterval(fetch_, intervalMs);
    return () => clearInterval(id);
  }, [intervalMs]);

  const platforms = Object.entries(PLATFORM_META).map(([key, meta]) => ({
    key, ...meta,
    status:  health?.data?.platforms?.[key]?.status  ?? "unknown",
    message: health?.data?.platforms?.[key]?.message ?? "—",
  }));

  return { platforms, loading, error, refresh: fetch_ };
}
