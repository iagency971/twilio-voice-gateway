import Fastify from "fastify";
import { WebSocketServer } from "ws";

const app = Fastify({ logger: true });

// Render fournit automatiquement l’URL publique
const PUBLIC_URL =
  process.env.RENDER_EXTERNAL_URL || "https://example.com";

// === Webhook Twilio Voice ===
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

// === Lancement serveur HTTP ===
const port = process.env.PORT || 3000;
const server = await app.listen({ port, host: "0.0.0.0" });

// === WebSocket pour Twilio Media Streams ===
const wss = new WebSocketServer({
  server,
  path: "/twilio/stream",
});

wss.on("connection", (ws) => {
  console.log("✅ Twilio WebSocket connecté");

  ws.on("message", (data) => {
    const msg = JSON.parse(data.toString());

    if (msg.event === "start") {
      console.log("▶️ START", msg.start);
    }

    if (msg.event === "media") {
      // Audio entrant (pour l’instant on ne fait rien)
    }

    if (msg.event === "stop") {
      console.log("⏹ STOP");
    }
  });
});
