/* ============================================================
   Florentia · 花与书页 — 本地存储层
   注册读者数据存在 localStorage，游客会话、足迹和收藏存在 sessionStorage。
   这是纯前端演示方案；接入后端后改为调用 API，接口签名保持一致。
   注意：密码哈希仅为本地演示，不可用于真实密码存储。
   ============================================================ */
window.FF = window.FF || {};

FF.store = (function () {
  const USERS_KEY = "ff.users";
  const SESSION_KEY = "ff.session";
  const GUEST_KEY = "ff.guest";
  const HISTORY_KEY = "ff.history";
  const FAVS_KEY = "ff.favorites";

  function read(key, fallback, storage = localStorage) {
    try {
      const raw = storage.getItem(key);
      return raw ? JSON.parse(raw) : fallback;
    } catch (e) {
      return fallback;
    }
  }

  function write(key, value, storage = localStorage) {
    storage.setItem(key, JSON.stringify(value));
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
      return { ok: false, msg: FF.language.text("账号需为 2—20 位字母、数字、下划线或中文。", "Use 2–20 letters, digits, underscores, or Chinese characters for your account.") };
    }
    if (!nickname) return { ok: false, msg: FF.language.text("请填写昵称，它会出现在书页的扉页。", "Enter a display name.") };
    if (password.length < 6) return { ok: false, msg: FF.language.text("密码至少 6 位。", "Choose a password with at least six characters.") };
    const map = users();
    if (map[account]) return { ok: false, msg: FF.language.text("这个账号已被注册，换一个试试。", "That account name is already taken.") };
    map[account] = { nickname, hash: demoHash(password), created: Date.now() };
    saveUsers(map);
    return { ok: true };
  }

  function login(account, password) {
    const map = users();
    const u = map[account && account.trim()];
    if (!u || u.hash !== demoHash(password)) {
      return { ok: false, msg: FF.language.text("账号或密码不正确。还记得你的借书证吗？", "The account name or password is incorrect.") };
    }
    return { ok: true, user: { account: account.trim(), nickname: u.nickname } };
  }

  /* ---- 会话 ---- */
  function startGuest() {
    write(GUEST_KEY, true, sessionStorage);
  }

  function clearGuest() {
    for (const key of [GUEST_KEY, HISTORY_KEY, FAVS_KEY]) sessionStorage.removeItem(key);
  }

  function setSession(user, remember) {
    clearGuest();
    write(SESSION_KEY, { ...user, remember: !!remember, at: Date.now() });
  }

  function session() {
    return read(GUEST_KEY, false, sessionStorage) ? { guest: true, nickname: "游客" } : read(SESSION_KEY, null);
  }

  function logout() {
    if (session()?.guest) clearGuest();
    else localStorage.removeItem(SESSION_KEY);
  }

  function personalStorage(key) {
    const reader = session();
    if (!reader) return null;
    return reader.guest ? { key, storage: sessionStorage } :
      { key: key + "." + reader.account, storage: localStorage };
  }

  /* ---- 查花记录 ---- */
  function history() {
    const target = personalStorage(HISTORY_KEY);
    return target ? read(target.key, [], target.storage) : [];
  }
  function addHistory(entry) {
    const target = personalStorage(HISTORY_KEY);
    if (!target) return;
    const { key, storage } = target;
    const list = read(key, [], storage);
    list.unshift({
      key: entry.key,
      zh: entry.zh,
      en: entry.en,
      time: entry.time || Date.now(),
      source: entry.source || "identify"   /* identify=识别 / library=浏览 */
    });
    write(key, list.slice(0, 200), storage);
  }

  /* ---- 收藏 ---- */
  function favorites() {
    const target = personalStorage(FAVS_KEY);
    return target ? read(target.key, {}, target.storage) : {};
  }
  function isFavorite(key) { return !!favorites()[key]; }
  function toggleFavorite(flowerKey, zh, en) {
    const target = personalStorage(FAVS_KEY);
    if (!target) return false;
    const { key, storage } = target;
    const map = read(key, {}, storage);
    if (map[flowerKey]) {
      delete map[flowerKey];
      write(key, map, storage);
      return false;
    }
    map[flowerKey] = { zh, en, time: Date.now() };
    write(key, map, storage);
    return true;
  }

  return {
    register, login, startGuest, setSession, session, logout,
    history, addHistory,
    favorites, isFavorite, toggleFavorite
  };
})();
