import Fastify from "fastify";
import { WebSocketServer } from "ws";
import twilio from "twilio";

const app = Fastify({ logger: true });

// ✅ accepter les webhooks Twilio Voice
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

// ✅ endpoint test : Twilio appelle ton téléphone
app.get("/test-call", async (req, reply) => {
  const { TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_FROM_NUMBER } =
    process.env;

  if (!TWILIO_ACCOUNT_SID || !TWILIO_AUTH_TOKEN || !TWILIO_FROM_NUMBER) {
    return reply.code(400).send({
      ok: false,
      error: "Missing env vars",
      needed: ["TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN", "TWILIO_FROM_NUMBER"],
    });
  }

  const client = twilio(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN);

  const call = await client.calls.create({
    to: MY_PHONE,
    from: TWILIO_FROM_NUMBER,
    url: `${PUBLIC_URL}/twilio/voice`,
    method: "POST",
  });

  return { ok: true, callSid: call.sid };
});

// ✅ webhook Twilio Voice : stream seulement (pas de dial)
app.post("/twilio/voice", async (req, reply) => {
  const wsUrl = PUBLIC_URL.replace("https://", "wss://").replace(/\/$/, "") + "/twilio/stream";
  app.log.info({ wsUrl }, "VOICE WEBHOOK");

  const twiml = `<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Say voice="alice" language="fr-FR">Connexion au serveur audio.</Say>
  <Pause length="1"/>
  <Connect>
    <Stream url="${wsUrl}" track="both_tracks" />
  </Connect>
</Response>`;

  reply.type("text/xml").send(twiml);
});

// ✅ et GET aussi (au cas où)
app.get("/twilio/voice", async (req, reply) => {
  const wsUrl = PUBLIC_URL.replace("https://", "wss://").replace(/\/$/, "") + "/twilio/stream";
  app.log.info({ wsUrl }, "VOICE WEBHOOK (GET)");

  const twiml = `<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Say voice="alice" language="fr-FR">Connexion au serveur audio.</Say>
  <Pause length="1"/>
  <Connect>
    <Stream url="${wsUrl}" track="both_tracks" />
  </Connect>
</Response>`;

  reply.type("text/xml").send(twiml);
});

// ✅ démarre le serveur HTTP
await app.listen({ port: PORT, host: "0.0.0.0" });

// ✅ WebSocket attaché au serveur (version qui marchait chez toi)
const wss = new WebSocketServer({
  server: app.server,
  path: "/twilio/stream",
});

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

  ws.on("close", () => console.log("❌ WebSocket closed"));
});
