"""Версия 3: открытый сайт. Добавлены частота, FPS, справочник процессоров и колонки для топа.
Замеры версии 2 несовместимы по формату, поэтому таблица создаётся заново
(на момент перехода в ней не было ни одного замера)."""
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [("bench", "0002_browser_bench")]

    operations = [
        migrations.DeleteModel(name="Result"),
        migrations.CreateModel(
            name="Result",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("uid", models.CharField(max_length=40, unique=True, verbose_name="ID замера")),
                ("device", models.CharField(blank=True, db_index=True, max_length=40,
                                            verbose_name="Компьютер (ID браузера)")),
                ("name", models.CharField(max_length=40, verbose_name="Имя")),
                ("cpu_key", models.CharField(blank=True, db_index=True, max_length=60,
                                             verbose_name="Процессор из справочника")),
                ("cpu", models.CharField(max_length=120, verbose_name="Процессор")),
                ("vendor", models.CharField(blank=True, max_length=10, verbose_name="Фирма")),
                ("threads", models.PositiveSmallIntegerField(default=1, verbose_name="Потоков")),
                ("engine", models.CharField(blank=True, max_length=20, verbose_name="Движок браузера")),
                ("single", models.FloatField(db_index=True, verbose_name="Очки: одно ядро")),
                ("multi", models.FloatField(db_index=True, verbose_name="Очки: все ядра")),
                ("fps", models.FloatField(blank=True, null=True, verbose_name="FPS в сцене")),
                ("freq", models.FloatField(blank=True, null=True, verbose_name="Частота 1 ядра, ГГц (оценка)")),
                ("freq_all", models.FloatField(blank=True, null=True, verbose_name="Частота всех ядер, ГГц (оценка)")),
                ("drop", models.FloatField(blank=True, null=True, verbose_name="Падение в марафоне, %")),
                ("created", models.DateTimeField(db_index=True, default=django.utils.timezone.now,
                                                 verbose_name="Когда замерено")),
                ("data", models.JSONField(verbose_name="Полный результат")),
            ],
            options={"verbose_name": "Результат", "verbose_name_plural": "Результаты", "ordering": ["-created"]},
        ),
    ]
