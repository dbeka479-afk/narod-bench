import json
import socket

from django.core.cache import cache
from django.test import TestCase

from .engine import analysis, cpus, meta
from .management.commands.serve import DualStackServer
from .models import Result
from .payload import clean


def fake(name="Друг", cpu_key="amd-ryzen-7-6800h", cpu="AMD Ryzen 7 6800H", k=1.0, device=None, threads=16,
         drop_to=9, freq=4.5):
    """Результат в том виде, в каком его присылает браузер."""
    return dict(
        format=meta.FORMAT, uid=f"uid-{name}-{k}-{cpu_key}", device=device or f"dev-{name}", name=name, duration=62,
        system=dict(cpu_key=cpu_key, cpu=cpu, threads=threads, cores=threads // 2, browser="Edge 142", engine="V8",
                    os="Windows", gpu="ANGLE (AMD, AMD Radeon(TM) Graphics (0x00001681) Direct3D11)",
                    power=dict(battery=True, plugged=True, percent=90)),
        single={t: dict(rate=meta.REF[t] * k, check=1) for t in meta.KEYS},
        multi={t: dict(rate=meta.REF[t] * 8 * k, check=1) for t in meta.KEYS},
        scaling=[dict(k=n, rate=10.0 * (min(n, 8) + max(0, n - 8) * 0.0625),
                      speedup=float(min(n, 8) + max(0, n - 8) * 0.0625)) for n in (1, 2, 4, 8, 16)],
        marathon=dict(series=[10, 10, 10, drop_to, drop_to, drop_to]),
        freq=dict(single=freq, multi=3.9, hot=3.7), fps=dict(fps=150 * k),
    )


class CatalogTests(TestCase):
    def test_catalog_is_consistent(self):
        self.assertGreater(len(cpus.CATALOG), 150)
        for c in cpus.CATALOG.values():
            self.assertIn(c["vendor"], ("intel", "amd", "apple"), c["name"])
            self.assertGreaterEqual(c["threads"], c["cores"], c["name"])
            if c["base"] and c["boost"]:
                self.assertLessEqual(c["base"], c["boost"], c["name"])

    def test_match_free_text(self):
        self.assertEqual(cpus.match("AMD Ryzen 7 6800H with Radeon Graphics")["key"], "amd-ryzen-7-6800h")
        self.assertEqual(cpus.match("i7-12700K")["key"], "intel-core-i7-12700k")
        self.assertEqual(cpus.match("Intel(R) Core(TM) i7-12700 CPU")["key"], "intel-core-i7-12700")
        self.assertEqual(cpus.match("Ryzen 5 5600X")["key"], "amd-ryzen-5-5600x")
        self.assertEqual(cpus.match("Apple M2 Pro")["key"], "apple-m2-pro")
        self.assertIsNone(cpus.match("Snapdragon 8 Gen 3"))

    def test_gpu_rules_are_valid_regexes(self):
        import re
        for pattern, fams in cpus.GPU_RULES:
            re.compile(pattern, re.I)
            self.assertTrue(fams)


class PayloadTests(TestCase):
    def test_scores_are_recomputed_on_server(self):
        p = fake(k=1.5)
        p["scores"] = dict(single=999999, multi=999999)  # браузер не может подсунуть свои очки
        c = clean(p)
        self.assertAlmostEqual(c["scores"]["single"], 1500, delta=0.5)
        self.assertAlmostEqual(c["scores"]["multi"], 12000, delta=1)
        self.assertEqual(c["multi"]["int"]["speedup"], 8.0)
        self.assertAlmostEqual(c["marathon"]["drop"], 10.0, places=1)
        self.assertEqual(c["freq"]["single"], 4.5)
        self.assertEqual(c["fps"]["fps"], 225.0)

    def test_cpu_name_comes_from_catalog(self):
        p = fake()
        p["system"]["cpu"] = "что угодно"
        c = clean(p)
        self.assertEqual(c["system"]["cpu"], "AMD Ryzen 7 6800H")
        self.assertEqual(c["system"]["vendor"], "amd")

    def test_unknown_cpu_is_kept_as_typed(self):
        c = clean(fake(cpu_key="", cpu="Snapdragon X Elite"))
        self.assertEqual((c["system"]["cpu_key"], c["system"]["cpu"], c["system"]["vendor"]), ("", "Snapdragon X Elite", "other"))
        c = clean(fake(cpu_key="", cpu="ryzen 5 5600x"))  # вписанный от руки, но есть в справочнике
        self.assertEqual(c["system"]["cpu_key"], "amd-ryzen-5-5600x")

    def test_rejects_garbage(self):
        for bad in ({}, {"format": "narod-bench/2"}, dict(fake(), single={})):
            with self.assertRaises(ValueError):
                clean(bad)
        p = fake()
        p["single"]["int"]["rate"] = float("nan")
        with self.assertRaises(ValueError):
            clean(p)

    def test_rejects_impossible_results(self):
        with self.assertRaises(ValueError):
            clean(fake(k=50))  # один поток в 50 раз быстрее эталона
        p = fake()
        p["multi"]["int"]["rate"] = meta.REF["int"] * 100  # ускорение ×100 на 16 потоках
        with self.assertRaises(ValueError):
            clean(p)

    def test_bad_optional_numbers_become_empty(self):
        p = fake()
        p["freq"] = dict(single=99, multi="x", hot=None)
        p["fps"] = dict(fps=-5)
        c = clean(p)
        self.assertEqual(c["freq"], dict(single=None, multi=None, hot=None))
        self.assertIsNone(c["fps"]["fps"])


class AnalysisTests(TestCase):
    def save(self, **kw):
        d = clean(fake(**kw))
        s = d["system"]
        return Result.objects.create(
            uid=d["uid"], device=d["device"], name=d["name"], cpu_key=s["cpu_key"], cpu=s["cpu"], vendor=s["vendor"],
            threads=s["threads"], engine=s["engine"], single=d["scores"]["single"], multi=d["scores"]["multi"],
            fps=d["fps"]["fps"], freq=d["freq"]["single"], freq_all=d["freq"]["multi"], drop=d["marathon"]["drop"], data=d)

    def test_first_of_its_kind(self):
        r = self.save()
        a = analysis.build(r)
        self.assertEqual(a["rank"], 1)
        self.assertIsNone(a["pct"]["multi"])
        self.assertEqual(a["health"]["checks"][0]["title"], "Сравнить пока не с кем")
        self.assertEqual(a["eff"], round(r.multi / 45, 1))

    def test_weaker_than_same_model_and_hot(self):
        self.save(name="A", k=1.0)
        self.save(name="B", k=1.05)
        r = self.save(name="C", k=0.6, drop_to=7, freq=2.4)
        h = analysis.build(r)["health"]
        self.assertEqual(h["level"], "bad")
        titles = [c["title"] for c in h["checks"]]
        self.assertIn("Заметно слабее таких же процессоров", titles)
        self.assertIn("Частота сильно ниже паспортной", titles)
        self.assertIn("Сильный нагрев", titles)

    def test_healthy(self):
        self.save(name="A", k=1.0)
        r = self.save(name="B", k=1.02, drop_to=9.8, freq=4.5)
        h = analysis.build(r)["health"]
        self.assertEqual(h["level"], "ok")
        self.assertEqual(h["title"], "Процессор не ослаб — работает как положено")

    def test_leaderboard_groups_by_cpu(self):
        self.save(name="A", k=1.0)
        self.save(name="B", k=1.2)
        self.save(name="C", cpu_key="intel-core-i7-11800h", cpu="Intel Core i7-11800H", k=0.9)
        board = analysis.leaderboard("multi", "cpu")
        self.assertEqual([g["cpu"] for g in board], ["AMD Ryzen 7 6800H", "Intel Core i7-11800H"])
        self.assertEqual(board[0]["count"], 2)
        self.assertAlmostEqual(board[0]["multi"], 9600, delta=1)
        self.assertEqual(len(analysis.leaderboard("fps", "runs")), 3)


class PageTests(TestCase):
    def setUp(self):
        cache.clear()

    def save(self, p, ip="10.0.0.1"):
        return self.client.post("/api/save/", json.dumps(p), content_type="application/json", REMOTE_ADDR=ip)

    def test_flow(self):
        self.assertContains(self.client.get("/top/"), "Здесь пока пусто")
        r1 = self.save(fake("Шакс", k=1.1))
        self.assertEqual(r1.status_code, 200, r1.content)
        r2 = self.save(fake("Друг", cpu_key="intel-core-i7-11800h", cpu="Intel Core i7-11800H"))
        page = self.client.get(r2.json()["url"])
        self.assertContains(page, "Intel Core i7-11800H")
        self.assertContains(page, "Не ослаб ли процессор?")
        self.assertContains(page, "45 Вт")
        top = self.client.get("/top/")
        self.assertContains(top, "Ryzen 7 6800H")
        self.assertContains(top, "i7-11800H")
        for url in ["/", "/top/?view=runs&sort=fps", "/top/?sort=eff", "/top/?sort=bogus", r1.json()["url"]]:
            self.assertEqual(self.client.get(url).status_code, 200, url)

    def test_unknown_cpu_result_page(self):
        r = self.save(fake("X", cpu_key="", cpu="Snapdragon X Elite", threads=12))
        page = self.client.get(r.json()["url"])
        self.assertContains(page, "нет в справочнике")

    def test_save_bad_request(self):
        r = self.client.post("/api/save/", "не json", content_type="application/json")
        self.assertEqual(r.status_code, 400)
        self.assertIn("error", r.json())

    def test_save_is_idempotent(self):
        self.save(fake())
        self.save(fake())
        self.assertEqual(Result.objects.count(), 1)

    def test_rate_limit(self):
        from .views import SAVE_LIMIT
        for i in range(SAVE_LIMIT):
            self.assertEqual(self.save(fake(f"n{i}")).status_code, 200)
        self.assertEqual(self.save(fake("лишний")).status_code, 429)
        self.assertEqual(self.save(fake("другой адрес"), ip="10.0.0.2").status_code, 200)

    def test_no_public_delete(self):
        r = self.save(fake())
        self.assertEqual(self.client.post(f"/r/{r.json()['id']}/delete/").status_code, 404)

    def test_home_has_config(self):
        page = self.client.get("/")
        self.assertContains(page, '"format": "narod-bench/3"')
        self.assertContains(page, "amd-ryzen-7-6800h")


class DatabaseUrlTests(TestCase):
    """DATABASE_URL с Render: понятные ошибки вместо трейсбека, без пароля в тексте ошибки."""
    PG = "postgresql://owner:s3cret@ep-x-pooler.eu-central-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"

    def test_plain_and_wrapped_connection_strings(self):
        from narod.dburl import config
        for raw in (self.PG, f"  {self.PG}\n", f"'{self.PG}'", f"psql '{self.PG}'", f'"{self.PG}"'):
            d = config(raw, default="sqlite:///x.db", required=True)
            self.assertEqual(d["ENGINE"], "django.db.backends.postgresql", raw)
            self.assertEqual(d["HOST"], "ep-x-pooler.eu-central-1.aws.neon.tech")
            self.assertEqual(d["OPTIONS"]["sslmode"], "require")

    def test_web_link_instead_of_connection_string(self):
        from django.core.exceptions import ImproperlyConfigured
        from narod.dburl import config
        with self.assertRaises(ImproperlyConfigured) as e:
            config("https://console.neon.tech/app/projects/abc?password=s3cret", default="sqlite:///x.db", required=True)
        msg = str(e.exception)
        self.assertIn("postgresql://", msg)
        self.assertIn("https://", msg)
        self.assertNotIn("s3cret", msg)

    def test_empty(self):
        from django.core.exceptions import ImproperlyConfigured
        from narod.dburl import config
        self.assertEqual(config("", default="sqlite:///x.db", required=False)["ENGINE"], "django.db.backends.sqlite3")
        with self.assertRaises(ImproperlyConfigured) as e:
            config("  ", default="sqlite:///x.db", required=True)
        self.assertIn("не задан", str(e.exception))


class ServerTests(TestCase):
    def test_dual_stack_accepts_ipv4_and_ipv6(self):
        """Локальный сервер слушает [::] и принимает подключения и по 127.0.0.1, и по ::1."""
        from django.core.servers.basehttp import WSGIRequestHandler
        srv = DualStackServer(("::", 0), WSGIRequestHandler, ipv6=True)
        port = srv.server_address[1]
        try:
            for host, fam in (("127.0.0.1", socket.AF_INET), ("::1", socket.AF_INET6)):
                with socket.socket(fam, socket.SOCK_STREAM) as c:
                    c.settimeout(3)
                    c.connect((host, port))
        finally:
            srv.server_close()
