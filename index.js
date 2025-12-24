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

  let streamSid = null;
  let beepTimer = null;

  // --- μ-law encoder (PCM 16-bit -> G.711 μ-law 8-bit) ---
  function linear2ulaw(sample) {
    const BIAS = 0x84;
    const CLIP = 32635;

    let sign = (sample >> 8) & 0x80;
    if (sign !== 0) sample = -sample;
    if (sample > CLIP) sample = CLIP;

    sample = sample + BIAS;

    // exponent
    let exponent = 7;
    for (let expMask = 0x4000; (sample & expMask) === 0 && exponent > 0; expMask >>= 1) {
      exponent--;
    }

    // mantissa
    let mantissa = (sample >> (exponent + 3)) & 0x0f;
    let ulawByte = ~(sign | (exponent << 4) | mantissa);

    return ulawByte & 0xff;
  }

  function pcm16ToMulawBytes(pcm16) {
    const out = Buffer.alloc(pcm16.length);
    for (let i = 0; i < pcm16.length; i++) out[i] = linear2ulaw(pcm16[i]);
    return out;
  }

  // Génère un beep PCM 16-bit à 8kHz
  function generateBeepPcm16({ freq = 440, ms = 1000, sampleRate = 8000, amp = 0.35 }) {
    const totalSamples = Math.floor((ms / 1000) * sampleRate);
    const pcm = new Int16Array(totalSamples);
    const twoPiF = 2 * Math.PI * freq;

    for (let n = 0; n < totalSamples; n++) {
      const t = n / sampleRate;
      // petite enveloppe pour éviter les "clicks" (attaque/relâche)
      const attack = Math.min(1, n / 80);
      const release = Math.min(1, (totalSamples - n) / 80);
      const env = Math.min(attack, release);

      const s = Math.sin(twoPiF * t) * amp * env;
      pcm[n] = Math.max(-1, Math.min(1, s)) * 32767;
    }
    return pcm;
  }

  // Envoie du μ-law 8kHz à Twilio en frames de 20ms (160 samples => 160 bytes μ-law)
  function sendMulawAudio(streamSid, mulawBytes, frameMs = 20) {
    const bytesPerFrame = 160; // 20ms à 8kHz = 160 échantillons => 160 bytes μ-law
    let offset = 0;

    if (beepTimer) clearInterval(beepTimer);

    beepTimer = setInterval(() => {
      if (ws.readyState !== ws.OPEN) {
        clearInterval(beepTimer);
        beepTimer = null;
        return;
      }
      if (!streamSid) return;

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

      // 🔔 Beep 1 seconde
      const pcm = generateBeepPcm16({ freq: 440, ms: 1000, sampleRate: 8000, amp: 0.35 });
      const mulaw = pcm16ToMulawBytes(pcm);

      // Envoi après un petit délai (laisse Twilio stabiliser le stream)
      setTimeout(() => sendMulawAudio(streamSid, mulaw), 200);
      return;
    }

    if (msg.event === "stop") {
      console.log("⏹ STOP");
      return;
    }

    // msg.event === "media" => audio entrant (on s’en servira plus tard pour STT)
  });

  ws.on("close", () => {
    console.log("❌ WebSocket closed");
    if (beepTimer) clearInterval(beepTimer);
    beepTimer = null;
  });
});

