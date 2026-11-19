from django.db import models
from django.utils import timezone


class Result(models.Model):
    """Один замер. Тесты выполняются в браузере того, кто открыл сайт, поэтому здесь лежат
    результаты всех компьютеров, которые заходили на сайт. Числа для топа вынесены в отдельные
    колонки, полный результат — в data."""

    uid = models.CharField("ID замера", max_length=40, unique=True)
    device = models.CharField("Компьютер (ID браузера)", max_length=40, blank=True, db_index=True)
    name = models.CharField("Имя", max_length=40)
    cpu_key = models.CharField("Процессор из справочника", max_length=60, blank=True, db_index=True)
    cpu = models.CharField("Процессор", max_length=120)
    vendor = models.CharField("Фирма", max_length=10, blank=True)
    threads = models.PositiveSmallIntegerField("Потоков", default=1)
    engine = models.CharField("Движок браузера", max_length=20, blank=True)
    single = models.FloatField("Очки: одно ядро", db_index=True)
    multi = models.FloatField("Очки: все ядра", db_index=True)
    fps = models.FloatField("FPS в сцене", null=True, blank=True)
    freq = models.FloatField("Частота 1 ядра, ГГц (оценка)", null=True, blank=True)
    freq_all = models.FloatField("Частота всех ядер, ГГц (оценка)", null=True, blank=True)
    drop = models.FloatField("Падение в марафоне, %", null=True, blank=True)
    created = models.DateTimeField("Когда замерено", default=timezone.now, db_index=True)
    data = models.JSONField("Полный результат")

    class Meta:
        ordering = ["-created"]
        verbose_name = "Результат"
        verbose_name_plural = "Результаты"

    def __str__(self):
        return f"{self.name} · {self.cpu} · {self.single:.0f}/{self.multi:.0f}"

    @property
    def system(self):
        return self.data.get("system", {})

    @property
    def group(self):
        """Чем объединять замеры в топе процессоров."""
        return self.cpu_key or "x:" + self.cpu.lower()
