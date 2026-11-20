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
        <h4>${escapeHTML(record.theme)}</h4>
        <p class="folio-text">${escapeHTML(record.kind)} · ${escapeHTML(record.creator)} · ${escapeHTML(record.title)}</p>
        <p class="folio-text">${escapeHTML(record.our_summary)}</p>
        <p class="folio-text">${escapeHTML(record.scope)}</p>
        <p class="folio-text">${sourceLink(record)} · ${escapeHTML(record.locator)}</p>
      </article>`;
  }

  function artworkHTML(artwork, related) {
    return `
      <section class="folio-section" id="folio-art" tabindex="-1" aria-labelledby="folio-art-heading">
        <h3 id="folio-art-heading">经典图像</h3>
        <figure class="folio-artwork">
          <img src="${escapeHTML(artwork.asset)}" width="${artwork.width}" height="${artwork.height}"
            alt="${escapeHTML(artwork.alt)}" loading="lazy">
          <figcaption>
            <h4>${escapeHTML(artwork.title_zh)}</h4>
            <p>${escapeHTML(artwork.creator)} · ${escapeHTML(artwork.year)}</p>
            <p>${escapeHTML(artwork.caption)}</p>
            <p class="artwork-credit">${escapeHTML(artwork.publisher)} · ${escapeHTML(artwork.accession)}</p>
            <div class="artwork-links">
              <a href="${escapeHTML(artwork.url)}" target="_blank" rel="noopener noreferrer">查看馆藏原页 ↗</a>
              <a href="${escapeHTML(artwork.rights_url)}" target="_blank" rel="noopener noreferrer">${escapeHTML(artwork.rights)}</a>
            </div>
          </figcaption>
        </figure>
        ${related.map(cultureHTML).join("")}
      </section>`;
  }

  function evidenceHTML(record, status) {
    const citation = [record.author, record.title || record.original_name, record.publication_year,
      `PDF 第 ${record.page_number} 页`].filter(Boolean).map(escapeHTML).join(" · ");
    let link = "";
    if (record.source_url) {
      try {
        const url = new URL(record.source_url);
        if (url.protocol === "https:" || url.protocol === "http:") {
          if (/\.pdf$/i.test(url.pathname)) url.hash = `page=${record.page_number}`;
          link = ` · <a href="${escapeHTML(url.href)}" target="_blank" rel="noopener noreferrer">查看原文</a>`;
        }
      } catch {
        // Keep the written citation if the source address is unavailable.
      }
    }
    return `
      <article class="folio-culture folio-evidence">
        <h3>${escapeHTML(record.topic)}</h3>
        <p class="folio-evidence-label">原文摘录</p>
        <blockquote>${escapeHTML(record.excerpt)}</blockquote>
        <p class="folio-evidence-label">中文整理</p>
        <p class="folio-text">${escapeHTML(record.content)}</p>
        <p class="folio-text">${citation}${link}</p>
        ${status === "translations" ? `
          <form class="translation-review" data-evidence-id="${escapeHTML(record.evidence_id)}" data-version="${escapeHTML(record.version)}">
            <label for="translation-${escapeHTML(record.evidence_id)}">中文译文初稿 · ${escapeHTML(record.translation_model)}</label>
            <textarea id="translation-${escapeHTML(record.evidence_id)}" name="translation" rows="4" maxlength="4000" required>${escapeHTML(record.translation)}</textarea>
            <div class="evidence-actions">
              <button class="btn-primary" type="submit" value="verified">通过译文</button>
              <button class="btn-ghost" type="submit" value="rejected" formnovalidate>退回译文</button>
            </div>
          </form>` : record.translation ? `
          <p class="folio-evidence-label">中文译文</p>
          <p class="folio-text evidence-translation">${escapeHTML(record.translation)}</p>` : `
          <button class="btn-ghost translate-evidence" type="button" data-evidence-id="${escapeHTML(record.evidence_id)}">生成中文译文</button>`}
        ${status === "pending" ? `<form class="evidence-actions" data-evidence-id="${escapeHTML(record.evidence_id)}" data-version="${escapeHTML(record.version)}">
          <button class="btn-primary" type="submit" value="verified">通过并显示在书页</button>
          <button class="btn-ghost" type="submit" value="rejected">不通过</button>
        </form>` : ""}
      </article>`;
  }

  function bindEvidence(classKey) {
    const published = document.getElementById("evidence-published");
    const review = document.getElementById("evidence-review");
    const pending = document.getElementById("evidence-pending");
    const feedback = document.getElementById("evidence-feedback");
    const translations = document.getElementById("translation-pending");
    const url = `/api/evidence/${encodeURIComponent(classKey)}`;
    const reads = new WeakMap();

    async function loadRecords(container, status = "verified") {
      const request = {};
      reads.set(container, request);
      const latest = () => container.isConnected && reads.get(container) === request;
      try {
        const response = await fetch(url + "?status=" + status);
        if (!response.ok) throw new Error();
        const { records } = await response.json();
        if (latest()) {
          const emptyMessages = { verified: "暂无已审核的文献摘录。", pending: "暂无待审核的摘录。",
            translations: "暂无待审核的译文。" };
          container.innerHTML = records.length ? records.map(record => evidenceHTML(record, status)).join("") : emptyMessages[status];
        }
      } catch {
        if (latest()) container.textContent = "暂时无法读取文献摘录。";
      }
    }

    function refreshReview() {
      return Promise.all([loadRecords(pending, "pending"), loadRecords(translations, "translations")]);
    }

    async function post(action, data) {
      const response = await fetch(url + action, {
        method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(data)
      });
      const result = await response.json();
      if (!response.ok) {
        if (response.status === 409) await refreshReview();
        throw new Error(result.error || "暂时无法保存，请重试。");
      }
      return result;
    }

    loadRecords(published);
    review.addEventListener("toggle", () => {
      if (review.open) refreshReview();
    });
    async function generate(event) {
      const button = event.target.closest(".translate-evidence");
      if (!button) return;
      button.disabled = true;
      review.open = true;
      feedback.textContent = "正在本机生成中文译文…";
      feedback.scrollIntoView({ block: "nearest" });
      try {
        const result = await post("/translate", { evidence_id: Number(button.dataset.evidenceId) });
        await refreshReview();
        feedback.textContent = result.status === "verified" ? "这条译文已通过审核。" : "译文初稿已保存，请对照原文审核。";
      } catch (error) {
        feedback.textContent = error instanceof TypeError ? "无法连接本机服务，请重试。" : error.message;
      } finally {
        button.disabled = false;
      }
    }
    published.addEventListener("click", generate);
    pending.addEventListener("click", generate);

    async function submitReview(event) {
      event.preventDefault();
      const form = event.target;
      const decision = event.submitter?.value;
      if (!decision) return;
      const isTranslation = form.classList.contains("translation-review");
      const buttons = [...form.querySelectorAll("button")];
      buttons.forEach(button => { button.disabled = true; });
      feedback.textContent = "正在保存审核结果…";
      try {
        await post(isTranslation ? "/review-translation" : "", {
          evidence_id: Number(form.dataset.evidenceId), version: form.dataset.version, decision,
          translation: isTranslation ? form.elements.translation.value : undefined
        });
        const item = isTranslation ? "译文" : "摘录";
        feedback.textContent = decision === "verified" ? `${item}已通过审核。` : `${item}已退回。`;
        await Promise.all([loadRecords(published), refreshReview()]);
      } catch (error) {
        feedback.textContent = error instanceof TypeError ? "无法连接本机服务，请重试。" : error.message;
        buttons.forEach(button => { button.disabled = false; });
      }
    }
    pending.addEventListener("submit", submitReview);
    translations.addEventListener("submit", submitReview);
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
        ${f.class_id === null ? '<div class="speak">可查阅 · 暂未纳入拍照识别</div>' : ""}
      </a>`;
  }

  function renderList() {
    document.getElementById("view").innerHTML = `
      <div class="page">
        <div class="page-kicker">THE HERBARIUM · 花卉资料馆</div>
        <h2>花之书</h2>
        <p class="lede">查阅花卉档案，阅读有出处的文学、艺术和民俗记录。资料馆收录 ${FF.data.flowers.length} 页，其中 ${FF.data.recognizableFlowers.length} 类可拍照识别。</p>
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
        const artTitles = f.artwork ? [f.artwork.title, f.artwork.title_zh] : [];
        return !q || [f.zh, f.en, f.latin, f.family, f.genus, ...(f.aliases || []), ...f.traits, ...topics, ...artTitles].join(" ").toLowerCase().includes(q);
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
    const recognizable = f.class_id !== null;
    const evidenceAvailable = window.FF_LOCAL_MODEL && recognizable;

    /* 浏览记录：同一朵花 10 分钟内不重复记录 */
    const hist = FF.store.history();
    const last = hist.find((h) => h.key === f.key);
    if (!last || Date.now() - last.time > 10 * 60 * 1000) {
      FF.store.addHistory({ key: f.key, zh: f.zh, en: f.en, source: "library" });
    }

    const favOn = FF.store.isFavorite(f.key);
    const artwork = f.artwork;
    const literature = artwork ? f.culture.filter(record => record.kind !== "绘画") : f.culture;
    const relatedArt = artwork ? f.culture.filter(record => record.kind === "绘画" && record.url !== artwork.url) : [];
    document.getElementById("view").innerHTML = `
      <div class="page">
        <div class="folio-wrap">
          <div class="folio-card">
            <a class="back" href="#/library">&#8592; 返回资料馆</a>
            <h2 class="folio-name">${escapeHTML(f.zh)}</h2>
            <div class="folio-latin">代表植物 · ${escapeHTML(f.latin)}</div>
            <div class="folio-en">${escapeHTML(f.en)} · ${escapeHTML(f.family)} · ${escapeHTML(f.genus)}</div>
            ${recognizable ? "" : '<p class="folio-text">可查阅 · 暂未纳入拍照识别</p>'}
            <nav class="folio-jump" aria-label="书页目录">
              <button type="button" data-section="folio-botany">植物档案</button>
              <button type="button" data-section="folio-literature">文学与文化</button>
              ${artwork ? '<button type="button" data-section="folio-art">经典图像</button>' : ""}
            </nav>
            <section class="folio-section" id="folio-botany" tabindex="-1" aria-labelledby="folio-botany-heading">
              <h3 id="folio-botany-heading">植物档案</h3>
              <div class="folio-label">辨识特征</div>
              <div class="folio-traits">${f.traits.map(t => `<span>${escapeHTML(t)}</span>`).join("")}</div>
              <div class="folio-label">生境与花期</div>
              <div class="folio-text">${escapeHTML(f.habitat)} ${escapeHTML(f.season)}</div>
              <div class="folio-label">类别说明</div>
              <div class="folio-text">${escapeHTML(f.note)}</div>
              <div class="folio-label">植物资料来源</div>
              <div class="folio-text">${f.sources.map(sourceLink).join("<br>")}</div>
            </section>
            <section class="folio-section" id="folio-literature" tabindex="-1" aria-labelledby="folio-literature-heading">
              <h3 id="folio-literature-heading">文学与文化</h3>
              ${literature.map(cultureHTML).join("")}
              ${evidenceAvailable ? '<div id="evidence-published" class="folio-text" aria-live="polite">正在读取已审核的摘录…</div>' : ""}
            </section>
            ${artwork ? artworkHTML(artwork, relatedArt) : ""}
            ${evidenceAvailable ? `
              <details id="evidence-review" class="evidence-review">
                <summary>审核文献摘录</summary>
                <p class="folio-text">打开原文，核对摘录、页码和中文整理后再提交。</p>
                <p id="evidence-feedback" class="folio-text" role="status"></p>
                <div id="evidence-pending" class="folio-text">正在读取待审核的摘录…</div>
                <div class="folio-label">待审核译文</div>
                <div id="translation-pending" class="folio-text">正在读取待审核的译文…</div>
              </details>` : ""}
            <div class="folio-actions">
              <button class="fav-toggle ${favOn ? "on" : ""}" id="fav-btn">${favOn ? "&#10084; 已收藏 · 点击取消" : "&#9825; 收藏这页书"}</button>
              ${recognizable ? '<button class="btn-primary" id="identify-again">上传照片验证它<span class="arrow">&#8594;</span></button>' : ""}
            </div>
          </div>
        </div>
      </div>`;

    for (const button of document.querySelectorAll(".folio-jump button")) {
      button.addEventListener("click", () => {
        const section = document.getElementById(button.dataset.section);
        section.focus({preventScroll: true});
        section.scrollIntoView({block: "start"});
      });
    }

    document.getElementById("fav-btn").addEventListener("click", (e) => {
      const on = FF.store.toggleFavorite(f.key, f.zh, f.en);
      e.currentTarget.className = "fav-toggle " + (on ? "on" : "");
      e.currentTarget.innerHTML = on ? "&#10084; 已收藏 · 点击取消" : "&#9825; 收藏这页书";
      FF.toast(on ? `「${f.zh}」已加入收藏。` : `已取消收藏「${f.zh}」。`);
    });
    document.getElementById("identify-again")?.addEventListener("click", () => {
      location.hash = "#/identify";
    });
    if (evidenceAvailable) bindEvidence(f.key);
    window.scrollTo(0, 0);
  }

  return { renderList, renderDetail };
})();
