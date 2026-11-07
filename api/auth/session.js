// Tokenta Signal auth: adopt a session that arrived via an email link.
// The email link lands on the site with tokens in the URL fragment; the
// page forwards them here once, we validate and set the session cookies.
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

  const at = String((req.body && req.body.access_token) || "");
  const rt = String((req.body && req.body.refresh_token) || "");
  if (!at || !rt) return res.status(400).json({ error: "missing_tokens" });
  const url = process.env.TS_SUPABASE_URL || process.env.SUPABASE_URL;
  const anon = process.env.TS_SUPABASE_ANON_KEY || process.env.SUPABASE_ANON_KEY;
  if (!url || !anon) return res.status(500).json({ error: "not_configured" });

  try {
    const ur = await fetch(url + "/auth/v1/user", {
      headers: { apikey: anon, Authorization: "Bearer " + at },
    });
    if (!ur.ok) return res.status(401).json({ error: "invalid_session" });
    const user = await ur.json();
    res.setHeader("Set-Cookie", [
      cookie("ts_at", at, 3600),
      cookie("ts_rt", rt, 60 * 60 * 24 * 30),
    ]);
    return res.status(200).json({ ok: true, user: { email: user.email } });
  } catch (e) {
    return res.status(502).json({ error: "session_failed" });
  }
}
