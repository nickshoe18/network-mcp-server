#!/bin/bash
set -e

# Append Zscaler CA chain to certifi bundle (once only)
# Required because Docker Desktop routes traffic through Zscaler SSL inspection
CERTIFI_BUNDLE=$(/app/.venv/bin/python -c "import certifi; print(certifi.where())")
MARKER="# Zscaler-chain-appended"

if ! grep -qF "$MARKER" "$CERTIFI_BUNDLE"; then
    cat /tmp/zscaler-chain.pem >> "$CERTIFI_BUNDLE"
    echo "$MARKER" >> "$CERTIFI_BUNDLE"
    echo "Zscaler chain appended"
else
    echo "Zscaler chain already present"
fi

# Patch UXI client to explicitly pass certifi bundle to httpx
UXI_CLIENT="/app/src/hpe_networking_mcp/platforms/uxi/client.py"
if ! grep -q "verify=_certifi" "$UXI_CLIENT"; then
    sed -i 's/self._http = httpx.AsyncClient(/import certifi as _certifi\n        self._http = httpx.AsyncClient(/' "$UXI_CLIENT"
    sed -i 's/timeout=_REQUEST_TIMEOUT,/timeout=_REQUEST_TIMEOUT,\n            verify=_certifi.where(),/' "$UXI_CLIENT"
    echo "UXI client patched"
else
    echo "UXI client already patched"
fi

exec uv run --no-sync python -m hpe_networking_mcp
