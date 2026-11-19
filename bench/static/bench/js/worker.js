/* Рабочий поток бенчмарка (Web Worker). Выполняет настоящую работу на одном потоке процессора
   того компьютера, где открыта страница. Главная страница запускает столько таких потоков,
   сколько потоков у процессора.

   Каждый тест — функция «одной порции работы»: возвращает [единицы работы, контрольная сумма].
   Порции одинаковые на всех компьютерах, поэтому контрольные суммы должны совпадать. */
"use strict";

// --- генератор случайных чисел с фиксированным зерном: у всех одинаковые данные ---
function rng(seed) {
  let s = seed >>> 0 || 1;
  return () => {
    s ^= s << 13; s >>>= 0;
    s ^= s >>> 17;
    s ^= s << 5; s >>>= 0;
    return s / 4294967296;
  };
}

// --- 1. Целые числа: гипотеза Коллатца для 1…60 000 ---
function tInt() {
  let steps = 0;
  for (let i = 1; i < 60000; i++) {
    let x = i;
    while (x !== 1) {
      x = x % 2 === 0 ? x / 2 : 3 * x + 1;
      steps++;
    }
  }
  return [steps / 1e6, steps];
}

// --- 2. Дробные числа: фрактал Мандельброта 240×240, до 100 итераций на точку ---
function tFloat() {
  const size = 240, maxIter = 100;
  let it = 0;
  for (let py = 0; py < size; py++) {
    const ci = -1.2 + (2.4 * py) / size;
    for (let px = 0; px < size; px++) {
      const cr = -2.1 + (2.8 * px) / size;
      let zr = 0, zi = 0, k = 0;
      while (k < maxIter && zr * zr + zi * zi < 4) {
        const t = zr * zr - zi * zi + cr;
        zi = 2 * zr * zi + ci;
        zr = t;
        k++;
      }
      it += k;
    }
  }
  return [it / 1e6, it];
}

// --- 3. Сортировка 200 000 случайных чисел ---
function tSort() {
  const n = 200000, r = rng(42), a = new Float64Array(n);
  for (let i = 0; i < n; i++) a[i] = r();
  a.sort();
  return [n / 1e6, Math.floor(a[n >> 1] * 1e9)];
}

// --- 4. Сжатие: deflate 4 МБ текста и обратно (встроенный в браузер zlib) ---
let TEXT = null;
function makeText(mb) {
  const r = rng(7), abc = "abcdefghijklmnopqrstuvwxyz ", words = [], parts = [];
  for (let i = 0; i < 800; i++) {
    let w = "";
    const len = 3 + Math.floor(r() * 7);
    for (let j = 0; j < len; j++) w += abc[Math.floor(r() * abc.length)];
    words.push(w);
  }
  for (let i = 0; i < 20000; i++) parts.push(words[Math.floor(r() * words.length)]);
  const chunk = new TextEncoder().encode(parts.join(" "));
  const out = new Uint8Array(mb << 20);
  for (let o = 0; o < out.length; o += chunk.length) out.set(chunk.subarray(0, Math.min(chunk.length, out.length - o)), o);
  return out;
}
async function through(bytes, transform) {
  const src = new ReadableStream({ start(c) { c.enqueue(bytes); c.close(); } });
  return new Uint8Array(await new Response(src.pipeThrough(transform)).arrayBuffer());
}
async function tZip() {
  if (typeof CompressionStream === "undefined") throw new Error("Браузер не умеет сжимать данные (нет CompressionStream) — обновите его.");
  if (!TEXT) TEXT = makeText(4);
  const packed = await through(TEXT, new CompressionStream("deflate"));
  const back = await through(packed, new DecompressionStream("deflate"));
  return [8, packed.length + back.length]; // 4 МБ сжали + 4 МБ распаковали
}

// --- 5. SHA-256 от 4 МБ (честная реализация на JavaScript: у всех одинаковая) ---
const K = new Uint32Array([
  0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
  0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
  0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
  0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
  0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13, 0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
  0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
  0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
  0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208, 0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2,
]);
const W = new Uint32Array(64);
function shaBlock(H, dv, o) {
  for (let i = 0; i < 16; i++) W[i] = dv.getUint32(o + i * 4);
  for (let i = 16; i < 64; i++) {
    const a = W[i - 15], b = W[i - 2];
    const s0 = ((a >>> 7) | (a << 25)) ^ ((a >>> 18) | (a << 14)) ^ (a >>> 3);
    const s1 = ((b >>> 17) | (b << 15)) ^ ((b >>> 19) | (b << 13)) ^ (b >>> 10);
    W[i] = (W[i - 16] + s0 + W[i - 7] + s1) | 0;
  }
  let a = H[0], b = H[1], c = H[2], d = H[3], e = H[4], f = H[5], g = H[6], h = H[7];
  for (let i = 0; i < 64; i++) {
    const S1 = ((e >>> 6) | (e << 26)) ^ ((e >>> 11) | (e << 21)) ^ ((e >>> 25) | (e << 7));
    const t1 = (h + S1 + ((e & f) ^ (~e & g)) + K[i] + W[i]) | 0;
    const S0 = ((a >>> 2) | (a << 30)) ^ ((a >>> 13) | (a << 19)) ^ ((a >>> 22) | (a << 10));
    const t2 = (S0 + ((a & b) ^ (a & c) ^ (b & c))) | 0;
    h = g; g = f; f = e; e = (d + t1) | 0; d = c; c = b; b = a; a = (t1 + t2) | 0;
  }
  H[0] += a; H[1] += b; H[2] += c; H[3] += d; H[4] += e; H[5] += f; H[6] += g; H[7] += h;
}
function sha256(bytes) {
  const H = new Uint32Array([0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a, 0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19]);
  const n = bytes.length, full = n >> 6;
  const dv = new DataView(bytes.buffer, bytes.byteOffset, n);
  for (let i = 0; i < full; i++) shaBlock(H, dv, i * 64);
  const rest = n - full * 64;
  const tail = new Uint8Array(rest + 9 <= 64 ? 64 : 128);
  tail.set(bytes.subarray(full * 64));
  tail[rest] = 0x80;
  const tv = new DataView(tail.buffer);
  tv.setUint32(tail.length - 8, Math.floor((n * 8) / 4294967296));
  tv.setUint32(tail.length - 4, (n * 8) >>> 0);
  for (let o = 0; o < tail.length; o += 64) shaBlock(H, tv, o);
  return H;
}
let SHA_DATA = null;
function tSha() {
  if (!SHA_DATA) {
    SHA_DATA = new Uint8Array(4 << 20);
    for (let i = 0; i < SHA_DATA.length; i++) SHA_DATA[i] = i & 255;
  }
  return [4, sha256(SHA_DATA)[0]];
}

// --- 6. JSON: 15 000 записей туда и обратно ---
function tJson() {
  const n = 15000, r = rng(3), rows = new Array(n);
  for (let i = 0; i < n; i++) rows[i] = { id: i, name: "user" + i, score: r(), tags: ["a", "b", String(i % 7)], ok: i % 3 === 0 };
  const s = JSON.stringify(rows);
  const back = JSON.parse(s);
  return [n / 1000, s.length + back.length];
}

// --- 7. Память: копирование блока (32 МБ на одном потоке, по 8 МБ на каждом при всех потоках) ---
let MEM = null;
function tMem(opt) {
  const mb = (opt && opt.mb) || 32, reps = 8;
  if (!MEM || MEM.mb !== mb) {
    const src = new Uint8Array(mb << 20);
    for (let i = 0; i < src.length; i += 4096) src[i] = 1;
    MEM = { mb, src, dst: new Uint8Array(mb << 20) };
  }
  for (let i = 0; i < reps; i++) MEM.dst.set(MEM.src);
  return [(mb * reps) / 1024, MEM.dst[4096]];
}

const TESTS = { int: tInt, float: tFloat, sort: tSort, zip: tZip, sha: tSha, json: tJson, mem: tMem };
const now = () => performance.now();

// --- Частота (оценка). Цепочка из 32 зависимых операций «сложить» и «исключающее ИЛИ»:
//     каждая ждёт результата предыдущей и занимает ровно 1 такт. Значит, операций в секунду ≈ тактов в секунду.
//     Проверено на Ryzen 7 6800H: оценка совпала с частотой из счётчиков Windows (≈3,4 ГГц) с точностью до 2–4 %.
function freqKernel(n, b, c) {
  let a = 1;
  for (let i = 0; i < n; i++) {
    a = (a + b) | 0; a ^= c; a = (a + b) | 0; a ^= c; a = (a + b) | 0; a ^= c; a = (a + b) | 0; a ^= c;
    a = (a + b) | 0; a ^= c; a = (a + b) | 0; a ^= c; a = (a + b) | 0; a ^= c; a = (a + b) | 0; a ^= c;
    a = (a + b) | 0; a ^= c; a = (a + b) | 0; a ^= c; a = (a + b) | 0; a ^= c; a = (a + b) | 0; a ^= c;
    a = (a + b) | 0; a ^= c; a = (a + b) | 0; a ^= c; a = (a + b) | 0; a ^= c; a = (a + b) | 0; a ^= c;
  }
  return a;
}
function measureFreq(ms) {
  let sink = 0, n = 20000;
  const tw = now();
  while (now() - tw < 150) sink ^= freqKernel(n, 3, 5); // разогрев: JIT компилирует цикл
  // порция ≈ 15 мс — точности таймера браузера (0,1–1 мс) хватает
  for (;;) {
    const a = now();
    sink ^= freqKernel(n, 3, 5);
    if (now() - a >= 15 || n > 1e8) break;
    n *= 2;
  }
  const ghz = [];
  const t0 = now();
  while (now() - t0 < ms) {
    const a = now();
    sink ^= freqKernel(n, 3, 5);
    const dt = now() - a;
    if (dt > 0) ghz.push((n * 32) / dt / 1e6);
  }
  ghz.sort((x, y) => x - y);
  // 75-й процентиль: отбрасываем порции, которые прервала система
  return { ghz: ghz.length ? ghz[Math.floor(ghz.length * 0.75)] : 0, n: ghz.length, check: sink };
}

// --- Игровая сцена: стая (boids). Каждый объект ищет соседей через сетку, держит дистанцию,
//     выравнивает скорость и тянется к центру группы — так считают ботов, толпу и частицы в играх.
//     Один кадр = один шаг всей стаи. Сцена каждые 120 кадров начинается заново из одного и того же
//     состояния, поэтому все компьютеры считают одинаковую работу.
let FLOCK = null;
function makeFlock(N) {
  const W = 1600, H = 900, R = 24, gw = Math.ceil(W / R), gh = Math.ceil(H / R);
  return { N, W, H, R, gw, gh, x: new Float64Array(N), y: new Float64Array(N), vx: new Float64Array(N),
    vy: new Float64Array(N), nx: new Float64Array(N), ny: new Float64Array(N), cell: new Int32Array(N),
    start: new Int32Array(gw * gh + 1), fill: new Int32Array(gw * gh), order: new Int32Array(N) };
}
function flockReset(S) {
  const r = rng(11);
  for (let i = 0; i < S.N; i++) {
    S.x[i] = r() * S.W; S.y[i] = r() * S.H;
    const a = r() * 6.283185;
    S.vx[i] = Math.cos(a) * 2; S.vy[i] = Math.sin(a) * 2;
  }
}
function flockStep(S) {
  const { N, W, H, R, gw, gh, x, y, vx, vy, nx, ny, cell, start, fill, order } = S;
  const cells = gw * gh;
  start.fill(0);
  for (let i = 0; i < N; i++) {
    const c = ((y[i] / R) | 0) * gw + ((x[i] / R) | 0);
    cell[i] = c; start[c + 1]++;
  }
  for (let c = 0; c < cells; c++) start[c + 1] += start[c];
  for (let c = 0; c < cells; c++) fill[c] = start[c];
  for (let i = 0; i < N; i++) order[fill[cell[i]]++] = i;
  const R2 = R * R, SEP2 = R * 0.4 * (R * 0.4), HW = W / 2, HH = H / 2;
  for (let i = 0; i < N; i++) {
    const xi = x[i], yi = y[i], cx = (xi / R) | 0, cy = (yi / R) | 0;
    let n = 0, ax = 0, ay = 0, px = 0, py = 0, sx = 0, sy = 0;
    for (let dy = -1; dy <= 1; dy++) {
      let gy = cy + dy;
      if (gy < 0) gy += gh; else if (gy >= gh) gy -= gh;
      for (let dx = -1; dx <= 1; dx++) {
        let gx = cx + dx;
        if (gx < 0) gx += gw; else if (gx >= gw) gx -= gw;
        const c = gy * gw + gx, e = start[c + 1];
        for (let k = start[c]; k < e; k++) {
          const j = order[k];
          if (j === i) continue;
          let ddx = x[j] - xi, ddy = y[j] - yi;
          if (ddx > HW) ddx -= W; else if (ddx < -HW) ddx += W;
          if (ddy > HH) ddy -= H; else if (ddy < -HH) ddy += H;
          const d2 = ddx * ddx + ddy * ddy;
          if (d2 < R2) {
            n++; ax += vx[j]; ay += vy[j]; px += ddx; py += ddy;
            if (d2 < SEP2) { const inv = 1 / (d2 + 1e-6); sx -= ddx * inv; sy -= ddy * inv; }
          }
        }
      }
    }
    let ux = vx[i], uy = vy[i];
    if (n > 0) {
      ux += (ax / n - ux) * 0.05 + (px / n) * 0.002 + sx * 0.9;
      uy += (ay / n - uy) * 0.05 + (py / n) * 0.002 + sy * 0.9;
    }
    const sp = Math.sqrt(ux * ux + uy * uy) || 1, lim = sp > 3 ? 3 / sp : sp < 1 ? 1 / sp : 1;
    nx[i] = ux * lim; ny[i] = uy * lim;
  }
  let chk = 0;
  for (let i = 0; i < N; i++) {
    vx[i] = nx[i]; vy[i] = ny[i];
    let a = x[i] + vx[i], b = y[i] + vy[i];
    if (a < 0) a += W; else if (a >= W) a -= W;
    if (b < 0) b += H; else if (b >= H) b -= H;
    x[i] = a; y[i] = b; chk += a;
  }
  return chk;
}
function runFps(m) {
  const N = m.objects || 10000, SHOW = Math.min(N, 2500);
  if (!FLOCK || FLOCK.N !== N) FLOCK = makeFlock(N);
  const S = FLOCK;
  flockReset(S);
  const tw = now();
  while (now() - tw < (m.warm || 0)) flockStep(S);
  flockReset(S);
  let frames = 0, f = 0, check = 0, tickFrames = 0;
  const t0 = now();
  let lastTick = t0;
  do {
    check = flockStep(S);
    frames++; tickFrames++;
    if (++f === 120) { f = 0; flockReset(S); }
    const t = now();
    if (t - lastTick >= 120) { // кадр для предпросмотра: координаты части стаи
      const pts = new Float32Array(SHOW * 2);
      for (let i = 0; i < SHOW; i++) { pts[2 * i] = S.x[i] / S.W; pts[2 * i + 1] = S.y[i] / S.H; }
      self.postMessage({ type: "tick", fps: (tickFrames * 1000) / (t - lastTick), pts }, [pts.buffer]);
      tickFrames = 0; lastTick = t;
    }
  } while (now() - t0 < m.ms);
  return { type: "done", units: frames, sec: (now() - t0) / 1000, check: Math.round(check) };
}

// Команды: { cmd: "run", key, warm, ms, opt, ticks } · { cmd: "freq", ms } · { cmd: "fps", objects, warm, ms } · { cmd: "free" }
self.onmessage = async (e) => {
  const m = e.data;
  try {
    if (m.cmd === "free") {
      MEM = null; TEXT = null; SHA_DATA = null; FLOCK = null;
      self.postMessage({ type: "ok" });
      return;
    }
    if (m.cmd === "freq") {
      self.postMessage({ type: "done", ...measureFreq(m.ms) });
      return;
    }
    if (m.cmd === "fps") {
      self.postMessage(runFps(m));
      return;
    }
    const fn = TESTS[m.key];
    if (!fn) throw new Error("Нет теста " + m.key);
    const tw = now();
    while (now() - tw < (m.warm || 0)) await fn(m.opt); // разогрев: JIT-компилятор успевает оптимизировать код
    let units = 0, check = 0, n = 0, acc = 0;
    const t0 = now();
    let lastTick = t0;
    do {
      const r = await fn(m.opt);
      units += r[0];
      check = r[1];
      n++;
      if (m.ticks) { // для марафона: отчёт раз в 0,1 с, чтобы не заваливать страницу сообщениями
        acc += r[0];
        if (now() - lastTick >= 100) { self.postMessage({ type: "tick", units: acc }); acc = 0; lastTick = now(); }
      }
    } while (now() - t0 < m.ms);
    self.postMessage({ type: "done", units, sec: (now() - t0) / 1000, check, n });
  } catch (err) {
    self.postMessage({ type: "error", message: String((err && err.message) || err) });
  }
};
