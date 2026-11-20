/* ============================================================
   视图：花卉资料馆（列表 + 详情书页）
   列表支持搜索；进入详情会记入「我的足迹」。
   ============================================================ */
window.FF = window.FF || {};
FF.views = FF.views || {};

FF.views.library = (function () {
  const {text: t} = FF.language;
  const statusLabel = () => t("可查阅 · 暂未纳入拍照识别", "Library entry · Photo identification unavailable");
  const entities = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" };
  const escapeHTML = (value) => String(value).replace(/[&<>"']/g, char => entities[char]);

  function sourceLink(source) {
    const linkTitle = t(`${source.publisher} · ${source.title}`, source.title);
    return `<a href="${escapeHTML(source.url)}" target="_blank" rel="noopener noreferrer">${escapeHTML(linkTitle)}</a>`;
  }

  function localCulture(flower) {
    if (!FF.language.english) return flower.culture;
    return flower.culture.map((record, index) => {
      const [kind, theme, summary, title = record.title, creator = record.creator] = flower.english.culture[index];
      return {...record, kind, theme, title, creator, our_summary: summary, scope: "", locator: ""};
    });
  }

  function cultureHTML(record) {
    return `
      <article class="folio-culture">
        <h4>${escapeHTML(record.theme)}</h4>
        <p class="folio-text">${escapeHTML(record.kind)} · ${escapeHTML(record.creator)} · ${escapeHTML(record.title)}</p>
        ${record.excerpt ? `
          <p class="folio-evidence-label">${t("原文摘录", "Original excerpt")}</p>
          <blockquote class="folio-excerpt" lang="${escapeHTML(record.excerpt_language || "zh-CN")}">${escapeHTML(record.excerpt)}</blockquote>` : ""}
        <p class="folio-text">${escapeHTML(record.our_summary)}</p>
        ${record.scope ? `<p class="folio-text">${escapeHTML(record.scope)}</p>` : ""}
        <p class="folio-text">${sourceLink(record)}${record.locator ? ` · ${escapeHTML(record.locator)}` : ""}</p>
      </article>`;
  }

  function artworkHTML(artwork, related, english) {
    const right = artwork.rights.includes("CC0") ? "CC0" : artwork.rights.includes("公有领域") ? "Public domain" : "Reuse terms";
    return `
      <section class="folio-section" id="folio-art" tabindex="-1" aria-labelledby="folio-art-heading">
        <h3 id="folio-art-heading">${t("经典图像", "Classic artwork")}</h3>
        <figure class="folio-artwork">
          <img src="${escapeHTML(artwork.asset)}" width="${artwork.width}" height="${artwork.height}"
            alt="${escapeHTML(t(artwork.alt, english[0]))}" loading="lazy">
          <figcaption>
            <h4>${escapeHTML(t(artwork.title_zh, artwork.title))}</h4>
            <p>${escapeHTML(t(artwork.creator, english[2]))} · ${escapeHTML(t(artwork.year, english[3]))}</p>
            <p>${escapeHTML(t(artwork.caption, english[1]))}</p>
            <p class="artwork-credit">${escapeHTML(t(artwork.publisher, english[4]))} · ${escapeHTML(artwork.accession)}</p>
            <div class="artwork-links">
              <a href="${escapeHTML(artwork.url)}" target="_blank" rel="noopener noreferrer">${t("查看馆藏原页", "Collection record")} ↗</a>
              <a href="${escapeHTML(artwork.rights_url)}" target="_blank" rel="noopener noreferrer">${escapeHTML(t(artwork.rights, right))}</a>
            </div>
          </figcaption>
        </figure>
        ${related.map(cultureHTML).join("")}
      </section>`;
  }

  function evidenceHTML(record, status) {
    const citation = [record.author, record.title || record.original_name, record.publication_year,
      t(`PDF 第 ${record.page_number} 页`, `PDF page ${record.page_number}`)].filter(Boolean).map(escapeHTML).join(" · ");
    let link = "";
    if (record.source_url) {
      try {
        const url = new URL(record.source_url);
        if (url.protocol === "https:" || url.protocol === "http:") {
          if (/\.pdf$/i.test(url.pathname)) url.hash = `page=${record.page_number}`;
          link = ` · <a href="${escapeHTML(url.href)}" target="_blank" rel="noopener noreferrer">${t("查看原文", "Open source")}</a>`;
        }
      } catch {
        // Keep the written citation if the source address is unavailable.
      }
    }
    return `
      <article class="folio-culture folio-evidence">
        <h3>${escapeHTML(record.topic)}</h3>
        <p class="folio-evidence-label">${t("原文摘录", "Original excerpt")}</p>
        <blockquote>${escapeHTML(record.excerpt)}</blockquote>
        <p class="folio-evidence-label">${t("中文整理", "Chinese notes")}</p>
        <p class="folio-text">${escapeHTML(record.content)}</p>
        <p class="folio-text">${citation}${link}</p>
        ${status === "translations" ? `
          <form class="translation-review" data-evidence-id="${escapeHTML(record.evidence_id)}" data-version="${escapeHTML(record.version)}">
            <label for="translation-${escapeHTML(record.evidence_id)}">${t("中文译文初稿", "Draft Chinese translation")} · ${escapeHTML(record.translation_model)}</label>
            <textarea id="translation-${escapeHTML(record.evidence_id)}" name="translation" rows="4" maxlength="4000" required>${escapeHTML(record.translation)}</textarea>
            <div class="evidence-actions">
              <button class="btn-primary" type="submit" value="verified">${t("通过译文", "Approve translation")}</button>
              <button class="btn-ghost" type="submit" value="rejected" formnovalidate>${t("退回译文", "Reject translation")}</button>
            </div>
          </form>` : record.translation ? `
          <p class="folio-evidence-label">${t("中文译文", "Chinese translation")}</p>
          <p class="folio-text evidence-translation">${escapeHTML(record.translation)}</p>` : `
          <button class="btn-ghost translate-evidence" type="button" data-evidence-id="${escapeHTML(record.evidence_id)}">${t("生成中文译文", "Generate Chinese translation")}</button>`}
        ${status === "pending" ? `<form class="evidence-actions" data-evidence-id="${escapeHTML(record.evidence_id)}" data-version="${escapeHTML(record.version)}">
          <button class="btn-primary" type="submit" value="verified">${t("通过并显示在书页", "Approve and show in folio")}</button>
          <button class="btn-ghost" type="submit" value="rejected">${t("不通过", "Reject excerpt")}</button>
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
          const emptyMessages = { verified: t("暂无已审核的文献摘录。", "No approved excerpts yet."), pending: t("暂无待审核的摘录。", "No excerpts await review."),
            translations: t("暂无待审核的译文。", "No translations await review.") };
          container.innerHTML = records.length ? records.map(record => evidenceHTML(record, status)).join("") : emptyMessages[status];
        }
      } catch {
        if (latest()) container.textContent = t("暂时无法读取文献摘录。", "Excerpts could not be loaded.");
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
        throw new Error(t(result.error || "暂时无法保存，请重试。", "The local service could not save the changes."));
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
      feedback.textContent = t("正在本机生成中文译文…", "Generating a Chinese draft locally…");
      feedback.scrollIntoView({ block: "nearest" });
      try {
        const result = await post("/translate", { evidence_id: Number(button.dataset.evidenceId) });
        await refreshReview();
        feedback.textContent = result.status === "verified" ? t("这条译文已通过审核。", "This translation is already approved.") : t("译文初稿已保存，请对照原文审核。", "Draft saved. Compare it with the original before approval.");
      } catch (error) {
        feedback.textContent = error instanceof TypeError ? t("无法连接本机服务，请重试。", "Cannot reach the local service.") : error.message;
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
      feedback.textContent = t("正在保存审核结果…", "Saving the review…");
      try {
        await post(isTranslation ? "/review-translation" : "", {
          evidence_id: Number(form.dataset.evidenceId), version: form.dataset.version, decision,
          translation: isTranslation ? form.elements.translation.value : undefined
        });
        const item = isTranslation ? "译文" : "摘录";
        feedback.textContent = decision === "verified" ? t(`${item}已通过审核。`, "Review approved.") : t(`${item}已退回。`, "Review rejected.");
        await Promise.all([loadRecords(published), refreshReview()]);
      } catch (error) {
        feedback.textContent = error instanceof TypeError ? t("无法连接本机服务，请重试。", "Cannot reach the local service.") : error.message;
        buttons.forEach(button => { button.disabled = false; });
      }
    }
    pending.addEventListener("submit", submitReview);
    translations.addEventListener("submit", submitReview);
  }

  /* ---------- 列表 ---------- */
  function cardHTML(f) {
    const fav = FF.store.isFavorite(f.key) ? '<span class="fav">&#10084;</span>' : "";
    const [record] = localCulture(f);
    return `
      <a class="lib-card" href="#/library/${encodeURIComponent(f.key)}">
        ${fav}
        <div class="no">No.${String(f.order).padStart(2, "0")}</div>
        <div class="zh">${escapeHTML(t(f.zh, f.en))}</div>
        <div class="en">${escapeHTML(t(f.en, f.latin))}</div>
        <div class="speak">${escapeHTML(record.kind)} · ${escapeHTML(record.theme)}</div>
        ${FF.recognition.supports(f.key) ? "" : `<div class="speak">${statusLabel()}</div>`}
      </a>`;
  }

  function renderList() {
    document.getElementById("view").innerHTML = `
      <div class="page">
        <div class="page-kicker">${t("THE HERBARIUM · 花卉资料馆", "THE HERBARIUM")}</div>
        <h2>${t("花之书", "Flower Library")}</h2>
        <p class="lede">${t(`资料馆收录 ${FF.data.flowers.length} 页。${window.FF_LOCAL_MODEL ? `其中 ${FF.recognition.count} 类可拍照识别。` : ""}`, `${FF.data.flowers.length} flower folios. ${window.FF_LOCAL_MODEL ? `${FF.recognition.count} categories supported by photo identification.` : "Browse plant profiles, literature and art."}`)}</p>
        ${window.FF_LOCAL_MODEL ? `<p><a class="btn-ghost import-link" href="#/documents/import">${t("导入 PDF 文献", "Import a PDF")}</a></p>` : ""}
        <div class="lib-toolbar">
          <div class="lib-search">
            <span class="glyph">&#9906;</span>
            <input id="lib-q" type="search" aria-label="${t("搜索花卉资料", "Search flower folios")}" placeholder="${t("搜索花名、学名、作品或关键词…", "Search names, species, works or keywords…")}">
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
        const topics = [...f.culture, ...localCulture(f)].flatMap(record => [record.kind, record.theme, record.creator, record.title, record.our_summary]);
        const artTitles = f.artwork ? [f.artwork.title, f.artwork.title_zh] : [];
        return !q || [f.zh, f.en, f.latin, f.family, f.genus, ...(f.aliases || []), ...f.traits, ...topics, ...artTitles].join(" ").toLowerCase().includes(q);
      });
      grid.innerHTML = list.length
        ? list.map((f) => cardHTML(f)).join("")
        : `<div class="lib-empty" style="grid-column:1/-1;">${t(`找不到「${escapeHTML(input.value)}」，换个关键词试试。`, `No folios match “${escapeHTML(input.value)}”. Try another search.`)}</div>`;
      count.textContent = t(`共 ${list.length} 页 · 全 ${FF.data.flowers.length} 页`, `${list.length} of ${FF.data.flowers.length} folios`);
    }

    input.addEventListener("input", drawList);
    drawList();
  }

  /* ---------- 详情书页 ---------- */
  function renderDetail(params) {
    const f = FF.data.byKey(params.key);
    if (!f) { location.hash = "#/library"; return; }
    const recognizable = FF.recognition.supports(f.key);
    const evidenceAvailable = window.FF_LOCAL_MODEL && f.class_id !== null;

    /* 浏览记录：同一朵花 10 分钟内不重复记录 */
    const hist = FF.store.history();
    const last = hist.find((h) => h.key === f.key);
    if (!last || Date.now() - last.time > 10 * 60 * 1000) {
      FF.store.addHistory({ key: f.key, zh: f.zh, en: f.en, source: "library" });
    }

    const favOn = FF.store.isFavorite(f.key);
    const artwork = f.artwork;
    const culture = localCulture(f);
    const isPainting = (_, index) => f.culture[index].kind === "绘画";
    const literature = artwork ? culture.filter((record, index) => !isPainting(record, index)) : culture;
    const relatedArt = artwork ? culture.filter((record, index) => isPainting(record, index) && record.url !== artwork.url) : [];
    const profile = t(f, f.english);
    const name = t(f.zh, f.en);
    const [botany, literatureLabel, artLabel] = t(["植物档案", "文学与文化", "经典图像"], ["Plant profile", "Literature & culture", "Classic artwork"]);
    const favorite = on => on ? t("&#10084; 已收藏 · 点击取消", "&#10084; Remove bookmark") : t("&#9825; 收藏这页书", "&#9825; Bookmark this folio");
    document.getElementById("view").innerHTML = `
      <div class="page">
        <div class="folio-wrap">
          <div class="folio-card">
            <a class="back" href="#/library">&#8592; ${t("返回资料馆", "Back to the library")}</a>
            <h2 class="folio-name">${escapeHTML(name)}</h2>
            <div class="folio-latin">${t("代表植物", "Representative species")} · ${escapeHTML(f.latin)}</div>
            <div class="folio-en">${escapeHTML(t(`${f.en} · ${f.family} · ${f.genus}`, `${profile.family} · ${f.latin.split(" ")[0]}`))}</div>
            ${recognizable ? "" : `<p class="folio-text">${statusLabel()}</p>`}
            <nav class="folio-jump" aria-label="${t("书页目录", "Folio sections")}">
              <button type="button" data-section="folio-botany">${botany}</button>
              <button type="button" data-section="folio-literature">${literatureLabel}</button>
              ${artwork ? `<button type="button" data-section="folio-art">${artLabel}</button>` : ""}
            </nav>
            <section class="folio-section" id="folio-botany" tabindex="-1" aria-labelledby="folio-botany-heading">
              <h3 id="folio-botany-heading">${botany}</h3>
              <div class="folio-label">${t("辨识特征", "Field marks")}</div>
              <div class="folio-traits">${profile.traits.map(trait => `<span>${escapeHTML(trait)}</span>`).join("")}</div>
              <div class="folio-label">${t("生境与花期", "Habitat and flowering season")}</div>
              <div class="folio-text">${escapeHTML(profile.habitat)} ${escapeHTML(profile.season)}</div>
              <div class="folio-label">${t("类别说明", "Species notes")}</div>
              <div class="folio-text">${escapeHTML(profile.note)}</div>
              ${profile.comparison ? `<h4 class="folio-label">${t("容易混淆的花", "Look-alikes")}</h4><p class="folio-text">${escapeHTML(profile.comparison)}</p>` : ""}
              <div class="folio-label">${t("植物资料来源", "Botanical sources")}</div>
              <div class="folio-text">${f.sources.map(sourceLink).join("<br>")}</div>
            </section>
            <section class="folio-section" id="folio-literature" tabindex="-1" aria-labelledby="folio-literature-heading">
              <h3 id="folio-literature-heading">${literatureLabel}</h3>
              ${literature.map(cultureHTML).join("")}
              ${evidenceAvailable ? `<div id="evidence-published" class="folio-text" aria-live="polite">${t("正在读取已审核的摘录…", "Loading approved excerpts…")}</div>` : ""}
            </section>
            ${artwork ? artworkHTML(artwork, relatedArt, f.english.art) : ""}
            ${evidenceAvailable ? `
              <details id="evidence-review" class="evidence-review">
                <summary>${t("审核文献摘录", "Review excerpts")}</summary>
                <p class="folio-text">${t("打开原文，核对摘录、页码和中文整理后再提交。", "Open the source and check the excerpt, page number and notes before approving.")}</p>
                <p id="evidence-feedback" class="folio-text" role="status"></p>
                <div id="evidence-pending" class="folio-text">${t("正在读取待审核的摘录…", "Loading excerpts for review…")}</div>
                <div class="folio-label">${t("待审核译文", "Translations for review")}</div>
                <div id="translation-pending" class="folio-text">${t("正在读取待审核的译文…", "Loading translations for review…")}</div>
              </details>` : ""}
            <div class="folio-actions">
              <button class="fav-toggle ${favOn ? "on" : ""}" id="fav-btn">${favorite(favOn)}</button>
              ${recognizable ? `<button class="btn-primary" id="identify-again">${t("上传照片识别", "Identify a photo")}<span class="arrow">&#8594;</span></button>` : ""}
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
      e.currentTarget.innerHTML = favorite(on);
      FF.toast(on ? t(`「${name}」已加入收藏。`, `Bookmarked ${name}.`) : t(`已取消收藏「${name}」。`, `Removed the bookmark for ${name}.`));
    });
    document.getElementById("identify-again")?.addEventListener("click", () => {
      location.hash = "#/identify";
    });
    if (evidenceAvailable) bindEvidence(f.key);
    window.scrollTo(0, 0);
  }

  return { renderList, renderDetail };
})();
