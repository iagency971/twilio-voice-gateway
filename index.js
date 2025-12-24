import Fastify from "fastify";
import WebSocket, { WebSocketServer } from "ws";
import twilio from "twilio";

const app = Fastify({ logger: true });

/* =========================
   CONFIG
========================= */

const PORT = process.env.PORT || 10000;
const PUBLIC_URL =
  process.env.PUBLIC_URL || "https://twilio-voice-gateway.onrender.com";

const MY_PHONE = process.env.MY_PHONE || "+590690565128";
const CALLER_ID = process.env.TWILIO_FROM_NUMBER || "+16802034198";

/* =========================
   ROOT
========================= */

app.get("/", async () => {
  return { status: "ok" };
});

/* =========================
   TEST CALL (Twilio appelle ton téléphone)
========================= */

app.get("/test-call", async (req, reply) => {
  const {
    TWILIO_ACCOUNT_SID,
    TWILIO_AUTH_TOKEN,
    TWILIO_FROM_NUMBER,
  } = process.env;

  if (!TWILIO_ACCOUNT_SID || !TWILIO_AUTH_TOKEN || !TWILIO_FROM_NUMBER) {
    return reply.code(400).send({
      error: "Missing Twilio credentials",
    });
  }

  const client = twilio(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN);

  const call = await client.calls.create({
    to: MY_PHONE,
    from: TWILIO_FROM_NUMBER,
    url: `${PUBLIC_URL}/twilio/voice?mode=outbound`,
    method: "POST",
  });

  return {
    ok: true,
    callSid: call.sid,
  };
});

/* =========================
   TWILIO VOICE WEBHOOK
========================= */

async function voiceHandler(req, reply) {
  const mode = (req.query?.mode || "outbound").toString();
  const wsUrl = PUBLIC_URL.replace("https://", "wss://") + "/twilio/stream";

  app.log.info({ mode }, "VOICE WEBHOOK");

  let twiml;

  // ⚠️ IMPORTANT :
  // - PAS de <Dial> ici
  // - Twilio a déjà appelé le téléphone
  if (mode === "outbound") {
    twiml = `<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Say voice="alice" language="fr-FR">
    Connexion au serveur audio.
  </Say>
  <Pause length="1"/>
  <Connect>
    <Stream url="${wsUrl}" />
  </Connect>
</Response>`;
  } else {
    twiml = `<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Say>Invalid mode</Say>
</Response>`;
  }

  reply.type("text/xml").send(twiml);
}

app.post("/twilio/voice", voiceHandler);
app.get("/twilio/voice", voiceHandler);

/* =========================
   WEBSOCKET – MEDIA STREAMS
========================= */

const wss = new WebSocketServer({ noServer: true });

wss.on("connection", (ws) => {
  console.log("✅ Twilio WebSocket connected");

  ws.on("message", (msg) => {
    const data = JSON.parse(msg.toString());

    if (data.event === "start") {
      console.log("▶️ START stream");

      // 🎵 Beep (440 Hz, µ-law, 8000 Hz, ~300 ms)
      const beep = Buffer.alloc(2400);
      for (let i = 0; i < beep.length; i++) {
        beep[i] =
          128 + Math.round(30 * Math.sin((2 * Math.PI * 440 * i) / 8000));
      }

      ws.send(
        JSON.stringify({
          event: "media",
          media: {
            payload: beep.toString("base64"),
          },
        })
      );
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
  }
});

app.listen({ port: PORT, host: "0.0.0.0" }, () => {
  console.log(`🚀 Server running on port ${PORT}`);
});
