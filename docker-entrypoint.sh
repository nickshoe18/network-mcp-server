#!/bin/bash
set -e

# Append Zscaler CA chain to certifi bundle (once only)
CERTIFI_BUNDLE=$(/app/.venv/bin/python -c "import certifi; print(certifi.where())" 2>/dev/null || true)
MARKER="# Zscaler-chain-appended"

if [ -n "$CERTIFI_BUNDLE" ] && [ -f "$CERTIFI_BUNDLE" ]; then
    if ! grep -qF "$MARKER" "$CERTIFI_BUNDLE"; then
        cat /tmp/zscaler-chain.pem >> "$CERTIFI_BUNDLE"
        echo "$MARKER" >> "$CERTIFI_BUNDLE"
        echo "Zscaler chain appended"
    else
        echo "Zscaler chain already present"
    fi
fi

# Patch UXI client to pass certifi bundle to httpx (find path dynamically)
UXI_CLIENT=$(find /app -name "client.py" -path "*/uxi/*" 2>/dev/null | head -1)
if [ -n "$UXI_CLIENT" ]; then
    if ! grep -q "verify=_certifi" "$UXI_CLIENT"; then
        sed -i 's/self._http = httpx.AsyncClient(/import certifi as _certifi\n        self._http = httpx.AsyncClient(/' "$UXI_CLIENT"
        sed -i 's/timeout=_REQUEST_TIMEOUT,/timeout=_REQUEST_TIMEOUT,\n            verify=_certifi.where(),/' "$UXI_CLIENT"
        echo "UXI client patched"
    else
        echo "UXI client already patched"
    fi
else
    echo "UXI client not found — skipping patch"
fi

exec uv run --no-sync python -m hpe_networking_mcp
