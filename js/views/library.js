/* ============================================================
   视图：花卉资料馆（列表 + 详情书页）
   列表支持搜索；进入详情会记入「我的足迹」。
   ============================================================ */
window.FF = window.FF || {};
FF.views = FF.views || {};

FF.views.library = (function () {
  const entities = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" };
  const escapeHTML = (value) => String(value).replace(/[&<>"']/g, char => entities[char]);

  function sourceLink(source) {
    return `<a href="${escapeHTML(source.url)}" target="_blank" rel="noopener noreferrer">${escapeHTML(source.publisher)} · ${escapeHTML(source.title)}</a>`;
  }

  function cultureHTML(record) {
    return `
      <article class="folio-culture">
        <h3>${escapeHTML(record.theme)}</h3>
        <p class="folio-text">${escapeHTML(record.kind)} · ${escapeHTML(record.creator)} · ${escapeHTML(record.title)}</p>
        <p class="folio-text">${escapeHTML(record.our_summary)}</p>
        <p class="folio-text">${escapeHTML(record.scope)}</p>
        <p class="folio-text">${sourceLink(record)} · ${escapeHTML(record.locator)}</p>
      </article>`;
  }

  /* ---------- 列表 ---------- */
  function cardHTML(f) {
    const fav = FF.store.isFavorite(f.key) ? '<span class="fav">&#10084;</span>' : "";
    return `
      <a class="lib-card" href="#/library/${encodeURIComponent(f.key)}">
        ${fav}
        <div class="no">No.${String(f.order).padStart(2, "0")}</div>
        <div class="zh">${escapeHTML(f.zh)}</div>
        <div class="en">${escapeHTML(f.en)}</div>
        <div class="speak">${escapeHTML(f.culture[0].kind)} · ${escapeHTML(f.culture[0].theme)}</div>
      </a>`;
  }

  function renderList() {
    document.getElementById("view").innerHTML = `
      <div class="page">
        <div class="page-kicker">THE HERBARIUM · 花卉资料馆</div>
        <h2>十七页花之书</h2>
        <p class="lede">查阅 Oxford Flower17 各类的代表植物、辨识特征与花期，阅读有出处的文学、艺术和民俗记录。</p>
        <div class="lib-toolbar">
          <div class="lib-search">
            <span class="glyph">&#9906;</span>
            <input id="lib-q" type="search" aria-label="搜索花卉资料" placeholder="搜索花名、学名、作品或关键词…">
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
      const list = FF.data.flowers.filter((f) => {
        const topics = f.culture.flatMap(record => [record.kind, record.theme, record.creator, record.title, record.our_summary]);
        return !q || [f.zh, f.en, f.latin, f.family, f.genus, ...f.traits, ...topics].join(" ").toLowerCase().includes(q);
      });
      grid.innerHTML = list.length
        ? list.map((f) => cardHTML(f)).join("")
        : `<div class="lib-empty" style="grid-column:1/-1;">找不到「${escapeHTML(input.value)}」，换个关键词试试。</div>`;
      count.textContent = `共 ${list.length} 页 · 全 ${FF.data.flowers.length} 页`;
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
            <div class="folio-name">${escapeHTML(f.zh)}</div>
            <div class="folio-latin">代表植物 · ${escapeHTML(f.latin)}</div>
            <div class="folio-en">${escapeHTML(f.en)} · ${escapeHTML(f.family)} · ${escapeHTML(f.genus)}</div>
            <div class="folio-rule"></div>
            <div class="folio-label">辨识特征</div>
            <div class="folio-traits">${f.traits.map(t => `<span>${escapeHTML(t)}</span>`).join("")}</div>
            <div class="folio-label">生境与花期</div>
            <div class="folio-text">${escapeHTML(f.habitat)} ${escapeHTML(f.season)}</div>
            <div class="folio-label">类别说明</div>
            <div class="folio-text">${escapeHTML(f.note)}</div>
            <div class="folio-label">植物资料来源</div>
            <div class="folio-text">${f.sources.map(sourceLink).join("<br>")}</div>
            <div class="folio-label">文献与文学</div>
            ${f.culture.map(cultureHTML).join("")}
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
