// Tokenta Signal auth: sign out. Clears session cookies and asks
// Supabase to revoke the current session (best effort).
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

function clear(name) {
  return `${name}=; Domain=.tokenta.space; Path=/; HttpOnly; Secure; SameSite=Lax; Max-Age=0`;
}

function parseCookies(req) {
  const out = {};
  const raw = req.headers.cookie || "";
  for (const part of raw.split(";")) {
    const i = part.indexOf("=");
    if (i > 0) out[part.slice(0, i).trim()] = decodeURIComponent(part.slice(i + 1).trim());
  }
  return out;
}

export default async function handler(req, res) {
  cors(req, res);
  if (req.method === "OPTIONS") return res.status(204).end();
  if (req.method !== "POST") return res.status(405).json({ error: "method_not_allowed" });

  const url = process.env.TS_SUPABASE_URL || process.env.SUPABASE_URL;
  const anon = process.env.TS_SUPABASE_ANON_KEY || process.env.SUPABASE_ANON_KEY;
  const at = parseCookies(req).ts_at;
  if (url && anon && at) {
    try {
      await fetch(url + "/auth/v1/logout", {
        method: "POST",
        headers: { apikey: anon, Authorization: "Bearer " + at },
      });
    } catch (e) { /* best effort */ }
  }
  res.setHeader("Set-Cookie", [clear("ts_at"), clear("ts_rt")]);
  return res.status(200).json({ ok: true });
}
