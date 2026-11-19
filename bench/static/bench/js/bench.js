/* Страница теста. Тесты выполняются в Web Workers — на процессоре ТОГО компьютера, где открыта
   страница. Сервер только хранит результаты и собирает общий топ.

   До нажатия «Начать» страница пустая и ничего о компьютере не узнаёт. После нажатия сайт сам определяет,
   что может: потоки, графику, систему, примерный объём памяти. Модель процессора браузер не сообщает
   ни с каким разрешением — сайт угадывает её по числу потоков и встроенной графике (название видно через
   WebGL) и сразу пишет. Если угадал неверно, человек поправляет через «не тот?», пока идёт тест.
   В топ результат попадает только по кнопке «Сохранить в топ» в конце. */
(() => {
  "use strict";
  const $ = (id) => document.getElementById(id);
  const CFG = JSON.parse($("cfg").textContent);
  const TESTS = CFG.tests;
  const fmt = (n, d = 0) => Number(n).toLocaleString("ru-RU", { minimumFractionDigits: d, maximumFractionDigits: d });
  const ghz = (x) => (x ? fmt(x, 2).replace(/0$/, "").replace(/,$/, "") : "—");
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

  // ---------- что браузер знает о компьютере ----------
  function browserInfo() {
    const ua = navigator.userAgent;
    const list = [[/Edg\/(\d+)/, "Edge", "V8"], [/OPR\/(\d+)/, "Opera", "V8"], [/YaBrowser\/(\d+)/, "Яндекс Браузер", "V8"],
      [/Firefox\/(\d+)/, "Firefox", "SpiderMonkey"], [/Chrome\/(\d+)/, "Chrome", "V8"], [/Version\/(\d+).*Safari/, "Safari", "JavaScriptCore"]];
    for (const [re, name, engine] of list) {
      const m = ua.match(re);
      if (m) return { browser: `${name} ${m[1]}`, engine };
    }
    return { browser: "Браузер", engine: "?" };
  }
  function osName() {
    const ua = navigator.userAgent;
    return /Windows/.test(ua) ? "Windows" : /Android/.test(ua) ? "Android" : /iPhone|iPad/.test(ua) ? "iOS"
      : /Mac OS X/.test(ua) ? "macOS" : /CrOS/.test(ua) ? "ChromeOS" : /Linux/.test(ua) ? "Linux" : "";
  }
  // Windows 10 и 11 в строке браузера одинаковые; Chrome и Edge отдают номер версии платформы отдельно (13+ — это 11).
  async function osFull() {
    const base = osName();
    try {
      const d = navigator.userAgentData;
      if (base === "Windows" && d && d.getHighEntropyValues) {
        const v = await d.getHighEntropyValues(["platformVersion"]);
        const major = parseInt(String(v.platformVersion || "").split(".")[0], 10);
        if (major >= 13) return "Windows 11";
        if (major >= 1) return "Windows 10";
      }
    } catch (e) { /* браузер не сообщает — оставим просто «Windows» */ }
    return base;
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
  const shortGpu = (g) => g.replace(/^ANGLE \(([^,]+),\s*/, "").replace(/\s*\(0x[0-9a-f]+\)/i, "").replace(/\s*(Direct3D|OpenGL|Metal|vs_|, D3D).*$/i, "")
    .replace(/\(R\)|\(TM\)/g, "").replace(/\s+/g, " ").trim() || "не видна";

  // Заполняется только после нажатия «Начать».
  let SYS = null; // { br, os, gpu, ram }
  let G = { list: [], gpu: { discrete: false } };

  // ---------- угадывание процессора ----------
  const RULES = CFG.gpu_rules.map(([re, fams]) => [new RegExp(re, "i"), fams.split(" ")]);
  function analyzeGpu(g) {
    const discrete = /NVIDIA|GeForce|Quadro|\bRTX\b|\bGTX\b|Radeon\s?(\(TM\)\s?)?(RX|Pro)\b|Arc\(TM\) A\d|Arc A\d/i.test(g);
    const apple = g.match(/Apple M(\d+)\s*(Pro|Max|Ultra)?/i);
    let vendor = null;
    if (/Apple/i.test(g)) vendor = "apple";
    else if (!discrete && /Intel/i.test(g)) vendor = "intel";
    else if (!discrete && /AMD|Radeon/i.test(g)) vendor = "amd";
    const fams = new Set();
    if (apple) fams.add("m" + apple[1] + (apple[2] ? apple[2].toLowerCase() : ""));
    else if (!discrete) {
      for (const [re, f] of RULES) if (re.test(g)) { f.forEach((x) => fams.add(x)); break; }
    }
    // Если браузер видит только дискретную видеокарту, процессор по ней не узнать, но можно сузить круг:
    // «Laptop GPU» — игровой ноутбук (обычно процессор серии H), поколение видеокарты — примерные годы.
    let laptop = null, era = null;
    if (discrete) {
      laptop = /Laptop|Max-Q|Mobile|RX\s?\d{4}M\b/i.test(g);
      const nv = g.match(/(?:RTX|GTX)\s?(\d{2})(\d{2})/i), rx = g.match(/RX\s?(\d)\d{3}/i);
      if (nv) era = { 50: 2025, 40: 2023, 30: 2021, 20: 2019, 16: 2019, 10: 2017 }[nv[1]] || null;
      else if (rx) era = { 9: 2025, 7: 2023, 6: 2021, 5: 2019 }[rx[1]] || null;
    }
    return { vendor, fams, discrete, laptop, era };
  }
  function guess(gpu, os) {
    const g = analyzeGpu(gpu);
    const mac = os === "macOS";
    const out = [];
    for (const c of CFG.catalog) {
      if (c.threads !== THREADS) continue;
      if (c.vendor === "apple" && !mac) continue;
      if (mac && c.vendor !== "apple" && g.vendor !== "intel") continue;
      let s = 40;
      if (g.vendor) {
        if (c.vendor !== g.vendor) continue;
        s += 15;
        if (!g.discrete && c.fam.length === 0) continue; // встроенная графика есть, а у этой модели её нет
      }
      if (g.fams.size) s += c.fam.some((f) => g.fams.has(f)) ? 50 : -25;
      if (g.laptop !== null) {
        s += g.laptop === (c.seg === "l") ? 10 : -20;
        if (g.laptop && c.tdp && c.tdp < 35) s -= 10; // в игровых ноутбуках редко ставят экономичные U-серии
      }
      if (g.era) s += c.year >= g.era - 1 && c.year <= g.era + 2 ? 10 : -10;
      s += (c.year - 2015) * 0.3; // при равенстве — новее выше
      out.push({ c, s });
    }
    return { list: out.sort((a, b) => b.s - a.s).slice(0, 3), gpu: g };
  }
  const norm = (s) => s.toLowerCase().replace(/[^a-z0-9а-я]/g, "");
  function search(q) {
    const toks = q.toLowerCase().split(/\s+/).map(norm).filter(Boolean);
    if (!toks.length) return [];
    return CFG.catalog.filter((c) => { const n = norm(c.name); return toks.every((t) => n.includes(t)); })
      .sort((a, b) => b.year - a.year).slice(0, 8);
  }

  // ---------- процессор: угаданный или исправленный ----------
  const vendorName = (v) => ({ intel: "Intel", amd: "AMD", apple: "Apple" }[v] || "CPU");
  const shortName = (n) => n.replace(/^(AMD|Intel|Apple)\s+/i, "");
  const byKey = (k) => CFG.catalog.find((c) => c.key === k);
  const estCores = () => (THREADS >= 4 && SYS && SYS.os !== "macOS" ? Math.round(THREADS / 2) : THREADS);
  let chosen = null; // { key, name, vendor, cores, threads, boost, year, est, sure }
  let extra = null;  // выбранный через поиск, если его нет среди угаданных

  function choose(c, how) {
    // how: "auto" — угадал сайт, "sure" — угадал уверенно, "manual" — выбрал человек
    if (c.other) {
      const v = /intel/i.test(c.name) ? "intel" : /amd|ryzen/i.test(c.name) ? "amd" : /apple/i.test(c.name) ? "apple" : "other";
      chosen = { key: "", name: c.name, vendor: v, cores: estCores(), threads: null, est: true, sure: true };
      store.set("nb.cpu", "other:" + c.name);
    } else {
      chosen = { key: c.key, name: c.name, vendor: c.vendor, cores: Math.min(c.cores, THREADS), threads: c.threads,
        boost: c.boost, year: c.year, est: false, sure: how !== "auto" };
      if (how === "manual") store.set("nb.cpu", c.key);
      if (!G.list.some((x) => x.c.key === c.key)) extra = c;
    }
    paint();
  }

  function renderCards() {
    const box = $("cands");
    box.textContent = "";
    const items = [];
    if (extra && !G.list.some((x) => x.c.key === extra.key)) items.push(extra);
    G.list.forEach((x) => items.push(x.c));
    $("cand-title").textContent = items.length ? "Похожие процессоры:" : "Угадать не получилось — найдите свой процессор:";
    items.forEach((c) => {
      const b = document.createElement("button");
      b.type = "button";
      b.className = "cand";
      b.setAttribute("role", "radio");
      b.dataset.vendor = c.vendor;
      b.setAttribute("aria-checked", chosen && chosen.key === c.key ? "true" : "false");
      b.innerHTML = `<span class="cand-v">${vendorName(c.vendor)}</span><span class="cand-n"></span>` +
        `<span class="cand-s">${c.cores} ядер · ${c.threads} потоков · ${c.year}</span>`;
      b.querySelector(".cand-n").textContent = shortName(c.name);
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

  function paint() {
    const c = chosen;
    $("cpu-card").dataset.vendor = c ? c.vendor : "other";
    $("cpu-name").textContent = c ? c.name : "Не удалось определить";
    $("cpu-name").classList.toggle("unknown", !c);
    const sub = [];
    if (c && !c.est) sub.push(`${c.cores} ядер · ${c.threads} потоков`, c.boost ? `до ${ghz(c.boost)} ГГц` : "", String(c.year));
    if (c && c.est) sub.push("нет в справочнике");
    if (c && !c.sure) sub.push("определён примерно");
    if (!c) sub.push("Браузер не сообщает модель — найдите свой процессор ниже");
    $("cpu-sub").textContent = sub.filter(Boolean).join(" · ");
    // ядра берутся из справочника — показываем их, только если в модели уверены; потоки браузер знает точно
    $("det-cores").textContent = c && !c.est && c.sure ? `${c.cores} / ${THREADS}` : `${THREADS} потоков`;

    const hint = $("cpu-hint");
    hint.classList.remove("bad");
    if (c && c.threads && c.threads !== THREADS) {
      hint.textContent = `Браузер видит ${THREADS} потоков, а у ${c.name} их ${c.threads}. Проверьте, тот ли процессор выбран.`;
      hint.classList.add("bad");
    } else if (G.gpu.discrete) {
      hint.textContent = "Браузер видит только дискретную видеокарту — по ней модель процессора точно не узнать. " +
        "Точное название написано в Диспетчере задач → Производительность → ЦП.";
    } else {
      hint.textContent = "Точное название написано в Диспетчере задач → Производительность → ЦП.";
    }
    $("save").disabled = !c || saving;
    $("save-hint").textContent = c ? "" : "Чтобы сохранить результат, укажите процессор: нажмите «не тот?» вверху страницы.";
    renderCards();
  }

  function openPicker(open) {
    $("picker").hidden = !open;
    $("fix").setAttribute("aria-expanded", open ? "true" : "false");
    $("fix").textContent = open ? "скрыть" : "не тот?";
  }
  $("fix").addEventListener("click", () => {
    const open = $("picker").hidden;
    openPicker(open);
    if (open) sIn.focus();
  });

  // поиск по справочнику
  const sIn = $("search"), sList = $("search-list");
  function renderSearch() {
    const q = sIn.value.trim();
    sList.textContent = "";
    if (!q) { sList.hidden = true; return; }
    const pick = (c) => { choose(c, "manual"); sIn.value = ""; sList.hidden = true; openPicker(false); };
    search(q).forEach((c) => {
      const li = document.createElement("li");
      li.innerHTML = `<button type="button"><span class="cand-v" data-vendor="${c.vendor}">${vendorName(c.vendor)}</span> <b></b> <small>${c.cores}/${c.threads} · ${c.year}</small></button>`;
      li.querySelector("b").textContent = shortName(c.name);
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

  // ---------- определение компьютера: только после нажатия «Начать» ----------
  async function detect() {
    if (SYS) return;
    SYS = { br: browserInfo(), os: await osFull(), gpu: gpuName(), ram: ramGb() };
    G = guess(SYS.gpu, SYS.os);
    $("det-gpu").textContent = shortGpu(SYS.gpu);
    $("det-gpu").title = SYS.gpu;
    $("det-os").textContent = [SYS.os, SYS.br.browser].filter(Boolean).join(" · ");
    $("det-ram").textContent = ramText(SYS.ram);

    // Человек уже поправлял процессор на этом компьютере — верим ему, если совпадает число потоков.
    const saved = params.get("cpu") || store.get("nb.cpu");
    const known = saved && !saved.startsWith("other:") ? byKey(saved) : null;
    if (saved && saved.startsWith("other:")) choose({ other: true, name: saved.slice(6) }, "manual");
    else if (known && known.threads === THREADS) choose(known, "sure");
    else if (G.list.length) choose(G.list[0].c, G.list[0].s >= 100 ? "sure" : "auto");
    else paint();
    openPicker(!chosen);
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
    $("current").textContent = current || (test ? `${test.title} · ${k === 1 ? "1 поток" : `${k} потоков`}` : `${k} потоков`);
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

  // ---------- тест ----------
  let pool = null, running = false, hidden = false;
  let result = null, saving = false, saved = false; // result — готовый замер, ещё не сохранённый в топ

  async function start() {
    $("start").hidden = true;
    $("run").hidden = false;
    window.scrollTo(0, 0);
    await detect();
    battery().then((b) => { $("power-warn").hidden = !(b.battery && b.plugged === false); });
    run();
  }

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
    const total = 3 * (T.freq + 400) + TESTS.length * (2 * T.warm + T.single + T.multi) + T.fps + T.fpsWarm
      + points.length * (T.warm + T.scale) + T.marathon * 1000;
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
      stage(1, `все ${THREADS} потоков`, null, THREADS);
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
        $("current").textContent = "Результат не сохранён.";
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
  $("again").addEventListener("click", run);
  $("save").addEventListener("click", save);
  $("name").addEventListener("keydown", (e) => { if (e.key === "Enter") save(); });
  $("stop").addEventListener("click", () => { if (pool) pool.close(); });
  document.addEventListener("visibilitychange", () => { if (running && document.hidden) hidden = true; });
  window.addEventListener("beforeunload", (e) => {
    if (running || (result && !saved)) { e.preventDefault(); e.returnValue = ""; }
  });

  // ---------- начальное состояние: пусто, только кнопка ----------
  $("name").value = params.get("name") || store.get("nb.name") || "";
  if (params.get("start") === "1") start();
})();
