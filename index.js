import Fastify from "fastify";
import WebSocket, { WebSocketServer } from "ws";
import twilio from "twilio";

const app = Fastify({ logger: true });

// ⚠️ Obligatoire pour Twilio Voice
app.addContentTypeParser(
  "application/x-www-form-urlencoded",
  { parseAs: "string" },
  (req, body, done) => {
    done(null, body);
  }
);

/* =========================
   CONFIG
========================= */

const PORT = process.env.PORT || 10000;
const PUBLIC_URL =
  process.env.PUBLIC_URL || "https://twilio-voice-gateway.onrender.com";

const MY_PHONE = process.env.MY_PHONE || "+590690565128";

/* =========================
   ROOT
========================= */

app.get("/", async () => {
  return { status: "ok" };
});

/* =========================
   TEST CALL
   Twilio appelle ton téléphone
========================= */

app.get("/test-call", async (req, reply) => {
  const { TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_FROM_NUMBER } =
    process.env;

  if (!TWILIO_ACCOUNT_SID || !TWILIO_AUTH_TOKEN || !TWILIO_FROM_NUMBER) {
    return reply.code(400).send({
      error: "Missing Twilio credentials",
    });
  }

  const client = twilio(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN);

  const call = await client.calls.create({
    to: MY_PHONE,
    from: TWILIO_FROM_NUMBER,
    url: `${PUBLIC_URL}/twilio/voice`,
    method: "POST",
  });

  return {
    ok: true,
    callSid: call.sid,
  };
});

/* =========================
   TWILIO VOICE WEBHOOK
   (TwiML)
========================= */

app.post("/twilio/voice", async (req, reply) => {
  const wsUrl =
    PUBLIC_URL.replace("https://", "wss://").replace(/\/$/, "") +
    "/twilio/stream";

  app.log.info({ wsUrl }, "VOICE WEBHOOK");

  const twiml = `<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Say voice="alice" language="fr-FR">
    Connexion au serveur audio.
  </Say>
  <Pause length="1"/>
  <Connect>
    <Stream url="${wsUrl}" />
  </Connect>
</Response>`;

  reply.type("text/xml").send(twiml);
});

app.get("/twilio/voice", async (req, reply) => {
  const wsUrl =
    PUBLIC_URL.replace("https://", "wss://").replace(/\/$/, "") +
    "/twilio/stream";

  const twiml = `<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Say voice="alice" language="fr-FR">
    Connexion au serveur audio.
  </Say>
  <Pause length="1"/>
  <Connect>
    <Stream url="${wsUrl}" />
  </Connect>
</Response>`;

  reply.type("text/xml").send(twiml);
});

/* =========================
   WEBSOCKET – MEDIA STREAMS
========================= */

const wss = new WebSocketServer({ noServer: true });

wss.on("connection", (ws) => {
  console.log("✅ Twilio WebSocket connected");

  ws.on("message", (msg) => {
    let data;
    try {
      data = JSON.parse(msg.toString());
    } catch {
      return;
    }

    if (data.event === "start") {
      console.log("▶️ START", data.start?.streamSid);
    }

    if (data.event === "stop") {
      console.log("⏹ STOP");
    }
  });

  ws.on("close", () => {
    console.log("❌ WebSocket closed");
  });
});

/* =========================
   SERVER + WS UPGRADE
========================= */

app.server.on("upgrade", (req, socket, head) => {
  if (req.url === "/twilio/stream") {
    wss.handleUpgrade(req, socket, head, (ws) => {
      wss.emit("connection", ws, req);
    });
  } else {
    socket.destroy();
  }
});

app.listen({ port: PORT, host: "0.0.0.0" }, () => {
  console.log(`🚀 Server running on port ${PORT}`);
});
