/* ============================================================
   视图：识花台
   上传图片 → 预览 → 本机模型预测 →
   结果卡 → 自动写入查花记录 → 可跳转书页详情。
   ============================================================ */
window.FF = window.FF || {};
FF.views = FF.views || {};

FF.views.identify = (function () {
  const localModel = window.FF_LOCAL_MODEL;
  const {text: t} = FF.language;
  const flowerName = flower => t(`${flower.zh} · ${flower.en}`, flower.en);
  let requestVersion = 0;

  function escapeText(value) {
    return String(value).replace(/[&<>"']/g, char => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[char]);
  }

  function waitingState() {
    const mode = localModel ? escapeText(localModel.name) + t(" · 本机识别", " · Local recognition") : t("静态演示 · 识别结果为示例数据", "Demo · Example predictions");
    return `<div class="demo-note">${mode}</div>
      <div class="result-top"><div class="rk">${t("TOP 1 · 等待照片", "TOP 1 · WAITING FOR A PHOTO")}</div><div class="flower">${t("尚未识别", "No prediction yet")}</div></div>`;
  }

  function shell() {
    return `
      <div class="page">
        <img class="hero-vine" src="assets/floral-header.webp" alt="">
        <div class="hero-copy">
          <div class="page-kicker">${t("FLOWER &amp; FOLIO · 识花台", "FLOWER &amp; FOLIO · IDENTIFY")}</div>
          <h2>${t("从一张花的照片开始", "Identify a flower from a photo")}</h2>
          <p class="lede">${t(`上传照片可查看候选花卉和相应书页。${localModel ? `当前支持 ${FF.recognition.count} 类。` : "本页提供界面演示。"}`, `Upload a photo to see candidate flowers and their folios. ${localModel ? `Supports ${FF.recognition.count} flower categories.` : "This is an interactive demo."}`)}</p>
        </div>
        <div class="identify-grid">
          <div class="panel">
            <div class="panel-kicker">01 · UPLOAD</div>
            <h3>${t("上传花卉照片", "Your flower photo")}</h3>
            <div id="upload-area"></div>
          </div>
          <div class="panel">
            <div class="panel-kicker">02 · RECOGNITION</div>
            <h3>${t("识别结果", "Predictions")}</h3>
            <div id="result-area" aria-live="polite">${waitingState()}</div>
          </div>
        </div>
      </div>`;
  }

  function emptyUpload() {
    return `
      <div class="dropzone" id="dropzone" tabindex="0">
        <div class="dz-mark">&#10047;</div>
        <strong>${t("点击或拖拽照片到这里", "Choose or drop a photo here")}</strong>
        <span>JPG, PNG, WebP · ${localModel ? t("10 MB 以内 · 照片由本机处理", "Up to 10 MB · Processed on this computer") : t("照片仅在浏览器中预览", "Previewed in your browser")}</span>
      </div>
      <input type="file" id="file-input" accept="image/jpeg,image/png,image/webp" class="hidden">`;
  }

  function previewState(dataUrl, filename) {
    return `
      <div class="preview-frame">
        <img id="preview-img" src="${dataUrl}" alt="${t("预览", "Photo preview")}">
        <div class="filename">${escapeText(filename)}</div>
      </div>
      <div class="preview-actions">
        <button class="btn-ghost" id="rechoose">${t("换一张", "Choose another photo")}</button>
        <button class="btn-primary" id="start-identify">${t("开始识别", "Identify flower")}<span class="arrow">&#8594;</span></button>
      </div>`;
  }

  function analyzingState() {
    return `
      <div class="analyzing">
        <div class="spin"></div>
        <p>${t("正在识别花卉…", "Identifying your flower…")}</p>
      </div>`;
  }

  function resultState(ranked, result) {
    const [first, ...otherCandidates] = ranked;
    const label = localModel ? escapeText(result.model_name) + t(" · 模型预测分数", " · Model scores") : t("静态演示 · 示例分数", "Demo · Example scores");
    return `
      <div class="result-top">
        <div class="rk">${t("TOP 1 · 预测类别", "TOP 1 · PREDICTED CATEGORY")}</div>
        <div class="flower">${escapeText(flowerName(first.flower))}</div>
        <div class="latin">${t("代表植物", "Representative species")} · ${escapeText(first.flower.latin)}</div>
        <div class="conf">
          <div class="bar"><i style="width:0%"></i></div>
          <b>${first.score.toFixed(1)}%</b>
        </div>
      </div>
      ${otherCandidates.map(({flower, score}, index) => `
        <a class="rank-row" href="#/library/${encodeURIComponent(flower.key)}">
          <span class="no">0${index + 2}</span><span class="nm">${escapeText(flowerName(flower))}</span>
          <span class="pc">${score.toFixed(1)}%</span><span class="rank-link">${t("书页", "Folio")} →</span>
        </a>`).join("")}
      <div class="result-links">
        <button class="btn-ghost" id="rechoose2">${t("重新上传", "Upload another photo")}</button>
        <button class="btn-primary" id="open-folio" data-key="${first.flower.key}">${escapeText(t(`查看${first.flower.zh}书页`, `Open ${first.flower.en} folio`))}<span class="arrow">&#8594;</span></button>
      </div>
      <div class="demo-note" style="margin-top:1rem;">${label}${localModel ? t(` · 支持 ${FF.recognition.count} 类。`, ` · ${FF.recognition.count} supported categories.`) : ""}${result.low_score ? t(" 第一候选分数较低，请核对候选或换一张照片。", " The leading score is low. Check the candidates or try another photo.") : ""}</div>
      ${localModel ? camPanel(ranked) : ""}`;
  }

  function camPanel(ranked) {
    return `<section class="cam-panel" aria-labelledby="cam-heading">
      <h4 id="cam-heading">${t("Grad-CAM 热力图", "Grad-CAM heatmap")}</h4>
      <div class="cam-choices" role="group" aria-label="${t("选择解释类别", "Choose a flower to explain")}">
        ${ranked.map(row => `<button type="button" class="btn-ghost" data-class-id="${row.classId}" aria-pressed="false">${escapeText(t(row.flower.zh,row.flower.en))}</button>`).join("")}
      </div>
      <div class="cam-output" aria-live="polite">${t("选择一种候选花卉，查看模型为它打分时关注的区域。", "Choose a candidate to see which regions contributed to its score.")}</div>
      <p class="cam-caption">${t("高亮表示支持该类别的区域线索。热力图对应模型实际使用的裁剪视图，识别正确性需结合照片核对。", "Highlights show regions that supported the candidate in the model's crop. Check the photo to confirm the identification.")}</p>
    </section>`;
  }

  function bindCam(file, version) {
    const output = document.querySelector(".cam-output");
    const buttons = [...document.querySelectorAll(".cam-choices button")];
    let request = 0;
    for (const button of buttons) {
      button.addEventListener("click", async () => {
        const current = ++request;
        const classId = Number(button.dataset.classId);
        const active = () => output.isConnected && requestVersion === version && current === request;
        for (const choice of buttons) choice.setAttribute("aria-pressed", String(choice === button));
        output.textContent = t(`正在生成「${button.textContent}」的热力图…`, `Generating the heatmap for ${button.textContent}…`);
        try {
          const response = await fetch(`/api/grad-cam?class_id=${classId}`, {
            method: "POST", headers: { "Content-Type": file.type }, body: file
          });
          const result = await response.json();
          if (!response.ok) throw new Error(t(result.error || "热力图生成失败，请重试。", "Could not generate the heatmap. Please retry."));
          if (!active()) return;
          if (result.class_id !== classId || ![result.input_image, result.overlay_image].every(value =>
            typeof value === "string" && value.startsWith("data:image/png;base64,"))) {
            throw new Error(t("热力图结果不完整，请重试。", "The heatmap is incomplete. Please retry."));
          }
          const images = [[result.input_image, t("模型输入", "Model input")], [result.overlay_image, t(`${result.name_zh}的热力图`, `Heatmap for ${button.textContent}`)]];
          output.innerHTML = `<div class="cam-images">${images.map(([src, title]) =>
            `<figure><img src="${escapeText(src)}" alt="${escapeText(title)}" width="224" height="224"><figcaption>${escapeText(title)}</figcaption></figure>`).join("")}</div>`;
        } catch (error) {
          if (active()) output.textContent = error instanceof TypeError ? t("无法连接本机识别服务。", "Cannot reach the local recognition service.") : error.message;
        }
      });
    }
  }

  function bindResult(ranked, file, version) {
    const bar = document.querySelector("#result-area .bar i");
    if (bar) requestAnimationFrame(() => { bar.style.width = ranked[0].score + "%"; });

    document.getElementById("open-folio").addEventListener("click", (e) => {
      const key = e.currentTarget.dataset.key;
      location.hash = "#/library/" + key;
    });
    document.getElementById("rechoose2").addEventListener("click", () => renderUploadArea());
    if (localModel) bindCam(file, version);
  }

  function handleFile(file) {
    if (!file) return;
    if (!/^image\/(jpeg|png|webp)$/.test(file.type)) {
      FF.toast(t("请选择 JPG、PNG 或 WEBP 图片。", "Choose a JPG, PNG, or WebP photo."), true);
      return;
    }
    if (localModel && file.size > localModel.maxBytes) {
      FF.toast(t("请选择一张不超过 10 MB 的照片。", "Choose a photo up to 10 MB."), true);
      return;
    }
    const version = ++requestVersion;
    const area = document.getElementById("upload-area");
    const reader = new FileReader();
    reader.onload = () => {
      if (!area.isConnected || version !== requestVersion) return;
      area.innerHTML = previewState(reader.result, file.name);
      document.getElementById("result-area").innerHTML = waitingState();
      document.getElementById("rechoose").addEventListener("click", () => renderUploadArea());
      document.getElementById("start-identify").addEventListener("click", () => runIdentify(file));
    };
    reader.onerror = () => FF.toast(t("照片无法读取，请重新选择。", "Could not read that photo. Choose another one."), true);
    reader.readAsDataURL(file);
  }

  async function runIdentify(file) {
    const area = document.getElementById("result-area");
    const button = document.getElementById("start-identify");
    const version = ++requestVersion;
    const active = () => area.isConnected && version === requestVersion;
    area.innerHTML = analyzingState();
    button.disabled = true;
    try {
      let result = {};
      let ranked;
      if (localModel) {
        const response = await fetch("/api/identify", { method: "POST", headers: { "Content-Type": file.type }, body: file });
        result = await response.json();
        if (!response.ok) throw new Error(t(result.error || "识别失败，请重试。", "Could not identify this photo. Try a clear, single JPG, PNG, or WebP image."));
        ranked = result.candidates.map(candidate => ({ flower: FF.data.byKey(candidate.key), score: candidate.score * 100, classId: candidate.class_id }));
        if (ranked.length !== 3 || ranked.some(row => !row.flower || !Number.isFinite(row.score) || !Number.isInteger(row.classId))) {
          throw new Error(t("识别结果和花卉书页无法对应，请检查本机资料。", "The prediction does not match the local flower library."));
        }
      } else {
        const bytes = new Uint8Array(await file.slice(0, 4096).arrayBuffer());
        let sum = 0, mod = 0;
        for (const value of bytes) { sum = (sum + value) % 99991; mod = (mod ^ value) % 251; }
        ranked = FF.data.demoIdentify(sum, mod);
      }
      if (!active()) return;
      area.innerHTML = resultState(ranked, result);
      const first = ranked[0].flower;
      FF.store.addHistory({ key: first.key, zh: first.zh, en: first.en, source: "identify" });
      bindResult(ranked, file, version);
    } catch (error) {
      if (!active()) return;
      area.innerHTML = waitingState();
      FF.toast(error instanceof TypeError ? t("无法连接识别服务，请检查本机服务后重试。", "Cannot reach the local recognition service.") : error.message, true);
    } finally {
      if (active()) button.disabled = false;
    }
  }

  function renderUploadArea() {
    requestVersion++;
    document.getElementById("result-area").innerHTML = waitingState();
    document.getElementById("upload-area").innerHTML = emptyUpload();
    const dz = document.getElementById("dropzone");
    const input = document.getElementById("file-input");
    dz.addEventListener("click", () => input.click());
    dz.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") input.click(); });
    dz.addEventListener("dragover", (e) => { e.preventDefault(); dz.classList.add("drag"); });
    dz.addEventListener("dragleave", () => dz.classList.remove("drag"));
    dz.addEventListener("drop", (e) => {
      e.preventDefault();
      dz.classList.remove("drag");
      handleFile(e.dataTransfer.files[0]);
    });
    input.addEventListener("change", () => handleFile(input.files[0]));
  }

  function render() {
    document.getElementById("view").innerHTML = shell();
    renderUploadArea();
  }

  return { render };
})();
