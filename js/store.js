/* ============================================================
   Florentia · 花与书页 — 本地存储层
   账号 / 会话 / 查花记录 / 收藏 全部保存在浏览器 localStorage。
   这是纯前端演示方案；接入后端后改为调用 API，接口签名保持一致。
   注意：密码哈希仅为本地演示，不可用于真实密码存储。
   ============================================================ */
window.FF = window.FF || {};

FF.store = (function () {
  const USERS_KEY = "ff.users";
  const SESSION_KEY = "ff.session";
  const HISTORY_KEY = "ff.history";
  const FAVS_KEY = "ff.favorites";

  function read(key, fallback) {
    try {
      const raw = localStorage.getItem(key);
      return raw ? JSON.parse(raw) : fallback;
    } catch (e) {
      return fallback;
    }
  }

  function write(key, value) {
    localStorage.setItem(key, JSON.stringify(value));
  }

  /* 极简字符串哈希（djb2 变体），仅作演示，
     正式系统必须由服务端做安全的密码散列与校验。 */
  function demoHash(text) {
    let h = 5381;
    for (let i = 0; i < text.length; i++) {
      h = ((h << 5) + h + text.charCodeAt(i)) >>> 0;
    }
    return "h" + h.toString(16);
  }

  function users() { return read(USERS_KEY, {}); }
  function saveUsers(map) { write(USERS_KEY, map); }

  /* ---- 账号 ---- */
  function register(account, nickname, password) {
    account = account.trim();
    nickname = nickname.trim();
    if (!/^[A-Za-z0-9_\u4e00-\u9fa5]{2,20}$/.test(account)) {
      return { ok: false, msg: "账号需为 2—20 位字母、数字、下划线或中文。" };
    }
    if (!nickname) return { ok: false, msg: "请填写昵称，它会出现在书页的扉页。" };
    if (password.length < 6) return { ok: false, msg: "密码至少 6 位。" };
    const map = users();
    if (map[account]) return { ok: false, msg: "这个账号已被注册，换一个试试。" };
    map[account] = { nickname, hash: demoHash(password), created: Date.now() };
    saveUsers(map);
    return { ok: true };
  }

  function login(account, password) {
    const map = users();
    const u = map[account && account.trim()];
    if (!u || u.hash !== demoHash(password)) {
      return { ok: false, msg: "账号或密码不正确。还记得你的借书证吗？" };
    }
    return { ok: true, user: { account: account.trim(), nickname: u.nickname } };
  }

  /* ---- 会话 ---- */
  function setSession(user, remember) {
    write(SESSION_KEY, { ...user, remember: !!remember, at: Date.now() });
  }
  function session() { return read(SESSION_KEY, null); }
  function logout() { localStorage.removeItem(SESSION_KEY); }

  /* ---- 查花记录（每个账号独立） ---- */
  function historyKey() {
    const s = session();
    return s ? HISTORY_KEY + "." + s.account : null;
  }
  function history() {
    const k = historyKey();
    return k ? read(k, []) : [];
  }
  function addHistory(entry) {
    const k = historyKey();
    if (!k) return;
    const list = read(k, []);
    list.unshift({
      key: entry.key,
      zh: entry.zh,
      en: entry.en,
      time: entry.time || Date.now(),
      source: entry.source || "identify"   /* identify=识别 / library=浏览 */
    });
    write(k, list.slice(0, 200));
  }

  /* ---- 收藏（每个账号独立） ---- */
  function favKey() {
    const s = session();
    return s ? FAVS_KEY + "." + s.account : null;
  }
  function favorites() {
    const k = favKey();
    return k ? read(k, {}) : {};
  }
  function isFavorite(key) { return !!favorites()[key]; }
  function toggleFavorite(key, zh, en) {
    const k = favKey();
    if (!k) return false;
    const map = read(k, {});
    if (map[key]) {
      delete map[key];
      write(k, map);
      return false;
    }
    map[key] = { zh, en, time: Date.now() };
    write(k, map);
    return true;
  }

  return {
    register, login, setSession, session, logout,
    history, addHistory,
    favorites, isFavorite, toggleFavorite
  };
})();
