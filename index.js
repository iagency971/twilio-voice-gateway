import Fastify from "fastify";
import WebSocket, { WebSocketServer } from "ws";
import twilio from "twilio";

const app = Fastify({ logger: true });

// Twilio Voice webhooks
app.addContentTypeParser(
  "application/x-www-form-urlencoded",
  { parseAs: "string" },
  (req, body, done) => done(null, body)
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

app.get("/", async () => ({ status: "ok" }));

/* =========================
   TEST CALL
========================= */

app.get("/test-call", async () => {
  const { TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_FROM_NUMBER } =
    process.env;

  const client = twilio(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN);

  const call = await client.calls.create({
    to: MY_PHONE,
    from: TWILIO_FROM_NUMBER,
    url: `${PUBLIC_URL}/twilio/voice`,
    method: "POST",
  });

  return { ok: true, callSid: call.sid };
});

/* =========================
   TWILIO VOICE WEBHOOK
========================= */

app.post("/twilio/voice", async (req, reply) => {
  const wsUrl =
    PUBLIC_URL.replace("https://", "wss://").replace(/\/$/, "") +
    "/twilio/stream";

  app.log.info({ wsUrl }, "VOICE WEBHOOK");

  reply.type("text/xml").send(`
<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Say voice="alice" language="fr-FR">Connexion au serveur audio.</Say>
  <Connect>
    <Stream url="${wsUrl}" />
  </Connect>
</Response>
`);
});

/* =========================
   WEBSOCKET – MEDIA STREAMS
========================= */

const wss = new WebSocketServer({ noServer: true });

function linear2ulaw(sample) {
  const BIAS = 0x84;
  const CLIP = 32635;

  let sign = (sample >> 8) & 0x80;
  if (sign) sample = -sample;
  if (sample > CLIP) sample = CLIP;

  sample += BIAS;

  let exponent = 7;
  for (
    let expMask = 0x4000;
    (sample & expMask) === 0 && exponent > 0;
    expMask >>= 1
  ) {
    exponent--;
  }

  const mantissa = (sample >> (exponent + 3)) & 0x0f;
  return ~(sign | (exponent << 4) | mantissa) & 0xff;
}

function buildMulawBeep({ freq = 600, seconds = 0.8, sampleRate = 8000 }) {
  const totalSamples = Math.floor(seconds * sampleRate);
  const out = Buffer.alloc(totalSamples);

  for (let i = 0; i < totalSamples; i++) {
    const t = i / sampleRate;
    const pcm = Math.sin(2 * Math.PI * freq * t) * 0.9; // 🔥 AMPLITUDE MAX
    const s16 = Math.max(-1, Math.min(1, pcm)) * 32767;
    out[i] = linear2ulaw(s16 | 0);
  }
  return out;
}

wss.on("connection", (ws) => {
  console.log("✅ Twilio WebSocket connected");

  let streamSid = null;

  function sendFrames(bytes) {
    const frameSize = 160;
    let offset = 0;

    const timer = setInterval(() => {
      if (ws.readyState !== WebSocket.OPEN || !streamSid) {
        clearInterval(timer);
        return;
      }

      const chunk = bytes.subarray(offset, offset + frameSize);
      offset += frameSize;

      if (!chunk.length) {
        clearInterval(timer);
        return;
      }

      ws.send(
        JSON.stringify({
          event: "media",
          streamSid,
          media: { payload: Buffer.from(chunk).toString("base64") },
        })
      );
    }, 20);
  }

  ws.on("message", (msg) => {
    const data = JSON.parse(msg.toString());

    if (data.event === "start") {
      streamSid = data.start.streamSid;
      console.log("▶️ START", streamSid);

      // 🔇 100 ms silence pour couper le ringback
      sendFrames(Buffer.alloc(800, 0xff));

      // 🔊 BEEP immédiatement après
      sendFrames(buildMulawBeep({}));
    }
  });
});

/* =========================
   WS UPGRADE
========================= */

app.server.on("upgrade", (req, socket, head) => {
  if (req.url === "/twilio/stream") {
    wss.handleUpgrade(req, socket, head, (ws) => {
      wss.emit("connection", ws);
    });
  } else {
    socket.destroy();
  }
});

app.listen({ port: PORT, host: "0.0.0.0" }, () =>
  console.log(`🚀 Server on ${PORT}`)
);
