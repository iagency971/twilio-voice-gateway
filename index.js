import Fastify from "fastify";
import { WebSocketServer } from "ws";

const app = Fastify({ logger: true });

// URL publique Render
const PUBLIC_URL =
  process.env.PUBLIC_BASE_URL ||
  process.env.RENDER_EXTERNAL_URL ||
  "https://example.com";
// Twilio envoie souvent application/x-www-form-urlencoded
app.addContentTypeParser(
  "application/x-www-form-urlencoded",
  { parseAs: "string" },
  (req, body, done) => done(null, body)
);
app.post("/twilio/voice", async (req, reply) => {
  const wsUrl = PUBLIC_URL.replace("https://", "wss://") + "/twilio/stream";

  const twiml = `<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Connect>
    <Stream url="${wsUrl}" />
  </Connect>
</Response>`;

  reply.type("text/xml").send(twiml);
});

// Endpoint test
app.get("/", async () => {
  return { status: "ok" };
});

// Start HTTP server
const port = process.env.PORT || 3000;
await app.listen({ port, host: "0.0.0.0" });

// WebSocket Media Stream
const wss = new WebSocketServer({
  server: app.server,
  path: "/twilio/stream",
});

wss.on("connection", (ws) => {
  console.log("✅ Twilio WebSocket connected");

  ws.on("message", (data) => {
    let msg;
    try {
      msg = JSON.parse(data.toString());
    } catch {
      return;
    }

    if (msg.event === "start") {
      console.log("▶️ START", msg.start);
    }

    if (msg.event === "stop") {
      console.log("⏹ STOP");
    }
  });

  ws.on("close", () => {
    console.log("❌ WebSocket closed");
  });
});
