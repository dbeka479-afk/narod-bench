import hashlib
import json

from django.core.cache import cache
from django.db.models import Count
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.templatetags.static import static
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from . import payload
from .engine import analysis, cpus, meta
from .models import Result

ASSET_V = "7"

# Защита топа от засорения: не больше SAVE_LIMIT сохранений с одного адреса за SAVE_WINDOW секунд.
SAVE_LIMIT, SAVE_WINDOW = 8, 15 * 60


def _cfg():
    return dict(
        format=meta.FORMAT, ref=meta.REF, worker=static("bench/js/worker.js") + "?v=" + ASSET_V,
        fps_objects=meta.FPS_OBJECTS,
        tests=[dict(key=t["key"], code=t["code"], title=t["title"], unit=t["unit"]) for t in meta.TESTS],
        catalog=cpus.for_browser(), gpu_rules=cpus.GPU_RULES, model_rules=cpus.MODEL_RULES,
    )


def home(request):
    stats = Result.objects.aggregate(runs=Count("id"), cpus=Count("cpu", distinct=True))
    return render(request, "bench/home.html", {"nav": "home", "cfg": _cfg(), "stats": stats})


def detail(request, pk):
    r = get_object_or_404(Result, pk=pk)
    return render(request, "bench/detail.html", {"nav": "", "r": r, "p": r.data, "a": analysis.build(r)})


def top(request):
    sort = request.GET.get("sort") if request.GET.get("sort") in analysis.SORTS else "multi"
    view = request.GET.get("view") if request.GET.get("view") in analysis.VIEWS else "cpu"
    rows = analysis.leaderboard(sort, view)[:200]
    return render(request, "bench/top.html", {
        "nav": "top", "rows": rows, "sort": sort, "view": view,
        "sorts": analysis.SORTS.items(), "views": analysis.VIEWS.items(),
    })


def _client_ip(request):
    fwd = request.META.get("HTTP_X_FORWARDED_FOR", "")
    return (fwd.split(",")[0].strip() if fwd else request.META.get("REMOTE_ADDR", "")) or "?"


def _too_many(request):
    """Простой счётчик в памяти сервера. IP не сохраняется — только его хэш, и только на 15 минут."""
    key = "save:" + hashlib.sha256(_client_ip(request).encode()).hexdigest()[:24]
    n = cache.get(key, 0)
    if n >= SAVE_LIMIT:
        return True
    cache.set(key, n + 1, SAVE_WINDOW)
    return False


@csrf_exempt  # JSON от нашей же страницы, без cookie
@require_POST
def api_save(request):
    try:
        raw = json.loads(request.body or b"{}")
    except ValueError:  # не JSON (в том числе битая кодировка)
        return JsonResponse({"error": payload.BROKEN}, status=400)
    try:
        data = payload.clean(raw)
    except ValueError as exc:
        return JsonResponse({"error": str(exc)}, status=400)
    if not Result.objects.filter(uid=data["uid"]).exists() and _too_many(request):
        return JsonResponse({"error": "Слишком много замеров подряд. Подождите 15 минут и попробуйте снова."},
                            status=429)
    s = data["system"]
    r, _ = Result.objects.update_or_create(uid=data["uid"], defaults=dict(
        device=data["device"], name=data["name"], cpu_key=s["cpu_key"], cpu=s["cpu"], vendor=s["vendor"],
        threads=s["threads"], engine=s["engine"],
        single=data["scores"]["single"], multi=data["scores"]["multi"], fps=data["fps"]["fps"],
        freq=data["freq"]["single"], freq_all=data["freq"]["multi"], drop=data["marathon"]["drop"], data=data))
    return JsonResponse({"id": r.id, "url": f"/r/{r.id}/", "single": r.single, "multi": r.multi})
