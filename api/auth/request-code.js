// Tokenta Signal auth: request a 6-digit email sign-in code.
// Self-hosted: the code hash is stored in Neon, the email is sent by Resend.
import crypto from "node:crypto";
import {
  cors, ensureSchema, sql, hmac, configured, sendSignInCode,
  CODE_TTL_MIN, RESEND_MIN_INTERVAL_S, MAX_SENDS_PER_HOUR,
} from "./_lib.js";

export default async function handler(req, res) {
  cors(req, res, "POST, OPTIONS");
  if (req.method === "OPTIONS") return res.status(204).end();
  if (req.method !== "POST") return res.status(405).json({ error: "method_not_allowed" });

  const email = String((req.body && req.body.email) || "").trim().toLowerCase();
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(email) || email.length > 254) {
    return res.status(400).json({ error: "invalid_email" });
  }
  if (!configured()) return res.status(500).json({ error: "not_configured" });

  try {
    await ensureSchema();
    const rows = await sql(
      `SELECT (sent_at > now() - ($2 || ' seconds')::interval) AS too_soon,
              (window_start > now() - interval '1 hour' AND window_count >= $3) AS capped
       FROM ts_login_codes WHERE email = $1`,
      [email, String(RESEND_MIN_INTERVAL_S), MAX_SENDS_PER_HOUR]
    );
    const row = rows[0];
    if (row && row.capped) return res.status(429).json({ error: "rate_limited" });
    if (row && row.too_soon) return res.status(200).json({ ok: true });

    const code = String(crypto.randomInt(0, 1000000)).padStart(6, "0");
    await sql(
      `INSERT INTO ts_login_codes (email, code_hash, expires_at, attempts, sent_at, window_start, window_count)
       VALUES ($1, $2, now() + ($3 || ' minutes')::interval, 0, now(), now(), 1)
       ON CONFLICT (email) DO UPDATE SET
         code_hash = EXCLUDED.code_hash,
         expires_at = EXCLUDED.expires_at,
         attempts = 0,
         sent_at = now(),
         window_start = CASE WHEN ts_login_codes.window_start > now() - interval '1 hour'
                              THEN ts_login_codes.window_start ELSE now() END,
         window_count = CASE WHEN ts_login_codes.window_start > now() - interval '1 hour'
                             THEN ts_login_codes.window_count + 1 ELSE 1 END`,
      [email, hmac(email + ":" + code), String(CODE_TTL_MIN)]
    );
    await sendSignInCode(email, code);
    return res.status(200).json({ ok: true });
  } catch (e) {
    return res.status(502).json({ error: "send_failed" });
  }
}
