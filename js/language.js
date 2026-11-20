window.FF = window.FF || {};

FF.language = (() => {
  const storageKey = "floralia-language";
  let english = localStorage.getItem(storageKey) === "en";

  function sync() {
    document.documentElement.lang = english ? "en" : "zh-CN";
    document.title = english ? "Florentia · Flower & Folio" : "Florentia · 花与书页";
  }

  sync();
  return {
    get english() { return english; },
    text: (zh, en) => english ? en : zh,
    button: () => `<button type="button" class="nav-exit language-toggle" data-language-toggle lang="${english ? "zh-CN" : "en"}">${english ? "简体中文" : "English"}</button>`,
    toggle() {
      english = !english;
      localStorage.setItem(storageKey, english ? "en" : "zh-CN");
      sync();
    }
  };
})();

FF.recognition = (() => {
  const keys = new Set(window.FF_LOCAL_MODEL?.classKeys || FF.data.recognizableFlowers.map(flower => flower.key));
  return { supports: key => keys.has(key), count: keys.size };
})();
