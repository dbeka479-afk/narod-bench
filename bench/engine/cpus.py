"""Справочник процессоров: паспортные данные (ядра, частоты, кэш, TDP, год, техпроцесс).

Браузер не сообщает модель процессора (защита приватности). Поэтому сайт подбирает кандидатов
по числу потоков и встроенной графике (её название и код устройства видны через WebGL),
а человек подтверждает выбор. Сами результаты замеров от этих цифр не зависят — они настоящие.
Справочник учебный и может содержать неточности."""
import re

# (название, год, тип, ядра, потоки, база ГГц, турбо ГГц, L3 МБ, TDP Вт, техпроцесс, архитектура, графика, P/E)
# тип: d — настольный ПК, l — ноутбук, m — Mac.  TDP: число или (от, до).
# графика — семейства встроенной графики через пробел (для угадывания по WebGL); "" — встроенной графики нет.
_ROWS = [
    # ---------------- Intel, настольные ----------------
    ("Intel Core i3-8100", 2017, "d", 4, 4, 3.6, None, 6, 65, "14 нм", "Coffee Lake", "cfl-s", ""),
    ("Intel Core i5-8400", 2017, "d", 6, 6, 2.8, 4.0, 9, 65, "14 нм", "Coffee Lake", "cfl-s", ""),
    ("Intel Core i7-8700", 2017, "d", 6, 12, 3.2, 4.6, 12, 65, "14 нм", "Coffee Lake", "cfl-s", ""),
    ("Intel Core i7-8700K", 2017, "d", 6, 12, 3.7, 4.7, 12, 95, "14 нм", "Coffee Lake", "cfl-s", ""),
    ("Intel Core i5-9400F", 2019, "d", 6, 6, 2.9, 4.1, 9, 65, "14 нм", "Coffee Lake Refresh", "", ""),
    ("Intel Core i5-9600K", 2018, "d", 6, 6, 3.7, 4.6, 9, 95, "14 нм", "Coffee Lake Refresh", "cfl-s", ""),
    ("Intel Core i7-9700K", 2018, "d", 8, 8, 3.6, 4.9, 12, 95, "14 нм", "Coffee Lake Refresh", "cfl-s", ""),
    ("Intel Core i9-9900K", 2018, "d", 8, 16, 3.6, 5.0, 16, 95, "14 нм", "Coffee Lake Refresh", "cfl-s", ""),
    ("Intel Core i3-10100", 2020, "d", 4, 8, 3.6, 4.3, 6, 65, "14 нм", "Comet Lake", "cml-s", ""),
    ("Intel Core i3-10105F", 2021, "d", 4, 8, 3.7, 4.4, 6, 65, "14 нм", "Comet Lake", "", ""),
    ("Intel Core i5-10400", 2020, "d", 6, 12, 2.9, 4.3, 12, 65, "14 нм", "Comet Lake", "cml-s", ""),
    ("Intel Core i5-10400F", 2020, "d", 6, 12, 2.9, 4.3, 12, 65, "14 нм", "Comet Lake", "", ""),
    ("Intel Core i5-10600K", 2020, "d", 6, 12, 4.1, 4.8, 12, 125, "14 нм", "Comet Lake", "cml-s", ""),
    ("Intel Core i7-10700", 2020, "d", 8, 16, 2.9, 4.8, 16, 65, "14 нм", "Comet Lake", "cml-s", ""),
    ("Intel Core i7-10700K", 2020, "d", 8, 16, 3.8, 5.1, 16, 125, "14 нм", "Comet Lake", "cml-s", ""),
    ("Intel Core i9-10900K", 2020, "d", 10, 20, 3.7, 5.3, 20, 125, "14 нм", "Comet Lake", "cml-s", ""),
    ("Intel Core i5-11400", 2021, "d", 6, 12, 2.6, 4.4, 12, 65, "14 нм", "Rocket Lake", "rkl", ""),
    ("Intel Core i5-11400F", 2021, "d", 6, 12, 2.6, 4.4, 12, 65, "14 нм", "Rocket Lake", "", ""),
    ("Intel Core i7-11700K", 2021, "d", 8, 16, 3.6, 5.0, 16, 125, "14 нм", "Rocket Lake", "rkl", ""),
    ("Intel Core i9-11900K", 2021, "d", 8, 16, 3.5, 5.3, 16, 125, "14 нм", "Rocket Lake", "rkl", ""),
    ("Intel Core i3-12100", 2022, "d", 4, 8, 3.3, 4.3, 12, 60, "Intel 7", "Alder Lake", "adl-s", ""),
    ("Intel Core i3-12100F", 2022, "d", 4, 8, 3.3, 4.3, 12, 58, "Intel 7", "Alder Lake", "", ""),
    ("Intel Core i5-12400", 2022, "d", 6, 12, 2.5, 4.4, 18, 65, "Intel 7", "Alder Lake", "adl-s", ""),
    ("Intel Core i5-12400F", 2022, "d", 6, 12, 2.5, 4.4, 18, 65, "Intel 7", "Alder Lake", "", ""),
    ("Intel Core i5-12600K", 2021, "d", 10, 16, 3.7, 4.9, 20, 125, "Intel 7", "Alder Lake", "adl-s", "6P+4E"),
    ("Intel Core i7-12700", 2022, "d", 12, 20, 2.1, 4.9, 25, 65, "Intel 7", "Alder Lake", "adl-s", "8P+4E"),
    ("Intel Core i7-12700K", 2021, "d", 12, 20, 3.6, 5.0, 25, 125, "Intel 7", "Alder Lake", "adl-s", "8P+4E"),
    ("Intel Core i9-12900K", 2021, "d", 16, 24, 3.2, 5.2, 30, 125, "Intel 7", "Alder Lake", "adl-s", "8P+8E"),
    ("Intel Core i3-13100", 2023, "d", 4, 8, 3.4, 4.5, 12, 60, "Intel 7", "Raptor Lake", "adl-s rpl-s", ""),
    ("Intel Core i5-13400", 2023, "d", 10, 16, 2.5, 4.6, 20, 65, "Intel 7", "Raptor Lake", "adl-s rpl-s", "6P+4E"),
    ("Intel Core i5-13400F", 2023, "d", 10, 16, 2.5, 4.6, 20, 65, "Intel 7", "Raptor Lake", "", "6P+4E"),
    ("Intel Core i5-13600K", 2022, "d", 14, 20, 3.5, 5.1, 24, 125, "Intel 7", "Raptor Lake", "rpl-s", "6P+8E"),
    ("Intel Core i7-13700", 2023, "d", 16, 24, 2.1, 5.2, 30, 65, "Intel 7", "Raptor Lake", "rpl-s", "8P+8E"),
    ("Intel Core i7-13700K", 2022, "d", 16, 24, 3.4, 5.4, 30, 125, "Intel 7", "Raptor Lake", "rpl-s", "8P+8E"),
    ("Intel Core i9-13900K", 2022, "d", 24, 32, 3.0, 5.8, 36, 125, "Intel 7", "Raptor Lake", "rpl-s", "8P+16E"),
    ("Intel Core i5-14400", 2024, "d", 10, 16, 2.5, 4.7, 20, 65, "Intel 7", "Raptor Lake Refresh", "adl-s rpl-s", "6P+4E"),
    ("Intel Core i5-14400F", 2024, "d", 10, 16, 2.5, 4.7, 20, 65, "Intel 7", "Raptor Lake Refresh", "", "6P+4E"),
    ("Intel Core i5-14600K", 2023, "d", 14, 20, 3.5, 5.3, 24, 125, "Intel 7", "Raptor Lake Refresh", "rpl-s", "6P+8E"),
    ("Intel Core i7-14700", 2024, "d", 20, 28, 2.1, 5.4, 33, 65, "Intel 7", "Raptor Lake Refresh", "rpl-s", "8P+12E"),
    ("Intel Core i7-14700K", 2023, "d", 20, 28, 3.4, 5.6, 33, 125, "Intel 7", "Raptor Lake Refresh", "rpl-s", "8P+12E"),
    ("Intel Core i9-14900K", 2023, "d", 24, 32, 3.2, 6.0, 36, 125, "Intel 7", "Raptor Lake Refresh", "rpl-s", "8P+16E"),
    ("Intel Core Ultra 5 245K", 2024, "d", 14, 14, 4.2, 5.2, 24, 125, "TSMC 3 нм", "Arrow Lake", "arl-s", "6P+8E"),
    ("Intel Core Ultra 7 265K", 2024, "d", 20, 20, 3.9, 5.5, 30, 125, "TSMC 3 нм", "Arrow Lake", "arl-s", "8P+12E"),
    ("Intel Core Ultra 9 285K", 2024, "d", 24, 24, 3.7, 5.7, 36, 125, "TSMC 3 нм", "Arrow Lake", "arl-s", "8P+16E"),

    # ---------------- Intel, ноутбуки ----------------
    ("Intel Celeron N4020", 2019, "l", 2, 2, 1.1, 2.8, 4, 6, "14 нм", "Gemini Lake Refresh", "glk", ""),
    ("Intel Pentium Silver N5030", 2019, "l", 4, 4, 1.1, 3.1, 4, 6, "14 нм", "Gemini Lake Refresh", "glk", ""),
    ("Intel Celeron N4500", 2021, "l", 2, 2, 1.1, 2.8, 4, 6, "10 нм", "Jasper Lake", "jsl", ""),
    ("Intel N100", 2023, "l", 4, 4, None, 3.4, 6, 6, "Intel 7", "Alder Lake-N", "adl-n", ""),
    ("Intel N200", 2023, "l", 4, 4, None, 3.7, 6, 6, "Intel 7", "Alder Lake-N", "adl-n", ""),
    ("Intel Core i3-N305", 2023, "l", 8, 8, None, 3.8, 6, 15, "Intel 7", "Alder Lake-N", "adl-n", ""),
    ("Intel Core i5-8250U", 2017, "l", 4, 8, 1.6, 3.4, 6, 15, "14 нм", "Kaby Lake R", "kbl-r", ""),
    ("Intel Core i7-8550U", 2017, "l", 4, 8, 1.8, 4.0, 8, 15, "14 нм", "Kaby Lake R", "kbl-r", ""),
    ("Intel Core i5-8265U", 2018, "l", 4, 8, 1.6, 3.9, 6, 15, "14 нм", "Whiskey Lake", "whl", ""),
    ("Intel Core i7-8565U", 2018, "l", 4, 8, 1.8, 4.6, 8, 15, "14 нм", "Whiskey Lake", "whl", ""),
    ("Intel Core i7-8750H", 2018, "l", 6, 12, 2.2, 4.1, 9, 45, "14 нм", "Coffee Lake", "cfl-h", ""),
    ("Intel Core i5-9300H", 2019, "l", 4, 8, 2.4, 4.1, 8, 45, "14 нм", "Coffee Lake Refresh", "cfl-h", ""),
    ("Intel Core i7-9750H", 2019, "l", 6, 12, 2.6, 4.5, 12, 45, "14 нм", "Coffee Lake Refresh", "cfl-h", ""),
    ("Intel Core i3-10110U", 2019, "l", 2, 4, 2.1, 4.1, 4, 15, "14 нм", "Comet Lake", "cml-u", ""),
    ("Intel Core i5-10210U", 2019, "l", 4, 8, 1.6, 4.2, 6, 15, "14 нм", "Comet Lake", "cml-u", ""),
    ("Intel Core i7-10510U", 2019, "l", 4, 8, 1.8, 4.9, 8, 15, "14 нм", "Comet Lake", "cml-u", ""),
    ("Intel Core i5-1035G1", 2019, "l", 4, 8, 1.0, 3.6, 6, 15, "10 нм", "Ice Lake", "icl", ""),
    ("Intel Core i7-1065G7", 2019, "l", 4, 8, 1.3, 3.9, 8, 15, "10 нм", "Ice Lake", "icl", ""),
    ("Intel Core i5-10300H", 2020, "l", 4, 8, 2.5, 4.5, 8, 45, "14 нм", "Comet Lake", "cml-h", ""),
    ("Intel Core i7-10750H", 2020, "l", 6, 12, 2.6, 5.0, 12, 45, "14 нм", "Comet Lake", "cml-h", ""),
    ("Intel Core i7-10870H", 2020, "l", 8, 16, 2.2, 5.0, 16, 45, "14 нм", "Comet Lake", "cml-h", ""),
    ("Intel Core i3-1115G4", 2020, "l", 2, 4, 3.0, 4.1, 6, 28, "10 нм SuperFin", "Tiger Lake", "tgl", ""),
    ("Intel Core i5-1135G7", 2020, "l", 4, 8, 2.4, 4.2, 8, 28, "10 нм SuperFin", "Tiger Lake", "tgl", ""),
    ("Intel Core i7-1165G7", 2020, "l", 4, 8, 2.8, 4.7, 12, 28, "10 нм SuperFin", "Tiger Lake", "tgl", ""),
    ("Intel Core i5-11400H", 2021, "l", 6, 12, 2.7, 4.5, 12, 45, "10 нм SuperFin", "Tiger Lake-H", "tgl-h", ""),
    ("Intel Core i7-11800H", 2021, "l", 8, 16, 2.3, 4.6, 24, 45, "10 нм SuperFin", "Tiger Lake-H", "tgl-h", ""),
    ("Intel Core i3-1215U", 2022, "l", 6, 8, 1.2, 4.4, 10, 15, "Intel 7", "Alder Lake", "adl-p", "2P+4E"),
    ("Intel Core i5-1235U", 2022, "l", 10, 12, 1.3, 4.4, 12, 15, "Intel 7", "Alder Lake", "adl-p", "2P+8E"),
    ("Intel Core i7-1255U", 2022, "l", 10, 12, 1.7, 4.7, 12, 15, "Intel 7", "Alder Lake", "adl-p", "2P+8E"),
    ("Intel Core i5-1240P", 2022, "l", 12, 16, 1.7, 4.4, 12, 28, "Intel 7", "Alder Lake", "adl-p", "4P+8E"),
    ("Intel Core i7-1260P", 2022, "l", 12, 16, 2.1, 4.7, 18, 28, "Intel 7", "Alder Lake", "adl-p", "4P+8E"),
    ("Intel Core i5-12450H", 2022, "l", 8, 12, 2.0, 4.4, 12, 45, "Intel 7", "Alder Lake", "adl-p", "4P+4E"),
    ("Intel Core i5-12500H", 2022, "l", 12, 16, 2.5, 4.5, 18, 45, "Intel 7", "Alder Lake", "adl-p", "4P+8E"),
    ("Intel Core i7-12650H", 2022, "l", 10, 16, 2.3, 4.7, 24, 45, "Intel 7", "Alder Lake", "adl-p", "6P+4E"),
    ("Intel Core i7-12700H", 2022, "l", 14, 20, 2.3, 4.7, 24, 45, "Intel 7", "Alder Lake", "adl-p", "6P+8E"),
    ("Intel Core i9-12900H", 2022, "l", 14, 20, 2.5, 5.0, 24, 45, "Intel 7", "Alder Lake", "adl-p", "6P+8E"),
    ("Intel Core i5-1335U", 2023, "l", 10, 12, 1.3, 4.6, 12, 15, "Intel 7", "Raptor Lake", "rpl-p", "2P+8E"),
    ("Intel Core i7-1355U", 2023, "l", 10, 12, 1.7, 5.0, 12, 15, "Intel 7", "Raptor Lake", "rpl-p", "2P+8E"),
    ("Intel Core i5-1340P", 2023, "l", 12, 16, 1.9, 4.6, 12, 28, "Intel 7", "Raptor Lake", "rpl-p", "4P+8E"),
    ("Intel Core i5-13420H", 2023, "l", 8, 12, 2.1, 4.6, 12, 45, "Intel 7", "Raptor Lake", "rpl-p", "4P+4E"),
    ("Intel Core i5-13500H", 2023, "l", 12, 16, 2.6, 4.7, 18, 45, "Intel 7", "Raptor Lake", "rpl-p", "4P+8E"),
    ("Intel Core i7-13620H", 2023, "l", 10, 16, 2.4, 4.9, 24, 45, "Intel 7", "Raptor Lake", "rpl-p", "6P+4E"),
    ("Intel Core i7-13700H", 2023, "l", 14, 20, 2.4, 5.0, 24, 45, "Intel 7", "Raptor Lake", "rpl-p", "6P+8E"),
    ("Intel Core i9-13900H", 2023, "l", 14, 20, 2.6, 5.4, 24, 45, "Intel 7", "Raptor Lake", "rpl-p", "6P+8E"),
    ("Intel Core i5-13450HX", 2023, "l", 10, 16, 2.4, 4.6, 20, 55, "Intel 7", "Raptor Lake-HX", "rpl-s", "6P+4E"),
    ("Intel Core i7-13650HX", 2023, "l", 14, 20, 2.6, 4.9, 24, 55, "Intel 7", "Raptor Lake-HX", "rpl-s", "6P+8E"),
    ("Intel Core i9-13980HX", 2023, "l", 24, 32, 2.2, 5.6, 36, 55, "Intel 7", "Raptor Lake-HX", "rpl-s", "8P+16E"),
    ("Intel Core i7-14650HX", 2024, "l", 16, 24, 2.2, 5.2, 30, 55, "Intel 7", "Raptor Lake-HX Refresh", "rpl-s", "8P+8E"),
    ("Intel Core i7-14700HX", 2024, "l", 20, 28, 2.1, 5.5, 33, 55, "Intel 7", "Raptor Lake-HX Refresh", "rpl-s", "8P+12E"),
    ("Intel Core i9-14900HX", 2024, "l", 24, 32, 2.2, 5.8, 36, 55, "Intel 7", "Raptor Lake-HX Refresh", "rpl-s", "8P+16E"),
    ("Intel Core 5 120U", 2024, "l", 10, 12, 1.4, 5.0, 12, 15, "Intel 7", "Raptor Lake Refresh", "rpl-p", "2P+8E"),
    ("Intel Core 7 150U", 2024, "l", 10, 12, 1.8, 5.4, 12, 15, "Intel 7", "Raptor Lake Refresh", "rpl-p", "2P+8E"),
    ("Intel Core 7 240H", 2024, "l", 10, 16, 2.5, 5.2, 24, 45, "Intel 7", "Raptor Lake Refresh", "rpl-p", "6P+4E"),
    ("Intel Core Ultra 5 125U", 2023, "l", 12, 14, 1.3, 4.3, 12, 15, "Intel 4", "Meteor Lake", "mtl", "2P+8E+2LP"),
    ("Intel Core Ultra 7 155U", 2023, "l", 12, 14, 1.7, 4.8, 12, 15, "Intel 4", "Meteor Lake", "mtl", "2P+8E+2LP"),
    ("Intel Core Ultra 5 125H", 2023, "l", 14, 18, 1.2, 4.5, 18, 28, "Intel 4", "Meteor Lake", "mtl", "4P+8E+2LP"),
    ("Intel Core Ultra 7 155H", 2023, "l", 16, 22, 1.4, 4.8, 24, 28, "Intel 4", "Meteor Lake", "mtl", "6P+8E+2LP"),
    ("Intel Core Ultra 9 185H", 2023, "l", 16, 22, 2.3, 5.1, 24, 45, "Intel 4", "Meteor Lake", "mtl", "6P+8E+2LP"),
    ("Intel Core Ultra 5 226V", 2024, "l", 8, 8, 2.1, 4.5, 8, 17, "TSMC 3 нм", "Lunar Lake", "lnl", "4P+4LP"),
    ("Intel Core Ultra 7 258V", 2024, "l", 8, 8, 2.2, 4.8, 12, 17, "TSMC 3 нм", "Lunar Lake", "lnl", "4P+4LP"),
    ("Intel Core Ultra 5 225H", 2025, "l", 14, 14, 1.7, 4.9, 18, 28, "TSMC 3 нм", "Arrow Lake-H", "arl-h", "4P+8E+2LP"),
    ("Intel Core Ultra 7 255H", 2025, "l", 16, 16, 2.0, 5.1, 24, 28, "TSMC 3 нм", "Arrow Lake-H", "arl-h", "6P+8E+2LP"),
    ("Intel Core Ultra 9 275HX", 2025, "l", 24, 24, 2.7, 5.4, 36, 55, "TSMC 3 нм", "Arrow Lake-HX", "arl-s", "8P+16E"),

    # ---------------- AMD, настольные ----------------
    ("AMD Ryzen 5 1600", 2017, "d", 6, 12, 3.2, 3.6, 16, 65, "14 нм", "Zen", "", ""),
    ("AMD Ryzen 7 1700", 2017, "d", 8, 16, 3.0, 3.7, 16, 65, "14 нм", "Zen", "", ""),
    ("AMD Ryzen 5 2400G", 2018, "d", 4, 8, 3.6, 3.9, 4, 65, "14 нм", "Zen (Raven Ridge)", "raven", ""),
    ("AMD Ryzen 5 2600", 2018, "d", 6, 12, 3.4, 3.9, 16, 65, "12 нм", "Zen+", "", ""),
    ("AMD Ryzen 7 2700X", 2018, "d", 8, 16, 3.7, 4.3, 16, 105, "12 нм", "Zen+", "", ""),
    ("AMD Ryzen 3 3200G", 2019, "d", 4, 4, 3.6, 4.0, 4, 65, "12 нм", "Zen+ (Picasso)", "raven", ""),
    ("AMD Ryzen 5 3400G", 2019, "d", 4, 8, 3.7, 4.2, 4, 65, "12 нм", "Zen+ (Picasso)", "raven", ""),
    ("AMD Ryzen 5 3600", 2019, "d", 6, 12, 3.6, 4.2, 32, 65, "7 нм", "Zen 2", "", ""),
    ("AMD Ryzen 7 3700X", 2019, "d", 8, 16, 3.6, 4.4, 32, 65, "7 нм", "Zen 2", "", ""),
    ("AMD Ryzen 9 3900X", 2019, "d", 12, 24, 3.8, 4.6, 64, 105, "7 нм", "Zen 2", "", ""),
    ("AMD Ryzen 5 5500", 2022, "d", 6, 12, 3.6, 4.2, 16, 65, "7 нм", "Zen 3", "", ""),
    ("AMD Ryzen 5 5600", 2022, "d", 6, 12, 3.5, 4.4, 32, 65, "7 нм", "Zen 3", "", ""),
    ("AMD Ryzen 5 5600X", 2020, "d", 6, 12, 3.7, 4.6, 32, 65, "7 нм", "Zen 3", "", ""),
    ("AMD Ryzen 5 5600G", 2021, "d", 6, 12, 3.9, 4.4, 16, 65, "7 нм", "Zen 3 (Cezanne)", "cezanne", ""),
    ("AMD Ryzen 7 5700G", 2021, "d", 8, 16, 3.8, 4.6, 16, 65, "7 нм", "Zen 3 (Cezanne)", "cezanne", ""),
    ("AMD Ryzen 7 5700X", 2022, "d", 8, 16, 3.4, 4.6, 32, 65, "7 нм", "Zen 3", "", ""),
    ("AMD Ryzen 7 5800X", 2020, "d", 8, 16, 3.8, 4.7, 32, 105, "7 нм", "Zen 3", "", ""),
    ("AMD Ryzen 7 5800X3D", 2022, "d", 8, 16, 3.4, 4.5, 96, 105, "7 нм", "Zen 3 + 3D V-Cache", "", ""),
    ("AMD Ryzen 9 5900X", 2020, "d", 12, 24, 3.7, 4.8, 64, 105, "7 нм", "Zen 3", "", ""),
    ("AMD Ryzen 9 5950X", 2020, "d", 16, 32, 3.4, 4.9, 64, 105, "7 нм", "Zen 3", "", ""),
    ("AMD Ryzen 5 7600", 2023, "d", 6, 12, 3.8, 5.1, 32, 65, "5 нм", "Zen 4", "raphael", ""),
    ("AMD Ryzen 5 7600X", 2022, "d", 6, 12, 4.7, 5.3, 32, 105, "5 нм", "Zen 4", "raphael", ""),
    ("AMD Ryzen 7 7700", 2023, "d", 8, 16, 3.8, 5.3, 32, 65, "5 нм", "Zen 4", "raphael", ""),
    ("AMD Ryzen 7 7700X", 2022, "d", 8, 16, 4.5, 5.4, 32, 105, "5 нм", "Zen 4", "raphael", ""),
    ("AMD Ryzen 7 7800X3D", 2023, "d", 8, 16, 4.2, 5.0, 96, 120, "5 нм", "Zen 4 + 3D V-Cache", "raphael", ""),
    ("AMD Ryzen 9 7900X", 2022, "d", 12, 24, 4.7, 5.6, 64, 170, "5 нм", "Zen 4", "raphael", ""),
    ("AMD Ryzen 9 7950X", 2022, "d", 16, 32, 4.5, 5.7, 64, 170, "5 нм", "Zen 4", "raphael", ""),
    ("AMD Ryzen 5 8600G", 2024, "d", 6, 12, 4.3, 5.0, 16, 65, "4 нм", "Zen 4 (Phoenix)", "phoenix", ""),
    ("AMD Ryzen 7 8700G", 2024, "d", 8, 16, 4.2, 5.1, 16, 65, "4 нм", "Zen 4 (Phoenix)", "phoenix", ""),
    ("AMD Ryzen 5 9600X", 2024, "d", 6, 12, 3.9, 5.4, 32, 65, "4 нм", "Zen 5", "granite", ""),
    ("AMD Ryzen 7 9700X", 2024, "d", 8, 16, 3.8, 5.5, 32, 65, "4 нм", "Zen 5", "granite", ""),
    ("AMD Ryzen 7 9800X3D", 2024, "d", 8, 16, 4.7, 5.2, 96, 120, "4 нм", "Zen 5 + 3D V-Cache", "granite", ""),
    ("AMD Ryzen 9 9900X", 2024, "d", 12, 24, 4.4, 5.6, 64, 120, "4 нм", "Zen 5", "granite", ""),
    ("AMD Ryzen 9 9950X", 2024, "d", 16, 32, 4.3, 5.7, 64, 170, "4 нм", "Zen 5", "granite", ""),

    # ---------------- AMD, ноутбуки ----------------
    ("AMD Ryzen 5 3500U", 2019, "l", 4, 8, 2.1, 3.7, 4, 15, "12 нм", "Zen+ (Picasso)", "raven", ""),
    ("AMD Ryzen 7 3700U", 2019, "l", 4, 8, 2.3, 4.0, 4, 15, "12 нм", "Zen+ (Picasso)", "raven", ""),
    ("AMD Ryzen 5 4500U", 2020, "l", 6, 6, 2.3, 4.0, 8, 15, "7 нм", "Zen 2 (Renoir)", "renoir", ""),
    ("AMD Ryzen 5 4600H", 2020, "l", 6, 12, 3.0, 4.0, 8, 45, "7 нм", "Zen 2 (Renoir)", "renoir", ""),
    ("AMD Ryzen 7 4700U", 2020, "l", 8, 8, 2.0, 4.1, 8, 15, "7 нм", "Zen 2 (Renoir)", "renoir", ""),
    ("AMD Ryzen 7 4800H", 2020, "l", 8, 16, 2.9, 4.2, 8, 45, "7 нм", "Zen 2 (Renoir)", "renoir", ""),
    ("AMD Ryzen 5 5500U", 2021, "l", 6, 12, 2.1, 4.0, 8, 15, "7 нм", "Zen 2 (Lucienne)", "lucienne", ""),
    ("AMD Ryzen 7 5700U", 2021, "l", 8, 16, 1.8, 4.3, 8, 15, "7 нм", "Zen 2 (Lucienne)", "lucienne", ""),
    ("AMD Ryzen 5 5600U", 2021, "l", 6, 12, 2.3, 4.2, 16, 15, "7 нм", "Zen 3 (Cezanne)", "cezanne", ""),
    ("AMD Ryzen 5 5600H", 2021, "l", 6, 12, 3.3, 4.2, 16, 45, "7 нм", "Zen 3 (Cezanne)", "cezanne", ""),
    ("AMD Ryzen 7 5800U", 2021, "l", 8, 16, 1.9, 4.4, 16, 15, "7 нм", "Zen 3 (Cezanne)", "cezanne", ""),
    ("AMD Ryzen 7 5800H", 2021, "l", 8, 16, 3.2, 4.4, 16, 45, "7 нм", "Zen 3 (Cezanne)", "cezanne", ""),
    ("AMD Ryzen 9 5900HX", 2021, "l", 8, 16, 3.3, 4.6, 16, 45, "7 нм", "Zen 3 (Cezanne)", "cezanne", ""),
    ("AMD Ryzen 5 5625U", 2022, "l", 6, 12, 2.3, 4.3, 16, 15, "7 нм", "Zen 3 (Barcelo)", "barcelo", ""),
    ("AMD Ryzen 7 5825U", 2022, "l", 8, 16, 2.0, 4.5, 16, 15, "7 нм", "Zen 3 (Barcelo)", "barcelo", ""),
    ("AMD Ryzen 5 7520U", 2022, "l", 4, 8, 2.8, 4.3, 4, 15, "6 нм", "Zen 2 (Mendocino)", "mendocino", ""),
    ("AMD Ryzen 5 7530U", 2023, "l", 6, 12, 2.0, 4.5, 16, 15, "7 нм", "Zen 3 (Barcelo-R)", "barcelo", ""),
    ("AMD Ryzen 7 7730U", 2023, "l", 8, 16, 2.0, 4.5, 16, 15, "7 нм", "Zen 3 (Barcelo-R)", "barcelo", ""),
    ("AMD Ryzen 5 6600U", 2022, "l", 6, 12, 2.9, 4.5, 16, (15, 28), "6 нм", "Zen 3+ (Rembrandt)", "rembrandt", ""),
    ("AMD Ryzen 5 6600H", 2022, "l", 6, 12, 3.3, 4.5, 16, 45, "6 нм", "Zen 3+ (Rembrandt)", "rembrandt", ""),
    ("AMD Ryzen 7 6800U", 2022, "l", 8, 16, 2.7, 4.7, 16, (15, 28), "6 нм", "Zen 3+ (Rembrandt)", "rembrandt", ""),
    ("AMD Ryzen 7 6800HS", 2022, "l", 8, 16, 3.2, 4.7, 16, 35, "6 нм", "Zen 3+ (Rembrandt)", "rembrandt", ""),
    ("AMD Ryzen 7 6800H", 2022, "l", 8, 16, 3.2, 4.7, 16, 45, "6 нм", "Zen 3+ (Rembrandt)", "rembrandt", ""),
    ("AMD Ryzen 9 6900HX", 2022, "l", 8, 16, 3.3, 4.9, 16, 45, "6 нм", "Zen 3+ (Rembrandt)", "rembrandt", ""),
    ("AMD Ryzen 5 7535HS", 2023, "l", 6, 12, 3.3, 4.55, 16, (35, 54), "6 нм", "Zen 3+ (Rembrandt-R)", "rembrandt", ""),
    ("AMD Ryzen 7 7735HS", 2023, "l", 8, 16, 3.2, 4.75, 16, (35, 54), "6 нм", "Zen 3+ (Rembrandt-R)", "rembrandt", ""),
    ("AMD Ryzen 5 7640HS", 2023, "l", 6, 12, 4.3, 5.0, 16, (35, 54), "4 нм", "Zen 4 (Phoenix)", "phoenix", ""),
    ("AMD Ryzen 7 7840U", 2023, "l", 8, 16, 3.3, 5.1, 16, (15, 30), "4 нм", "Zen 4 (Phoenix)", "phoenix", ""),
    ("AMD Ryzen 7 7840HS", 2023, "l", 8, 16, 3.8, 5.1, 16, (35, 54), "4 нм", "Zen 4 (Phoenix)", "phoenix", ""),
    ("AMD Ryzen 9 7940HS", 2023, "l", 8, 16, 4.0, 5.2, 16, (35, 54), "4 нм", "Zen 4 (Phoenix)", "phoenix", ""),
    ("AMD Ryzen 9 7945HX", 2023, "l", 16, 32, 2.5, 5.4, 64, (55, 75), "5 нм", "Zen 4 (Dragon Range)", "raphael", ""),
    ("AMD Ryzen 5 8645HS", 2024, "l", 6, 12, 4.3, 5.0, 16, (35, 54), "4 нм", "Zen 4 (Hawk Point)", "phoenix", ""),
    ("AMD Ryzen 7 8845HS", 2024, "l", 8, 16, 3.8, 5.1, 16, (35, 54), "4 нм", "Zen 4 (Hawk Point)", "phoenix", ""),
    ("AMD Ryzen 7 260", 2025, "l", 8, 16, 3.8, 5.1, 16, (35, 54), "4 нм", "Zen 4 (Hawk Point)", "phoenix", ""),
    ("AMD Ryzen AI 7 350", 2025, "l", 8, 16, 2.0, 5.0, 16, 28, "4 нм", "Zen 5 (Krackan Point)", "krackan", "4+4c"),
    ("AMD Ryzen AI 9 365", 2024, "l", 10, 20, 2.0, 5.0, 24, 28, "4 нм", "Zen 5 (Strix Point)", "strix", "4+6c"),
    ("AMD Ryzen AI 9 HX 370", 2024, "l", 12, 24, 2.0, 5.1, 24, 28, "4 нм", "Zen 5 (Strix Point)", "strix", "4+8c"),

    # ---------------- Apple (официальный TDP Apple не публикует — указано примерно) ----------------
    ("Apple M1", 2020, "m", 8, 8, None, 3.2, None, 20, "5 нм", "Firestorm + Icestorm", "m1", "4P+4E"),
    ("Apple M1 Pro", 2021, "m", 10, 10, None, 3.2, None, 30, "5 нм", "Firestorm + Icestorm", "m1pro", "8P+2E"),
    ("Apple M1 Max", 2021, "m", 10, 10, None, 3.2, None, 30, "5 нм", "Firestorm + Icestorm", "m1max", "8P+2E"),
    ("Apple M2", 2022, "m", 8, 8, None, 3.5, None, 20, "5 нм", "Avalanche + Blizzard", "m2", "4P+4E"),
    ("Apple M2 Pro", 2023, "m", 12, 12, None, 3.5, None, 30, "5 нм", "Avalanche + Blizzard", "m2pro", "8P+4E"),
    ("Apple M2 Max", 2023, "m", 12, 12, None, 3.7, None, 35, "5 нм", "Avalanche + Blizzard", "m2max", "8P+4E"),
    ("Apple M3", 2023, "m", 8, 8, None, 4.05, None, 20, "3 нм", "Apple M3", "m3", "4P+4E"),
    ("Apple M3 Pro", 2023, "m", 12, 12, None, 4.05, None, 30, "3 нм", "Apple M3", "m3pro", "6P+6E"),
    ("Apple M3 Max", 2023, "m", 16, 16, None, 4.05, None, 40, "3 нм", "Apple M3", "m3max", "12P+4E"),
    ("Apple M4", 2024, "m", 10, 10, None, 4.4, None, 22, "3 нм", "Apple M4", "m4", "4P+6E"),
    ("Apple M4 Pro", 2024, "m", 14, 14, None, 4.5, None, 40, "3 нм", "Apple M4", "m4pro", "10P+4E"),
    ("Apple M4 Max", 2024, "m", 16, 16, None, 4.5, None, 45, "3 нм", "Apple M4", "m4max", "12P+4E"),
    ("Apple M5", 2025, "m", 10, 10, None, None, None, 22, "3 нм", "Apple M5", "m5", "4P+6E"),
]

SEGMENTS = {"d": "настольный ПК", "l": "ноутбук", "m": "Mac"}

# Встроенная графика → семейство процессора. Код устройства (0x…) Chrome и Edge показывают в названии видеокарты.
# Правила проверяются по порядку; шаблоны — регулярные выражения, одинаково понятные Python и JavaScript.
GPU_RULES = [
    # AMD (коды устройств встроенной графики Radeon)
    (r"0x0*1681|Radeon\(TM\) 6[68]0M|Radeon 6[68]0M", "rembrandt"),
    (r"0x0*15BF|0x0*15C8|Radeon\(TM\) 7[468]0M|Radeon 7[468]0M", "phoenix"),
    (r"0x0*150E|Radeon\(TM\) 8[89]0M|Radeon 8[89]0M", "strix"),
    (r"0x0*1114|Radeon\(TM\) 8[46]0M|Radeon 8[46]0M", "krackan"),
    (r"0x0*1638", "cezanne"),
    (r"0x0*15E7", "barcelo"),
    (r"0x0*164C", "lucienne"),
    (r"0x0*1636", "renoir"),
    (r"0x0*15D8|0x0*15DD|Vega (3|6|8|9|10|11) ", "raven"),
    (r"0x0*1506", "mendocino"),
    (r"0x0*164E|Radeon\(TM\) 610M|Radeon 610M", "raphael"),
    (r"0x0*13C0", "granite"),
    # Intel
    (r"0x0*9A(49|40|78|7F)", "tgl"),
    (r"0x0*9A(60|68|70)", "tgl-h"),
    (r"0x0*46(A[0-9A-F]|B[0-9A-F]|2[0-9A-F])", "adl-p"),
    (r"0x0*46(8[0-9A-F]|9[0-9A-F])", "adl-s"),
    (r"0x0*46D[0-4]", "adl-n"),
    (r"0x0*A7(A[0-9A-F]|2[0-9A-F])", "rpl-p"),
    (r"0x0*A78[0-9A-F]", "rpl-s"),
    (r"0x0*7D(55|D5|45|40)", "mtl"),
    (r"0x0*64A0|0x0*6420", "lnl"),
    (r"0x0*7D(51|D1|41)", "arl-h"),
    (r"0x0*7D67", "arl-s"),
    (r"0x0*4C8[A-C]", "rkl"),
    (r"0x0*9BC4", "cml-h"),
    (r"0x0*9B(C5|C8|E6|F6)", "cml-s"),
    (r"0x0*9B(41|CA|CC|21|AC)", "cml-u"),
    (r"0x0*3E9B", "cfl-h"),
    (r"0x0*3E9[0-8]", "cfl-s"),
    (r"0x0*3EA0", "whl"),
    (r"0x0*5917", "kbl-r"),
    (r"0x0*8A5[0-9A-F]", "icl"),
    (r"0x0*318[45]", "glk"),
    (r"0x0*4E[5-7][0-9A-F]", "jsl"),
    # если кода устройства нет (Firefox, macOS) — по названию
    (r"Iris\(R\) Xe|Iris Xe", "tgl adl-p rpl-p"),
    (r"UHD Graphics 620", "kbl-r whl cml-u"),
    (r"UHD Graphics 630", "cfl-s cfl-h cml-s cml-h"),
    (r"UHD Graphics 7[3-7]0", "adl-s rpl-s rkl"),
    (r"UHD Graphics 60[05]", "glk"),
    (r"Iris\(R\) Plus|Iris Plus", "icl"),
    (r"Intel.*Arc(\(TM\))? (Graphics|130V|140V|140T)", "mtl lnl arl-h"),
]


def _key(name):
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def _vendor(name):
    return name.split()[0].lower()  # intel / amd / apple


def _tdp_text(tdp, vendor):
    if tdp is None:
        return None
    if isinstance(tdp, tuple):
        return f"{tdp[0]}–{tdp[1]} Вт"
    return ("≈" if vendor == "apple" else "") + f"{tdp} Вт"


def _tdp_avg(tdp):
    if tdp is None:
        return None
    return (tdp[0] + tdp[1]) / 2 if isinstance(tdp, tuple) else float(tdp)


def _build():
    out = {}
    for name, year, seg, cores, threads, base, boost, l3, tdp, proc, arch, fam, pe in _ROWS:
        v = _vendor(name)
        k = _key(name)
        out[k] = dict(
            key=k, name=name, vendor=v, year=year, seg=seg, segment=SEGMENTS[seg],
            cores=cores, threads=threads, base=base, boost=boost, l3=l3,
            tdp=_tdp_avg(tdp), tdp_text=_tdp_text(tdp, v), process=proc, arch=arch,
            fam=fam.split(), pe=pe,
        )
    return out


CATALOG = _build()


def get(key):
    return CATALOG.get(key or "")


def _norm(s):
    s = (s or "").lower()
    s = re.sub(r"\(r\)|\(tm\)|®|™|with radeon graphics|radeon graphics|processor|cpu|@.*$", " ", s)
    return re.sub(r"[^a-z0-9]", "", s)


_NORMED = sorted(((_norm(re.sub(r"^(Intel|AMD|Apple)\s+(Core\s+)?", "", c["name"])), c) for c in CATALOG.values()),
                 key=lambda x: -len(x[0]))


def match(text):
    """Найти процессор справочника по названию, вписанному от руки («Ryzen 5 5600X», «i5-12400f»)."""
    n = _norm(text)
    if not n:
        return None
    for token, c in _NORMED:  # самое длинное совпадение — первым: «12700K» раньше «12700»
        if token and token in n:
            return c
    return None


def for_browser():
    """Компактный справочник для страницы теста (угадывание и поиск)."""
    return [dict(key=c["key"], name=c["name"], vendor=c["vendor"], year=c["year"], seg=c["seg"],
                 cores=c["cores"], threads=c["threads"], boost=c["boost"], tdp=c["tdp"], fam=c["fam"])
            for c in CATALOG.values()]
