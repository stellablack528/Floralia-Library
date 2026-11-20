/* ============================================================
   Florentia · 花与书页 — 应用入口
   导航栏渲染 + 全局 Toast + 路由启动。
   ============================================================ */
window.FF = window.FF || {};

(function () {
  const {text: t} = FF.language;

  /* ---- Toast ---- */
  let toastTimer = null;
  FF.toast = function (msg, isErr) {
    const el = document.getElementById("toast");
    el.textContent = msg;
    el.className = "toast" + (isErr ? " err" : "");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => el.classList.add("hidden"), 2600);
  };

  /* ---- 导航栏 ---- */
  function renderNavbar(routePath) {
    const nav = document.getElementById("navbar");
    const session = FF.store.session();
    if (!session) { nav.classList.add("hidden"); return; }
    nav.classList.remove("hidden");

    const links = [
      { href: "#/identify", label: t("识花台", "Identify") },
      { href: "#/library", label: t("花卉资料馆", "Flower Library") },
      { href: "#/history", label: t("我的足迹", "History") }
    ];
    /* 路由高亮：#/library/xxx 也算资料馆 */
    const active = (l) => routePath === l.href || (l.href === "#/library" && routePath.startsWith("#/library/"));

    nav.innerHTML = `
      <a class="nav-brand" href="#/identify">
        <span class="badge"><svg viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round"><path d="M12 5.2C10.4 3.9 8.2 3.2 5.6 3.2v13.2c2.6 0 4.8.7 6.4 2 1.6-1.3 3.8-2 6.4-2V3.2c-2.6 0-4.8.7-6.4 2z"/><path d="M12 5.2v13.2"/></svg></span>
        <span><span class="name">Florentia</span><br><span class="sub">Flower &amp; Folio</span></span>
      </a>
      <nav class="nav-links">
        ${links.map((l) => `<a href="${l.href}" class="${active(l) ? "active" : ""}">${l.label}</a>`).join("")}
      </nav>
      <div class="nav-user">
        <div class="who"><strong></strong><small></small></div>
        ${FF.language.button()}
        <button class="nav-exit" id="nav-exit">${t("退出", "Sign out")}</button>
      </div>`;

    nav.querySelector(".who strong").textContent = session.guest ? t("游客", "Guest") : session.nickname;
    nav.querySelector(".who small").textContent = session.guest ? t("临时会话", "Temporary session") : session.account;
    document.getElementById("nav-exit").addEventListener("click", () => {
      FF.store.logout();
      FF.toast(t("已退出阅览室。", "Signed out."));
      location.hash = "#/login";
    });
  }

  /* 每次路由渲染后同步导航栏状态 */
  window.addEventListener("ff:route", (e) => {
    const h = e.detail.hash.split("?")[0];
    if (h !== "#/login") renderNavbar(h);
  });

  document.addEventListener("click", event => {
    if (event.target.closest("[data-language-toggle]")) {
      FF.language.toggle();
      FF.router.render();
      document.querySelector("[data-language-toggle]")?.focus();
    }
  });

  FF.router.start();
})();
