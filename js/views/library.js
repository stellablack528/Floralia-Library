/* ============================================================
   视图：花卉资料馆（列表 + 详情书页）
   列表支持搜索；进入详情会记入「我的足迹」。
   ============================================================ */
window.FF = window.FF || {};
FF.views = FF.views || {};

FF.views.library = (function () {

  /* ---------- 列表 ---------- */
  function cardHTML(f, i) {
    const fav = FF.store.isFavorite(f.key) ? '<span class="fav">&#10084;</span>' : "";
    return `
      <a class="lib-card" href="#/library/${f.key}">
        ${fav}
        <div class="no">No.${String(f.order).padStart(2, "0")}</div>
        <div class="zh">${f.zh}</div>
        <div class="en">${f.en}</div>
        <div class="speak">花语 · ${f.speak}</div>
      </a>`;
  }

  function renderList(params) {
    document.getElementById("view").innerHTML = `
      <div class="page">
        <div class="page-kicker">THE HERBARIUM · 花卉资料馆</div>
        <h2>十七页花之书</h2>
        <p class="lede">Oxford Flower17 的 17 个类别，每一页都是一张资料卡：中文名、学名、花语与寓意。花语为西方花语文化的通用整理，文学引文待核对后补充。</p>
        <div class="lib-toolbar">
          <div class="lib-search">
            <span class="glyph">&#9906;</span>
            <input id="lib-q" type="text" placeholder="搜索中文名、英文名或花语…">
          </div>
          <div class="lib-count" id="lib-count"></div>
        </div>
        <div class="lib-grid" id="lib-grid"></div>
      </div>`;

    const input = document.getElementById("lib-q");
    const grid = document.getElementById("lib-grid");
    const count = document.getElementById("lib-count");

    function drawList() {
      const q = input.value.trim().toLowerCase();
      const list = FF.data.flowers.filter((f) =>
        !q || [f.zh, f.en, f.latin, f.speak, f.family].join(" ").toLowerCase().includes(q)
      );
      grid.innerHTML = list.length
        ? list.map((f) => cardHTML(f)).join("")
        : `<div class="lib-empty" style="grid-column:1/-1;">图鉴里没有找到「${input.value}」，换个关键词试试。</div>`;
      count.textContent = `共 ${list.length} 页 · 全 17 页`;
    }

    input.addEventListener("input", drawList);
    drawList();
  }

  /* ---------- 详情书页 ---------- */
  function renderDetail(params) {
    const f = FF.data.byKey(params.key);
    if (!f) { location.hash = "#/library"; return; }

    /* 浏览记录：同一朵花 10 分钟内不重复记录 */
    const hist = FF.store.history();
    const last = hist.find((h) => h.key === f.key);
    if (!last || Date.now() - last.time > 10 * 60 * 1000) {
      FF.store.addHistory({ key: f.key, zh: f.zh, en: f.en, source: "library" });
    }

    const favOn = FF.store.isFavorite(f.key);
    document.getElementById("view").innerHTML = `
      <div class="page">
        <div class="folio-wrap">
          <div class="folio-card">
            <a class="back" href="#/library">&#8592; 返回资料馆</a>
            <div class="folio-kicker page-kicker">FOLIO No.${String(f.order).padStart(2, "0")}</div>
            <div class="folio-name">${f.zh}</div>
            <div class="folio-latin">${f.latin}</div>
            <div class="folio-en">${f.en} · ${f.family}</div>
            <div class="folio-rule"></div>
            <div class="folio-label">花语</div>
            <div class="folio-text">${f.speak}</div>
            <div class="folio-label">寓意与联想（项目赏析）</div>
            <div class="folio-text">${f.meaning}</div>
            <div class="folio-label">辨识特征</div>
            <div class="folio-traits">${f.traits.map((t) => `<span>${t}</span>`).join("")}</div>
            <div class="folio-label">分布与花期</div>
            <div class="folio-text">${f.season}</div>
            <div class="folio-label">核对说明</div>
            <div class="folio-text">${f.note}</div>
            <div class="folio-actions">
              <button class="fav-toggle ${favOn ? "on" : ""}" id="fav-btn">${favOn ? "&#10084; 已收藏 · 点击取消" : "&#9825; 收藏这页书"}</button>
              <button class="btn-primary" id="identify-again">上传照片验证它<span class="arrow">&#8594;</span></button>
            </div>
          </div>
        </div>
      </div>`;

    document.getElementById("fav-btn").addEventListener("click", (e) => {
      const on = FF.store.toggleFavorite(f.key, f.zh, f.en);
      e.currentTarget.className = "fav-toggle " + (on ? "on" : "");
      e.currentTarget.innerHTML = on ? "&#10084; 已收藏 · 点击取消" : "&#9825; 收藏这页书";
      FF.toast(on ? `「${f.zh}」已加入收藏。` : `已取消收藏「${f.zh}」。`);
    });
    document.getElementById("identify-again").addEventListener("click", () => {
      location.hash = "#/identify";
    });
    window.scrollTo(0, 0);
  }

  return { renderList, renderDetail };
})();
