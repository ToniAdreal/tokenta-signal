// Tokenta Signal auth: shared helpers for the self-hosted auth backend.
// Storage is a Neon Postgres database reached over its HTTP SQL API
// (no npm dependencies). Sign-in codes are delivered by Resend.
// Sessions are opaque random tokens; only their hashes are stored.
import crypto from "node:crypto";

export const ALLOWED = [
  "https://signal.tokenta.space",
  "https://go.tokenta.space",
  "https://signals.tokenta.space",
  "https://tokenta-signal.vercel.app",
  "https://auth.tokenta.space",
];

export const ACCESS_TTL_S = 3600;
export const REFRESH_TTL_S = 60 * 60 * 24 * 30;
export const CODE_TTL_MIN = 10;
export const CODE_MAX_ATTEMPTS = 5;
export const RESEND_MIN_INTERVAL_S = 60;
export const MAX_SENDS_PER_HOUR = 5;

export function cors(req, res, methods) {
  const origin = req.headers.origin || "";
  if (ALLOWED.includes(origin)) {
    res.setHeader("Access-Control-Allow-Origin", origin);
    res.setHeader("Access-Control-Allow-Credentials", "true");
    res.setHeader("Access-Control-Allow-Methods", methods);
    res.setHeader("Access-Control-Allow-Headers", "Content-Type");
    res.setHeader("Vary", "Origin");
  }
}

export function cookie(name, value, maxAge) {
  return `${name}=${encodeURIComponent(value)}; Domain=.tokenta.space; Path=/; HttpOnly; Secure; SameSite=Lax; Max-Age=${maxAge}`;
}

export function clearCookie(name) {
  return `${name}=; Domain=.tokenta.space; Path=/; HttpOnly; Secure; SameSite=Lax; Max-Age=0`;
}

export function parseCookies(req) {
  const out = {};
  const raw = req.headers.cookie || "";
  for (const part of raw.split(";")) {
    const i = part.indexOf("=");
    if (i > 0) out[part.slice(0, i).trim()] = decodeURIComponent(part.slice(i + 1).trim());
  }
  return out;
}

/* ---------------- database (Neon over HTTP) ---------------- */

export function dbUrl() {
  return (
    process.env.TS_DATABASE_URL ||
    process.env.DATABASE_URL ||
    process.env.NEON_DATABASE_URL ||
    process.env.DATABASE_URL_UNPOOLED ||
    process.env.POSTGRES_URL ||
    ""
  );
}

export function configured() {
  return !!(dbUrl() && process.env.RESEND_API_KEY && process.env.AUTH_SECRET);
}

export async function sql(query, params = []) {
  const conn = dbUrl();
  if (!conn) throw new Error("db_not_configured");
  const host = new URL(conn).host;
  const r = await fetch(`https://${host}/sql`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Neon-Connection-String": conn,
    },
    body: JSON.stringify({ query, params }),
  });
  const data = await r.json().catch(() => ({}));
  if (!r.ok) {
    throw new Error("db_error:" + (data && data.message ? data.message : r.status));
  }
  return data.rows || [];
}

let schemaReady = null;
export function ensureSchema() {
  if (!schemaReady) {
    schemaReady = (async () => {
      await sql(`CREATE TABLE IF NOT EXISTS ts_users (
        id BIGSERIAL PRIMARY KEY,
        email TEXT UNIQUE NOT NULL,
        plan TEXT NOT NULL DEFAULT 'registered',
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        last_login_at TIMESTAMPTZ
      )`);
      await sql(`CREATE TABLE IF NOT EXISTS ts_login_codes (
        email TEXT PRIMARY KEY,
        code_hash TEXT NOT NULL,
        expires_at TIMESTAMPTZ NOT NULL,
        attempts INT NOT NULL DEFAULT 0,
        sent_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        window_start TIMESTAMPTZ NOT NULL DEFAULT now(),
        window_count INT NOT NULL DEFAULT 0
      )`);
      await sql(`CREATE TABLE IF NOT EXISTS ts_sessions (
        id BIGSERIAL PRIMARY KEY,
        user_id BIGINT NOT NULL REFERENCES ts_users(id) ON DELETE CASCADE,
        access_hash TEXT UNIQUE NOT NULL,
        refresh_hash TEXT UNIQUE NOT NULL,
        access_expires_at TIMESTAMPTZ NOT NULL,
        refresh_expires_at TIMESTAMPTZ NOT NULL,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now()
      )`);
    })().catch((e) => {
      schemaReady = null;
      throw e;
    });
  }
  return schemaReady;
}

/* ---------------- crypto helpers ---------------- */

function secret() {
  return process.env.AUTH_SECRET || "";
}

export function hmac(value) {
  return crypto.createHmac("sha256", secret()).update(value).digest("hex");
}

export function tokenHash(token) {
  return crypto.createHash("sha256").update(token).digest("hex");
}

export function randomToken(bytes = 32) {
  return crypto.randomBytes(bytes).toString("base64url");
}

export function safeEqual(a, b) {
  const ba = Buffer.from(String(a));
  const bb = Buffer.from(String(b));
  return ba.length === bb.length && crypto.timingSafeEqual(ba, bb);
}

/* ---------------- users & sessions ---------------- */

export async function upsertUser(email) {
  const rows = await sql(
    `INSERT INTO ts_users (email, last_login_at) VALUES ($1, now())
     ON CONFLICT (email) DO UPDATE SET last_login_at = now()
     RETURNING id, email, plan`,
    [email]
  );
  return rows[0];
}

export async function createSession(res, userId) {
  const at = randomToken(32);
  const rt = randomToken(32);
  await sql(
    `INSERT INTO ts_sessions (user_id, access_hash, refresh_hash, access_expires_at, refresh_expires_at)
     VALUES ($1, $2, $3, now() + ($4 || ' seconds')::interval, now() + ($5 || ' seconds')::interval)`,
    [userId, tokenHash(at), tokenHash(rt), String(ACCESS_TTL_S), String(REFRESH_TTL_S)]
  );
  res.setHeader("Set-Cookie", [
    cookie("ts_at", at, ACCESS_TTL_S),
    cookie("ts_rt", rt, REFRESH_TTL_S),
  ]);
}

export async function userByAccessToken(at) {
  const rows = await sql(
    `SELECT u.email, u.plan FROM ts_sessions s JOIN ts_users u ON u.id = s.user_id
     WHERE s.access_hash = $1 AND s.access_expires_at > now()`,
    [tokenHash(at)]
  );
  return rows[0] || null;
}

export async function rotateByRefreshToken(res, rt) {
  const rows = await sql(
    `SELECT s.id, s.user_id, u.email, u.plan FROM ts_sessions s JOIN ts_users u ON u.id = s.user_id
     WHERE s.refresh_hash = $1 AND s.refresh_expires_at > now()`,
    [tokenHash(rt)]
  );
  const row = rows[0];
  if (!row) return null;
  const at = randomToken(32);
  const newRt = randomToken(32);
  await sql(
    `UPDATE ts_sessions SET access_hash = $1, refresh_hash = $2,
       access_expires_at = now() + ($3 || ' seconds')::interval,
       refresh_expires_at = now() + ($4 || ' seconds')::interval
     WHERE id = $5`,
    [tokenHash(at), tokenHash(newRt), String(ACCESS_TTL_S), String(REFRESH_TTL_S), row.id]
  );
  res.setHeader("Set-Cookie", [
    cookie("ts_at", at, ACCESS_TTL_S),
    cookie("ts_rt", newRt, REFRESH_TTL_S),
  ]);
  return { email: row.email, plan: row.plan };
}

export async function deleteSessionByAccessToken(at) {
  await sql(`DELETE FROM ts_sessions WHERE access_hash = $1`, [tokenHash(at)]);
}

/* ---------------- email via Resend ---------------- */

export async function sendSignInCode(email, code) {
  const link =
    "https://signal.tokenta.space/account/?ts_email=" +
    encodeURIComponent(email) +
    "&ts_code=" +
    encodeURIComponent(code);
  const text = [
    `Your Tokenta Signal sign-in code is ${code}.`,
    "",
    `It expires in ${CODE_TTL_MIN} minutes. Enter it on the sign-in screen,`,
    "or open this link on the device you want to sign in:",
    link,
    "",
    "If you did not request this code, you can ignore this email.",
    "No password is ever needed for Tokenta Signal.",
  ].join("\n");
  const html =
    `<div style="font-family:Arial,sans-serif;color:#111;max-width:480px">` +
    `<p style="font-size:13px;letter-spacing:.12em;color:#666">TOKENTA SIGNAL / ACCOUNT</p>` +
    `<p>Your sign-in code is</p>` +
    `<p style="font-size:32px;font-weight:700;letter-spacing:.3em">${code}</p>` +
    `<p>It expires in ${CODE_TTL_MIN} minutes. Enter it on the sign-in screen, or ` +
    `<a href="${link}">open this sign-in link</a> on the device you want to sign in.</p>` +
    `<p style="color:#666;font-size:13px">If you did not request this code, you can ignore this email. No password is ever needed for Tokenta Signal.</p></div>`;
  const r = await fetch("https://api.resend.com/emails", {
    method: "POST",
    headers: {
      Authorization: "Bearer " + process.env.RESEND_API_KEY,
      "Content-Type": "application/json",
      "User-Agent":
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36",
    },
    body: JSON.stringify({
      from: "Tokenta Signal <team@tokenta.space>",
      to: [email],
      subject: `${code} is your Tokenta Signal sign-in code`,
      text,
      html,
    }),
  });
  if (!r.ok) throw new Error("send_failed:" + r.status);
  return r.json().catch(() => ({}));
}

/* ---------------- OAuth helpers ---------------- */

export function validReturnUrl(raw) {
  try {
    const u = new URL(String(raw || ""));
    if (ALLOWED.includes(u.origin)) return u.toString();
  } catch (e) { /* fall through */ }
  return "https://signal.tokenta.space/";
}

export function setOAuthStateCookie(res, provider, returnUrl) {
  const state = randomToken(18);
  const payload = Buffer.from(
    JSON.stringify({ s: state, p: provider, r: returnUrl })
  ).toString("base64url");
  const value = payload + "." + hmac(payload);
  res.setHeader("Set-Cookie", cookie("ts_oauth", value, 600));
  return state;
}

export function readOAuthStateCookie(req, provider, state) {
  const raw = parseCookies(req).ts_oauth || "";
  const i = raw.lastIndexOf(".");
  if (i < 1) return null;
  const payload = raw.slice(0, i);
  const sig = raw.slice(i + 1);
  if (!safeEqual(sig, hmac(payload))) return null;
  try {
    const data = JSON.parse(Buffer.from(payload, "base64url").toString("utf8"));
    if (data.p !== provider || !safeEqual(data.s, state || "")) return null;
    return data;
  } catch (e) {
    return null;
  }
}
