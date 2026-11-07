// Tokenta Signal auth: verify the 6-digit email code, set session cookies.
const ALLOWED = [
  "https://signal.tokenta.space",
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

function cookie(name, value, maxAge) {
  return `${name}=${encodeURIComponent(value)}; Domain=.tokenta.space; Path=/; HttpOnly; Secure; SameSite=Lax; Max-Age=${maxAge}`;
}

export default async function handler(req, res) {
  cors(req, res);
  if (req.method === "OPTIONS") return res.status(204).end();
  if (req.method !== "POST") return res.status(405).json({ error: "method_not_allowed" });

  const email = String((req.body && req.body.email) || "").trim().toLowerCase();
  const token = String((req.body && req.body.token) || "").trim();
  if (!email || !/^\d{6}$/.test(token)) {
    return res.status(400).json({ error: "invalid_code" });
  }
  const url = process.env.TS_SUPABASE_URL || process.env.SUPABASE_URL;
  const anon = process.env.TS_SUPABASE_ANON_KEY || process.env.SUPABASE_ANON_KEY;
  if (!url || !anon) return res.status(500).json({ error: "not_configured" });

  try {
    const attempt = (type) =>
      fetch(url + "/auth/v1/verify", {
        method: "POST",
        headers: { apikey: anon, "Content-Type": "application/json" },
        body: JSON.stringify({ type, email, token }),
      });
    let r = await attempt("email");
    let data = await r.json().catch(() => ({}));
    if (!r.ok || !data.access_token) {
      // First-time registrations are issued a signup confirmation token.
      r = await attempt("signup");
      data = await r.json().catch(() => ({}));
    }
    if (!r.ok || !data.access_token) {
      return res.status(401).json({ error: "code_rejected" });
    }
    res.setHeader("Set-Cookie", [
      cookie("ts_at", data.access_token, 3600),
      cookie("ts_rt", data.refresh_token, 60 * 60 * 24 * 30),
    ]);
    return res.status(200).json({
      ok: true,
      user: { email: data.user && data.user.email },
    });
  } catch (e) {
    return res.status(502).json({ error: "verify_failed" });
  }
}
