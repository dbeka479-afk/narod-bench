"""Проверка результата, который прислал браузер. Очки пересчитываются здесь, на сервере,
по скоростям — чтобы у всех они считались одинаково и их нельзя было просто вписать."""
import math
import uuid

from .engine import cpus, meta

BROKEN = "Результат повреждён — запустите тест ещё раз."
FAKE = "Результат не похож на настоящий замер — запустите тест ещё раз."

# Пределы правдоподобия: очки одного потока в одном тесте не больше 8 эталонных ядер Ryzen 7 6800H.
MAX_SCORE_PER_THREAD = 8000


def geomean(xs):
    xs = [x for x in xs if x > 0]
    return math.exp(sum(math.log(x) for x in xs) / len(xs)) if xs else 0.0


def _f(x, lo=0.0, hi=1e9):
    v = float(x)
    if not math.isfinite(v) or not lo <= v <= hi:
        raise ValueError(x)
    return v


def _opt(x, lo, hi, nd=2):
    """Необязательное число в пределах; всё странное превращается в None."""
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return round(v, nd) if math.isfinite(v) and lo <= v <= hi else None


def _s(x, n):
    return " ".join(str(x or "").split())[:n]


def _check(x):
    return x if isinstance(x, (int, float)) and math.isfinite(x) else None


def _power(p):
    p = p if isinstance(p, dict) else {}
    battery = p.get("battery")
    return dict(battery=battery if isinstance(battery, bool) else None,
                plugged=p.get("plugged") if isinstance(p.get("plugged"), bool) else None,
                percent=round(_f(p["percent"], 0, 100)) if p.get("percent") is not None else None)


def _score(key, rate):
    return round(1000 * rate / meta.REF[key], 1)


def _cpu(s):
    """Процессор: из справочника по ключу, иначе вписанный от руки (и, если получится, узнанный по названию)."""
    known = cpus.get(s.get("cpu_key"))
    if not known:
        known = cpus.match(s.get("cpu"))
    if known:
        return known["key"], known["name"], known["vendor"]
    name = _s(s.get("cpu"), 120) or "Неизвестный процессор"
    return "", name, cpus.vendor_of_text(name)


def clean(p):
    if not isinstance(p, dict) or p.get("format") != meta.FORMAT:
        raise ValueError("Страница устарела — обновите её (Ctrl+F5) и запустите тест ещё раз.")
    try:
        s = p["system"]
        threads = int(_f(s["threads"], 1, 512))
        key, cpu_name, vendor = _cpu(s)
        system = dict(
            cpu_key=key, cpu=cpu_name, vendor=vendor,
            threads=threads, cores=int(_f(s.get("cores") or threads, 1, threads)), cores_est=bool(s.get("cores_est")),
            browser=_s(s.get("browser"), 40), engine=_s(s.get("engine"), 20), os=_s(s.get("os"), 20),
            gpu=_s(s.get("gpu"), 160), power=_power(s.get("power")),
            ram=_opt(s.get("ram"), 0.1, 4096),  # ГБ, как сообщил браузер: округлено вниз, обычно не больше 8
        )
        single, multi = {}, {}
        for k in meta.KEYS:
            a, b = p["single"][k], p["multi"][k]
            rs, rm = _f(a["rate"], 1e-9), _f(b["rate"], 1e-9)
            single[k] = dict(rate=round(rs, 4), score=_score(k, rs), check=_check(a.get("check")))
            multi[k] = dict(rate=round(rm, 4), score=_score(k, rm), speedup=round(rm / rs, 2), check=_check(b.get("check")))
        scaling = [dict(k=int(_f(x["k"], 1, 1024)), rate=round(_f(x["rate"]), 4), speedup=round(_f(x["speedup"]), 2))
                   for x in (p.get("scaling") or [])[:40]]
        series = [round(_f(v), 3) for v in ((p.get("marathon") or {}).get("series") or [])[:120]]
        duration = round(_f(p.get("duration") or 0, 0, 3600), 1)
    except (KeyError, TypeError, ValueError, AttributeError):
        raise ValueError(BROKEN) from None

    # правдоподобие: один поток не может быть быстрее нескольких эталонных ядер, все потоки — быстрее суммы
    for k in meta.KEYS:
        if single[k]["score"] > MAX_SCORE_PER_THREAD or multi[k]["score"] > MAX_SCORE_PER_THREAD * threads:
            raise ValueError(FAKE)
        # «Память» не проверяем: на всех потоках блоки меньше и могут поместиться в кэш
        if k != "mem" and multi[k]["speedup"] > threads * 1.5 + 1:
            raise ValueError(FAKE)

    f = p.get("freq") if isinstance(p.get("freq"), dict) else {}
    freq = dict(single=_opt(f.get("single"), 0.2, 8.0), multi=_opt(f.get("multi"), 0.2, 8.0),
                hot=_opt(f.get("hot"), 0.2, 8.0))
    g = p.get("fps") if isinstance(p.get("fps"), dict) else {}
    fps = dict(fps=_opt(g.get("fps"), 0.1, 20000, 1), objects=meta.FPS_OBJECTS)

    head = sum(series[:3]) / len(series[:3]) if series else 0
    tail = sum(series[-3:]) / len(series[-3:]) if series else 0
    marathon = dict(seconds=len(series), series=series, start=round(head, 3), end=round(tail, 3),
                    drop=round(100 * (1 - tail / head), 1) if head else 0.0)
    return dict(
        format=meta.FORMAT, uid=_s(p.get("uid"), 40) or uuid.uuid4().hex, device=_s(p.get("device"), 40),
        name=_s(p.get("name"), 40) or "Аноним", duration=duration, hidden=bool(p.get("hidden")),
        system=system, single=single, multi=multi, scaling=scaling, marathon=marathon, freq=freq, fps=fps,
        scores=dict(single=round(geomean([v["score"] for v in single.values()]), 1),
                    multi=round(geomean([v["score"] for v in multi.values()]), 1)),
    )
