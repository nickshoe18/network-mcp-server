import "dotenv/config";
import express from "express";
import cors from "cors";
import helmet from "helmet";
import rateLimit from "express-rate-limit";
import { chatRouter } from "./routes/chat.js";
import { healthRouter } from "./routes/health.js";
import { findingsRouter } from "./routes/findings.js";
import { start as startAutopilot } from "./poller.js";

const app = express();
const PORT = process.env.PORT || 3001;

app.use(helmet({ contentSecurityPolicy: false }));
app.use(cors({
  origin: "*",
  methods: ["GET", "POST"],
  credentials: true,
}));
app.use(express.json());
app.use(rateLimit({ windowMs: 60 * 1000, max: 60,
  message: { error: "Too many requests." } }));

// Remote (tailnet) requests arrive through the frontend's remote-only port, which sets X-Netops-Remote: 1.
// They must carry a Tailscale identity that is on the allow-list; with no allow-list, remote access is denied.
const ALLOWED_LOGINS = (process.env.TAILSCALE_ALLOWED_LOGINS || "")
  .split(",").map(s => s.trim().toLowerCase()).filter(Boolean);
app.use((req, res, next) => {
  req.remote = req.get("X-Netops-Remote") === "1";
  req.remoteLogin = (req.get("Tailscale-User-Login") || "").toLowerCase();
  if (req.remote && !ALLOWED_LOGINS.includes(req.remoteLogin)) {
    return res.status(403).json({ error: "Remote access denied: Tailscale identity not allowed." });
  }
  next();
});
app.get("/api/whoami", (req, res) => res.json({ remote: req.remote, login: req.remoteLogin || null }));

app.use("/api/chat", chatRouter);
app.use("/api/health", healthRouter);
app.use("/api/findings", findingsRouter);
app.get("/api/ping", (_, res) => res.json({ ok: true, ts: Date.now() }));

app.listen(PORT, () => {
  console.log(`NetOps backend running on port ${PORT}`);
  console.log(`MCP server: ${process.env.MCP_SERVER_URL}`);
  startAutopilot();
});
