/* Tokenta Signal accounts: sign-in modal, session state, article meter.
   Auth API lives on the auth subdomain (Vercel project tokenta-signal-auth).
   Free anonymous reading: 8 articles per calendar month (Reuters-style meter).
   Registered accounts read without the meter. */
(function () {
  var AUTH = "https://auth.tokenta.space";
  var FREE_LIMIT = 8;
  var state = { authed: false, email: null, plan: null, checked: false };

  function $(s, r) { return (r || document).querySelector(s); }

  /* ---------- modal ---------- */
  var modal = null;
  function buildModal() {
    if (modal) return modal;
    var wrap = document.createElement("div");
    wrap.id = "ts-auth-modal";
    wrap.style.cssText = "display:none;position:fixed;inset:0;z-index:200;background:rgba(0,0,0,.82);align-items:center;justify-content:center;padding:20px";
    wrap.innerHTML =
      '<div style="background:#0A0A0A;border:1px solid #383838;border-top:3px solid #C9D0D9;max-width:420px;width:100%;padding:30px 28px;font-family:\'IBM Plex Sans\',Arial,sans-serif;color:#F4F4F4">' +
      '<div style="font-family:\'IBM Plex Mono\',monospace;font-size:11px;font-weight:700;letter-spacing:.14em;color:#C9D0D9">TOKENTA SIGNAL / ACCOUNT</div>' +
      '<h3 id="ts-am-title" style="font-family:\'IBM Plex Serif\',Georgia,serif;font-size:24px;font-weight:600;margin:12px 0 6px">Sign in or register</h3>' +
      '<p id="ts-am-sub" style="color:#9A9A9A;font-size:13px;margin:0 0 18px">One account for the wire, briefings and the terminal. Continue with a provider, or take a 6-digit email code. No password, ever.</p>' +
      '<div id="ts-am-social">' +
      '<button data-ts-provider="google" style="width:100%;background:#111;border:1px solid #383838;color:#F4F4F4;padding:12px;font-family:\'IBM Plex Mono\',monospace;font-size:12px;font-weight:700;letter-spacing:.08em;cursor:pointer;margin-bottom:10px">CONTINUE WITH GOOGLE</button>' +
      '<button data-ts-provider="github" style="width:100%;background:#111;border:1px solid #383838;color:#F4F4F4;padding:12px;font-family:\'IBM Plex Mono\',monospace;font-size:12px;font-weight:700;letter-spacing:.08em;cursor:pointer;margin-bottom:10px">CONTINUE WITH GITHUB</button>' +
      '<button data-ts-provider="twitter" style="width:100%;background:#111;border:1px solid #383838;color:#F4F4F4;padding:12px;font-family:\'IBM Plex Mono\',monospace;font-size:12px;font-weight:700;letter-spacing:.08em;cursor:pointer;margin-bottom:4px">CONTINUE WITH X</button>' +
      '<div style="display:flex;align-items:center;gap:12px;margin:14px 0 16px"><span style="flex:1;height:1px;background:#2A2A2A"></span><span style="font-family:\'IBM Plex Mono\',monospace;font-size:10px;letter-spacing:.14em;color:#6E6E6E">OR WITH EMAIL</span><span style="flex:1;height:1px;background:#2A2A2A"></span></div>' +
      "</div>" +
      '<div id="ts-am-step1">' +
      '<label style="display:block;font-family:\'IBM Plex Mono\',monospace;font-size:11px;color:#9A9A9A;margin-bottom:6px">EMAIL ADDRESS</label>' +
      '<input id="ts-am-email" type="email" autocomplete="email" placeholder="you@example.com" style="width:100%;background:#111;border:1px solid #383838;color:#F4F4F4;padding:12px;font-size:15px;font-family:\'IBM Plex Mono\',monospace;box-sizing:border-box">' +
      '<button id="ts-am-send" style="width:100%;margin-top:14px;background:#C9D0D9;color:#000;border:1px solid #C9D0D9;padding:12px;font-family:\'IBM Plex Mono\',monospace;font-size:12px;font-weight:700;letter-spacing:.08em;cursor:pointer">EMAIL ME A SIGN-IN CODE</button>' +
      "</div>" +
      '<div id="ts-am-step2" style="display:none">' +
      '<label style="display:block;font-family:\'IBM Plex Mono\',monospace;font-size:11px;color:#9A9A9A;margin-bottom:6px">6-DIGIT CODE FROM YOUR EMAIL</label>' +
      '<input id="ts-am-code" inputmode="numeric" autocomplete="one-time-code" maxlength="6" placeholder="------" style="width:100%;background:#111;border:1px solid #383838;color:#F4F4F4;padding:12px;font-size:22px;letter-spacing:.35em;text-align:center;font-family:\'IBM Plex Mono\',monospace;box-sizing:border-box">' +
      '<button id="ts-am-verify" style="width:100%;margin-top:14px;background:#C9D0D9;color:#000;border:1px solid #C9D0D9;padding:12px;font-family:\'IBM Plex Mono\',monospace;font-size:12px;font-weight:700;letter-spacing:.08em;cursor:pointer">VERIFY AND SIGN IN</button>' +
      '<p style="margin:12px 0 0;font-size:12px;color:#9A9A9A">The email also carries a sign-in link if the code is awkward. <a href="#" id="ts-am-back" style="color:#C9D0D9">Use a different email</a></p>' +
      "</div>" +
      '<p id="ts-am-msg" style="min-height:18px;margin:14px 0 0;font-size:13px;color:#C9D0D9"></p>' +
      '<button id="ts-am-close" style="margin-top:8px;background:none;border:none;color:#6E6E6E;font-family:\'IBM Plex Mono\',monospace;font-size:11px;cursor:pointer;padding:4px 0">CLOSE ✕</button>' +
      "</div>";
    document.body.appendChild(wrap);
    modal = wrap;
    $("#ts-am-close", wrap).addEventListener("click", closeModal);
    wrap.addEventListener("click", function (e) { if (e.target === wrap) closeModal(); });
    $("#ts-am-back", wrap).addEventListener("click", function (e) {
      e.preventDefault();
      $("#ts-am-step2", wrap).style.display = "none";
      $("#ts-am-step1", wrap).style.display = "block";
      msg("");
    });
    $("#ts-am-send", wrap).addEventListener("click", sendCode);
    var provs = wrap.querySelectorAll("[data-ts-provider]");
    for (var pi = 0; pi < provs.length; pi++) provs[pi].addEventListener("click", function () { social(this.getAttribute("data-ts-provider")); });
    $("#ts-am-verify", wrap).addEventListener("click", verifyCode);
    $("#ts-am-email", wrap).addEventListener("keydown", function (e) { if (e.key === "Enter") sendCode(); });
    $("#ts-am-code", wrap).addEventListener("keydown", function (e) { if (e.key === "Enter") verifyCode(); });
    return wrap;
  }
  function msg(t) { var m = $("#ts-am-msg"); if (m) m.textContent = t || ""; }
  function openModal() {
    var w = buildModal();
    w.style.display = "flex";
    var em = $("#ts-am-email", w); if (em) em.focus();
  }
  function closeModal() { if (modal) modal.style.display = "none"; }
  window.TSAuth = { open: openModal, state: state, refresh: refresh, signOut: signOut };

  function fetchT(url, opts, ms) {
    var ctl = ("AbortController" in window) ? new AbortController() : null;
    var timer = ctl ? setTimeout(function () { ctl.abort(); }, ms || 12000) : null;
    var o = opts || {};
    if (ctl) o.signal = ctl.signal;
    return fetch(url, o).then(function (r) { if (timer) clearTimeout(timer); return r; }, function (e) { if (timer) clearTimeout(timer); throw e; });
  }

  function post(path, body) {
    return fetchT(AUTH + path, {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body || {}),
    }).then(function (r) { return r.json().catch(function () { return {}; }).then(function (j) { return { ok: r.ok, j: j }; }); });
  }

  var SB = "https://axelczmkhxwrbhkrvmgv.supabase.co";
  function social(provider) {
    var back = location.origin + location.pathname;
    window.location = SB + "/auth/v1/authorize?provider=" + provider + "&redirect_to=" + encodeURIComponent(back);
  }

  function sendCode() {
    var email = ($("#ts-am-email").value || "").trim();
    if (!email) { msg("Enter your email address first."); return; }
    msg("Sending your code…");
    post("/api/auth/request-code", { email: email }).then(function (res) {
      if (res.ok) {
        $("#ts-am-step1").style.display = "none";
        $("#ts-am-step2").style.display = "block";
        $("#ts-am-title").textContent = "Check your email";
        $("#ts-am-sub").textContent = "We sent a 6-digit code to " + email + ". Enter it below to finish signing in.";
        msg("");
        var c = $("#ts-am-code"); if (c) c.focus();
        modal.dataset.email = email;
      } else {
        msg("That email could not be sent a code. Check the address and try again.");
      }
    }).catch(function () { msg("Network problem. Try again in a moment."); });
  }

  function verifyCode() {
    var code = ($("#ts-am-code").value || "").trim();
    var email = modal.dataset.email || ($("#ts-am-email").value || "").trim();
    if (!/^\d{6}$/.test(code)) { msg("The code is 6 digits, from the email we just sent."); return; }
    msg("Verifying…");
    post("/api/auth/verify-code", { email: email, token: code }).then(function (res) {
      if (res.ok) {
        msg("Signed in. Welcome to Tokenta Signal.");
        refresh().then(function () {
          setTimeout(function () { closeModal(); unlockArticle(); }, 600);
        });
      } else {
        msg("That code did not check out. Codes expire quickly, request a fresh one if needed.");
      }
    }).catch(function () { msg("Network problem. Try again in a moment."); });
  }

  function fetchMe() {
    return fetchT(AUTH + "/api/auth/me", { credentials: "include" }, 9000)
      .then(function (r) { return r.json(); });
  }
  function refresh() {
    return fetchMe()
      .catch(function () {
        return new Promise(function (res) { setTimeout(res, 1500); }).then(fetchMe);
      })
      .then(function (j) {
        state.authed = !!j.authenticated;
        state.email = j.email || null;
        state.plan = j.plan || null;
        state.checked = true;
        paintButton();
        paintAccount();
        return state;
      })
      .catch(function () { state.checked = true; paintButton(); paintAccount(); return state; });
  }

  function signOut() {
    return post("/api/auth/signout", {}).then(function () {
      state.authed = false; state.email = null; state.plan = null;
      paintButton(); paintAccount();
    });
  }

  /* ---------- nav button ---------- */
  function paintButton() {
    var b = $("#auth-btn");
    if (!b) return;
    if (state.authed) {
      b.textContent = "ACCOUNT";
      b.setAttribute("href", accountHref());
    } else {
      b.textContent = "SIGN IN";
      b.removeAttribute("href");
    }
  }
  function accountHref() {
    var p = "/";
    var path = location.pathname;
    if (path.indexOf("/articles/") === 0 || path.split("/").length > 2) p = "../../";
    else if (path !== "/" && path !== "/index.html") p = "../";
    return p + "account/";
  }

  /* ---------- account page ---------- */
  function paintAccount() {
    var box = $("#acct-box");
    if (!box) return;
    if (!state.checked) { box.innerHTML = '<p style="color:#9A9A9A">Checking your session…</p>'; return; }
    if (state.authed) {
      box.innerHTML =
        '<p style="color:#9A9A9A;font-size:13px" class="mono">SIGNED IN AS</p>' +
        '<p style="font-size:19px;margin:6px 0">' + escapeHtml(state.email || "") + "</p>" +
        '<p style="color:#9A9A9A;font-size:13px" class="mono">PLAN / ' + escapeHtml((state.plan || "registered").toUpperCase()) + "</p>" +
        '<p style="margin-top:20px"><a class="btn primary" href="../pricing/">SEE SIGNAL PRO</a> <button id="acct-out" class="btn ghost" style="cursor:pointer">SIGN OUT</button></p>';
      var out = $("#acct-out");
      if (out) out.addEventListener("click", function () { signOut(); });
    } else {
      box.innerHTML =
        '<p style="color:#9A9A9A">You are reading as a guest. Sign in or register with your email, no password needed. Registered readers get the full wire without the monthly meter.</p>' +
        '<p style="margin-top:20px"><button id="acct-in" class="btn primary" style="cursor:pointer">SIGN IN / REGISTER</button></p>';
      var inn = $("#acct-in");
      if (inn) inn.addEventListener("click", openModal);
    }
  }
  function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }

  /* ---------- article meter ---------- */
  function monthKey() {
    var d = new Date();
    return d.getUTCFullYear() + "-" + String(d.getUTCMonth() + 1).padStart(2, "0");
  }
  function meterCount(slug) {
    try {
      var raw = localStorage.getItem("ts_meter");
      var m = raw ? JSON.parse(raw) : null;
      if (!m || m.month !== monthKey()) m = { month: monthKey(), slugs: [] };
      if (slug && m.slugs.indexOf(slug) === -1) { m.slugs.push(slug); localStorage.setItem("ts_meter", JSON.stringify(m)); }
      return m.slugs.length;
    } catch (e) { return 0; }
  }
  function unlockArticle() {
    var gate = $("#ts-gate");
    if (gate) gate.remove();
    var art = $("article.read");
    if (art) art.classList.remove("ts-locked");
    var st = $("#ts-lock-style"); if (st) st.remove();
  }
  function applyMeter() {
    var art = $("article.read");
    if (!art) return;
    var slug = location.pathname.replace(/\/+$/, "").split("/").pop();
    var n = meterCount(slug);
    if (state.authed || n <= FREE_LIMIT) return;
    art.classList.add("ts-locked");
    var st = document.createElement("style");
    st.id = "ts-lock-style";
    st.textContent =
      "article.read.ts-locked > *:nth-child(n+9){display:none!important}" +
      "#ts-gate{max-width:780px;margin:0 auto 60px;padding:0 24px}" +
      "#ts-gate .card{border:1px solid #383838;border-top:3px solid #C9D0D9;background:#0A0A0A;padding:30px 28px;text-align:left}" +
      "#ts-gate h3{font-family:'IBM Plex Serif',Georgia,serif;font-size:24px;font-weight:600;margin:10px 0}" +
      "#ts-gate p{color:#9A9A9A;font-size:14px}";
    document.head.appendChild(st);
    var gate = document.createElement("div");
    gate.id = "ts-gate";
    gate.innerHTML =
      '<div class="card"><div class="eyebrow">FREE READING LIMIT</div>' +
      "<h3>You have read your " + FREE_LIMIT + " free reports this month</h3>" +
      "<p>Register free to keep reading the full wire, briefings and terminal. Paid Signal Pro adds the complete analysis archive, terminal alerts and the daily briefing email.</p>" +
      '<p style="margin-top:18px"><button id="ts-gate-reg" class="btn primary" style="cursor:pointer">REGISTER FREE</button> <a class="btn ghost" href="../../pricing/">SEE SIGNAL PRO</a></p></div>';
    art.parentNode.insertBefore(gate, art.nextSibling);
    var reg = $("#ts-gate-reg");
    if (reg) reg.addEventListener("click", openModal);
  }

  /* ---------- boot ---------- */
  function adoptHashSession() {
    if (!location.hash || location.hash.indexOf("access_token=") === -1) return Promise.resolve();
    var p = new URLSearchParams(location.hash.slice(1));
    var at = p.get("access_token"), rt = p.get("refresh_token");
    history.replaceState(null, "", location.pathname + location.search);
    if (!at || !rt) return Promise.resolve();
    return post("/api/auth/session", { access_token: at, refresh_token: rt }).catch(function () {});
  }
  document.addEventListener("DOMContentLoaded", function () {
    var b = $("#auth-btn");
    if (b) b.addEventListener("click", function (e) {
      if (!state.authed) { e.preventDefault(); openModal(); }
    });
    adoptHashSession().then(function () { return refresh(); }).then(applyMeter);
    paintAccount();
    setTimeout(function () { if (!state.checked) refresh(); }, 6000);
  });
})();
