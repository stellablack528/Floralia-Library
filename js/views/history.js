/* ============================================================
   视图：我的足迹（查花记录 + 收藏）
   每个账号独立：记录来源 identify=识别 / library=浏览书页。
   ============================================================ */
window.FF = window.FF || {};
FF.views = FF.views || {};

FF.views.history = (function () {

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
        <div class="page-kicker">READER'S LEDGER · 我的足迹</div>
        <h2>你在这本图鉴里留下的痕迹</h2>
        <p class="lede">每一次识别与翻阅都会记在这里，数据保存在本机浏览器中。</p>

        <div class="stat-row">
          <div class="stat-box"><b>${new Set(records.map((r) => r.key)).size}</b><span>查过的花（去重）</span></div>
          <div class="stat-box"><b>${records.length}</b><span>累计查询次数</span></div>
          <div class="stat-box"><b>${favList.length}</b><span>收藏的书页</span></div>
        </div>

        <div class="hist-grid">
          <div class="panel">
            <div class="panel-kicker">TIMELINE · 查花记录</div>
            <h3>最近翻过的花</h3>
            <div id="hist-list">
              ${records.length ? records.slice(0, 30).map((r) => `
                <div class="hist-item">
                  <span class="when">${fmtTime(r.time)}</span>
                  <span class="what"><strong>${r.zh}</strong><small>${r.en}</small></span>
                  <span class="hist-tag ${r.source === "identify" ? "" : "look"}">${r.source === "identify" ? "识别" : "翻阅"}</span>
                  <a class="go" href="#/library/${r.key}">书页 &#8594;</a>
                </div>`).join("")
              : `<div class="empty-hint"><div class="mark">&#10047;</div><p>还没有查过任何花。<a href="#/identify">去识花台上传第一张照片</a>。</p></div>`}
            </div>
          </div>
          <div class="panel">
            <div class="panel-kicker">BLOOMMARKS · 收藏夹</div>
            <h3>夹在书里的花</h3>
            <div id="fav-list">
              ${favList.length ? favList.map(([key, v]) => `
                <div class="fav-mini">
                  <a class="nm" href="#/library/${key}" style="text-decoration:none;">${v.zh}<small>${v.en}</small></a>
                  <button data-key="${key}" title="取消收藏">&#10007;</button>
                </div>`).join("")
              : `<div class="empty-hint"><div class="mark">&#9825;</div><p>收藏夹还空着。在书页底部按下「收藏这页书」。</p></div>`}
            </div>
          </div>
        </div>
      </div>`;

    document.querySelectorAll("#fav-list button").forEach((btn) => {
      btn.addEventListener("click", () => {
        const key = btn.dataset.key;
        const f = FF.data.byKey(key);
        FF.store.toggleFavorite(key, f ? f.zh : key, f ? f.en : "");
        FF.toast("已从收藏夹移出。");
        render();
      });
    });
  }

  return { render };
})();
