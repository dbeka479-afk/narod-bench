import re

from django import template

register = template.Library()


@register.filter
def vendor_name(v):
    return {"intel": "Intel", "amd": "AMD", "apple": "Apple"}.get(v, "CPU")


@register.filter
def short_cpu(name):
    """«AMD Ryzen 7 6800H» → «Ryzen 7 6800H»: фирма и так написана отдельно."""
    return re.sub(r"^(AMD|Intel|Apple)\s+", "", name or "", flags=re.I)


@register.filter
def ru(x, d=0):
    """Число по-русски: 12 345,6."""
    if x is None or x == "":
        return "—"
    try:
        s = f"{float(x):,.{int(d)}f}"
    except (TypeError, ValueError):
        return "—"
    return s.replace(",", " ").replace(".", ",")


@register.filter
def ghz(x):
    """4.75 → «4,75»; 5.0 → «5»."""
    if x is None:
        return "—"
    return f"{float(x):.2f}".rstrip("0").rstrip(".").replace(".", ",")


@register.filter
def signed(x, d=1):
    """Изменение со знаком: −8,0."""
    if x is None:
        return "—"
    return f"{float(x):+.{int(d)}f}".replace(".", ",").replace("-", "−")


@register.filter
def pct_of(x, total):
    try:
        return round(100 * float(x) / float(total)) if total else 0
    except (TypeError, ValueError):
        return 0


@register.filter
def neg(x):
    return -x if x is not None else None
