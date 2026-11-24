// Tokenta Signal auth: verify the 6-digit email code, set session cookies.
// Self-hosted: codes and sessions live in Neon (see _lib.js).
import {
  cors, ensureSchema, sql, hmac, safeEqual, configured,
  upsertUser, createSession, CODE_MAX_ATTEMPTS,
} from "./_lib.js";

export default async function handler(req, res) {
  cors(req, res, "POST, OPTIONS");
  if (req.method === "OPTIONS") return res.status(204).end();
  if (req.method !== "POST") return res.status(405).json({ error: "method_not_allowed" });

  const email = String((req.body && req.body.email) || "").trim().toLowerCase();
  const token = String((req.body && req.body.token) || "").trim();
  if (!email || !/^\d{6}$/.test(token)) {
    return res.status(400).json({ error: "invalid_code" });
  }
  if (!configured()) return res.status(500).json({ error: "not_configured" });

  try {
    await ensureSchema();
    const rows = await sql(
      `SELECT code_hash, attempts, (expires_at > now()) AS fresh
       FROM ts_login_codes WHERE email = $1`,
      [email]
    );
    const row = rows[0];
    if (!row || !row.fresh || row.attempts >= CODE_MAX_ATTEMPTS) {
      if (row && row.attempts >= CODE_MAX_ATTEMPTS) {
        await sql(`DELETE FROM ts_login_codes WHERE email = $1`, [email]);
      }
      return res.status(401).json({ error: "code_rejected" });
    }
    if (!safeEqual(row.code_hash, hmac(email + ":" + token))) {
      await sql(
        `UPDATE ts_login_codes SET attempts = attempts + 1 WHERE email = $1`,
        [email]
      );
      return res.status(401).json({ error: "code_rejected" });
    }
    await sql(`DELETE FROM ts_login_codes WHERE email = $1`, [email]);
    const user = await upsertUser(email);
    await createSession(res, user.id);
    return res.status(200).json({ ok: true, user: { email } });
  } catch (e) {
    return res.status(502).json({ error: "verify_failed" });
  }
}
