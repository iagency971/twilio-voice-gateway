import Fastify from "fastify";
import { WebSocketServer } from "ws";

const app = Fastify({ logger: true });

// URL publique Render (ou variable que tu mets toi-même)
const PUBLIC_URL =
  process.env.PUBLIC_BASE_URL ||
  process.env.RENDER_EXTERNAL_URL ||
  "https://example.com";

// 1) Webhook Twilio Voice -> renvoie TwiML
app.post("/twilio/voice", async (req, reply) => {
  const wsUrl = PUBLIC_URL.replace("https://", "wss://") + "/twilio/stream";

  const twiml = `<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Connect>
    <Stream url="${wsUrl}" />
  </Connect>
</Response>`;

  reply.header("Content-Type", "text/xml").send(twiml);
});

// 2) Petit endpoint de test (facultatif mais utile)
app.get("/", async () => {
  return { ok: true };
});

// 3) Démarrage HTTP
const port = process.env.PORT || 3000;
await app.listen({ port, host: "0.0.0.0" });

// 4) WebSocket Server attaché au vrai serveur HTTP Fastify
const wss = new WebSocketServer({
  server: app.server,
  path: "/twilio/stream",
});

wss.on("connection", (ws) => {
  console.log("✅ Twilio WebSocket connecté");

  ws.on("message", (data) => {
    let msg;
    try {
      msg = JSON.parse(data.toString());
    } c
