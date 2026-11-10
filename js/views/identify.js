/* ============================================================
   视图：识花台
   上传图片 → 预览 → 演示识别（模型接入前的占位推理）→
   结果卡 → 自动写入查花记录 → 可跳转书页详情。
   ============================================================ */
window.FF = window.FF || {};
FF.views = FF.views || {};

FF.views.identify = (function () {

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
            <div id="result-area">
              <div class="demo-note">演示模式：识别结果由界面演示数据生成，用于预览完整流程；识别模型接入后，此处将返回真实预测与分数。</div>
              <div class="result-top">
                <div class="rk">TOP 1 · 等待照片</div>
                <div class="flower">尚未识别</div>
                <div class="latin">上传照片后开始</div>
              </div>
            </div>
          </div>
        </div>
      </div>`;
  }

  function emptyUpload() {
    return `
      <div class="dropzone" id="dropzone" tabindex="0">
        <div class="dz-mark">&#10047;</div>
        <strong>点击或拖拽照片到这里</strong>
        <span>支持 JPG、PNG、WEBP · 照片仅在本机预览，不会上传到任何服务器</span>
      </div>
      <input type="file" id="file-input" accept="image/jpeg,image/png,image/webp" class="hidden">`;
  }

  function previewState(dataUrl, filename) {
    return `
      <div class="preview-frame">
        <img id="preview-img" src="${dataUrl}" alt="预览">
        <div class="filename">${filename}</div>
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

  function resultState(ranked, filename) {
    const [first, second, third] = ranked;
    return `
      <div class="result-top">
        <div class="rk">TOP 1 · 预测类别</div>
        <div class="flower">${first.flower.zh} · ${first.flower.en}</div>
        <div class="latin">${first.flower.latin}</div>
        <div class="conf">
          <div class="bar"><i style="width:0%"></i></div>
          <b>${first.score}%</b>
        </div>
      </div>
      <div class="rank-row"><span class="no">01</span><span class="nm">${second.flower.zh} · ${second.flower.en}</span><span class="pc">${second.score}%</span></div>
      <div class="rank-row"><span class="no">02</span><span class="nm">${third.flower.zh} · ${third.flower.en}</span><span class="pc">${third.score}%</span></div>
      <div class="rank-row"><span class="no">03</span><span class="nm">其余候选</span><span class="pc">${Math.max(1, 100 - first.score - second.score - third.score)}%</span></div>
      <div class="result-links">
        <button class="btn-ghost" id="rechoose2">重新上传</button>
        <button class="btn-primary" id="open-folio" data-key="${first.flower.key}">查看花之书页<span class="arrow">&#8594;</span></button>
      </div>
      <div class="demo-note" style="margin-top:1rem;">本次查询已记入「我的足迹」。预测分数不是正确率保证；识别范围外的花会被误判，需人工复核。</div>`;
  }

  function bindResult(ranked, filename) {
    const bar = document.querySelector("#result-area .bar i");
    if (bar) requestAnimationFrame(() => { bar.style.width = ranked[0].score + "%"; });

    document.getElementById("open-folio").addEventListener("click", (e) => {
      const key = e.currentTarget.dataset.key;
      const f = FF.data.byKey(key);
      if (f) FF.store.addHistory({ key: f.key, zh: f.zh, en: f.en, source: "identify" });
      location.hash = "#/library/" + key;
    });
    document.getElementById("rechoose2").addEventListener("click", () => renderUploadArea());
  }

  function handleFile(file) {
    if (!file) return;
    if (!/^image\/(jpeg|png|webp)$/.test(file.type)) {
      FF.toast("请选择 JPG、PNG 或 WEBP 图片。", true);
      return;
    }
    const reader = new FileReader();
    reader.onload = () => {
      const area = document.getElementById("upload-area");
      area.innerHTML = previewState(reader.result, file.name);
      document.getElementById("rechoose").addEventListener("click", () => renderUploadArea());
      document.getElementById("start-identify").addEventListener("click", () => runIdentify(file));
    };
    reader.readAsDataURL(file);
  }

  function runIdentify(file) {
    document.getElementById("result-area").innerHTML = analyzingState();
    /* 读取字节特征 → 确定性演示结果 */
    file.arrayBuffer().then((buf) => {
      const bytes = new Uint8Array(buf.slice(0, 4096));
      let sum = 0, mod = 0;
      for (let i = 0; i < bytes.length; i++) { sum = (sum + bytes[i]) % 99991; mod = (mod ^ bytes[i]) % 251; }
      const ranked = FF.data.demoIdentify(sum, mod);
      setTimeout(() => {
        document.getElementById("result-area").innerHTML = resultState(ranked, file.name);
        const f = ranked[0].flower;
        FF.store.addHistory({ key: f.key, zh: f.zh, en: f.en, source: "identify" });
        bindResult(ranked, file.name);
      }, 1400);
    });
  }

  function renderUploadArea() {
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
