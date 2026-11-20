/* ============================================================
   视图：登录 / 注册（Welcome to Florentia）
   纯净版：不渲染设计稿中的角落装饰文字与光圈。
   ============================================================ */
window.FF = window.FF || {};
FF.views = FF.views || {};

/* 打开的书本线条图标（对应设计稿徽章） */
const BOOK_SVG = `<svg viewBox="0 0 24 24" width="26" height="26" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round"><path d="M12 5.2C10.4 3.9 8.2 3.2 5.6 3.2v13.2c2.6 0 4.8.7 6.4 2 1.6-1.3 3.8-2 6.4-2V3.2c-2.6 0-4.8.7-6.4 2z"/><path d="M12 5.2v13.2"/></svg>`;

FF.views.login = (function () {
  const {text: t} = FF.language;

  function shell(mode) {
    const isLogin = mode === "login";
    return `
      <div class="login-stage">
        <div class="login-card">
          <div class="emblem">${BOOK_SVG}</div>
          ${FF.language.button()}
          <h1>Florentia Library</h1>
          <div class="motto">Where Stories Bloom</div>
          <p class="lead">${isLogin
            ? t("登录保存阅读记录，或以游客身份直接体验识花与书页。", "Sign in to save your reading history, or continue as a guest to identify flowers and browse.")
            : t("在 Florentia 办一张新借书证。你的查花记录与收藏，都会保存在这本手册里。", "Create a reader account to keep your identifications and bookmarks.")}</p>
          <div class="form-error hidden" id="form-error"></div>
          <form id="auth-form" autocomplete="off">
            <div class="field">
              <label for="f-account">${t("账号", "Account")} ${t(`<span>/ ${isLogin ? "CARD NUMBER" : "ACCOUNT"}</span>`, "")}</label>
              <div class="box">
                <span class="glyph">&#9878;</span>
                <input id="f-account" type="text" placeholder="${isLogin ? t("FL-1874-0231 或你注册的账号", "Your account name") : t("想一个好记的账号", "Choose an account name")}" required>
              </div>
            </div>
            ${isLogin ? "" : `
            <div class="field">
              <label for="f-nick">${t("昵称 <span>/ NAME</span>", "Display name")}</label>
              <div class="box">
                <span class="glyph">&#10048;</span>
                <input id="f-nick" type="text" placeholder="${t("扉页上署这个名字", "Your display name")}" required>
              </div>
            </div>`}
            <div class="field">
              <label for="f-pass">${t("密码 <span>/ PASSWORD</span>", "Password")}</label>
              <div class="box">
                <span class="glyph">&#9919;</span>
                <input id="f-pass" type="password" placeholder="${t("至少 6 位", "At least 6 characters")}" required>
                <button type="button" class="eye" id="eye-btn" title="${t("显示/隐藏密码", "Show or hide password")}">&#128065;</button>
              </div>
            </div>
            ${isLogin ? `
            <div class="login-row">
              <label><input type="checkbox" id="f-remember"> ${t("记住这台设备", "Remember this device")}</label>
              <a href="#" id="forgot">${t("忘记密码？", "Forgot password?")}</a>
            </div>` : ""}
            <button type="submit" class="btn-primary" id="submit-btn">
              ${isLogin ? t("登录阅览室", "Sign in") : t("办理借书证", "Create account")}<span class="arrow">&#8594;</span>
            </button>
          </form>
          <button type="button" class="btn-ghost guest-entry" id="guest-btn">${t("以游客身份进入", "Continue as a guest")}</button>
          <div class="login-switch">
            ${isLogin
              ? `${t("还没有借书证？", "New here? ")}<a href="#/login?mode=register">${t("注册新读者", "Create an account")}</a>`
              : `${t("已有账号？", "Already have an account? ")}<a href="#/login">${t("返回登录", "Sign in")}</a>`}
          </div>
          <div class="login-foot">${t("Florentia · 花与书页", "Florentia · Flower &amp; Folio")}</div>
        </div>
      </div>`;
  }

  function showError(msg) {
    const el = document.getElementById("form-error");
    el.textContent = msg;
    el.classList.remove("hidden");
  }

  function bind(mode) {
    const form = document.getElementById("auth-form");
    const guest = document.getElementById("guest-btn");
    guest.addEventListener("click", () => {
      FF.store.startGuest();
      FF.router.enter();
    });
    const eye = document.getElementById("eye-btn");
    if (eye) {
      eye.addEventListener("click", () => {
        const input = document.getElementById("f-pass");
        input.type = input.type === "password" ? "text" : "password";
      });
    }
    const forgot = document.getElementById("forgot");
    if (forgot) {
      forgot.addEventListener("click", (e) => {
        e.preventDefault();
        FF.toast(t("演示版暂未接入找回密码；请重新注册一个账号。", "Password recovery is unavailable. You can create a new account."));
      });
    }

    form.addEventListener("submit", (e) => {
      e.preventDefault();
      const account = document.getElementById("f-account").value;
      const pass = document.getElementById("f-pass").value;
      const btn = document.getElementById("submit-btn");
      btn.disabled = true;
      guest.disabled = true;

      /* crypto.subtle 不可用时无感降级：直接同步校验 */
      setTimeout(() => {
        if (!form.isConnected) return;
        if (mode === "login") {
          const res = FF.store.login(account, pass);
          if (!res.ok) {
            btn.disabled = false;
            guest.disabled = false;
            showError(res.msg);
            return;
          }
          const remember = document.getElementById("f-remember").checked;
          FF.store.setSession(res.user, remember);
          FF.toast(t(`欢迎回来，${res.user.nickname}。`, `Welcome back, ${res.user.nickname}.`));
          FF.router.enter();
        } else {
          const nick = document.getElementById("f-nick").value;
          const res = FF.store.register(account, nick, pass);
          if (!res.ok) {
            btn.disabled = false;
            guest.disabled = false;
            showError(res.msg);
            return;
          }
          FF.store.setSession({ account: account.trim(), nickname: nick.trim() }, false);
          FF.toast(t("借书证已办好，欢迎加入 Florentia。", "Your reader account is ready. Welcome to Florentia."));
          FF.router.enter();
        }
      }, 420);
    });
  }

  function render(params) {
    const mode = params && params.mode === "register" ? "register" : "login";
    document.getElementById("view").innerHTML = shell(mode);
    bind(mode);
  }

  return { render };
})();
