/* Страница теста. Тесты выполняются в Web Workers — на процессоре ТОГО устройства, где открыта
   страница. Сервер только хранит результаты и собирает общий топ.

   До нажатия «Начать» страница пустая и ничего об устройстве не узнаёт. После нажатия сайт определяет,
   что может (устройство, процессор, графику, систему, память), показывает это и СПРАШИВАЕТ РАЗРЕШЕНИЯ:
   процессор начинает нагружаться только после кнопки «Разрешить и начать». Модель процессора браузер
   не сообщает — её угадывает guess.js по косвенным признакам; если угадал неверно, человек поправляет
   через «не тот?». В топ результат попадает только по кнопке «Сохранить в топ» в конце. */
(() => {
  "use strict";
  const $ = (id) => document.getElementById(id);
  const CFG = JSON.parse($("cfg").textContent);
  const GCFG = Guess.prepare(CFG);
  const TESTS = CFG.tests;
  const fmt = (n, d = 0) => Number(n).toLocaleString("ru-RU", { minimumFractionDigits: d, maximumFractionDigits: d });
  const ghz = (x) => (x ? fmt(x, 2).replace(/0$/, "").replace(/,$/, "") : "—");
  const plural = (n, [one, few, many]) => {
    const a = Math.abs(n) % 100, b = a % 10;
    return `${n} ${a > 10 && a < 20 ? many : b === 1 ? one : b >= 2 && b <= 4 ? few : many}`;
  };
  const CORES = ["ядро", "ядра", "ядер"], THR = ["поток", "потока", "потоков"];
  const store = {
    get(k) { try { return localStorage.getItem(k); } catch (e) { return null; } },
    set(k, v) { try { localStorage.setItem(k, v); } catch (e) { /* приватный режим — не страшно */ } },
  };
  const randomId = () => Array.from({ length: 4 }, () => Math.floor(Math.random() * 0xffffffff).toString(16).padStart(8, "0")).join("");
  const median = (xs) => { const s = xs.filter((x) => x > 0).sort((a, b) => a - b); return s.length ? s[s.length >> 1] : 0; };
  const geomean = (xs) => { const v = xs.filter((x) => x > 0); return v.length ? Math.exp(v.reduce((s, x) => s + Math.log(x), 0) / v.length) : 0; };

  const DEVICE = store.get("nb.device") || (() => { const id = randomId(); store.set("nb.device", id); return id; })();
  const THREADS = Math.max(1, Math.min(256, navigator.hardwareConcurrency || 4));
  const T = { warm: 250, single: 1500, multi: 1500, scale: 1000, marathon: 20, freq: 1200, fps: 3000, fpsWarm: 400 };
  const params = new URLSearchParams(location.search);

  // ---------- что браузер знает об устройстве ----------
  function browserInfo() {
    const ua = navigator.userAgent;
    const list = [[/Edg\/(\d+)/, "Edge", "V8"], [/OPR\/(\d+)/, "Opera", "V8"], [/YaBrowser\/(\d+)/, "Яндекс Браузер", "V8"],
      [/SamsungBrowser\/(\d+)/, "Samsung Internet", "V8"], [/Firefox\/(\d+)/, "Firefox", "SpiderMonkey"],
      [/Chrome\/(\d+)/, "Chrome", "V8"], [/Version\/(\d+).*Safari/, "Safari", "JavaScriptCore"]];
    for (const [re, name, engine] of list) {
      const m = ua.match(re);
      if (m) return { browser: `${name} ${m[1]}`, engine };
    }
    return { browser: "Браузер", engine: "?" };
  }
  function osName() {
    const ua = navigator.userAgent;
    return /Windows/.test(ua) ? "Windows" : /Android/.test(ua) ? "Android" : /iPhone|iPad|iPod/.test(ua) ? "iOS"
      : /Mac OS X/.test(ua) ? "macOS" : /CrOS/.test(ua) ? "ChromeOS" : /Linux/.test(ua) ? "Linux" : "";
  }
  // Подсказки Chrome и Edge: версия Windows, модель телефона, архитектура (ARM — ноутбуки на Snapdragon X).
  async function uaHints() {
    try {
      const d = navigator.userAgentData;
      if (d && d.getHighEntropyValues) return await d.getHighEntropyValues(["platformVersion", "model", "architecture"]);
    } catch (e) { /* браузер не сообщает */ }
    return {};
  }
  // Windows 10 и 11 в строке браузера одинаковые; Chrome и Edge отдают номер версии платформы отдельно (13+ — это 11).
  function osFull(base, h) {
    if (base === "Windows") {
      const major = parseInt(String(h.platformVersion || "").split(".")[0], 10);
      if (major >= 13) return "Windows 11";
      if (major >= 1) return "Windows 10";
    }
    return base;
  }
  // Модель телефона: Chrome сообщает её отдельно, Samsung Internet и Яндекс Браузер — прямо в строке браузера.
  function phoneModel(h) {
    let m = String(h.model || "").trim();
    if (!m) {
      const x = navigator.userAgent.match(/Android [\d.]+; ([^;)]+?)(?:;|\)| Build\/)/);
      m = x ? x[1].trim() : "";
    }
    m = m.replace(/^SAMSUNG\s+/i, "");
    return m === "K" || /^wv$/i.test(m) ? "" : m.slice(0, 40); // «K» — Chrome скрыл модель
  }
  function gpuName() {
    try {
      const gl = document.createElement("canvas").getContext("webgl");
      if (!gl) return "";
      const ext = gl.getExtension("WEBGL_debug_renderer_info");
      return String(gl.getParameter(ext ? ext.UNMASKED_RENDERER_WEBGL : gl.RENDERER) || "");
    } catch (e) { return ""; }
  }
  // Память браузер сообщает с округлением вниз до 0,5 / 1 / 2 / 4 / 8 ГБ, и не больше 8 — поэтому «N+ ГБ».
  const ramGb = () => (typeof navigator.deviceMemory === "number" && navigator.deviceMemory > 0 ? navigator.deviceMemory : null);
  const ramText = (gb) => (gb ? `${fmt(gb, gb < 1 ? 1 : 0)}+ ГБ` : "браузер не сообщает");
  async function battery() {
    try {
      if (!navigator.getBattery) return { battery: null, plugged: null, percent: null };
      const b = await navigator.getBattery();
      return { battery: true, plugged: !!b.charging, percent: Math.round(b.level * 100) };
    } catch (e) { return { battery: null, plugged: null, percent: null }; }
  }
  const shortGpu = (g) => g.replace(/^ANGLE \(([^,]+),\s*/, "").replace(/\s*\(0x[0-9a-f]+\)/i, "").replace(/\s*(Direct3D|OpenGL|Metal|Vulkan|vs_|, D3D).*$/i, "")
    .replace(/\(R\)|\(TM\)/g, "").replace(/[,\s]+$/, "").replace(/\s+/g, " ").trim() || "не видна";

  // Заполняется только после нажатия «Начать».
  let SYS = null; // { br, os, gpu, ram, model }
  let G = { kind: "pc", list: [], conf: "low", vendor: null, why: "", gpu: { discrete: false } };
  let POWER = null;
  const mobileKind = () => G.kind === "phone" || G.kind === "tablet";
  const KIND = { phone: "Телефон", tablet: "Планшет", laptop: "Ноутбук", desktop: "Настольный ПК", pc: "Компьютер", mac: "Mac" };

  // ---------- процессор: угаданный или исправленный ----------
  const vendorName = (v) => Guess.VENDORS[v] || "CPU";
  const shortName = (n) => n.replace(/^(AMD|Intel|Apple|Qualcomm|MediaTek|Samsung|Google|Unisoc|HiSilicon)\s+/i, "");
  const byKey = (k) => CFG.catalog.find((c) => c.key === k);
  const vendorOfText = (n) => {
    const l = n.toLowerCase();
    return /intel|core i|pentium|celeron|xeon/.test(l) ? "intel" : /amd|ryzen|athlon/.test(l) ? "amd"
      : /qualcomm|snapdragon/.test(l) ? "qualcomm" : /mediatek|dimensity|helio/.test(l) ? "mediatek"
      : /exynos/.test(l) ? "samsung" : /tensor/.test(l) ? "google" : /unisoc/.test(l) ? "unisoc"
      : /kirin|hisilicon/.test(l) ? "hisilicon" : /apple/.test(l) ? "apple" : "other";
  };
  // у телефонов и Mac нет «двух потоков на ядро», у остальных компьютеров обычно есть
  const estCores = () => (THREADS >= 4 && G.kind !== "mac" && !mobileKind() ? Math.round(THREADS / 2) : THREADS);
  // подходит ли процессор этому устройству: телефонный — телефону; у компьютера число потоков браузер знает точно
  const fits = (c) => (c.seg === "p") === mobileKind() && (c.seg === "p" || c.threads === THREADS);
  let chosen = null; // { key, name, vendor, cores, threads, boost, year, est, sure, why }
  let extra = null;  // выбранный через поиск, если его нет среди угаданных

  function choose(c, how, why) {
    // how: "sure" — признаки указывают на эту модель, "auto" — одна из похожих, "manual" — выбрал человек
    if (c.other) {
      chosen = { key: "", name: c.name, vendor: vendorOfText(c.name), cores: estCores(), threads: null, est: true, sure: true, why: "вписан вами" };
      store.set("nb.cpu", "other:" + c.name);
    } else {
      chosen = { key: c.key, name: c.name, vendor: c.vendor, cores: Math.min(c.cores, THREADS), threads: c.threads,
        boost: c.boost, year: c.year, seg: c.seg, est: false, sure: how !== "auto",
        why: why || (how === "manual" ? "выбран вами" : G.why) };
      if (how === "manual") store.set("nb.cpu", c.key);
      if (!G.list.some((x) => x.c.key === c.key)) extra = c;
    }
    paint();
  }

  function coresText(c) {
    return c.cores === c.threads ? plural(c.cores, CORES) : `${plural(c.cores, CORES)} · ${plural(c.threads, THR)}`;
  }

  function renderCards() {
    const box = $("cands");
    box.textContent = "";
    const items = [];
    if (extra && !G.list.some((x) => x.c.key === extra.key)) items.push(extra);
    G.list.slice(0, chosen ? 3 : 6).forEach((x) => items.push(x.c));
    $("cand-title").textContent = !items.length ? "Найдите свой процессор:" : chosen ? "Похожие процессоры:" : "Похоже на один из этих — выберите свой:";
    items.forEach((c) => {
      const b = document.createElement("button");
      b.type = "button";
      b.className = "cand";
      b.setAttribute("role", "radio");
      b.dataset.vendor = c.vendor;
      b.setAttribute("aria-checked", chosen && chosen.key === c.key ? "true" : "false");
      b.innerHTML = `<span class="cand-v"></span><span class="cand-n"></span><span class="cand-s"></span>`;
      b.querySelector(".cand-v").textContent = vendorName(c.vendor);
      b.querySelector(".cand-n").textContent = shortName(c.name);
      b.querySelector(".cand-s").textContent = [coresText(c), c.gpu && c.gpu !== "Apple GPU" ? c.gpu : "", c.year].filter(Boolean).join(" · ");
      b.addEventListener("click", () => { choose(c, "manual"); openPicker(false); });
      box.appendChild(b);
    });
    if (chosen && chosen.est) {
      const b = document.createElement("button");
      b.type = "button"; b.className = "cand"; b.setAttribute("role", "radio"); b.setAttribute("aria-checked", "true");
      b.dataset.vendor = chosen.vendor;
      b.innerHTML = `<span class="cand-v">вписан вручную</span><span class="cand-n"></span><span class="cand-s">нет в справочнике · паспорта не будет</span>`;
      b.querySelector(".cand-n").textContent = chosen.name;
      box.appendChild(b);
    }
  }

  function whereToLook() {
    if (G.kind === "phone" || G.kind === "tablet") {
      return SYS && SYS.os === "iOS" ? "Модель устройства: Настройки → Основные → Об этом устройстве."
        : "Название процессора: Настройки → О телефоне → Все характеристики (или приложение CPU-Z).";
    }
    if (G.kind === "mac") return "Название чипа: меню Apple → Об этом Mac.";
    return "Точное название: Диспетчер задач → Производительность → ЦП.";
  }

  function paint() {
    const c = chosen;
    // ноутбук или настольный — если по браузеру не понять, подсказывает найденный процессор
    const kind = G.kind === "pc" && c && (c.seg === "d" || c.seg === "l") ? (c.seg === "d" ? "desktop" : "laptop") : G.kind;
    if (SYS) $("det-kind").textContent = KIND[kind] + (SYS.model ? " · " + SYS.model : "");
    $("cpu-card").dataset.vendor = c ? c.vendor : G.vendor || "other";
    $("cpu-name").textContent = c ? c.name : G.vendor ? `Процессор ${Guess.FAMILY[G.vendor]}` : "Модель не видна браузеру";
    $("cpu-name").classList.toggle("unknown", !c);
    const sub = [];
    if (c && !c.est) sub.push(coresText(c), c.boost ? `до ${ghz(c.boost)} ГГц` : "", String(c.year));
    if (c && c.est) sub.push("нет в справочнике");
    if (c) sub.push(c.sure ? (c.why ? (/^(выбран|вписан)/.test(c.why) ? c.why : "узнан " + c.why) : "") : "примерно" + (c.why ? ", " + c.why : ""));
    if (!c) sub.push("Браузер не сообщает модель процессора — " + (G.list.length ? "выберите свой из похожих ниже" : "найдите свой ниже") + ", сайт запомнит");
    $("cpu-sub").textContent = sub.filter(Boolean).join(" · ");
    // ядра берутся из справочника — показываем их, только если в модели уверены; потоки браузер знает точно
    $("det-cores").textContent = c && !c.est && c.sure ? `${c.cores} / ${THREADS}` : plural(THREADS, THR);

    const hint = $("cpu-hint");
    hint.classList.remove("bad");
    if (c && c.threads && c.threads !== THREADS && c.seg !== "p") {
      hint.textContent = `Браузер видит ${plural(THREADS, THR)}, а у ${c.name} их ${c.threads}. Проверьте, тот ли процессор выбран.`;
      hint.classList.add("bad");
    } else if (!c && G.gpu.discrete) {
      hint.textContent = "Браузеру видна только дискретная видеокарта — по ней модель процессора не узнать. " + whereToLook();
    } else {
      hint.textContent = whereToLook();
    }
    $("save").disabled = !c || saving;
    $("save-hint").textContent = c ? "" : "Чтобы сохранить результат, укажите процессор: нажмите «не тот?» вверху страницы.";
    $("fix").textContent = $("picker").hidden ? (c ? "не тот?" : "выбрать") : "скрыть";
    renderCards();
  }

  function openPicker(open) {
    $("picker").hidden = !open;
    $("fix").setAttribute("aria-expanded", open ? "true" : "false");
    $("fix").textContent = open ? "скрыть" : chosen ? "не тот?" : "выбрать";
  }
  $("fix").addEventListener("click", () => {
    const open = $("picker").hidden;
    openPicker(open);
    if (open) sIn.focus();
  });

  // поиск по справочнику: сначала процессоры того же вида устройства (телефонные — для телефона)
  const sIn = $("search"), sList = $("search-list");
  const norm = (s) => s.toLowerCase().replace(/\+/g, "plus").replace(/[^a-z0-9а-я]/g, "");
  function search(q) {
    const toks = q.toLowerCase().split(/\s+/).map(norm).filter(Boolean);
    if (!toks.length) return [];
    const same = (c) => ((c.seg === "p") === mobileKind() ? 1 : 0);
    return CFG.catalog.filter((c) => { const n = norm(c.name); return toks.every((t) => n.includes(t)); })
      .sort((a, b) => same(b) - same(a) || b.year - a.year).slice(0, 8);
  }
  function renderSearch() {
    const q = sIn.value.trim();
    sList.textContent = "";
    if (!q) { sList.hidden = true; return; }
    const pick = (c) => { choose(c, "manual"); sIn.value = ""; sList.hidden = true; openPicker(false); };
    search(q).forEach((c) => {
      const li = document.createElement("li");
      li.innerHTML = `<button type="button"><span class="cand-v"></span> <b></b> <small></small></button>`;
      li.querySelector(".cand-v").dataset.vendor = c.vendor;
      li.querySelector(".cand-v").textContent = vendorName(c.vendor);
      li.querySelector("b").textContent = shortName(c.name);
      li.querySelector("small").textContent = `${c.cores}/${c.threads} · ${c.year}`;
      li.firstChild.addEventListener("click", () => pick(c));
      sList.appendChild(li);
    });
    const li = document.createElement("li");
    li.className = "other";
    li.innerHTML = `<button type="button">Моего нет в списке — сохранить как «<b></b>»</button>`;
    li.querySelector("b").textContent = q;
    li.firstChild.addEventListener("click", () => pick({ other: true, name: q.slice(0, 120) }));
    sList.appendChild(li);
    sList.hidden = false;
  }
  sIn.addEventListener("input", renderSearch);
  sIn.addEventListener("keydown", (e) => {
    if (e.key === "Enter") { e.preventDefault(); const b = sList.querySelector("button"); if (b) b.click(); }
    if (e.key === "Escape") { sIn.value = ""; renderSearch(); }
  });

  // ---------- определение устройства: только после нажатия «Начать», без нагрузки ----------
  async function detect() {
    if (SYS) return;
    const [h, b] = await Promise.all([uaHints(), battery()]);
    const os = osName();
    SYS = { br: browserInfo(), os: osFull(os, h), gpu: gpuName(), ram: ramGb(), model: os === "Android" ? phoneModel(h) : "" };
    POWER = b;
    G = Guess.guess({
      ua: navigator.userAgent, os, threads: THREADS, gpu: SYS.gpu, model: SYS.model, arch: String(h.architecture || ""),
      mobile: navigator.userAgentData ? navigator.userAgentData.mobile : undefined, touch: navigator.maxTouchPoints || 0,
      battery: b.battery ? { level: b.percent / 100, charging: b.plugged } : null,
      screen: { w: screen.width, h: screen.height, dpr: window.devicePixelRatio || 1 },
    }, GCFG);

    const gpuShort = G.mg ? G.mg.label : shortGpu(SYS.gpu);
    $("det-gpu").textContent = gpuShort;
    $("det-gpu").title = SYS.gpu;
    $("det-os").textContent = [SYS.os, SYS.br.browser].filter(Boolean).join(" · ");
    $("det-os").title = $("det-os").textContent;
    $("det-ram").textContent = ramText(SYS.ram);

    // Человек уже выбирал процессор на этом устройстве — верим ему, если выбор подходит устройству.
    const saved = params.get("cpu") || store.get("nb.cpu");
    const known = saved && !saved.startsWith("other:") ? byKey(saved) : null;
    if (saved && saved.startsWith("other:")) choose({ other: true, name: saved.slice(6) }, "manual");
    else if (known && fits(known)) choose(known, "sure", "выбран вами раньше");
    else if (G.conf !== "low" && G.list.length) choose(G.list[0].c, G.conf);
    else paint();
    openPicker(!chosen);
  }

  // ---------- разрешение на нагрузку ----------
  const plannedMs = (points) => 3 * (T.freq + 400) + TESTS.length * (2 * T.warm + T.single + T.multi) + T.fps + T.fpsWarm
    + points * (T.warm + T.scale) + T.marathon * 1000;
  function etaText() {
    const sec = (plannedMs(scalePoints(THREADS, chosen ? chosen.cores : estCores()).length) * 1.15) / 1000;
    const m = Math.round(sec / 30) / 2; // с точностью до полминуты
    return m <= 1 ? "около минуты" : m % 1 ? `около ${fmt(m, 1)} минуты` : `около ${m} минут`;
  }
  function askConsent() {
    $("consent").hidden = false;
    $("live").hidden = true;
    $("eta").textContent = etaText();
    $("consent-phone").hidden = !mobileKind();
    const onBattery = !!(POWER && POWER.battery && POWER.plugged === false);
    $("power-warn").hidden = !onBattery;
    if (onBattery) {
      $("power-warn").textContent = `${mobileKind() ? "Устройство" : "Ноутбук"} работает от батареи — процессор будет ограничен, `
        + "очки выйдут ниже, а заряд быстро уйдёт. Лучше подключить зарядку.";
    }
    $("allow").focus({ preventScroll: true });
  }
  async function start() {
    $("start").hidden = true;
    $("run").hidden = false;
    window.scrollTo(0, 0);
    await detect();
    askConsent();
  }
  function allow() {
    $("consent").hidden = true;
    $("power-warn").hidden = true;
    $("live").hidden = false;
    run();
  }
  function deny() {
    $("run").hidden = true;
    $("start").hidden = false;
    $("go").focus({ preventScroll: true });
  }

  // ---------- ход теста ----------
  const STEPS = ["Частота", "Одно ядро", "Все ядра", "Игровая сцена", "Масштабирование", "Марафон"];
  const cell = (key, col, text) => {
    const td = document.querySelector(`#row-${key} .${col}`);
    td.textContent = text;
    td.classList.add("got");
  };
  const score = (key, rate) => (1000 * rate) / CFG.ref[key];
  function stage(n, current, test, k) {
    document.querySelectorAll("#steps li").forEach((li, i) => {
      li.classList.toggle("done", i < n - 1);
      li.classList.toggle("now", i === n - 1);
    });
    $("stage").textContent = `${n} из ${STEPS.length} · ${STEPS[n - 1]}`;
    $("current").textContent = current || (test ? `${test.title} · ${plural(k, THR)}` : plural(k, THR));
    document.querySelectorAll("#tests tbody tr").forEach((tr) => tr.classList.toggle("active", !!test && tr.id === "row-" + test.key));
  }
  function setProgress(p) {
    $("bar").style.width = (p * 100).toFixed(1) + "%";
    $("pct").textContent = Math.floor(p * 100) + "%";
  }

  // предпросмотр игровой сцены
  const fcv = $("fps-canvas");
  function drawFlock(pts) {
    const ctx = fcv.getContext("2d");
    const w = fcv.width, h = fcv.height;
    ctx.fillStyle = "#0b0b0b";
    ctx.fillRect(0, 0, w, h);
    ctx.fillStyle = "#c6ff3d";
    for (let i = 0; i < pts.length; i += 2) ctx.fillRect(pts[i] * w, pts[i + 1] * h, 1.6, 1.6);
  }
  function sizeCanvas() {
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    fcv.width = Math.round((fcv.clientWidth || 480) * dpr);
    fcv.height = Math.round(fcv.width * 9 / 16);
  }

  // ---------- пул рабочих потоков ----------
  class Cancelled extends Error {}
  class Pool {
    constructor(n) {
      this.workers = Array.from({ length: n }, () => new Worker(CFG.worker));
      this.pending = new Set();
    }
    call(i, msg, onTick) {
      return new Promise((resolve, reject) => {
        const w = this.workers[i];
        const job = { reject };
        this.pending.add(job);
        const finish = (fn, v) => { this.pending.delete(job); fn(v); };
        w.onmessage = (e) => {
          const d = e.data;
          if (d.type === "tick") { if (onTick) onTick(d); return; }
          if (d.type === "error") finish(reject, new Error(d.message));
          else finish(resolve, d);
        };
        w.onerror = (e) => { e.preventDefault(); finish(reject, new Error(e.message || "Ошибка в рабочем потоке")); };
        w.postMessage(msg);
      });
    }
    run(k, msg, onTick) { return Promise.all(Array.from({ length: k }, (_, i) => this.call(i, msg, onTick))); }
    close() {
      this.workers.forEach((w) => w.terminate());
      this.pending.forEach((j) => j.reject(new Cancelled()));
      this.pending.clear();
    }
  }

  function scalePoints(threads, cores) {
    const ks = new Set([1, 2, 4, 6, 8, 12, 16, 24, 32, 48, 64, cores, threads]);
    return [...ks].filter((k) => k >= 1 && k <= threads).sort((a, b) => a - b);
  }

  // ---------- тест (запускается только после разрешения) ----------
  let pool = null, running = false, hidden = false;
  let result = null, saving = false, saved = false; // result — готовый замер, ещё не сохранённый в топ

  async function run() {
    if (running) return;
    if (typeof Worker === "undefined") return fail("Браузер не поддерживает Web Workers — откройте сайт в Chrome, Edge, Firefox или Safari.");

    running = true;
    hidden = document.hidden;
    result = null;
    saved = false;
    document.body.classList.add("running");
    $("done").hidden = true;
    $("error").hidden = true;
    $("again").hidden = true;
    $("stop").hidden = false;
    document.querySelectorAll("#tests td.s, #tests td.m, #tests td.x").forEach((td) => { td.textContent = "—"; td.classList.remove("got"); });
    ["freq-1", "freq-all", "freq-hot", "fps-val"].forEach((id) => { $(id).textContent = "—"; });
    sizeCanvas();
    drawFlock(new Float32Array(0));

    const cores = chosen ? chosen.cores : estCores();
    const points = scalePoints(THREADS, cores);
    const total = plannedMs(points.length);
    let doneMs = 0, stepMs = 0, stepAt = performance.now();
    const step = (ms) => { doneMs += stepMs; stepMs = ms; stepAt = performance.now(); };
    const timer = setInterval(() => setProgress(Math.min(0.99, (doneMs + Math.min(stepMs, performance.now() - stepAt)) / total)), 200);
    setProgress(0);

    const single = {}, multi = {}, scaling = [], freq = {}, fps = {};
    const buckets = new Array(T.marathon).fill(0);
    const series = (more) => [{ name: "", vendor: "signal", cores, ...more }];
    const drawScaling = () => Charts.scaling($("c-scale"), series({ scaling }));
    const drawMarathon = (n) => Charts.marathon($("c-mar"), series({ marathon: { series: buckets.slice(0, n) } }), T.marathon);
    drawScaling();
    drawMarathon(0);

    const t0 = performance.now();
    const power0 = await battery();
    pool = new Pool(THREADS);
    try {
      // 1. частота: одно ядро (пока процессор холодный и разгоняется сильнее всего), затем все ядра
      stage(1, "одно ядро", null, 1);
      step(T.freq + 400);
      const [f1] = await pool.run(1, { cmd: "freq", ms: T.freq });
      freq.single = f1.ghz;
      $("freq-1").textContent = ghz(f1.ghz);
      stage(1, `все ${plural(THREADS, THR)}`, null, THREADS);
      step(T.freq + 400);
      const fa = await pool.run(THREADS, { cmd: "freq", ms: T.freq });
      freq.multi = median(fa.map((r) => r.ghz));
      $("freq-all").textContent = ghz(freq.multi);

      // 2. одно ядро
      for (const t of TESTS) {
        stage(2, null, t, 1);
        step(T.warm + T.single);
        const [r] = await pool.run(1, { cmd: "run", key: t.key, warm: T.warm, ms: T.single, opt: { mb: 32 } });
        single[t.key] = { rate: r.units / r.sec, check: r.check };
        cell(t.key, "s", fmt(score(t.key, single[t.key].rate)));
      }
      await pool.run(1, { cmd: "free" });

      // 3. все потоки сразу
      for (const t of TESTS) {
        stage(3, null, t, THREADS);
        step(T.warm + T.multi);
        const rs = await pool.run(THREADS, { cmd: "run", key: t.key, warm: T.warm, ms: T.multi, opt: { mb: 8 } });
        const rate = rs.reduce((s, r) => s + r.units / r.sec, 0);
        multi[t.key] = { rate, check: rs[0].check };
        cell(t.key, "m", fmt(score(t.key, rate)));
        cell(t.key, "x", "×" + fmt(rate / single[t.key].rate, 1));
      }
      await pool.run(THREADS, { cmd: "free" });

      // 4. игровая сцена: один поток, как главный поток игры
      stage(4, `стая из ${fmt(CFG.fps_objects)} объектов · 1 поток`, null, 1);
      step(T.fps + T.fpsWarm);
      $("fps-box").classList.add("on");
      const [fr] = await pool.run(1, { cmd: "fps", objects: CFG.fps_objects, warm: T.fpsWarm, ms: T.fps }, (d) => {
        drawFlock(d.pts);
        $("fps-val").textContent = fmt(d.fps);
      });
      fps.fps = fr.units / fr.sec;
      $("fps-val").textContent = fmt(fps.fps);
      $("fps-box").classList.remove("on");
      await pool.run(1, { cmd: "free" });

      // 5. масштабирование: 1, 2, 4 … все потоки
      for (const k of points) {
        stage(5, null, null, k);
        step(T.warm + T.scale);
        const rs = await pool.run(k, { cmd: "run", key: "float", warm: T.warm, ms: T.scale });
        const rate = rs.reduce((s, r) => s + r.units / r.sec, 0);
        scaling.push({ k, rate, speedup: rate / (scaling.length ? scaling[0].rate : rate) });
        drawScaling();
      }

      // 6. марафон: все потоки без перерыва — видно, сбрасывает ли процессор частоту от нагрева
      stage(6, `${T.marathon} секунд полной нагрузки`, null, THREADS);
      step(T.marathon * 1000);
      const m0 = performance.now();
      let drawn = 0;
      await pool.run(THREADS, { cmd: "run", key: "float", warm: 0, ms: T.marathon * 1000, ticks: true }, (d) => {
        const b = Math.floor((performance.now() - m0) / 1000);
        if (b < T.marathon) buckets[b] += d.units;
        if (b > drawn) { drawn = b; drawMarathon(b); }
      });
      drawMarathon(T.marathon);
      // частота сразу после нагрузки — «горячая»
      $("current").textContent = "частота после нагрева";
      step(T.freq + 400);
      const fh = await pool.run(THREADS, { cmd: "freq", ms: T.freq });
      freq.hot = median(fh.map((r) => r.ghz));
      $("freq-hot").textContent = ghz(freq.hot);

      const power1 = await battery();
      const power = { ...power0, plugged: power0.plugged === null ? null : power0.plugged && power1.plugged };
      setProgress(1);
      result = {
        format: CFG.format, uid: randomId(), device: DEVICE, hidden,
        duration: (performance.now() - t0) / 1000,
        system: { threads: THREADS, browser: SYS.br.browser, engine: SYS.br.engine, os: SYS.os, gpu: SYS.gpu, ram: SYS.ram, power },
        single, multi, scaling, marathon: { series: buckets }, freq, fps,
      };
      finished();
    } catch (err) {
      if (err instanceof Cancelled) {
        $("stage").textContent = "Тест остановлен";
        $("current").textContent = "Нагрузка снята. Результат не сохранён.";
      } else {
        fail(err && err.message ? err.message : String(err));
      }
      $("again").hidden = false;
    } finally {
      clearInterval(timer);
      if (pool) pool.close();
      pool = null;
      running = false;
      $("stop").hidden = true;
      $("fps-box").classList.remove("on");
      document.body.classList.remove("running");
      document.querySelectorAll("#tests tbody tr").forEach((tr) => tr.classList.remove("active"));
    }
  }

  function finished() {
    document.querySelectorAll("#steps li").forEach((li) => { li.classList.add("done"); li.classList.remove("now"); });
    $("stage").textContent = "Готово";
    $("current").textContent = "Все тесты выполнены";
    $("d-single").textContent = fmt(geomean(TESTS.map((t) => score(t.key, result.single[t.key].rate))));
    $("d-multi").textContent = fmt(geomean(TESTS.map((t) => score(t.key, result.multi[t.key].rate))));
    $("again").hidden = false;
    $("done").hidden = false;
    paint();
    $("done").scrollIntoView({ behavior: "smooth", block: "center" });
  }

  async function save() {
    if (!result || saving) return;
    if (!chosen) { openPicker(true); $("cpu-card").scrollIntoView({ behavior: "smooth", block: "start" }); sIn.focus(); return; }
    const name = $("name").value.trim().slice(0, 40) || "Аноним";
    store.set("nb.name", name);
    saving = true;
    $("save").disabled = true;
    $("save").textContent = "Сохраняю…";
    $("error").hidden = true;
    const cpu = chosen;
    try {
      const res = await fetch("/api/save/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ...result, name,
          system: { ...result.system, cpu_key: cpu.key, cpu: cpu.name, cores: cpu.cores, cores_est: cpu.est },
        }),
      });
      const out = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(out.error || `Сервер не сохранил результат (код ${res.status}).`);
      saved = true;
      location.href = out.url;
    } catch (err) {
      fail(err && err.message ? err.message : String(err), true);
      saving = false;
      $("save").textContent = "Сохранить в топ";
      paint();
    }
  }

  function fail(msg, keepStage) {
    $("error").textContent = msg;
    $("error").hidden = false;
    if (!keepStage) $("stage").textContent = "Тест прерван";
  }

  $("go").addEventListener("click", start);
  $("allow").addEventListener("click", allow);
  $("deny").addEventListener("click", deny);
  $("again").addEventListener("click", run);
  $("save").addEventListener("click", save);
  $("name").addEventListener("keydown", (e) => { if (e.key === "Enter") save(); });
  $("stop").addEventListener("click", () => { if (pool) pool.close(); });
  document.addEventListener("visibilitychange", () => { if (running && document.hidden) hidden = true; });
  window.addEventListener("beforeunload", (e) => {
    if (running || (result && !saved)) { e.preventDefault(); e.returnValue = ""; }
  });

  // ---------- начальное состояние: пусто, только кнопка. Даже ссылка с ?start=1 лишь показывает
  // устройство и спрашивает разрешения — нагрузка без нажатия «Разрешить и начать» не начинается. ----------
  $("name").value = params.get("name") || store.get("nb.name") || "";
  if (params.get("start") === "1") start();
})();
