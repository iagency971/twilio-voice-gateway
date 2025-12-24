import Fastify from "fastify";
import twilio from "twilio";
import WebSocket, { WebSocketServer } from "ws";

/* =========================
   FASTIFY
========================= */

const app = Fastify({ logger: true });

// ✅ Twilio Voice webhooks arrivent en x-www-form-urlencoded
app.addContentTypeParser(
  "application/x-www-form-urlencoded",
  { parseAs: "string" },
  (req, body, done) => done(null, body)
);

/* =========================
   CONFIG
========================= */

const PORT = process.env.PORT || 10000;

// IMPORTANT : mets PUBLIC_URL dans Render: https://twilio-voice-gateway.onrender.com
const PUBLIC_URL =
  process.env.PUBLIC_URL || "https://twilio-voice-gateway.onrender.com";

const MY_PHONE = process.env.MY_PHONE || "+590690565128";

/* =========================
   ROUTES
========================= */

app.get("/", async () => ({ status: "ok" }));

/**
 * 1 clic = Twilio appelle ton téléphone (vrai appel)
 * Variables Render nécessaires :
 * - TWILIO_ACCOUNT_SID
 * - TWILIO_AUTH_TOKEN
 * - TWILIO_FROM_NUMBER
 * - MY_PHONE
 * - PUBLIC_URL
 */
app.get("/test-call", async (req, reply) => {
  const { TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_FROM_NUMBER } =
    process.env;

  if (!TWILIO_ACCOUNT_SID || !TWILIO_AUTH_TOKEN || !TWILIO_FROM_NUMBER) {
    return reply.code(400).send({
      ok: false,
      error: "Missing env vars",
      needed: ["TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN", "TWILIO_FROM_NUMBER"],
      got: {
        TWILIO_ACCOUNT_SID: !!TWILIO_ACCOUNT_SID,
        TWILIO_AUTH_TOKEN: !!TWILIO_AUTH_TOKEN,
        TWILIO_FROM_NUMBER: !!TWILIO_FROM_NUMBER,
        MY_PHONE: !!process.env.MY_PHONE,
        PUBLIC_URL: !!process.env.PUBLIC_URL,
      },
    });
  }

  const client = twilio(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN);

  // Twilio va récupérer le TwiML ici
  const url = `${PUBLIC_URL}/twilio/voice?mode=outbound`;

  const call = await client.calls.create({
    to: MY_PHONE,
    from: TWILIO_FROM_NUMBER,
    url,
    method: "POST",
  });

  return { ok: true, callSid: call.sid, url };
});

/**
 * Voice webhook -> renvoie TwiML
 * Objectif : Connect + Stream vers wss://.../twilio/stream
 */
async function voiceHandler(req, reply) {
  const mode = (req.query?.mode || "outbound").toString();

  // ✅ base fiable côté Render (si dispo)
  const base =
    process.env.RENDER_EXTERNAL_URL || process.env.PUBLIC_URL || PUBLIC_URL;

  const wsUrl =
    base.replace("https://", "wss://").replace(/\/$/, "") + "/twilio/stream";

  app.log.info({ mode, base, wsUrl }, "VOICE WEBHOOK");

  let twiml;

  if (mode === "outbound") {
    twiml = `<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Say voice="alice" language="fr-FR">Connexion au serveur audio.</Say>
  <Pause length="1"/>
  <Connect>
    <Stream url="${wsUrl}" track="both_tracks" />
  </Connect>
</Response>`;
  } else {
    twiml = `<?xml version="1.0" encoding="UTF-8"?>
<Response><Say>Invalid mode</Say></Response>`;
  }

  reply.type("text/xml").send(twiml);
}

app.post("/twilio/voice", voiceHandler);
app.get("/twilio/voice", voiceHandler);

/* =========================
   START HTTP SERVER
========================= */

await app.listen({ port: PORT, host: "0.0.0.0" });

/* =========================
   WEBSOCKET (Media Streams)
   Upgrade tolérant: /twilio/stream et /twilio/stream?...
========================= */

const wss = new WebSocketServer({ noServer: true });

app.server.on("upgrade", (req, socket, head) => {
  const url = req.url || "";
  app.log.info({ url }, "WS UPGRADE REQUEST");

  // ✅ tolérant : accepte query params éventuels
  if (!url.startsWith("/twilio/stream")) {
    app.log.warn({ url }, "WS REJECT (bad path)");
    socket.destroy();
    return;
  }

  wss.handleUpgrade(req, socket, head, (ws) => {
    wss.emit("connection", ws, req);
  });
});

wss.on("connection", (ws, req) => {
  app.log.info({ url: req.url }, "✅ WS CONNECTED");

  ws.on("message", (msg) => {
    let data;
    try {
      data = JSON.parse(msg.toString());
    } catch {
      return;
    }

    if (data.event === "start") {
      app.log.info({ streamSid: data.start?.streamSid }, "▶️ START");
    }

    if (data.event === "stop") {
      app.log.info("⏹ STOP");
    }
  });

  ws.on("close", () => app.log.info("❌ WS CLOSED"));
});
