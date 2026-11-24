// Tokenta Signal auth: self-hosted GitHub sign-in (OAuth 2.0 code flow).
// Same shape as the Google handler: begin without ?code, callback with it.
// The account email is the primary verified address from the GitHub API.
import {
  ensureSchema, configured, upsertUser, createSession, clearCookie,
  validReturnUrl, setOAuthStateCookie, readOAuthStateCookie,
} from "../_lib.js";

const REDIRECT = "https://auth.tokenta.space/api/auth/oauth/github";
const FAIL = "https://signal.tokenta.space/account/?ts_error=oauth";
const UA = { "User-Agent": "TokentaSignal" };

function redirect(res, url) {
  res.statusCode = 302;
  res.setHeader("Location", url);
  res.end();
}

export default async function handler(req, res) {
  if (req.method !== "GET") return res.status(405).json({ error: "method_not_allowed" });
  const clientId = process.env.GITHUB_OAUTH_CLIENT_ID;
  const clientSecret = process.env.GITHUB_OAUTH_CLIENT_SECRET;
  if (!configured() || !clientId || !clientSecret) {
    return res.status(500).json({ error: "not_configured" });
  }
  const q = req.query || {};

  if (!q.code) {
    const returnUrl = validReturnUrl(q.return);
    const state = setOAuthStateCookie(res, "github", returnUrl);
    const u = new URL("https://github.com/login/oauth/authorize");
    u.searchParams.set("client_id", clientId);
    u.searchParams.set("redirect_uri", REDIRECT);
    u.searchParams.set("scope", "read:user user:email");
    u.searchParams.set("state", state);
    return redirect(res, u.toString());
  }

  const stateData = readOAuthStateCookie(req, "github", q.state);
  if (!stateData) return redirect(res, FAIL);
  try {
    await ensureSchema();
    const tr = await fetch("https://github.com/login/oauth/access_token", {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json", ...UA },
      body: JSON.stringify({
        client_id: clientId,
        client_secret: clientSecret,
        code: String(q.code),
        redirect_uri: REDIRECT,
      }),
    });
    const td = await tr.json().catch(() => ({}));
    if (!tr.ok || !td.access_token) return redirect(res, FAIL);
    const auth = { Authorization: "Bearer " + td.access_token, ...UA };
    let email = "";
    const er = await fetch("https://api.github.com/user/emails", { headers: auth });
    if (er.ok) {
      const list = await er.json().catch(() => []);
      const pick =
        list.find((e) => e.primary && e.verified) || list.find((e) => e.verified);
      if (pick) email = String(pick.email || "").trim().toLowerCase();
    }
    if (!email) {
      const pr = await fetch("https://api.github.com/user", { headers: auth });
      if (pr.ok) {
        const prof = await pr.json().catch(() => ({}));
        email = String(prof.email || "").trim().toLowerCase();
      }
    }
    if (!email) return redirect(res, FAIL);
    const row = await upsertUser(email);
    await createSession(res, row.id);
    const existing = res.getHeader("Set-Cookie") || [];
    res.setHeader("Set-Cookie", [...existing, clearCookie("ts_oauth")]);
    return redirect(res, validReturnUrl(stateData.r));
  } catch (e) {
    return redirect(res, FAIL);
  }
}
