/* Два графика на canvas без библиотек: масштабирование по потокам и марафон. */
const Charts = (() => {
  "use strict";
  const COL = { signal: "#4d8dff", intel: "#5aa9ff", amd: "#ff6b57", apple: "#d3d8e0", other: "#5fd0c0", other2: "#b393ff" };
  const INK = "#e8edf4", MU = "#6f7c8f", GRID = "#1b2431", BG = "#0c1118";
  const FONT = '11px "Martian Mono", Consolas, monospace';
  const BOLD = '600 11px "Martian Mono", Consolas, monospace';
  const fmt = (n, d = 1) => Number(n).toLocaleString("ru-RU", { minimumFractionDigits: d, maximumFractionDigits: d });

  function setup(cv) {
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    const w = cv.clientWidth || 500;
    const h = +(cv.dataset.h || (cv.dataset.h = cv.getAttribute("height") || 220)); // атрибут перезаписывается ниже
    cv.width = Math.round(w * dpr);
    cv.height = Math.round(h * dpr);
    cv.style.height = h + "px";
    const ctx = cv.getContext("2d");
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, w, h);
    ctx.font = FONT;
    return { ctx, w, h };
  }

  function empty(ctx, h) {
    ctx.fillStyle = MU;
    ctx.fillText("появится во время замера", 12, h / 2);
  }

  function nice(max) {
    const p = Math.pow(10, Math.floor(Math.log10(max || 1)));
    const m = max / p;
    const step = (m <= 2 ? 0.5 : m <= 5 ? 1 : 2) * p;
    const out = [];
    for (let v = 0; v <= max + 1e-9; v += step) out.push(+v.toFixed(6));
    return out;
  }

  function axes(ctx, box, xmax, ymax, xlab, ylab, xticks, yticks, xpos) {
    const { l, t, r, b } = box;
    ctx.lineWidth = 1;
    ctx.fillStyle = MU;
    yticks.forEach((v) => {
      const y = b - (v / ymax) * (b - t);
      ctx.strokeStyle = GRID;
      ctx.beginPath(); ctx.moveTo(l, y); ctx.lineTo(r, y); ctx.stroke();
      ctx.textAlign = "right"; ctx.fillText(fmt(v, v % 1 ? 1 : 0), l - 6, y + 4);
    });
    xticks.forEach((v) => { ctx.textAlign = "center"; ctx.fillText(String(v), xpos(v), b + 16); });
    ctx.strokeStyle = INK;
    ctx.beginPath(); ctx.moveTo(l, b); ctx.lineTo(r, b); ctx.stroke();
    ctx.textAlign = "right"; ctx.fillText(xlab, r, b + 32);
    ctx.textAlign = "left"; ctx.fillText(ylab, l - 34, t - 14);
  }

  function legend(ctx, series, w) {
    let x = w - 4;
    ctx.font = BOLD;
    series.filter((s) => s.name).slice().reverse().forEach((s) => {
      const tw = ctx.measureText(s.name).width;
      x -= tw;
      ctx.fillStyle = INK; ctx.textAlign = "left"; ctx.fillText(s.name, x, 12);
      x -= 18;
      ctx.fillStyle = COL[s.vendor] || COL.other; ctx.fillRect(x, 6, 12, 4);
      x -= 18;
    });
    ctx.font = FONT;
  }

  function scaling(cv, series) {
    if (!cv) return;
    const { ctx, w, h } = setup(cv);
    const all = series.flatMap((s) => s.scaling || []);
    if (!all.length) return empty(ctx, h);
    const kmax = Math.max(...all.map((p) => p.k), 2);
    const ymax = Math.max(...all.map((p) => p.speedup), 2) * 1.12;
    const box = { l: 40, t: 40, r: w - 10, b: h - 38 };
    const X = (k) => box.l + (k / kmax) * (box.r - box.l);
    const Y = (v) => box.b - (v / ymax) * (box.b - box.t);
    const ks = [...new Set(all.map((p) => p.k))].sort((a, b) => a - b);
    axes(ctx, box, kmax, ymax, "потоков", "ускорение, раз", ks, nice(ymax), X);
    ctx.setLineDash([4, 4]); ctx.strokeStyle = MU; ctx.lineWidth = 1;
    ctx.beginPath(); ctx.moveTo(X(1), Y(1)); ctx.lineTo(X(Math.min(kmax, ymax)), Y(Math.min(kmax, ymax))); ctx.stroke();
    ctx.setLineDash([]);
    // вертикаль «N ядер»: одна общая (серая), если число ядер у всех одинаковое
    const same = series.length > 1 && series.every((s) => s.cores === series[0].cores);
    const marks = same ? [{ cores: series[0].cores, c: MU }] : series.map((s) => ({ cores: s.cores, c: COL[s.vendor] || COL.other }));
    marks.forEach((m, i) => {
      if (!m.cores || m.cores >= kmax) return;
      ctx.strokeStyle = m.c + "55"; ctx.lineWidth = 2;
      ctx.beginPath(); ctx.moveTo(X(m.cores), box.t); ctx.lineTo(X(m.cores), box.b); ctx.stroke();
      ctx.fillStyle = m.c; ctx.textAlign = "center";
      ctx.fillText(`${m.cores} ядер`, X(m.cores), box.t - 4 - i * 13);
    });
    series.forEach((s, si) => {
      const c = COL[s.vendor] || COL.other;
      const pts = s.scaling || [];
      ctx.strokeStyle = c; ctx.lineWidth = 2.5; ctx.lineJoin = "round";
      ctx.beginPath();
      pts.forEach((p, i) => (i ? ctx.lineTo(X(p.k), Y(p.speedup)) : ctx.moveTo(X(p.k), Y(p.speedup))));
      ctx.stroke();
      pts.forEach((p) => {
        ctx.fillStyle = BG; ctx.strokeStyle = c; ctx.lineWidth = 2;
        ctx.beginPath(); ctx.arc(X(p.k), Y(p.speedup), 3.5, 0, 7); ctx.fill(); ctx.stroke();
      });
      const last = pts[pts.length - 1];
      if (last) {
        ctx.fillStyle = c; ctx.textAlign = "right"; ctx.font = BOLD;
        ctx.fillText("×" + fmt(last.speedup), X(last.k) - 8, Y(last.speedup) + (si ? 18 : -10));
        ctx.font = FONT;
      }
    });
    legend(ctx, series, w);
  }

  function marathon(cv, series, secondsHint) {
    if (!cv) return;
    const { ctx, w, h } = setup(cv);
    const data = series.map((s) => (s.marathon && s.marathon.series) || []);
    const n = Math.max(secondsHint || 0, ...data.map((d) => d.length), 1);
    const all = data.flat();
    if (!all.length) return empty(ctx, h);
    const ymax = Math.max(...all) * 1.15;
    const box = { l: 52, t: 40, r: w - 10, b: h - 38 };
    const X = (i) => box.l + ((i + 0.5) / n) * (box.r - box.l);
    const Y = (v) => box.b - (v / ymax) * (box.b - box.t);
    const xt = [];
    for (let i = 0; i <= n; i += n > 15 ? 5 : 2) xt.push(i);
    axes(ctx, box, n, ymax, "секунды", "млн итераций/с", xt, nice(ymax), (v) => box.l + (v / n) * (box.r - box.l));
    series.forEach((s, si) => {
      const d = data[si];
      if (!d.length) return;
      const c = COL[s.vendor] || COL.other;
      ctx.fillStyle = c + "1c";
      ctx.beginPath(); ctx.moveTo(X(0), box.b);
      d.forEach((v, i) => ctx.lineTo(X(i), Y(v)));
      ctx.lineTo(X(d.length - 1), box.b); ctx.closePath(); ctx.fill();
      ctx.strokeStyle = c; ctx.lineWidth = 2.5; ctx.lineJoin = "round";
      ctx.beginPath();
      d.forEach((v, i) => (i ? ctx.lineTo(X(i), Y(v)) : ctx.moveTo(X(i), Y(v))));
      ctx.stroke();
    });
    legend(ctx, series, w);
  }

  return { scaling, marathon, COL };
})();
