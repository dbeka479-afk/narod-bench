"""Версия 2: тесты перенесены в браузер. Старые замеры (Python на сервере) несовместимы
с новыми по единицам и очкам, поэтому таблица создаётся заново."""
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [("bench", "0001_initial")]

    operations = [
        migrations.DeleteModel(name="Result"),
        migrations.CreateModel(
            name="Result",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("uid", models.CharField(max_length=40, unique=True, verbose_name="ID замера")),
                ("device", models.CharField(blank=True, db_index=True, max_length=40,
                                            verbose_name="Компьютер (ID браузера)")),
                ("name", models.CharField(max_length=60, verbose_name="Имя")),
                ("cpu", models.CharField(max_length=120, verbose_name="Процессор")),
                ("single", models.FloatField(verbose_name="Очки: одно ядро")),
                ("multi", models.FloatField(verbose_name="Очки: все потоки")),
                ("created", models.DateTimeField(default=django.utils.timezone.now, verbose_name="Когда замерено")),
                ("data", models.JSONField(verbose_name="Полный результат")),
            ],
            options={"verbose_name": "Результат", "verbose_name_plural": "Результаты", "ordering": ["-created"]},
        ),
    ]
