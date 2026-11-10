/* ============================================================
   Florentia · 花与书页 — Hash 路由
   路由表 + 登录守卫：未登录访问受保护页面时重定向到 #/login。
   ============================================================ */
window.FF = window.FF || {};

FF.router = (function () {
  const routes = [
    { path: "#/login",      view: () => FF.views.login.render(),    public: true,  bare: true },
    { path: "#/identify",   view: () => FF.views.identify.render(), public: false, bare: false },
    { path: "#/library",    view: () => FF.views.library.renderList(), public: false, bare: false },
    { path: "#/library/:key", view: (p) => FF.views.library.renderDetail(p.key), public: false, bare: false },
    { path: "#/history",    view: () => FF.views.history.render(),  public: false, bare: false }
  ];

  function currentHash() {
    return location.hash || "#/identify";
  }

  function match(hash) {
    for (const r of routes) {
      const rp = r.path.split("/");
      const hp = hash.split("?")[0].split("/");
      const params = {};
      if (rp.length !== hp.length) continue;
      let ok = true;
      for (let i = 0; i < rp.length; i++) {
        if (rp[i].startsWith(":")) params[rp[i].slice(1)] = decodeURIComponent(hp[i]);
        else if (rp[i] !== hp[i]) { ok = false; break; }
      }
      if (ok) return { route: r, params };
    }
    return null;
  }

  function render() {
    const hash = currentHash();
    const found = match(hash);
    const navbar = document.getElementById("navbar");
    const viewEl = document.getElementById("view");

    if (!found) {
      location.hash = "#/identify";
      return;
    }

    const { route, params } = found;
    /* 合并查询参数（如 #/login?mode=register） */
    const queryStr = hash.includes("?") ? hash.split("?")[1] : "";
    const query = {};
    new URLSearchParams(queryStr).forEach((v, k) => { query[k] = v; });
    const viewParams = { ...query, ...params };

    /* 登录守卫 */
    const session = FF.store.session();
    if (!route.public && !session) {
      location.hash = "#/login";
      return;
    }
    /* 已登录用户访问登录页 → 送回识花台 */
    if (route.path === "#/login" && session) {
      location.hash = "#/identify";
      return;
    }

    navbar.classList.toggle("hidden", route.bare);
    viewEl.innerHTML = "";
    route.view(viewParams);

    /* 通知导航栏刷新（app.js 监听此事件） */
    window.dispatchEvent(new CustomEvent("ff:route", { detail: { hash, route } }));

    if (!route.bare) window.scrollTo(0, 0);
  }

  function start() {
    window.addEventListener("hashchange", render);
    if (!location.hash) location.hash = "#/identify";
    render();
  }

  return { start, render };
})();
