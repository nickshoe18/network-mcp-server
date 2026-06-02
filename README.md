# HPE Networking MCP Server Setup

Setup guides and configuration for connecting Claude Desktop to
Juniper Mist and HPE Aruba Central using the unified hpe-networking-mcp server.

## What This Repo Contains
- Setup guides for macOS Apple Silicon and Windows 11 (see docs/)
- Claude Desktop config example
- Secrets folder structure (examples only — never commit real credentials)

## Quick Start
1. Clone the MCP server: https://github.com/nowireless4u/hpe-networking-mcp
2. Follow the setup guide for your OS in the docs/ folder
3. Copy secrets.example/ to secrets/ and fill in your real credentials
4. Build and run the Docker container
5. Configure Claude Desktop using claude_desktop_config.example.json

## Prerequisites
- Docker Desktop
- Node.js 18+
- Claude Desktop
- HPE GreenLake API credentials (Client ID + Secret)
- Juniper Mist API token

## Guides
- docs/HPE_Networking_MCP_macOS_v2.0.docx — Apple Silicon Mac setup
- docs/HPE_Networking_MCP_Windows11_v2.0.docx — Windows 11 setup

## Claude Desktop Config
See claude_desktop_config.example.json — uses mcp-remote to bridge
Claude Desktop to the Docker container over SSE.

## MCP Server
This setup uses the community hpe-networking-mcp unified server:
https://github.com/nowireless4u/hpe-networking-mcp
Covers Juniper Mist (209 tools) and Aruba Central (624 tools).

## Security
- Never commit real credentials to Git
- The secrets/ folder is excluded via .gitignore
- Use secrets.example/ as a template only
