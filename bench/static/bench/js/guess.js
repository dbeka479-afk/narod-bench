/* Угадывание процессора. Модель процессора браузер не сообщает никогда, поэтому сайт собирает косвенные признаки:
   — что это за устройство: телефон, планшет, ноутбук или настольный ПК (строка браузера, батарея, сенсорный экран,
     подпись видеокарты «Laptop GPU»);
   — графика: у встроенной графики Intel и AMD по коду устройства видно поколение процессора, а у телефонов графика
     прямо указывает на чип (Adreno бывает только в Snapdragon, Xclipse — только в Exynos и т. д.);
   — модель телефона (Chrome на Android её сообщает) и размер экрана iPhone;
   — число потоков.
   Если признаков мало (например, у настольного ПК браузеру видна только дискретная видеокарта), сайт честно пишет,
   что модель не видна, и предлагает выбрать из похожих. Здесь только расчёт, без страницы. */
const Guess = (() => {
  "use strict";

  const VENDORS = { intel: "Intel", amd: "AMD", apple: "Apple", qualcomm: "Qualcomm", mediatek: "MediaTek",
    samsung: "Samsung", google: "Google", unisoc: "Unisoc", hisilicon: "HiSilicon" };
  // как называть процессор, если известна только фирма
  const FAMILY = { intel: "Intel", amd: "AMD", apple: "Apple", qualcomm: "Snapdragon", mediatek: "MediaTek",
    samsung: "Samsung Exynos", google: "Google Tensor", unisoc: "Unisoc", hisilicon: "Kirin" };

  // Экран iPhone (ширина × высота в точках @ плотность) → какие чипы стоят в iPhone с таким экраном.
  // Первым — самый распространённый вариант.
  const IPHONE = {
    "375x667@2": ["apple-a13-bionic", "apple-a15-bionic", "apple-a11-bionic"],      // SE 2, SE 3, 8
    "414x736@3": ["apple-a11-bionic"],                                              // 8 Plus
    "375x812@3": ["apple-a13-bionic", "apple-a12-bionic", "apple-a11-bionic", "apple-a14-bionic", "apple-a15-bionic"],
    "414x896@2": ["apple-a13-bionic", "apple-a12-bionic"],                          // 11, XR
    "414x896@3": ["apple-a13-bionic", "apple-a12-bionic"],                          // 11 Pro Max, XS Max
    "390x844@3": ["apple-a15-bionic", "apple-a14-bionic", "apple-a18"],             // 13/14, 12, 16e
    "428x926@3": ["apple-a15-bionic", "apple-a14-bionic"],                          // 13 Pro Max / 14 Plus, 12 Pro Max
    "393x852@3": ["apple-a16-bionic", "apple-a18", "apple-a17-pro"],                // 15 / 14 Pro, 16, 15 Pro
    "430x932@3": ["apple-a16-bionic", "apple-a18", "apple-a17-pro"],                // 15 Plus / 14 Pro Max, 16 Plus, 15 Pro Max
    "402x874@3": ["apple-a18-pro", "apple-a19", "apple-a19-pro"],                   // 16 Pro, 17, 17 Pro
    "440x956@3": ["apple-a18-pro", "apple-a19-pro"],                                // 16 Pro Max, 17 Pro Max
    "420x912@3": ["apple-a19-pro"],                                                 // Air
  };

  function prepare(cfg) {
    return {
      catalog: cfg.catalog,
      rules: cfg.gpu_rules.map(([re, fams]) => [new RegExp(re, "i"), fams.split(" ")]),
      models: (cfg.model_rules || []).map(([re, keys]) => [new RegExp(re, "i"), keys.split(" ")]),
    };
  }

  // ---------- видеокарта компьютера ----------
  function pcGpu(g, rules) {
    const igpVega = /Vega \d+ Graphics/i.test(g); // встроенная графика Ryzen, хоть и называется «RX Vega»
    const discrete = !igpVega && /NVIDIA|GeForce|Quadro|\bRTX\b|\bGTX\b|Radeon\s?(\(TM\)\s?)?(RX|Pro)\b|Arc\(TM\) A\d|Arc A\d/i.test(g);
    const m = g.match(/Apple M(\d+)\s*(Pro|Max|Ultra)?/i);
    let vendor = null;
    if (/Apple/i.test(g)) vendor = "apple";
    else if (/Qualcomm|Adreno/i.test(g)) vendor = "qualcomm";
    else if (!discrete && /Intel/i.test(g)) vendor = "intel";
    else if (!discrete && /AMD|Radeon/i.test(g)) vendor = "amd";
    const fams = new Set();
    if (m) fams.add("m" + m[1] + (m[2] ? m[2].toLowerCase() : ""));
    else if (!discrete) {
      for (const [re, f] of rules) if (re.test(g)) { f.forEach((x) => fams.add(x)); break; }
    }
    // Если видна только дискретная видеокарта, процессор по ней не узнать, но можно понять ноутбук это или нет
    // и примерные годы. Ноутбучные NVIDIA начиная с RTX 30 всегда подписаны «Laptop GPU», AMD — буквой M или S.
    let laptop = null, era = null;
    if (discrete) {
      const nv = g.match(/(?:RTX|GTX)\s?(\d{2})(\d{2})/i), rx = g.match(/RX\s?(\d)\d{3}/i);
      if (/Laptop|Max-Q|Mobile|GeForce MX|RX\s?\d{4}[MS]\b/i.test(g)) laptop = true;
      else if ((nv && +nv[1] >= 30) || rx) laptop = false;
      if (nv) era = { 50: 2025, 40: 2023, 30: 2021, 20: 2019, 16: 2019, 10: 2017 }[nv[1]] || null;
      else if (rx) era = { 9: 2025, 7: 2023, 6: 2021, 5: 2019 }[rx[1]] || null;
    }
    return { vendor, fams, discrete, laptop, era, apple: m ? m[0] : "" };
  }

  // ---------- видеокарта телефона: «Adreno (TM) 642L» → adreno-642l, «Mali-G57 MC2» → mali-g57 ×2 ----------
  function mobileGpu(s) {
    s = String(s || "");
    let m = s.match(/Adreno\D{0,8}?(\d{3}[A-Z]?)\b/i);
    if (m) return { f: "adreno-" + m[1].toLowerCase(), n: 0, vendor: "qualcomm", label: "Adreno " + m[1].toUpperCase() };
    m = s.match(/(Mali|Immortalis)[-\s]?(G\d{2,3}[A-Z]?)(?:\s*(MC|MP)(\d+))?/i);
    if (m) {
      const label = `${m[1][0].toUpperCase()}${m[1].slice(1).toLowerCase()}-${m[2].toUpperCase().replace(/S$/, "s")}`;
      return { f: (m[1] + "-" + m[2]).toLowerCase(), n: m[4] ? +m[4] : 0, vendor: null,
        label: label + (m[4] ? ` ${m[3].toUpperCase()}${m[4]}` : "") };
    }
    m = s.match(/Xclipse\s?(\d{3})/i);
    if (m) return { f: "xclipse-" + m[1], n: 0, vendor: "samsung", label: "Xclipse " + m[1] };
    m = s.match(/PowerVR.*?\b(GE\d{4}|BXM-\d+-\d+|DXT-\d+-\d+)/i);
    if (m) return { f: "powervr-" + m[1].toLowerCase(), n: 0, vendor: null, label: "PowerVR " + m[1].toUpperCase() };
    m = s.match(/Maleoon\s?(\d{3})/i);
    if (m) return { f: "maleoon-" + m[1], n: 0, vendor: "hisilicon", label: "Maleoon " + m[1] };
    if (/^\s*Apple GPU\s*$/i.test(s)) return { f: "apple-gpu", n: 0, vendor: "apple", label: "Apple GPU" };
    return null;
  }

  // ---------- что за устройство ----------
  function kind(env, pg) {
    if (env.os === "Android") {
      return env.mobile === true || /Mobile/.test(env.ua || "") ? "phone" : "tablet"; // у планшетов «Mobile» нет
    }
    if (env.os === "iOS") return /iPad/.test(env.ua || "") ? "tablet" : "phone";
    if (env.os === "macOS") return env.touch > 1 ? "tablet" : "mac"; // iPad притворяется Mac'ом, но у него сенсорный экран
    // компьютер: ноутбук или настольный? Набираем очки «за ноутбук» и «против».
    let s = 0;
    if (pg.laptop === true) s += 3;
    else if (pg.laptop === false) s -= 3;
    const b = env.battery; // у настольного ПК браузер показывает «заряд 100%, на зарядке» — как у полного ноутбука
    if (b && (b.level < 0.99 || b.charging === false)) s += 3;
    if (env.touch > 0) s += 1;
    if (env.arch === "arm" || env.os === "ChromeOS") s += 2;
    return s >= 2 ? "laptop" : s <= -2 ? "desktop" : "pc";
  }

  const bonus = (c, k = 0.3) => (c.year - 2010) * k + (c.pop ? 2 : 0); // при прочих равных — новее и популярнее

  function finish(out, res) {
    res.sort((a, b) => b.s - a.s);
    out.list = res;
    return out;
  }
  const clearWin = (res) => res.length < 2 || res[0].s - res[1].s >= 6;

  // ---------- компьютер и Mac ----------
  function pc(env, cfg, g, out) {
    const mac = out.kind === "mac", arm = env.arch === "arm";
    const res = [];
    for (const c of cfg.catalog) {
      if (c.threads !== env.threads || c.seg === "p") continue;
      if (mac ? c.vendor !== "apple" && g.vendor !== "intel" : c.seg === "m") continue;
      if (!mac && (c.vendor === "qualcomm" ? !(arm || g.vendor === "qualcomm") : arm)) continue; // Windows на ARM — это Snapdragon X
      let s = 40, hit = false;
      if (g.vendor) {
        if (c.vendor !== g.vendor) continue;
        s += 15;
        if (!g.discrete && c.fam.length === 0) continue; // встроенная графика есть, а у этой модели её нет
      }
      if (g.fams.size) {
        hit = c.fam.some((f) => g.fams.has(f));
        s += hit ? 50 : -25;
      }
      if (out.kind === "laptop") s += c.seg === "l" ? 12 : -25;
      else if (out.kind === "desktop") s += c.seg === "d" ? 12 : -25;
      if (g.laptop && c.tdp && c.tdp < 35) s -= 10; // в игровых ноутбуках редко ставят экономичные U-серии
      if (g.era) s += c.year >= g.era - 1 && c.year <= g.era + 2 ? 10 : -10;
      res.push({ c, s: s + bonus(c), hit });
    }
    finish(out, res);
    const top = res[0];
    out.vendor = top && top.hit ? top.c.vendor : g.vendor;
    if (top && top.hit) {
      out.conf = clearWin(res) ? "sure" : "auto";
      out.why = g.apple ? "по графике " + g.apple : "по встроенной графике";
    }
    return out;
  }

  // ---------- телефон или планшет на Android ----------
  function android(env, cfg, out) {
    const mg = mobileGpu(env.gpu);
    let mk = null;
    if (env.model) for (const [re, keys] of cfg.models) if (re.test(env.model)) { mk = new Set(keys); break; }
    const res = [];
    for (const c of cfg.catalog) {
      if (c.seg !== "p" || c.vendor === "apple") continue;
      const cg = mobileGpu(c.gpu);
      const byModel = !!(mk && mk.has(c.key));
      let s = 40, gpuHit = false;
      if (mg) {
        if (cg && cg.f === mg.f) {
          gpuHit = true;
          s += 60;
          if (mg.n && cg.n) s += mg.n === cg.n ? 15 : -20; // Mali-G57 MC2 и Mali-G57 MC3 — разные чипы
        } else if (!byModel) continue;
        else s -= 30; // модель говорит одно, графика — другое
      }
      if (mk) s += byModel ? 80 : -30;
      if (c.threads === env.threads) s += 4; // Android иногда отключает часть ядер — поэтому не строго
      res.push({ c, s: s + bonus(c), hit: gpuHit, model: byModel });
    }
    finish(out, res);
    const top = res[0];
    if (top && top.model) {
      out.conf = (!mg || top.hit) && clearWin(res) ? "sure" : "auto";
      out.why = "по модели " + env.model;
    } else if (top && top.hit) {
      out.conf = clearWin(res) ? "sure" : "auto";
      out.why = "по графике " + mg.label;
    }
    out.vendor = top && (top.hit || top.model) ? top.c.vendor : mg ? mg.vendor : null;
    out.mg = mg;
    return out;
  }

  // ---------- iPhone и iPad ----------
  function apple(env, cfg, out) {
    const sc = env.screen || {};
    const keys = out.kind === "phone" ? IPHONE[`${Math.min(sc.w, sc.h)}x${Math.max(sc.w, sc.h)}@${Math.round(sc.dpr || 1)}`] || [] : [];
    const res = [];
    for (const c of cfg.catalog) {
      if (c.vendor !== "apple" || (out.kind === "phone" && c.seg !== "p")) continue;
      const i = keys.indexOf(c.key);
      if (keys.length && i < 0) continue; // экран известен — только подходящие iPhone
      res.push({ c, s: 40 + (i >= 0 ? 50 + (keys.length - i) * 2 : 0) + bonus(c, 0.1), hit: i >= 0 });
    }
    finish(out, res);
    out.vendor = "apple";
    if (res[0] && res[0].hit) {
      out.conf = keys.length === 1 ? "sure" : "auto";
      out.why = "по размеру экрана iPhone";
    }
    return out;
  }

  /* env: { ua, os, threads, gpu, model, arch, mobile, touch, battery: {level, charging} | null, screen: {w, h, dpr} }
     Ответ: { kind, list: [{ c, s }], conf: "sure" | "auto" | "low", vendor, why }
       sure — признаки указывают на одну модель; auto — на несколько похожих (первая — самая вероятная);
       low — признаков нет, модель не видна. */
  function guess(env, cfg) {
    const pg = pcGpu(String(env.gpu || ""), cfg.rules);
    const out = { kind: kind(env, pg), list: [], conf: "low", vendor: null, why: "", gpu: pg, mg: null };
    if (out.kind === "phone" || out.kind === "tablet") return env.os === "Android" ? android(env, cfg, out) : apple(env, cfg, out);
    return pc(env, cfg, pg, out);
  }

  return { prepare, guess, mobileGpu, pcGpu, kind, VENDORS, FAMILY };
})();
