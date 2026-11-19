"""Разбор одного замера для страницы «Результат» и сборка общего топа.

«Не ослаб ли процессор» — честные проверки, которые можно сделать из браузера:
сравнение с такими же процессорами у других посетителей, оценка частоты против паспортной
турбо-частоты, падение скорости под долгой нагрузкой (нагрев), питание и прошлые замеры
этого же компьютера. Сам кристалл почти не изнашивается — слабеют охлаждение и настройки питания."""
from statistics import median

from . import cpus, meta

SORTS = {"multi": "Все ядра", "single": "Одно ядро", "fps": "FPS", "eff": "Очков на ватт"}
VIEWS = {"cpu": "Процессоры", "runs": "Все замеры"}
LEVEL = {"bad": 3, "warn": 2, "ok": 1, "info": 0}


def num(x, d=1):
    return f"{x:.{d}f}".replace(".", ",").replace("-", "−")


def efficiency(multi, passport):
    """Очки «все ядра» на ватт паспортного TDP."""
    if passport and passport.get("tdp") and multi:
        return round(multi / passport["tdp"], 1)
    return None


def _pct_below(value, values):
    values = [v for v in values if v is not None]
    if value is None or not values:
        return None
    return round(100 * sum(v < value for v in values) / len(values))


# ---------------------------------------------------------------- топ

def _rows():
    from ..models import Result
    rows = list(Result.objects.values("id", "name", "cpu_key", "cpu", "vendor", "threads", "single", "multi",
                                      "fps", "freq", "freq_all", "drop", "created", "device", "engine"))
    for r in rows:
        r["passport"] = cpus.get(r["cpu_key"])
        r["eff"] = efficiency(r["multi"], r["passport"])
        r["group"] = r["cpu_key"] or "x:" + r["cpu"].lower()
    return rows


def _desc(key):
    """Сортировка по убыванию; у кого нет значения — в конце."""
    return lambda r: (r.get(key) is not None, r.get(key) or 0)


def leaderboard(sort="multi", view="cpu", rows=None):
    sort = sort if sort in SORTS else "multi"
    rows = _rows() if rows is None else rows
    if view == "runs":
        return sorted(rows, key=_desc(sort), reverse=True)
    groups = {}
    for r in rows:
        g = groups.setdefault(r["group"], dict(group=r["group"], cpu=r["cpu"], cpu_key=r["cpu_key"],
                                               vendor=r["vendor"], passport=r["passport"], runs=[]))
        g["runs"].append(r)
    out = []
    for g in groups.values():
        runs = g.pop("runs")
        for k in ("multi", "single", "fps", "eff", "freq"):
            vals = [x[k] for x in runs if x[k] is not None]
            g[k] = max(vals) if vals else None
        g["median"] = median(x["multi"] for x in runs)
        g["count"] = len(runs)
        g["devices"] = len({x["device"] or x["id"] for x in runs})
        g["best_id"] = max(runs, key=_desc(sort))["id"]
        out.append(g)
    return sorted(out, key=_desc(sort), reverse=True)


# ---------------------------------------------------------------- один результат

def _scale_at(p, k):
    return next((x for x in p.get("scaling", []) if x["k"] == k), None)


def smt_gain(p):
    """Сколько добавили вторые потоки ядер (Hyper-Threading / SMT)."""
    s = p["system"]
    c, t = _scale_at(p, s["cores"]), _scale_at(p, s["threads"])
    if c and t and s["threads"] > s["cores"] and c["rate"]:
        return t["rate"] / c["rate"] - 1
    return None


def tests_profile(p):
    """Тесты с полосками и сильные/слабые стороны относительно собственного среднего уровня."""
    mx_s = max(p["single"][k]["score"] for k in meta.KEYS) or 1
    mx_m = max(p["multi"][k]["score"] for k in meta.KEYS) or 1
    avg = p["scores"]["single"] or 1
    tests = []
    for t in meta.TESTS:
        s, m = p["single"][t["key"]], p["multi"][t["key"]]
        tests.append(dict(t, s=s, m=m, sw=round(100 * s["score"] / mx_s), mw=round(100 * m["score"] / mx_m),
                          rel=s["score"] / avg))
    ranked = sorted(tests, key=lambda t: -t["rel"])
    strong = [t for t in ranked[:2] if t["rel"] >= 1.05]
    weak = [t for t in ranked[-1:] if t["rel"] <= 0.95]
    for t in tests:
        t["tag"] = "strong" if t in strong else "weak" if t in weak else ""
    return tests, strong, weak


def _check(level, title, text):
    return dict(level=level, title=title, text=text)


def health(r, passport, same_vals, history):
    """Проверки «не ослаб ли процессор» и общий вывод."""
    p = r.data
    checks = []
    name = passport["name"] if passport else r.cpu

    # 1. такие же процессоры у других посетителей
    if same_vals:
        med = median(same_vals)
        ratio = r.multi / med if med else 0
        pct, n = round(ratio * 100), len(same_vals)
        base = f"{pct}% от среднего для {name} на сайте (замеров с других компьютеров: {n})."
        if ratio >= 1.1:
            checks.append(_check("ok", "Сильнее таких же процессоров", base))
        elif ratio >= 0.9:
            checks.append(_check("ok", "Как у других с таким же процессором", base))
        elif ratio >= 0.75:
            checks.append(_check("warn", "Чуть слабее таких же процессоров",
                                 base + " Бывает из-за режима питания, фоновых программ или другого браузера."))
        else:
            checks.append(_check("bad", "Заметно слабее таких же процессоров",
                                 base + " Частые причины: пыль и высохшая термопаста, режим экономии энергии, "
                                        "работа от батареи."))
    else:
        checks.append(_check("info", "Сравнить пока не с кем",
                             f"Вы первый с {name} на сайте. Когда его проверят другие, здесь появится сравнение."))

    # 2. частота против паспортной турбо-частоты
    f = (p.get("freq") or {}).get("single")
    boost = passport and passport.get("boost")
    if f and boost:
        ratio = f / boost
        boost_txt = f"{boost:.2f}".rstrip("0").rstrip(".").replace(".", ",")
        base = f"≈{num(f)} ГГц на одном ядре, по паспорту — до {boost_txt} ГГц."
        if ratio >= 0.85:
            checks.append(_check("ok", "Разгоняется до турбо-частоты", base))
        elif ratio >= 0.65:
            checks.append(_check("warn", "Не дотягивает до турбо-частоты",
                                 base + " Проверьте режим питания Windows («Максимальная производительность») "
                                        "и подключена ли зарядка."))
        else:
            checks.append(_check("bad", "Частота сильно ниже паспортной",
                                 base + " Похоже на энергосбережение, работу от батареи или свёрнутую вкладку."))
    elif f:
        checks.append(_check("info", "Частота измерена", f"≈{num(f)} ГГц на одном ядре. "
                                                          "Паспортной турбо-частоты для сравнения нет."))

    # 3. нагрев: падение скорости за марафон
    mar = p.get("marathon") or {}
    if mar.get("series"):
        drop = mar.get("drop") or 0
        hot, cold = (p.get("freq") or {}).get("hot"), (p.get("freq") or {}).get("multi")
        tail = f" Частота всех ядер: ≈{num(cold)} → ≈{num(hot)} ГГц." if hot and cold else ""
        sec = mar.get("seconds") or len(mar["series"])
        if drop < 8:
            checks.append(_check("ok", "Нагрев не мешает",
                                 f"За {sec} с полной нагрузки скорость изменилась на {num(-drop)}%.{tail}"))
        elif drop < 20:
            checks.append(_check("warn", "Под долгой нагрузкой скорость падает",
                                 f"За {sec} с — на {num(drop)}%: процессор упирается в лимит мощности или нагрев. "
                                 f"Для ноутбуков это частое явление.{tail}"))
        else:
            checks.append(_check("bad", "Сильный нагрев",
                                 f"За {sec} с скорость упала на {num(drop)}%. Охлаждению не хватает сил: почистите "
                                 f"от пыли, замените термопасту, не ставьте ноутбук на мягкое.{tail}"))

    # 4. условия замера
    pw = p["system"].get("power") or {}
    if pw.get("battery") and pw.get("plugged") is False:
        checks.append(_check("warn", "Работал от батареи",
                             "От батареи процессор обычно ограничен. Подключите зарядку и проверьте ещё раз."))
    if p.get("hidden"):
        checks.append(_check("warn", "Вкладку сворачивали",
                             "Свёрнутую вкладку браузер притормаживает — результат может быть ниже настоящего."))

    # 5. прошлые замеры этого же компьютера
    if history:
        best = max(history, key=lambda h: h.multi)
        ratio = r.multi / best.multi if best.multi else 0
        when = best.created.strftime("%d.%m.%Y")
        if ratio >= 0.9:
            checks.append(_check("ok", "Не хуже прошлых замеров",
                                 f"{round(ratio * 100)}% от вашего лучшего замера ({when})."))
        else:
            checks.append(_check("warn", "Слабее вашего прошлого замера",
                                 f"{round(ratio * 100)}% от вашего лучшего замера ({when}). Сравните условия: "
                                 f"зарядка, режим питания, открытые программы."))

    worst = max((LEVEL[c["level"]] for c in checks), default=0)
    verdict = {
        3: ("bad", "Похоже, процессор работает слабее, чем может"),
        2: ("warn", "В целом в порядке, но есть замечания"),
        1: ("ok", "Процессор не ослаб — работает как положено"),
        0: ("info", "Данных для вывода пока мало"),
    }[worst]
    return dict(level=verdict[0], title=verdict[1], checks=checks)


def build(r):
    """Всё для страницы результата."""
    from ..models import Result
    p = r.data
    passport = cpus.get(r.cpu_key)
    others = Result.objects.exclude(pk=r.pk)
    if r.device:
        others_dev = others.exclude(device=r.device)
    else:
        others_dev = others
    same = others_dev.filter(cpu_key=r.cpu_key) if r.cpu_key else others_dev.filter(cpu__iexact=r.cpu)
    same_vals = list(same.values_list("multi", flat=True))
    history = list(Result.objects.filter(device=r.device).exclude(pk=r.pk).order_by("-created")[:8]) if r.device else []

    rows = _rows()
    board = leaderboard("multi", "cpu", rows)
    rank = next((i + 1 for i, g in enumerate(board) if g["group"] == r.group), None)
    rest = [x for x in rows if x["id"] != r.id]

    tests, strong, weak = tests_profile(p)
    eff = efficiency(r.multi, passport)
    speedup = r.multi / r.single if r.single else None
    return dict(
        passport=passport, tests=tests, strong=strong, weak=weak, eff=eff,
        speedup=speedup, smt=smt_gain(p), health=health(r, passport, same_vals, history), history=history,
        rank=rank, groups=len(board), total=len(rows), tiles=range(min(r.threads, 64)),
        die_cols=r.threads if r.threads <= 8 else -(-min(r.threads, 64) // -(-min(r.threads, 64) // 8)),
        pct=dict(multi=_pct_below(r.multi, [x["multi"] for x in rest]),
                 single=_pct_below(r.single, [x["single"] for x in rest]),
                 fps=_pct_below(r.fps, [x["fps"] for x in rest])),
        chart=dict(scaling=p.get("scaling", []), marathon=p.get("marathon", {}), cores=p["system"]["cores"]),
    )
