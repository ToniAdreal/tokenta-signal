// Tokenta Signal auth: who am I. Refreshes the session when the access
// cookie has expired but the refresh cookie is still valid, and returns
// the account email plus the plan stored on the user row.
import {
  cors, ensureSchema, configured, parseCookies,
  userByAccessToken, rotateByRefreshToken,
} from "./_lib.js";

export default async function handler(req, res) {
  cors(req, res, "GET, OPTIONS");
  if (req.method === "OPTIONS") return res.status(204).end();
  if (req.method !== "GET") return res.status(405).json({ error: "method_not_allowed" });
  if (!configured()) return res.status(500).json({ error: "not_configured" });

  const c = parseCookies(req);
  const at = c.ts_at || "";
  const rt = c.ts_rt || "";
  if (!at && !rt) return res.status(200).json({ authenticated: false });

  try {
    await ensureSchema();
    if (at) {
      const user = await userByAccessToken(at);
      if (!user) return res.status(200).json({ authenticated: false });
      return res.status(200).json({ authenticated: true, email: user.email, plan: user.plan });
    }
    const user = await rotateByRefreshToken(res, rt);
    if (!user) return res.status(200).json({ authenticated: false });
    return res.status(200).json({ authenticated: true, email: user.email, plan: user.plan });
  } catch (e) {
    return res.status(200).json({ authenticated: false });
  }
}
