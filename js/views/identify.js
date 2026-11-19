/* ============================================================
   视图：识花台
   上传图片 → 预览 → 本机模型预测 →
   结果卡 → 自动写入查花记录 → 可跳转书页详情。
   ============================================================ */
window.FF = window.FF || {};
FF.views = FF.views || {};

FF.views.identify = (function () {
  const localModel = window.FF_LOCAL_MODEL;
  let requestVersion = 0;

  function escapeText(value) {
    return String(value).replace(/[&<>"']/g, char => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[char]);
  }

  function waitingState() {
    const mode = localModel ? escapeText(localModel.name) + " · 本机识别" : "静态演示 · 识别结果为示例数据";
    return `<div class="demo-note">${mode}</div>
      <div class="result-top"><div class="rk">TOP 1 · 等待照片</div><div class="flower">尚未识别</div></div>`;
  }

  function shell() {
    return `
      <div class="page">
        <img class="hero-vine" src="assets/floral-header.webp" alt="">
        <div class="hero-copy">
          <div class="page-kicker">FLOWER &amp; FOLIO · 识花台</div>
          <h2>从一张花的照片开始</h2>
          <p class="lede">上传一张照片，Florentia 会为你翻开对应的花之书页。识别范围：Oxford Flower17 的 17 类。</p>
        </div>
        <div class="identify-grid">
          <div class="panel">
            <div class="panel-kicker">01 · UPLOAD</div>
            <h3>你的花，会在这里出现</h3>
            <div id="upload-area"></div>
          </div>
          <div class="panel">
            <div class="panel-kicker">02 · RECOGNITION</div>
            <h3>识别结果</h3>
            <div id="result-area" aria-live="polite">${waitingState()}</div>
          </div>
        </div>
      </div>`;
  }

  function emptyUpload() {
    return `
      <div class="dropzone" id="dropzone" tabindex="0">
        <div class="dz-mark">&#10047;</div>
        <strong>点击或拖拽照片到这里</strong>
        <span>支持 JPG、PNG、WebP · ${localModel ? "10 MB 以内 · 照片由本机处理" : "照片仅在浏览器中预览"}</span>
      </div>
      <input type="file" id="file-input" accept="image/jpeg,image/png,image/webp" class="hidden">`;
  }

  function previewState(dataUrl, filename) {
    return `
      <div class="preview-frame">
        <img id="preview-img" src="${dataUrl}" alt="预览">
        <div class="filename">${escapeText(filename)}</div>
      </div>
      <div class="preview-actions">
        <button class="btn-ghost" id="rechoose">换一张</button>
        <button class="btn-primary" id="start-identify">开始识别<span class="arrow">&#8594;</span></button>
      </div>`;
  }

  function analyzingState() {
    return `
      <div class="analyzing">
        <div class="spin"></div>
        <p>正在翻阅植物图鉴…</p>
      </div>`;
  }

  function resultState(ranked, result) {
    const [first, second, third] = ranked;
    const label = localModel ? escapeText(result.model_name) + " · 模型预测分数" : "静态演示 · 示例分数";
    return `
      <div class="result-top">
        <div class="rk">TOP 1 · 预测类别</div>
        <div class="flower">${first.flower.zh} · ${first.flower.en}</div>
        <div class="latin">代表植物 · ${first.flower.latin}</div>
        <div class="conf">
          <div class="bar"><i style="width:0%"></i></div>
          <b>${first.score.toFixed(1)}%</b>
        </div>
      </div>
      <div class="rank-row"><span class="no">02</span><span class="nm">${second.flower.zh} · ${second.flower.en}</span><span class="pc">${second.score.toFixed(1)}%</span></div>
      <div class="rank-row"><span class="no">03</span><span class="nm">${third.flower.zh} · ${third.flower.en}</span><span class="pc">${third.score.toFixed(1)}%</span></div>
      <div class="result-links">
        <button class="btn-ghost" id="rechoose2">重新上传</button>
        <button class="btn-primary" id="open-folio" data-key="${first.flower.key}">查看花之书页<span class="arrow">&#8594;</span></button>
      </div>
      <div class="demo-note" style="margin-top:1rem;">${label} · 仅支持 Flower17 的 17 类。${result.low_score ? " 第一候选分数较低，请核对候选或换一张照片。" : ""}</div>
      ${localModel ? camPanel(ranked) : ""}`;
  }

  function camPanel(ranked) {
    return `<section class="cam-panel" aria-labelledby="cam-heading">
      <h4 id="cam-heading">Grad-CAM 热力图</h4>
      <div class="cam-choices" role="group" aria-label="选择解释类别">
        ${ranked.map(row => `<button type="button" class="btn-ghost" data-class-id="${row.classId}" aria-pressed="false">${escapeText(row.flower.zh)}</button>`).join("")}
      </div>
      <div class="cam-output" aria-live="polite">选择一种候选花卉，查看模型为它打分时关注的区域。</div>
      <p class="cam-caption">高亮表示支持该类别的区域线索。热力图对应模型实际使用的裁剪视图，识别正确性需结合照片核对。</p>
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
        output.textContent = `正在生成「${button.textContent}」的热力图…`;
        try {
          const response = await fetch(`/api/grad-cam?class_id=${classId}`, {
            method: "POST", headers: { "Content-Type": file.type }, body: file
          });
          const result = await response.json();
          if (!response.ok) throw new Error(result.error || "热力图生成失败，请重试。");
          if (!active()) return;
          if (result.class_id !== classId || ![result.input_image, result.overlay_image].every(value =>
            typeof value === "string" && value.startsWith("data:image/png;base64,"))) {
            throw new Error("热力图结果不完整，请重试。");
          }
          const images = [[result.input_image, "模型输入"], [result.overlay_image, `${result.name_zh}的热力图`]];
          output.innerHTML = `<div class="cam-images">${images.map(([src, title]) =>
            `<figure><img src="${escapeText(src)}" alt="${escapeText(title)}" width="224" height="224"><figcaption>${escapeText(title)}</figcaption></figure>`).join("")}</div>`;
        } catch (error) {
          if (active()) output.textContent = error instanceof TypeError ? "无法连接本机识别服务。" : error.message;
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
      FF.toast("请选择 JPG、PNG 或 WEBP 图片。", true);
      return;
    }
    if (localModel && file.size > localModel.maxBytes) {
      FF.toast("请选择一张不超过 10 MB 的照片。", true);
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
    reader.onerror = () => FF.toast("照片无法读取，请重新选择。", true);
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
        if (!response.ok) throw new Error(result.error || "识别失败，请重试。");
        ranked = result.candidates.map(candidate => ({ flower: FF.data.byKey(candidate.key), score: candidate.score * 100, classId: candidate.class_id }));
        if (ranked.length !== 3 || ranked.some(row => !row.flower || !Number.isFinite(row.score) || !Number.isInteger(row.classId))) {
          throw new Error("识别结果和花卉书页无法对应，请检查本机资料。");
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
      FF.toast(error instanceof TypeError ? "无法连接识别服务，请检查本机服务后重试。" : error.message, true);
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
