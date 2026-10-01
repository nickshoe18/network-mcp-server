#!/usr/bin/env python3
"""Run ping / traceroute / cable_test from a Mist-managed device and print the output.

Mist returns command output only over its websocket stream, so the MCP tools can start these but never show
the result. This subscribes to the device's cmd channel first, starts the command over REST, then prints the
streamed output for that session.

Usage (from the repo root):
  uv run --with websockets python .claude/tools/mist_device_cmd.py ping --device switch --host 10.103.10.10 --count 4
  uv run --with websockets python .claude/tools/mist_device_cmd.py traceroute --device gateway --host 8.8.8.8
  uv run --with websockets python .claude/tools/mist_device_cmd.py cable_test --device switch --port ge-0/0/10

The token comes from secrets/mist_api_token and is never printed. Only run this when the operator asked for a test.
"""

import argparse
import asyncio
import json
import sys
import time
import urllib.request
from pathlib import Path

import websockets

ROOT = Path(__file__).resolve().parents[2]
SECRETS = ROOT / "secrets"
SITE_ID = "59f74351-5c94-49bf-adea-dc96f4b132bf"
DEVICES = {
    "switch": "00000000-0000-0000-1000-045c6c556ee2",
    "gateway": "00000000-0000-0000-1000-0c812665a868",
    "srx": "00000000-0000-0000-1000-0c812665a868",
    "ap": "00000000-0000-0000-1000-c878670856ea",
}


def read_secret(name: str) -> str:
    return (SECRETS / name).read_text().strip()


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("command", choices=["ping", "traceroute", "cable_test"])
    p.add_argument("--device", required=True, help="switch | gateway | ap | <device uuid>")
    p.add_argument("--host", help="target for ping/traceroute")
    p.add_argument("--port", help="switch port for cable_test, e.g. ge-0/0/10")
    p.add_argument("--count", type=int, default=4)
    p.add_argument("--vrf", help="routing instance/VRF for ping/traceroute")
    p.add_argument("--site", default=SITE_ID)
    p.add_argument("--timeout", type=int, default=45, help="max seconds to wait for output")
    p.add_argument("--debug", action="store_true", help="print raw websocket messages to stderr")
    a = p.parse_args()

    device_id = DEVICES.get(a.device, a.device)
    body: dict = {}
    if a.command == "cable_test":
        if not a.port:
            p.error("cable_test needs --port")
        body["port"] = a.port
    else:
        if not a.host:
            p.error(f"{a.command} needs --host")
        body["host"] = a.host
        if a.command == "ping":
            body["count"] = a.count
        if a.vrf:
            body["vrf"] = a.vrf

    token = read_secret("mist_api_token")
    api_host = read_secret("mist_host") if (SECRETS / "mist_host").exists() else "api.gc4.mist.com"
    api_host = api_host.replace("https://", "").strip("/")
    ws_host = api_host.replace("api.", "api-ws.", 1)
    headers = {"Authorization": f"Token {token}", "Content-Type": "application/json"}
    channel = f"/sites/{a.site}/devices/{device_id}/cmd"
    return asyncio.run(run(a, api_host, ws_host, headers, channel, device_id, body))


async def run(a, api_host, ws_host, headers, channel, device_id, body) -> int:
    url = f"wss://{ws_host}/api-ws/v1/stream"
    async with websockets.connect(url, additional_headers={"Authorization": headers["Authorization"]}) as ws:
        await ws.send(json.dumps({"subscribe": channel}))
        await asyncio.sleep(1.0)

        req = urllib.request.Request(
            f"https://{api_host}/api/v1/sites/{a.site}/devices/{device_id}/{a.command}",
            data=json.dumps(body).encode(),
            headers=headers,
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                resp = json.loads(r.read() or "{}")
        except urllib.error.HTTPError as e:
            print(f"Mist API error {e.code}: {e.read().decode()[:300]}", file=sys.stderr)
            return 2
        session = resp.get("session")
        print(f"# {a.command} from {a.device}, session {session}", file=sys.stderr)

        deadline = time.time() + a.timeout
        got_output = False
        last = time.time()
        while time.time() < deadline:
            try:
                raw = await asyncio.wait_for(ws.recv(), timeout=2.0)
            except asyncio.TimeoutError:
                if got_output and time.time() - last > 6:
                    break
                continue
            if a.debug:
                print(f"[ws] {raw[:400]}", file=sys.stderr)
            try:
                msg = json.loads(raw)
                data = msg.get("data")
                inner = json.loads(data) if isinstance(data, str) else (data or {})
                if isinstance(inner.get("data"), dict):  # Mist double-wraps the payload
                    inner = inner["data"]
            except (ValueError, TypeError, AttributeError):
                continue
            if msg.get("channel") != channel or (session and inner.get("session") != session):
                continue
            chunk = inner.get("raw")
            if chunk:
                got_output = True
                last = time.time()
                print(chunk, end="" if chunk.endswith("\n") else "\n")
        if not got_output:
            print("(no output received before timeout)", file=sys.stderr)
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
