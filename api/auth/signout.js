// Tokenta Signal auth: sign out. Deletes the session row (best effort)
// and clears the session cookies.
import {
  cors, ensureSchema, configured, parseCookies, clearCookie,
  deleteSessionByAccessToken,
} from "./_lib.js";

export default async function handler(req, res) {
  cors(req, res, "POST, OPTIONS");
  if (req.method === "OPTIONS") return res.status(204).end();
  if (req.method !== "POST") return res.status(405).json({ error: "method_not_allowed" });

  const at = parseCookies(req).ts_at;
  if (configured() && at) {
    try {
      await ensureSchema();
      await deleteSessionByAccessToken(at);
    } catch (e) { /* best effort */ }
  }
  res.setHeader("Set-Cookie", [clearCookie("ts_at"), clearCookie("ts_rt")]);
  return res.status(200).json({ ok: true });
}
