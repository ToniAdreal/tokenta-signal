// Tokenta Signal auth: self-hosted Google sign-in (OAuth 2.0 code flow).
// GET without ?code starts the flow; Google redirects back here with
// ?code & ?state, we exchange, upsert the user by verified email, set the
// session cookies and return to the page the reader came from.
import {
  ensureSchema, configured, upsertUser, createSession, clearCookie,
  validReturnUrl, setOAuthStateCookie, readOAuthStateCookie,
} from "../_lib.js";

const REDIRECT = "https://auth.tokenta.space/api/auth/oauth/google";
const FAIL = "https://signal.tokenta.space/account/?ts_error=oauth";

function redirect(res, url) {
  res.statusCode = 302;
  res.setHeader("Location", url);
  res.end();
}

export default async function handler(req, res) {
  if (req.method !== "GET") return res.status(405).json({ error: "method_not_allowed" });
  const clientId = process.env.GOOGLE_OAUTH_CLIENT_ID;
  const clientSecret = process.env.GOOGLE_OAUTH_CLIENT_SECRET;
  if (!configured() || !clientId || !clientSecret) {
    return res.status(500).json({ error: "not_configured" });
  }
  const q = req.query || {};

  if (!q.code) {
    const returnUrl = validReturnUrl(q.return);
    const state = setOAuthStateCookie(res, "google", returnUrl);
    const u = new URL("https://accounts.google.com/o/oauth2/v2/auth");
    u.searchParams.set("client_id", clientId);
    u.searchParams.set("redirect_uri", REDIRECT);
    u.searchParams.set("response_type", "code");
    u.searchParams.set("scope", "openid email profile");
    u.searchParams.set("state", state);
    u.searchParams.set("prompt", "select_account");
    return redirect(res, u.toString());
  }

  const stateData = readOAuthStateCookie(req, "google", q.state);
  if (!stateData) return redirect(res, FAIL);
  try {
    await ensureSchema();
    const tr = await fetch("https://oauth2.googleapis.com/token", {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: new URLSearchParams({
        code: String(q.code),
        client_id: clientId,
        client_secret: clientSecret,
        redirect_uri: REDIRECT,
        grant_type: "authorization_code",
      }),
    });
    const td = await tr.json().catch(() => ({}));
    if (!tr.ok || !td.access_token) return redirect(res, FAIL);
    const ur = await fetch("https://openidconnect.googleapis.com/v1/userinfo", {
      headers: { Authorization: "Bearer " + td.access_token },
    });
    const user = await ur.json().catch(() => ({}));
    const email = String(user.email || "").trim().toLowerCase();
    if (!ur.ok || !email || user.email_verified !== true) return redirect(res, FAIL);
    const row = await upsertUser(email);
    await createSession(res, row.id);
    const existing = res.getHeader("Set-Cookie") || [];
    res.setHeader("Set-Cookie", [...existing, clearCookie("ts_oauth")]);
    return redirect(res, validReturnUrl(stateData.r));
  } catch (e) {
    return redirect(res, FAIL);
  }
}
