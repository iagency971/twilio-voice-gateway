import Fastify from "fastify";
import { WebSocketServer } from "ws";

const app = Fastify({ logger: true });

// Mets ici ton numéro perso (doit être Verified Caller ID en trial)
const MY_PHONE = process.env.MY_PHONE || "+590690565128";
// CallerId: en trial depuis client web, utilise un numéro "validé" (souvent ton numéro perso)
const CALLER_ID = process.env.CALLER_ID || MY_PHONE;

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

app.get("/", async () => ({ status: "ok" }));

/**
 * MODE TEST #1 (Dial) : fait sonner ton téléphone
 * -> Utile pour vérifier que Twilio peut composer ton numéro
 *
 * MODE TEST #2 (Stream) : connecte le call au WebSocket Media Streams
 * -> Utile pour l'agent vocal temps réel
 *
 * On bascule entre les deux via ?mode=dial ou ?mode=stream
 */
app.post("/twilio/voice", async (req, reply) => {
  const mode = (req.query?.mode || "stream").toString();
  const wsUrl = PUBLIC_URL.replace("https://", "wss://") + "/twilio/stream";

  let twiml;

  if (mode === "dial") {
    twiml = `<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Say voice="alice">Test appel sortant</Say>
  <Dial callerId="${CALLER_ID}">
    <Number>${MY_PHONE}</Number>
  </Dial>
</Response>`;
  } else {
    twiml = `<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Connect>
    <Stream url="${wsUrl}" />
  </Connect>
</Response>`;
  }

  reply.type("text/xml").send(twiml);
});

// Start HTTP server
const port = process.env.PORT || 3000;
await app.listen({ port, host: "0.0.0.0" });

// WebSocket Media Streams
const wss = new WebSocketServer({
  server: app.server,
  path: "/twilio/stream",
});

wss.on("connection", (ws) => {
  console.log("✅ Twilio WebSocket connected");

  let streamSid = null;
  let beepTimer = null;

  // --- μ-law encoder (PCM16 -> G.711 μ-law) ---
  function linear2ulaw(sample) {
    const BIAS = 0x84;
    const CLIP = 32635;

    let sign = (sample >> 8) & 0x80;
    if (sign !== 0) sample = -sample;
    if (sample > CLIP) sample = CLIP;

    sample += BIAS;

    let exponent = 7;
    for (let expMask = 0x4000; (sample & expMask) === 0 && exponent > 0; expMask >>= 1) {
      exponent--;
    }

    const mantissa = (sample >> (exponent + 3)) & 0x0f;
    const ulawByte = ~(sign | (exponent << 4) | mantissa);
    return ulawByte & 0xff;
  }

  function pcm16ToMulawBytes(pcm16) {
    const out = Buffer.alloc(pcm16.length);
    for (let i = 0; i < pcm16.length; i++) out[i] = linear2ulaw(pcm16[i]);
    return out;
  }

  function generateBeepPcm16({ freq = 440, ms = 700, sampleRate = 8000, amp = 0.35 }) {
    const totalSamples = Math.floor((ms / 1000) * sampleRate);
    const pcm = new Int16Array(totalSamples);
    const twoPiF = 2 * Math.PI * freq;

    for (let n = 0; n < totalSamples; n++) {
      const t = n / sampleRate;
      const attack = Math.min(1, n / 80);
      const release = Math.min(1, (totalSamples - n) / 80);
      const env = Math.min(attack, release);

      const s = Math.sin(twoPiF * t) * amp * env;
      pcm[n] = Math.max(-1, Math.min(1, s)) * 32767;
    }
    return pcm;
  }

  function sendMulawAudio(mulawBytes, frameMs = 20) {
    const bytesPerFrame = 160; // 20ms @ 8kHz
    let offset = 0;

    if (beepTimer) clearInterval(beepTimer);

    beepTimer = setInterval(() => {
      if (ws.readyState !== ws.OPEN || !streamSid) {
        clearInterval(beepTimer);
        beepTimer = null;
        return;
      }

      const chunk = mulawBytes.subarray(offset, offset + bytesPerFrame);
      offset += bytesPerFrame;

      if (chunk.length === 0) {
        clearInterval(beepTimer);
        beepTimer = null;
        return;
      }

      const payload = Buffer.from(chunk).toString("base64");
      ws.send(
        JSON.stringify({
          event: "media",
          streamSid,
          media: { payload },
        })
      );
    }, frameMs);
  }

  ws.on("message", (data) => {
    let msg;
    try {
      msg = JSON.parse(data.toString());
    } catch {
      return;
    }

    if (msg.event === "start") {
      streamSid = msg.start.streamSid;
      console.log("▶️ START", msg.start);

      // 🔔 Beep court dès le début
      const pcm = generateBeepPcm16({ freq: 440, ms: 700 });
      const mulaw = pcm16ToMulawBytes(pcm);
      setTimeout(() => sendMulawAudio(mulaw), 150);
      return;
    }

    if (msg.event === "stop") {
      console.log("⏹ STOP");
      return;
    }
  });

  ws.on("close", () => {
    console.log("❌ WebSocket closed");
    if (beepTimer) clearInterval(beepTimer);
    beepTimer = null;
  });
});


