import "dotenv/config";
import express from "express";
import cors from "cors";
import helmet from "helmet";
import rateLimit from "express-rate-limit";
import { chatRouter } from "./routes/chat.js";
import { healthRouter } from "./routes/health.js";

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

app.use("/api/chat", chatRouter);
app.use("/api/health", healthRouter);
app.get("/api/ping", (_, res) => res.json({ ok: true, ts: Date.now() }));

app.listen(PORT, () => {
  console.log(`NetOps backend running on port ${PORT}`);
  console.log(`MCP server: ${process.env.MCP_SERVER_URL}`);
});
