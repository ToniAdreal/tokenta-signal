// Tokenta Signal auth: who am I. Refreshes the session when needed and
// returns the account email plus the plan from public.profiles.
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
    res.setHeader("Access-Control-Allow-Methods", "GET, OPTIONS");
    res.setHeader("Access-Control-Allow-Headers", "Content-Type");
    res.setHeader("Vary", "Origin");
  }
}

function cookie(name, value, maxAge) {
  return `${name}=${encodeURIComponent(value)}; Domain=.tokenta.space; Path=/; HttpOnly; Secure; SameSite=Lax; Max-Age=${maxAge}`;
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
  if (req.method !== "GET") return res.status(405).json({ error: "method_not_allowed" });

  const url = process.env.SUPABASE_URL;
  const anon = process.env.SUPABASE_ANON_KEY;
  if (!url || !anon) return res.status(500).json({ error: "not_configured" });

  const c = parseCookies(req);
  let at = c.ts_at || "";
  const rt = c.ts_rt || "";
  if (!at && !rt) return res.status(200).json({ authenticated: false });

  try {
    if (!at && rt) {
      const r = await fetch(url + "/auth/v1/token?grant_type=refresh_token", {
        method: "POST",
        headers: { apikey: anon, "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: rt }),
      });
      const data = await r.json().catch(() => ({}));
      if (!r.ok || !data.access_token) return res.status(200).json({ authenticated: false });
      at = data.access_token;
      res.setHeader("Set-Cookie", [
        cookie("ts_at", data.access_token, 3600),
        cookie("ts_rt", data.refresh_token, 60 * 60 * 24 * 30),
      ]);
    }
    const ur = await fetch(url + "/auth/v1/user", {
      headers: { apikey: anon, Authorization: "Bearer " + at },
    });
    if (!ur.ok) return res.status(200).json({ authenticated: false });
    const user = await ur.json();
    let plan = "registered";
    const pr = await fetch(
      url + "/rest/v1/profiles?select=plan&id=eq." + encodeURIComponent(user.id),
      { headers: { apikey: anon, Authorization: "Bearer " + at } }
    );
    if (pr.ok) {
      const rows = await pr.json().catch(() => []);
      if (rows && rows[0] && rows[0].plan) plan = rows[0].plan;
    }
    return res.status(200).json({ authenticated: true, email: user.email, plan });
  } catch (e) {
    return res.status(200).json({ authenticated: false });
  }
}
