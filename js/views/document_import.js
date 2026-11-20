window.FF = window.FF || {};
FF.views = FF.views || {};

FF.views.documentImport = (function () {
  const {text: t} = FF.language;
  const endpoint = "/api/document-imports";

  async function request(url, options) {
    const response = await fetch(url, options);
    const data = await response.json();
    if (!response.ok) throw new Error(t(data.error || "本机服务暂时无法处理请求。", "The local service could not complete the request."));
    return data;
  }

  function render() {
    if (!window.FF_LOCAL_MODEL) {
      location.replace("#/library");
      return;
    }
    document.getElementById("view").innerHTML = `
      <div class="page document-import">
        <a class="back" href="#/library">← ${t("返回花卉资料馆", "Back to the flower library")}</a>
        <h2>${t("导入 PDF 文献", "Import a PDF")}</h2>
        <p class="lede">${t("选一份 PDF 和一页，预览文字后把原文摘录关联到花卉书页。", "Choose a PDF and a page, preview the text, then link an excerpt to a supported folio.")}</p>
        <form id="pdf-upload" class="panel import-form">
          <div class="import-fields">
            <label>${t("PDF 文件（最多 40 MB）", "PDF file (up to 40 MB)")}<input name="pdf" type="file" accept=".pdf,application/pdf" required></label>
            <label>${t("PDF 页码", "Page number")}<input name="page" type="number" min="1" max="10000" value="1" required></label>
            <label>${t("解析方式", "Parsing mode")}<select name="tier">
              <option value="flash">${t("Flash · 可复制文字的 PDF", "Flash · Selectable text")}</option>
              <option value="basic">${t("Basic · 扫描件（OCR）", "Basic · Scanned PDF (OCR)")}</option>
            </select></label>
          </div>
          <button class="btn-primary" type="submit">${t("解析这一页", "Parse this page")}</button>
          <p id="import-progress" class="folio-text" role="status"></p>
        </form>
        <section id="pdf-preview" class="panel hidden">
          <h3>${t("原文预览", "Source preview")}</h3>
          <p id="preview-meta" class="folio-text"></p>
          <label class="folio-text" for="preview-text">${t("在下方选中要入库的文字", "Select the text to save below")}</label>
          <textarea id="preview-text" rows="13" readonly spellcheck="false"></textarea>
          <button id="select-excerpt" class="btn-ghost" type="button">${t("使用选中的原文", "Use the selected text")}</button>
        </section>
        <form id="save-excerpt" class="panel import-form hidden">
          <h3>${t("摘录入库", "Save an excerpt")}</h3>
          <label>${t("原文摘录", "Original excerpt")}<textarea name="excerpt" rows="5" readonly required></textarea></label>
          <div class="import-fields">
            <label>${t("关联书页", "Related folio")}<select name="flower" required></select></label>
            <label>${t("摘录标题", "Excerpt title")}<input name="topic" maxlength="120" required></label>
          </div>
          <label>${t("PDF 原文网址（可选）", "Source PDF URL (optional)")}<input name="source" type="url" maxlength="2048" placeholder="https://…"></label>
          <label>${t("中文整理（可选）", "Chinese notes (optional)")}<textarea name="summary" maxlength="2400" rows="3"></textarea></label>
          <div class="import-actions">
            <button class="btn-primary" type="submit">${t("存为待审核摘录", "Save for review")}</button>
            <a id="import-book" class="hidden">${t("打开对应书页", "Open related folio")} →</a>
          </div>
          <p id="save-status" class="folio-text" role="status"></p>
        </form>
      </div>`;

    const upload = document.getElementById("pdf-upload");
    const progress = document.getElementById("import-progress");
    const preview = document.getElementById("pdf-preview");
    const previewMeta = document.getElementById("preview-meta");
    const text = document.getElementById("preview-text");
    const save = document.getElementById("save-excerpt");
    const status = document.getElementById("save-status");
    const book = document.getElementById("import-book");
    save.elements.flower.add(new Option(t("选择花卉", "Select a flower"), ""));
    for (const entry of FF.data.recognizableFlowers) save.elements.flower.add(new Option(t(entry.zh, entry.en), entry.key));
    let job;

    upload.addEventListener("submit", async event => {
      event.preventDefault();
      const file = upload.elements.pdf.files[0];
      if (!file || file.size > 40 * 1024 * 1024) {
        progress.textContent = t("请选择不超过 40 MB 的 PDF。", "Choose a PDF up to 40 MB.");
        return;
      }
      const button = event.submitter;
      button.disabled = true;
      job = undefined;
      preview.classList.add("hidden");
      save.classList.add("hidden");
      book.classList.add("hidden");
      progress.textContent = t("正在上传到本机…", "Uploading to the local service…");
      try {
        const options = new URLSearchParams({filename: file.name, page: upload.elements.page.value,
          tier: upload.elements.tier.value});
        ({job} = await request(endpoint + "?" + options, {
          method: "POST", headers: {"Content-Type": "application/pdf"}, body: file
        }));
        while (upload.isConnected) {
          const result = await request(`${endpoint}/${job}`);
          if (!upload.isConnected) break;
          if (result.state === "failed") throw new Error(t(result.error, "MinerU could not parse this page."));
          if (result.state === "ready") {
            text.value = result.preview;
            previewMeta.textContent = t(`${result.filename} · PDF 第 ${result.page} 页`, `${result.filename} · PDF page ${result.page}`);
            progress.textContent = result.cached ? t("已复用本次运行中缓存的解析结果。", "Reused the cached result.") : t(`解析完成 · ${result.seconds} 秒`, `Parsed in ${result.seconds} seconds`);
            preview.classList.remove("hidden");
            break;
          }
          progress.textContent = result.state === "queued" ? t("等待 MinerU 处理…", "Waiting for MinerU…") : t("MinerU 正在解析这一页…", "MinerU is parsing this page…");
          await new Promise(resolve => setTimeout(resolve, 500));
        }
      } catch (error) {
        progress.textContent = error instanceof TypeError ? t("无法连接本机解析服务，请重试。", "Cannot reach the local parsing service.") : error.message;
      } finally {
        button.disabled = false;
      }
    });

    document.getElementById("select-excerpt").addEventListener("click", () => {
      const excerpt = text.value.slice(text.selectionStart, text.selectionEnd).trim();
      if (!excerpt || excerpt.length > 2400) {
        progress.textContent = t("请在预览里选中不超过 2400 字符的连续原文。", "Select a passage of up to 2,400 characters in the preview.");
        return;
      }
      save.elements.excerpt.value = excerpt;
      save.classList.remove("hidden");
      book.classList.add("hidden");
      status.textContent = "";
      save.elements.flower.focus();
    });

    save.addEventListener("submit", async event => {
      event.preventDefault();
      const button = event.submitter;
      const field = save.elements;
      const classKey = field.flower.value;
      const submittedJob = job;
      button.disabled = true;
      status.textContent = t("正在保存…", "Saving…");
      try {
        const result = await request(`${endpoint}/${submittedJob}/evidence`, {
          method: "POST", headers: {"Content-Type": "application/json"},
          body: JSON.stringify({class_key: classKey, topic: field.topic.value, excerpt: field.excerpt.value,
            summary: field.summary.value, source_url: field.source.value})
        });
        if (job !== submittedJob || !save.isConnected) return;
        status.textContent = result.duplicate ? t("这个书页已有相同摘录。", "This folio already has that excerpt.") : t("摘录已入库。请在对应书页的「审核文献摘录」里查看。", "Saved for review in the related folio.");
        book.href = "#/library/" + encodeURIComponent(classKey);
        book.classList.remove("hidden");
      } catch (error) {
        if (job === submittedJob) {
          status.textContent = error instanceof TypeError ? t("无法连接本机知识库，请重试。", "Cannot reach the local knowledge base.") : error.message;
        }
      } finally {
        button.disabled = false;
      }
    });
  }

  return {render};
})();
