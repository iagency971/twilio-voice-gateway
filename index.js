import Fastify from "fastify";
import { WebSocketServer } from "ws";
import WebSocket from "ws";
import twilio from "twilio";

const app = Fastify({ logger: true });

// ✅ Twilio webhooks voice arrivent en x-www-form-urlencoded
app.addContentTypeParser(
  "application/x-www-form-urlencoded",
  { parseAs: "string" },
  (req, body, done) => done(null, body)
);

const PORT = process.env.PORT || 10000;
const PUBLIC_URL =
  process.env.PUBLIC_URL || "https://twilio-voice-gateway.onrender.com";

const MY_PHONE = process.env.MY_PHONE || "+590690565128";

app.get("/", async () => ({ status: "ok" }));

/** 1 clic = Twilio appelle ton téléphone */
app.get("/test-call", async () => {
  const { TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_FROM_NUMBER } =
    process.env;

  if (!TWILIO_ACCOUNT_SID || !TWILIO_AUTH_TOKEN || !TWILIO_FROM_NUMBER) {
    return {
      ok: false,
      error: "Missing env vars",
      needed: ["TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN", "TWILIO_FROM_NUMBER"],
    };
  }

  const client = twilio(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN);

  const call = await client.calls.create({
    to: MY_PHONE,
    from: TWILIO_FROM_NUMBER,
    url: `${PUBLIC_URL}/twilio/voice?mode=outbound`,
    method: "POST",
  });

  return { ok: true, callSid: call.sid };
});

/** TwiML Voice webhook */
async function voiceHandler(req, reply) {
  const mode = (req.query?.mode || "outbound").toString();
  const wsUrl = PUBLIC_URL.replace("https://", "wss://") + "/twilio/stream";

  app.log.info({ mode, wsUrl }, "VOICE WEBHOOK");

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

/** Start HTTP server */
await app.listen({ port: PORT, host: "0.0.0.0" });

/** WebSocket Media Streams — attaché au serveur (stable Render) */
const wss = new WebSocketServer({
  server: app.server,
  path: "/twilio/stream",
});

wss.on("connection", (ws) => {
  console.log("✅ Twilio WebSocket connected");

  let streamSid = null;

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

  function buildMulawBeep({ freq = 440, seconds = 0.6, sampleRate = 8000 }) {
    const totalSamples = Math.floor(seconds * sampleRate);
    const out = Buffer.alloc(totalSamples);

    for (let i = 0; i < totalSamples; i++) {
      const t = i / sampleRate;
      const pcm = Math.sin(2 * Math.PI * freq * t) * 0.35;
      const s16 = Math.max(-1, Math.min(1, pcm)) * 32767;
      out[i] = linear2ulaw(s16 | 0);
    }
    return out;
  }

  function sendMulawInFrames(mulawBytes) {
    const frameSize = 160; // 20ms @ 8kHz
    let offset = 0;

    const timer = setInterval(() => {
      if (ws.readyState !== WebSocket.OPEN || !streamSid) {
        clearInterval(timer);
        return;
      }

      const chunk = mulawBytes.subarray(offset, offset + frameSize);
      offset += frameSize;

      if (chunk.length === 0) {
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
    let data;
    try {
      data = JSON.parse(msg.toString());
    } catch {
      return;
    }

    if (data.event === "start") {
      streamSid = data.start.streamSid;
      console.log("▶️ START", { streamSid });

      setTimeout(() => {
        const beep = buildMulawBeep({ seconds: 0.6 });
        sendMulawInFrames(beep);
      }, 150);
    }

    if (data.event === "stop") {
      console.log("⏹ STOP");
    }
  });

  ws.on("close", () => console.log("❌ WebSocket closed"));
});
