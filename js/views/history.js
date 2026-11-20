/* ============================================================
   视图：我的足迹（查花记录 + 收藏）
   每个账号独立：记录来源 identify=识别 / library=浏览书页。
   ============================================================ */
window.FF = window.FF || {};
FF.views = FF.views || {};

FF.views.history = (function () {
  const {text: t} = FF.language;
  const escape = value => String(value).replace(/[&<>"']/g, char => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"})[char]);

  function fmtTime(ts) {
    const d = new Date(ts);
    const p = (n) => String(n).padStart(2, "0");
    return `${d.getMonth() + 1}/${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}`;
  }

  function render() {
    const records = FF.store.history();
    const favs = FF.store.favorites();
    const favList = Object.entries(favs).sort((a, b) => b[1].time - a[1].time);

    document.getElementById("view").innerHTML = `
      <div class="page">
        <div class="page-kicker">${t("READER'S LEDGER · 我的足迹", "READER'S LEDGER")}</div>
        <h2>${t("你在这本图鉴里留下的痕迹", "Your history and bookmarks")}</h2>
        <p class="lede">${FF.store.session()?.guest ? t("足迹和收藏暂存在此标签页，退出游客模式时清除。", "Guest history and bookmarks are kept in this tab until you sign out.") :
          t("每一次识别与翻阅都会记在这里，数据保存在本机浏览器中。", "Identifications and folio visits are saved in this browser.")}</p>

        <div class="stat-row">
          <div class="stat-box"><b>${new Set(records.map((r) => r.key)).size}</b><span>${t("查过的花（去重）", "Distinct flowers")}</span></div>
          <div class="stat-box"><b>${records.length}</b><span>${t("累计查询次数", "History entries")}</span></div>
          <div class="stat-box"><b>${favList.length}</b><span>${t("收藏的书页", "Bookmarked folios")}</span></div>
        </div>

        <div class="hist-grid">
          <div class="panel">
            <div class="panel-kicker">${t("TIMELINE · 查花记录", "TIMELINE")}</div>
            <h3>${t("最近翻过的花", "Recently viewed")}</h3>
            <div id="hist-list">
              ${records.length ? records.slice(0, 30).map((r) => `
                <div class="hist-item">
                  <span class="when">${fmtTime(r.time)}</span>
                  <span class="what"><strong>${escape(t(r.zh,r.en))}</strong>${FF.language.english ? "" : `<small>${escape(r.en)}</small>`}</span>
                  <span class="hist-tag ${r.source === "identify" ? "" : "look"}">${r.source === "identify" ? t("识别", "Prediction") : t("翻阅", "Visit")}</span>
                  <a class="go" href="#/library/${encodeURIComponent(r.key)}">${t("书页", "Folio")} &#8594;</a>
                </div>`).join("")
              : `<div class="empty-hint"><div class="mark">&#10047;</div><p><a href="#/identify">${t("去识花台上传第一张照片", "Upload your first flower photo")}</a></p></div>`}
            </div>
          </div>
          <div class="panel">
            <div class="panel-kicker">${t("BLOOMMARKS · 收藏夹", "BOOKMARKS")}</div>
            <h3>${t("夹在书里的花", "Bookmarked flowers")}</h3>
            <div id="fav-list">
              ${favList.length ? favList.map(([key, v]) => `
                <div class="fav-mini">
                  <a class="nm" href="#/library/${encodeURIComponent(key)}" style="text-decoration:none;">${escape(t(v.zh,v.en))}${FF.language.english ? "" : `<small>${escape(v.en)}</small>`}</a>
                  <button data-key="${escape(key)}" title="${t("取消收藏", "Remove bookmark")}">&#10007;</button>
                </div>`).join("")
              : `<div class="empty-hint"><div class="mark">&#9825;</div><p>${t("收藏夹还空着。在书页底部按下「收藏这页书」。", "Bookmark a folio to see it here.")}</p></div>`}
            </div>
          </div>
        </div>
      </div>`;

    document.querySelectorAll("#fav-list button").forEach((btn) => {
      btn.addEventListener("click", () => {
        const key = btn.dataset.key;
        const f = FF.data.byKey(key);
        FF.store.toggleFavorite(key, f ? f.zh : key, f ? f.en : "");
        FF.toast(t("已从收藏夹移出。", "Bookmark removed."));
        render();
      });
    });
  }

  return { render };
})();
