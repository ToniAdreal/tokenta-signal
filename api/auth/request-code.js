// Tokenta Signal auth: request a 6-digit email sign-in code (Supabase OTP).
// Runs on the tokenta-signal-auth Vercel project (auth.tokenta.space).
// Uses only environment provided by the Vercel Supabase integration.
const ALLOWED = [
  "https://signal.tokenta.space",
  "https://go.tokenta.space",
  "https://signals.tokenta.space",
  "https://tokenta-signal.vercel.app",
  "https://auth.tokenta.space",
];

function cors(req, res) {
  const origin = req.headers.origin || "";
  if (ALLOWED.includes(origin)) {
    res.setHeader("Access-Control-Allow-Origin", origin);
    res.setHeader("Access-Control-Allow-Credentials", "true");
    res.setHeader("Access-Control-Allow-Methods", "POST, OPTIONS");
    res.setHeader("Access-Control-Allow-Headers", "Content-Type");
    res.setHeader("Vary", "Origin");
  }
}

export default async function handler(req, res) {
  cors(req, res);
  if (req.method === "OPTIONS") return res.status(204).end();
  if (req.method !== "POST") return res.status(405).json({ error: "method_not_allowed" });

  const email = String((req.body && req.body.email) || "").trim().toLowerCase();
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(email) || email.length > 254) {
    return res.status(400).json({ error: "invalid_email" });
  }
  const url = process.env.TS_SUPABASE_URL || process.env.SUPABASE_URL;
  const anon = process.env.TS_SUPABASE_ANON_KEY || process.env.SUPABASE_ANON_KEY;
  if (!url || !anon) return res.status(500).json({ error: "not_configured" });

  try {
    const r = await fetch(url + "/auth/v1/otp", {
      method: "POST",
      headers: { apikey: anon, "Content-Type": "application/json" },
      body: JSON.stringify({ email, create_user: true }),
    });
    if (!r.ok) return res.status(502).json({ error: "send_failed" });
    return res.status(200).json({ ok: true });
  } catch (e) {
    return res.status(502).json({ error: "send_failed" });
  }
}
