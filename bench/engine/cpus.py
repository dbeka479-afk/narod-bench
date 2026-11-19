"""Справочник процессоров: паспортные данные (ядра, частоты, кэш, TDP, год, техпроцесс).

Браузер не сообщает модель процессора (защита приватности). Поэтому сайт подбирает кандидатов
по косвенным признакам: телефон это или компьютер, число потоков, встроенная графика (её название
и код устройства видны через WebGL), модель телефона. Человек может поправить выбор. Сами результаты
замеров от этих цифр не зависят — они настоящие. Справочник учебный и может содержать неточности."""
import re

# (название, год, тип, ядра, потоки, база ГГц, турбо ГГц, L3 МБ, TDP Вт, техпроцесс, архитектура, графика, P/E)
# тип: d — настольный ПК, l — ноутбук, m — Mac.  TDP: число или (от, до).
# графика — семейства встроенной графики через пробел (для угадывания по WebGL); "" — встроенной графики нет.
_ROWS = [
    # ---------------- Intel, настольные ----------------
    ("Intel Core i3-2100", 2011, "d", 2, 4, 3.1, None, 3, 65, "32 нм", "Sandy Bridge", "snb-s", ""),
    ("Intel Core i5-2400", 2011, "d", 4, 4, 3.1, 3.4, 6, 95, "32 нм", "Sandy Bridge", "snb-s", ""),
    ("Intel Core i5-2500K", 2011, "d", 4, 4, 3.3, 3.7, 6, 95, "32 нм", "Sandy Bridge", "snb-s", ""),
    ("Intel Core i7-2600", 2011, "d", 4, 8, 3.4, 3.8, 8, 95, "32 нм", "Sandy Bridge", "snb-s", ""),
    ("Intel Core i5-3470", 2012, "d", 4, 4, 3.2, 3.6, 6, 77, "22 нм", "Ivy Bridge", "ivb-s", ""),
    ("Intel Core i7-3770", 2012, "d", 4, 8, 3.4, 3.9, 8, 77, "22 нм", "Ivy Bridge", "ivb-s", ""),
    ("Intel Xeon E5-2650 v2", 2013, "d", 8, 16, 2.6, 3.4, 20, 95, "22 нм", "Ivy Bridge-EP", "", ""),
    ("Intel Core i3-4130", 2013, "d", 2, 4, 3.4, None, 3, 54, "22 нм", "Haswell", "hsw-s", ""),
    ("Intel Core i3-4170", 2015, "d", 2, 4, 3.7, None, 3, 54, "22 нм", "Haswell", "hsw-s", ""),
    ("Intel Core i5-4460", 2014, "d", 4, 4, 3.2, 3.4, 6, 84, "22 нм", "Haswell", "hsw-s", ""),
    ("Intel Core i5-4590", 2014, "d", 4, 4, 3.3, 3.7, 6, 84, "22 нм", "Haswell", "hsw-s", ""),
    ("Intel Core i5-4690K", 2014, "d", 4, 4, 3.5, 3.9, 6, 88, "22 нм", "Haswell", "hsw-s", ""),
    ("Intel Core i7-4770", 2013, "d", 4, 8, 3.4, 3.9, 8, 84, "22 нм", "Haswell", "hsw-s", ""),
    ("Intel Core i7-4790", 2014, "d", 4, 8, 3.6, 4.0, 8, 84, "22 нм", "Haswell", "hsw-s", ""),
    ("Intel Core i7-4790K", 2014, "d", 4, 8, 4.0, 4.4, 8, 88, "22 нм", "Haswell", "hsw-s", ""),
    ("Intel Xeon E3-1230 v3", 2013, "d", 4, 8, 3.3, 3.7, 8, 80, "22 нм", "Haswell", "", ""),
    ("Intel Xeon E5-2670 v3", 2014, "d", 12, 24, 2.3, 3.1, 30, 120, "22 нм", "Haswell-EP", "", ""),
    ("Intel Xeon E5-2680 v4", 2016, "d", 14, 28, 2.4, 3.3, 35, 120, "14 нм", "Broadwell-EP", "", ""),
    ("Intel Core i3-6100", 2015, "d", 2, 4, 3.7, None, 3, 51, "14 нм", "Skylake", "skl-s", ""),
    ("Intel Core i5-6400", 2015, "d", 4, 4, 2.7, 3.3, 6, 65, "14 нм", "Skylake", "skl-s", ""),
    ("Intel Core i5-6500", 2015, "d", 4, 4, 3.2, 3.6, 6, 65, "14 нм", "Skylake", "skl-s", ""),
    ("Intel Core i5-6600K", 2015, "d", 4, 4, 3.5, 3.9, 6, 91, "14 нм", "Skylake", "skl-s", ""),
    ("Intel Core i7-6700", 2015, "d", 4, 8, 3.4, 4.0, 8, 65, "14 нм", "Skylake", "skl-s", ""),
    ("Intel Core i7-6700K", 2015, "d", 4, 8, 4.0, 4.2, 8, 91, "14 нм", "Skylake", "skl-s", ""),
    ("Intel Pentium G4560", 2017, "d", 2, 4, 3.5, None, 3, 54, "14 нм", "Kaby Lake", "kbl-s", ""),
    ("Intel Core i3-7100", 2017, "d", 2, 4, 3.9, None, 3, 51, "14 нм", "Kaby Lake", "kbl-s", ""),
    ("Intel Core i5-7400", 2017, "d", 4, 4, 3.0, 3.5, 6, 65, "14 нм", "Kaby Lake", "kbl-s", ""),
    ("Intel Core i5-7500", 2017, "d", 4, 4, 3.4, 3.8, 6, 65, "14 нм", "Kaby Lake", "kbl-s", ""),
    ("Intel Core i5-7600K", 2017, "d", 4, 4, 3.8, 4.2, 6, 91, "14 нм", "Kaby Lake", "kbl-s", ""),
    ("Intel Core i7-7700", 2017, "d", 4, 8, 3.6, 4.2, 8, 65, "14 нм", "Kaby Lake", "kbl-s", ""),
    ("Intel Core i7-7700K", 2017, "d", 4, 8, 4.2, 4.5, 8, 91, "14 нм", "Kaby Lake", "kbl-s", ""),
    ("Intel Pentium Gold G5400", 2018, "d", 2, 4, 3.7, None, 4, 58, "14 нм", "Coffee Lake", "cfl-s", ""),
    ("Intel Core i3-8100", 2017, "d", 4, 4, 3.6, None, 6, 65, "14 нм", "Coffee Lake", "cfl-s", ""),
    ("Intel Core i5-8500", 2018, "d", 6, 6, 3.0, 4.1, 9, 65, "14 нм", "Coffee Lake", "cfl-s", ""),
    ("Intel Core i5-8600K", 2017, "d", 6, 6, 3.6, 4.3, 9, 95, "14 нм", "Coffee Lake", "cfl-s", ""),
    ("Intel Core i3-9100F", 2019, "d", 4, 4, 3.6, 4.2, 6, 65, "14 нм", "Coffee Lake Refresh", "", ""),
    ("Intel Core i5-9400", 2019, "d", 6, 6, 2.9, 4.1, 9, 65, "14 нм", "Coffee Lake Refresh", "cfl-s", ""),
    ("Intel Core i7-9700", 2019, "d", 8, 8, 3.0, 4.7, 12, 65, "14 нм", "Coffee Lake Refresh", "cfl-s", ""),
    ("Intel Pentium Gold G6400", 2020, "d", 2, 4, 4.0, None, 4, 58, "14 нм", "Comet Lake", "cml-s", ""),
    ("Intel Core i5-10500", 2020, "d", 6, 12, 3.1, 4.5, 12, 65, "14 нм", "Comet Lake", "cml-s", ""),
    ("Intel Core i7-10700F", 2020, "d", 8, 16, 2.9, 4.8, 16, 65, "14 нм", "Comet Lake", "", ""),
    ("Intel Core i5-12500", 2022, "d", 6, 12, 3.0, 4.6, 18, 65, "Intel 7", "Alder Lake", "adl-s", ""),
    ("Intel Core i5-12600KF", 2021, "d", 10, 16, 3.7, 4.9, 20, 125, "Intel 7", "Alder Lake", "", "6P+4E"),
    ("Intel Core i7-12700F", 2022, "d", 12, 20, 2.1, 4.9, 25, 65, "Intel 7", "Alder Lake", "", "8P+4E"),
    ("Intel Core i5-13600KF", 2022, "d", 14, 20, 3.5, 5.1, 24, 125, "Intel 7", "Raptor Lake", "", "6P+8E"),
    ("Intel Core i7-13700KF", 2022, "d", 16, 24, 3.4, 5.4, 30, 125, "Intel 7", "Raptor Lake", "", "8P+8E"),
    ("Intel Core i5-14600KF", 2023, "d", 14, 20, 3.5, 5.3, 24, 125, "Intel 7", "Raptor Lake Refresh", "", "6P+8E"),
    ("Intel Core i7-14700KF", 2023, "d", 20, 28, 3.4, 5.6, 33, 125, "Intel 7", "Raptor Lake Refresh", "", "8P+12E"),
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
    ("Intel Core i5-4210U", 2014, "l", 2, 4, 1.7, 2.7, 3, 15, "22 нм", "Haswell", "hsw-u", ""),
    ("Intel Core i7-4510U", 2014, "l", 2, 4, 2.0, 3.1, 4, 15, "22 нм", "Haswell", "hsw-u", ""),
    ("Intel Core i7-4710HQ", 2014, "l", 4, 8, 2.5, 3.5, 6, 47, "22 нм", "Haswell", "hsw-h", ""),
    ("Intel Core i3-5005U", 2015, "l", 2, 4, 2.0, None, 3, 15, "14 нм", "Broadwell", "bdw-u", ""),
    ("Intel Core i5-5200U", 2015, "l", 2, 4, 2.2, 2.7, 3, 15, "14 нм", "Broadwell", "bdw-u", ""),
    ("Intel Core i3-6006U", 2016, "l", 2, 4, 2.0, None, 3, 15, "14 нм", "Skylake", "skl-u", ""),
    ("Intel Core i5-6200U", 2015, "l", 2, 4, 2.3, 2.8, 3, 15, "14 нм", "Skylake", "skl-u", ""),
    ("Intel Core i7-6500U", 2015, "l", 2, 4, 2.5, 3.1, 4, 15, "14 нм", "Skylake", "skl-u", ""),
    ("Intel Core i7-6700HQ", 2015, "l", 4, 8, 2.6, 3.5, 6, 45, "14 нм", "Skylake", "skl-h", ""),
    ("Intel Celeron N3350", 2016, "l", 2, 2, 1.1, 2.4, 2, 6, "14 нм", "Apollo Lake", "apl", ""),
    ("Intel Core i3-7020U", 2018, "l", 2, 4, 2.3, None, 3, 15, "14 нм", "Kaby Lake", "kbl-u", ""),
    ("Intel Core i5-7200U", 2016, "l", 2, 4, 2.5, 3.1, 3, 15, "14 нм", "Kaby Lake", "kbl-u", ""),
    ("Intel Core i7-7500U", 2016, "l", 2, 4, 2.7, 3.5, 4, 15, "14 нм", "Kaby Lake", "kbl-u", ""),
    ("Intel Core i5-7300HQ", 2017, "l", 4, 4, 2.5, 3.5, 6, 45, "14 нм", "Kaby Lake", "kbl-h", ""),
    ("Intel Core i7-7700HQ", 2017, "l", 4, 8, 2.8, 3.8, 6, 45, "14 нм", "Kaby Lake", "kbl-h", ""),
    ("Intel Celeron N4000", 2017, "l", 2, 2, 1.1, 2.6, 4, 6, "14 нм", "Gemini Lake", "glk", ""),
    ("Intel Core i5-8300H", 2018, "l", 4, 8, 2.3, 4.0, 8, 45, "14 нм", "Coffee Lake", "cfl-h", ""),
    ("Intel Core i3-1005G1", 2019, "l", 2, 4, 1.2, 3.4, 4, 15, "10 нм", "Ice Lake", "icl", ""),
    ("Intel Core i5-10500H", 2020, "l", 6, 12, 2.5, 4.5, 12, 45, "14 нм", "Comet Lake", "cml-h", ""),
    ("Intel Celeron N5100", 2021, "l", 4, 4, 1.1, 2.8, 4, 6, "10 нм", "Jasper Lake", "jsl", ""),
    ("Intel Core i5-1155G7", 2021, "l", 4, 8, 2.5, 4.5, 8, 28, "10 нм SuperFin", "Tiger Lake", "tgl", ""),
    ("Intel Core i5-11300H", 2021, "l", 4, 8, 3.1, 4.4, 8, 35, "10 нм SuperFin", "Tiger Lake", "tgl", ""),
    ("Intel Core i5-11320H", 2021, "l", 4, 8, 3.2, 4.5, 8, 35, "10 нм SuperFin", "Tiger Lake", "tgl", ""),
    ("Intel Core i7-11370H", 2021, "l", 4, 8, 3.3, 4.8, 12, 35, "10 нм SuperFin", "Tiger Lake", "tgl", ""),
    ("Intel Core i5-11260H", 2021, "l", 6, 12, 2.6, 4.4, 12, 45, "10 нм SuperFin", "Tiger Lake-H", "tgl-h", ""),
    ("Intel Core i3-1315U", 2023, "l", 6, 8, 1.2, 4.5, 10, 15, "Intel 7", "Raptor Lake", "rpl-p", "2P+4E"),
    ("Intel Core i5-1334U", 2023, "l", 10, 12, 1.3, 4.6, 12, 15, "Intel 7", "Raptor Lake", "rpl-p", "2P+8E"),
    ("Intel Core i5-1345U", 2023, "l", 10, 12, 1.6, 4.7, 12, 15, "Intel 7", "Raptor Lake", "rpl-p", "2P+8E"),
    ("Intel Core i7-13700HX", 2023, "l", 16, 24, 2.1, 5.0, 30, 55, "Intel 7", "Raptor Lake-HX", "rpl-s", "8P+8E"),
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
    ("AMD FX-6300", 2012, "d", 6, 6, 3.5, 4.1, 8, 95, "32 нм", "Piledriver", "", ""),
    ("AMD FX-8350", 2012, "d", 8, 8, 4.0, 4.2, 8, 125, "32 нм", "Piledriver", "", ""),
    ("AMD Athlon 200GE", 2018, "d", 2, 4, 3.2, None, 4, 35, "14 нм", "Zen (Raven Ridge)", "raven", ""),
    ("AMD Athlon 3000G", 2019, "d", 2, 4, 3.5, None, 4, 35, "14 нм", "Zen (Raven Ridge)", "raven", ""),
    ("AMD Ryzen 3 1200", 2017, "d", 4, 4, 3.1, 3.4, 8, 65, "14 нм", "Zen", "", ""),
    ("AMD Ryzen 5 1600 AF", 2019, "d", 6, 12, 3.2, 3.6, 16, 65, "12 нм", "Zen+", "", ""),
    ("AMD Ryzen 3 3100", 2020, "d", 4, 8, 3.6, 3.9, 16, 65, "7 нм", "Zen 2", "", ""),
    ("AMD Ryzen 5 3500", 2019, "d", 6, 6, 3.6, 4.1, 16, 65, "7 нм", "Zen 2", "", ""),
    ("AMD Ryzen 5 3500X", 2019, "d", 6, 6, 3.6, 4.1, 32, 65, "7 нм", "Zen 2", "", ""),
    ("AMD Ryzen 3 4100", 2022, "d", 4, 8, 3.8, 4.0, 4, 65, "7 нм", "Zen 2 (Renoir)", "", ""),
    ("AMD Ryzen 5 4500", 2022, "d", 6, 12, 3.6, 4.1, 8, 65, "7 нм", "Zen 2 (Renoir)", "", ""),
    ("AMD Ryzen 5 4600G", 2022, "d", 6, 12, 3.7, 4.2, 8, 65, "7 нм", "Zen 2 (Renoir)", "renoir", ""),
    ("AMD Ryzen 7 5700", 2022, "d", 8, 16, 3.7, 4.6, 16, 65, "7 нм", "Zen 3 (Cezanne)", "", ""),
    ("AMD Ryzen 5 7500F", 2023, "d", 6, 12, 3.7, 5.0, 32, 65, "5 нм", "Zen 4", "", ""),
    ("AMD Ryzen 5 8400F", 2024, "d", 6, 12, 4.2, 4.7, 16, 65, "4 нм", "Zen 4 (Phoenix)", "", ""),
    ("AMD Ryzen 9 7900", 2023, "d", 12, 24, 3.7, 5.4, 64, 65, "5 нм", "Zen 4", "raphael", ""),
    ("AMD Ryzen 9 7950X3D", 2023, "d", 16, 32, 4.2, 5.7, 128, 120, "5 нм", "Zen 4 + 3D V-Cache", "raphael", ""),
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
    ("AMD Ryzen 5 2500U", 2017, "l", 4, 8, 2.0, 3.6, 4, 15, "14 нм", "Zen (Raven Ridge)", "raven", ""),
    ("AMD Athlon Silver 3050U", 2020, "l", 2, 2, 2.3, 3.2, 4, 15, "14 нм", "Zen (Dali)", "raven", ""),
    ("AMD Athlon Gold 3150U", 2020, "l", 2, 4, 2.4, 3.3, 4, 15, "14 нм", "Zen (Dali)", "raven", ""),
    ("AMD Ryzen 3 3200U", 2019, "l", 2, 4, 2.6, 3.5, 4, 15, "12 нм", "Zen+ (Picasso)", "raven", ""),
    ("AMD Ryzen 3 3250U", 2020, "l", 2, 4, 2.6, 3.5, 4, 15, "14 нм", "Zen (Dali)", "raven", ""),
    ("AMD Ryzen 5 3550H", 2019, "l", 4, 8, 2.1, 3.7, 4, 35, "12 нм", "Zen+ (Picasso)", "raven", ""),
    ("AMD Ryzen 7 3750H", 2019, "l", 4, 8, 2.3, 4.0, 4, 35, "12 нм", "Zen+ (Picasso)", "raven", ""),
    ("AMD Ryzen 3 5300U", 2021, "l", 4, 8, 2.6, 3.8, 4, 15, "7 нм", "Zen 2 (Lucienne)", "lucienne", ""),
    ("AMD Ryzen 3 7320U", 2022, "l", 4, 8, 2.4, 4.1, 4, 15, "6 нм", "Zen 2 (Mendocino)", "mendocino", ""),
    ("AMD Ryzen 5 7430U", 2023, "l", 6, 12, 2.3, 4.3, 16, 15, "7 нм", "Zen 3 (Barcelo-R)", "barcelo", ""),
    ("AMD Ryzen 5 7235HS", 2024, "l", 4, 8, 3.2, 4.2, 8, 35, "6 нм", "Zen 3+ (Rembrandt-R)", "", ""),
    ("AMD Ryzen 7 7435HS", 2024, "l", 8, 16, 3.1, 4.5, 16, (35, 54), "6 нм", "Zen 3+ (Rembrandt-R)", "", ""),
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

    # ---------------- Qualcomm, ноутбуки на Windows для ARM ----------------
    ("Qualcomm Snapdragon X Plus X1P-42-100", 2024, "l", 8, 8, None, 3.4, 6, None, "TSMC 4 нм", "Oryon", "x1", ""),
    ("Qualcomm Snapdragon X Plus X1P-64-100", 2024, "l", 10, 10, None, 3.4, 6, None, "TSMC 4 нм", "Oryon", "x1", ""),
    ("Qualcomm Snapdragon X Elite X1E-78-100", 2024, "l", 12, 12, None, 3.4, 6, None, "TSMC 4 нм", "Oryon", "x1", ""),

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

# Телефоны и планшеты: (название, год, ядра, потоки, макс. частота ГГц, техпроцесс, ядра по типам, графика).
# Графику телефона браузер называет прямо (Adreno 740, Mali-G57 MC2…) — по ней и угадывается чип.
# TDP производители телефонных чипов не публикуют — его нет.
_MOBILE = [
    # ---------------- Qualcomm Snapdragon ----------------
    ("Qualcomm Snapdragon 8 Elite Gen 5", 2025, 8, 8, 4.6, "TSMC 3 нм", "2× Oryon + 6× Oryon", "Adreno 840"),
    ("Qualcomm Snapdragon 8 Elite", 2024, 8, 8, 4.32, "TSMC 3 нм", "2× Oryon + 6× Oryon", "Adreno 830"),
    ("Qualcomm Snapdragon 8s Gen 4", 2025, 8, 8, 3.21, "TSMC 4 нм", "1× X4 + 7× A720", "Adreno 825"),
    ("Qualcomm Snapdragon 8 Gen 3", 2023, 8, 8, 3.3, "TSMC 4 нм", "1× X4 + 5× A720 + 2× A520", "Adreno 750"),
    ("Qualcomm Snapdragon 8s Gen 3", 2024, 8, 8, 3.0, "TSMC 4 нм", "1× X4 + 4× A720 + 3× A520", "Adreno 735"),
    ("Qualcomm Snapdragon 8 Gen 2", 2022, 8, 8, 3.2, "TSMC 4 нм", "1× X3 + 4× A715/A710 + 3× A510", "Adreno 740"),
    ("Qualcomm Snapdragon 8+ Gen 1", 2022, 8, 8, 3.2, "TSMC 4 нм", "1× X2 + 3× A710 + 4× A510", "Adreno 730"),
    ("Qualcomm Snapdragon 8 Gen 1", 2021, 8, 8, 3.0, "Samsung 4 нм", "1× X2 + 3× A710 + 4× A510", "Adreno 730"),
    ("Qualcomm Snapdragon 888", 2020, 8, 8, 2.84, "Samsung 5 нм", "1× X1 + 3× A78 + 4× A55", "Adreno 660"),
    ("Qualcomm Snapdragon 870", 2021, 8, 8, 3.2, "TSMC 7 нм", "1× A77 + 3× A77 + 4× A55", "Adreno 650"),
    ("Qualcomm Snapdragon 865", 2019, 8, 8, 2.84, "TSMC 7 нм", "1× A77 + 3× A77 + 4× A55", "Adreno 650"),
    ("Qualcomm Snapdragon 855", 2019, 8, 8, 2.84, "TSMC 7 нм", "1× A76 + 3× A76 + 4× A55", "Adreno 640"),
    ("Qualcomm Snapdragon 845", 2018, 8, 8, 2.8, "Samsung 10 нм", "4× Kryo 385 Gold + 4× Silver", "Adreno 630"),
    ("Qualcomm Snapdragon 7+ Gen 3", 2024, 8, 8, 2.8, "TSMC 4 нм", "1× X4 + 4× A720 + 3× A520", "Adreno 732"),
    ("Qualcomm Snapdragon 7+ Gen 2", 2023, 8, 8, 2.91, "TSMC 4 нм", "1× X2 + 3× A710 + 4× A510", "Adreno 725"),
    ("Qualcomm Snapdragon 7 Gen 3", 2023, 8, 8, 2.63, "TSMC 4 нм", "4× A715 + 4× A510", "Adreno 720"),
    ("Qualcomm Snapdragon 7s Gen 3", 2024, 8, 8, 2.5, "TSMC 4 нм", "4× A720 + 4× A520", "Adreno 810"),
    ("Qualcomm Snapdragon 7s Gen 2", 2023, 8, 8, 2.4, "Samsung 4 нм", "4× A78 + 4× A55", "Adreno 710"),
    ("Qualcomm Snapdragon 7 Gen 1", 2022, 8, 8, 2.4, "Samsung 4 нм", "4× A710 + 4× A510", "Adreno 644"),
    ("Qualcomm Snapdragon 6 Gen 3", 2024, 8, 8, 2.4, "Samsung 4 нм", "4× A78 + 4× A55", "Adreno 710"),
    ("Qualcomm Snapdragon 6 Gen 1", 2022, 8, 8, 2.2, "TSMC 4 нм", "4× A78 + 4× A55", "Adreno 710"),
    ("Qualcomm Snapdragon 4 Gen 2", 2023, 8, 8, 2.2, "Samsung 4 нм", "2× A78 + 6× A55", "Adreno 613"),
    ("Qualcomm Snapdragon 4 Gen 1", 2022, 8, 8, 2.0, "TSMC 6 нм", "2× A78 + 6× A55", "Adreno 619"),
    ("Qualcomm Snapdragon 782G", 2022, 8, 8, 2.7, "TSMC 6 нм", "4× A78 + 4× A55", "Adreno 642L"),
    ("Qualcomm Snapdragon 778G", 2021, 8, 8, 2.4, "TSMC 6 нм", "4× A78 + 4× A55", "Adreno 642L"),
    ("Qualcomm Snapdragon 780G", 2021, 8, 8, 2.4, "Samsung 5 нм", "4× A78 + 4× A55", "Adreno 642"),
    ("Qualcomm Snapdragon 765G", 2019, 8, 8, 2.4, "Samsung 7 нм", "2× A76 + 6× A55", "Adreno 620"),
    ("Qualcomm Snapdragon 750G", 2020, 8, 8, 2.2, "Samsung 8 нм", "2× A77 + 6× A55", "Adreno 619"),
    ("Qualcomm Snapdragon 732G", 2020, 8, 8, 2.3, "Samsung 8 нм", "2× A76 + 6× A55", "Adreno 618"),
    ("Qualcomm Snapdragon 730G", 2019, 8, 8, 2.2, "Samsung 8 нм", "2× A76 + 6× A55", "Adreno 618"),
    ("Qualcomm Snapdragon 720G", 2020, 8, 8, 2.3, "Samsung 8 нм", "2× A76 + 6× A55", "Adreno 618"),
    ("Qualcomm Snapdragon 712", 2019, 8, 8, 2.3, "Samsung 10 нм", "2× A75 + 6× A55", "Adreno 616"),
    ("Qualcomm Snapdragon 695", 2021, 8, 8, 2.2, "TSMC 6 нм", "2× A78 + 6× A55", "Adreno 619"),
    ("Qualcomm Snapdragon 690", 2020, 8, 8, 2.0, "Samsung 8 нм", "2× A77 + 6× A55", "Adreno 619L"),
    ("Qualcomm Snapdragon 685", 2023, 8, 8, 2.8, "TSMC 6 нм", "4× A73 + 4× A53", "Adreno 610"),
    ("Qualcomm Snapdragon 680", 2021, 8, 8, 2.4, "TSMC 6 нм", "4× A73 + 4× A53", "Adreno 610"),
    ("Qualcomm Snapdragon 678", 2020, 8, 8, 2.2, "Samsung 11 нм", "2× A76 + 6× A55", "Adreno 612"),
    ("Qualcomm Snapdragon 665", 2019, 8, 8, 2.0, "Samsung 11 нм", "4× A73 + 4× A53", "Adreno 610"),
    ("Qualcomm Snapdragon 662", 2020, 8, 8, 2.0, "Samsung 11 нм", "4× A73 + 4× A53", "Adreno 610"),
    ("Qualcomm Snapdragon 660", 2017, 8, 8, 2.2, "Samsung 14 нм", "4× Kryo 260 Gold + 4× Silver", "Adreno 512"),
    ("Qualcomm Snapdragon 636", 2017, 8, 8, 1.8, "Samsung 14 нм", "4× Kryo 260 Gold + 4× Silver", "Adreno 509"),
    ("Qualcomm Snapdragon 625", 2016, 8, 8, 2.0, "Samsung 14 нм", "8× A53", "Adreno 506"),
    ("Qualcomm Snapdragon 480", 2021, 8, 8, 2.0, "Samsung 8 нм", "2× A76 + 6× A55", "Adreno 619"),
    ("Qualcomm Snapdragon 460", 2020, 8, 8, 1.8, "Samsung 11 нм", "4× A73 + 4× A53", "Adreno 610"),
    ("Qualcomm Snapdragon 450", 2017, 8, 8, 1.8, "Samsung 14 нм", "8× A53", "Adreno 506"),
    ("Qualcomm Snapdragon 439", 2018, 8, 8, 1.95, "TSMC 12 нм", "8× A53", "Adreno 505"),

    # ---------------- MediaTek ----------------
    ("MediaTek Dimensity 9400", 2024, 8, 8, 3.63, "TSMC 3 нм", "1× X925 + 3× X4 + 4× A720", "Immortalis-G925 MC12"),
    ("MediaTek Dimensity 9300", 2023, 8, 8, 3.25, "TSMC 4 нм", "4× X4 + 4× A720", "Immortalis-G720 MC12"),
    ("MediaTek Dimensity 9200", 2022, 8, 8, 3.05, "TSMC 4 нм", "1× X3 + 3× A715 + 4× A510", "Immortalis-G715 MC11"),
    ("MediaTek Dimensity 9000", 2021, 8, 8, 3.05, "TSMC 4 нм", "1× X2 + 3× A710 + 4× A510", "Mali-G710 MC10"),
    ("MediaTek Dimensity 8300", 2023, 8, 8, 3.35, "TSMC 4 нм", "4× A715 + 4× A510", "Mali-G615 MC6"),
    ("MediaTek Dimensity 8200", 2022, 8, 8, 3.1, "TSMC 4 нм", "4× A78 + 4× A55", "Mali-G610 MC6"),
    ("MediaTek Dimensity 8100", 2022, 8, 8, 2.85, "TSMC 5 нм", "4× A78 + 4× A55", "Mali-G610 MC6"),
    ("MediaTek Dimensity 8050", 2023, 8, 8, 3.0, "TSMC 6 нм", "4× A78 + 4× A55", "Mali-G77 MC9"),
    ("MediaTek Dimensity 8020", 2023, 8, 8, 2.6, "TSMC 6 нм", "4× A78 + 4× A55", "Mali-G77 MC9"),
    ("MediaTek Dimensity 1200", 2021, 8, 8, 3.0, "TSMC 6 нм", "4× A78 + 4× A55", "Mali-G77 MC9"),
    ("MediaTek Dimensity 7300", 2024, 8, 8, 2.5, "TSMC 4 нм", "4× A78 + 4× A55", "Mali-G615 MC2"),
    ("MediaTek Dimensity 7200", 2023, 8, 8, 2.8, "TSMC 4 нм", "2× A715 + 6× A510", "Mali-G610 MC4"),
    ("MediaTek Dimensity 7050", 2023, 8, 8, 2.6, "TSMC 6 нм", "2× A78 + 6× A55", "Mali-G68 MC4"),
    ("MediaTek Dimensity 7025", 2023, 8, 8, 2.5, "TSMC 6 нм", "2× A78 + 6× A55", "PowerVR BXM-8-256"),
    ("MediaTek Dimensity 1080", 2022, 8, 8, 2.6, "TSMC 6 нм", "2× A78 + 6× A55", "Mali-G68 MC4"),
    ("MediaTek Dimensity 920", 2021, 8, 8, 2.5, "TSMC 6 нм", "2× A78 + 6× A55", "Mali-G68 MC4"),
    ("MediaTek Dimensity 900", 2021, 8, 8, 2.4, "TSMC 6 нм", "2× A78 + 6× A55", "Mali-G68 MC4"),
    ("MediaTek Dimensity 6300", 2024, 8, 8, 2.4, "TSMC 6 нм", "2× A76 + 6× A55", "Mali-G57 MC2"),
    ("MediaTek Dimensity 6100+", 2023, 8, 8, 2.2, "TSMC 6 нм", "2× A76 + 6× A55", "Mali-G57 MC2"),
    ("MediaTek Dimensity 6080", 2023, 8, 8, 2.4, "TSMC 6 нм", "2× A76 + 6× A55", "Mali-G57 MC2"),
    ("MediaTek Dimensity 6020", 2023, 8, 8, 2.2, "TSMC 7 нм", "2× A76 + 6× A55", "Mali-G57 MC2"),
    ("MediaTek Dimensity 810", 2021, 8, 8, 2.4, "TSMC 6 нм", "2× A76 + 6× A55", "Mali-G57 MC2"),
    ("MediaTek Dimensity 800U", 2020, 8, 8, 2.4, "TSMC 7 нм", "2× A76 + 6× A55", "Mali-G57 MC3"),
    ("MediaTek Dimensity 720", 2020, 8, 8, 2.0, "TSMC 7 нм", "2× A76 + 6× A55", "Mali-G57 MC3"),
    ("MediaTek Dimensity 700", 2020, 8, 8, 2.2, "TSMC 7 нм", "2× A76 + 6× A55", "Mali-G57 MC2"),
    ("MediaTek Helio G99", 2022, 8, 8, 2.2, "TSMC 6 нм", "2× A76 + 6× A55", "Mali-G57 MC2"),
    ("MediaTek Helio G96", 2021, 8, 8, 2.05, "TSMC 12 нм", "2× A76 + 6× A55", "Mali-G57 MC2"),
    ("MediaTek Helio G95", 2020, 8, 8, 2.05, "TSMC 12 нм", "2× A76 + 6× A55", "Mali-G76 MC4"),
    ("MediaTek Helio G90T", 2019, 8, 8, 2.05, "TSMC 12 нм", "2× A76 + 6× A55", "Mali-G76 MC4"),
    ("MediaTek Helio G88", 2021, 8, 8, 2.0, "TSMC 12 нм", "2× A75 + 6× A55", "Mali-G52 MC2"),
    ("MediaTek Helio G85", 2020, 8, 8, 2.0, "TSMC 12 нм", "2× A75 + 6× A55", "Mali-G52 MC2"),
    ("MediaTek Helio G81", 2024, 8, 8, 2.0, "TSMC 12 нм", "2× A75 + 6× A55", "Mali-G52 MC2"),
    ("MediaTek Helio G80", 2020, 8, 8, 2.0, "TSMC 12 нм", "2× A75 + 6× A55", "Mali-G52 MC2"),
    ("MediaTek Helio G70", 2020, 8, 8, 2.0, "TSMC 12 нм", "2× A75 + 6× A55", "Mali-G52 MC2"),
    ("MediaTek Helio P70", 2018, 8, 8, 2.1, "TSMC 12 нм", "4× A73 + 4× A53", "Mali-G72 MP3"),
    ("MediaTek Helio G37", 2021, 8, 8, 2.3, "TSMC 12 нм", "8× A53", "PowerVR GE8320"),
    ("MediaTek Helio G36", 2022, 8, 8, 2.2, "TSMC 12 нм", "8× A53", "PowerVR GE8320"),
    ("MediaTek Helio G35", 2020, 8, 8, 2.3, "TSMC 12 нм", "8× A53", "PowerVR GE8320"),
    ("MediaTek Helio P35", 2018, 8, 8, 2.3, "TSMC 12 нм", "8× A53", "PowerVR GE8320"),
    ("MediaTek Helio G25", 2020, 8, 8, 2.0, "TSMC 12 нм", "8× A53", "PowerVR GE8320"),
    ("MediaTek Helio P22", 2018, 8, 8, 2.0, "TSMC 12 нм", "8× A53", "PowerVR GE8320"),
    ("MediaTek Helio A22", 2018, 4, 4, 2.0, "TSMC 12 нм", "4× A53", "PowerVR GE8320"),

    # ---------------- Samsung Exynos ----------------
    ("Samsung Exynos 2400", 2024, 10, 10, 3.2, "Samsung 4 нм", "1× X4 + 5× A720 + 4× A520", "Xclipse 940"),
    ("Samsung Exynos 2200", 2022, 8, 8, 2.8, "Samsung 4 нм", "1× X2 + 3× A710 + 4× A510", "Xclipse 920"),
    ("Samsung Exynos 2100", 2021, 8, 8, 2.9, "Samsung 5 нм", "1× X1 + 3× A78 + 4× A55", "Mali-G78 MP14"),
    ("Samsung Exynos 990", 2020, 8, 8, 2.73, "Samsung 7 нм", "2× M5 + 2× A76 + 4× A55", "Mali-G77 MP11"),
    ("Samsung Exynos 9820", 2019, 8, 8, 2.73, "Samsung 8 нм", "2× M4 + 2× A75 + 4× A55", "Mali-G76 MP12"),
    ("Samsung Exynos 1580", 2025, 8, 8, 2.9, "Samsung 4 нм", "4× A720 + 4× A520", "Xclipse 540"),
    ("Samsung Exynos 1480", 2024, 8, 8, 2.75, "Samsung 4 нм", "4× A78 + 4× A55", "Xclipse 530"),
    ("Samsung Exynos 1380", 2023, 8, 8, 2.4, "Samsung 5 нм", "4× A78 + 4× A55", "Mali-G68 MP5"),
    ("Samsung Exynos 1330", 2023, 8, 8, 2.4, "Samsung 5 нм", "2× A78 + 6× A55", "Mali-G68 MP2"),
    ("Samsung Exynos 1280", 2022, 8, 8, 2.4, "Samsung 5 нм", "2× A78 + 6× A55", "Mali-G68 MP4"),
    ("Samsung Exynos 9611", 2019, 8, 8, 2.3, "Samsung 10 нм", "4× A73 + 4× A53", "Mali-G72 MP3"),
    ("Samsung Exynos 850", 2020, 8, 8, 2.0, "Samsung 8 нм", "8× A55", "Mali-G52 MP1"),

    # ---------------- Google Tensor ----------------
    ("Google Tensor G5", 2025, 8, 8, 3.78, "TSMC 3 нм", "1× X4 + 5× A725 + 2× A520", "PowerVR DXT-48-1536"),
    ("Google Tensor G4", 2024, 8, 8, 3.1, "Samsung 4 нм", "1× X4 + 3× A720 + 4× A520", "Mali-G715 MC7"),
    ("Google Tensor G3", 2023, 9, 9, 2.91, "Samsung 4 нм", "1× X3 + 4× A715 + 4× A510", "Immortalis-G715s MC10"),
    ("Google Tensor G2", 2022, 8, 8, 2.85, "Samsung 5 нм", "2× X1 + 2× A78 + 4× A55", "Mali-G710 MP7"),
    ("Google Tensor G1", 2021, 8, 8, 2.8, "Samsung 5 нм", "2× X1 + 2× A76 + 4× A55", "Mali-G78 MP20"),

    # ---------------- Unisoc и HiSilicon (Huawei) ----------------
    ("Unisoc T616", 2021, 8, 8, 2.0, "TSMC 12 нм", "2× A75 + 6× A55", "Mali-G57 MP1"),
    ("Unisoc T612", 2022, 8, 8, 1.8, "TSMC 12 нм", "2× A75 + 6× A55", "Mali-G57 MP1"),
    ("Unisoc T606", 2021, 8, 8, 1.6, "TSMC 12 нм", "2× A75 + 6× A55", "Mali-G57 MP1"),
    ("Unisoc T618", 2020, 8, 8, 2.0, "TSMC 12 нм", "2× A75 + 6× A55", "Mali-G52 MP2"),
    ("Unisoc T610", 2019, 8, 8, 1.8, "TSMC 12 нм", "2× A75 + 6× A55", "Mali-G52 MP2"),
    ("Unisoc SC9863A", 2018, 8, 8, 1.6, "TSMC 28 нм", "8× A55", "PowerVR GE8322"),
    ("HiSilicon Kirin 9000S", 2023, 8, 12, 2.62, "SMIC 7 нм", "1× TaiShan V120 + 3× TaiShan V120 + 4× A510", "Maleoon 910"),
    ("HiSilicon Kirin 990", 2019, 8, 8, 2.86, "TSMC 7 нм", "2× A76 + 2× A76 + 4× A55", "Mali-G76 MP16"),
    ("HiSilicon Kirin 980", 2018, 8, 8, 2.6, "TSMC 7 нм", "2× A76 + 2× A76 + 4× A55", "Mali-G76 MP10"),
    ("HiSilicon Kirin 710", 2018, 8, 8, 2.2, "TSMC 12 нм", "4× A73 + 4× A53", "Mali-G51 MP4"),

    # ---------------- Apple, iPhone ----------------
    ("Apple A19 Pro", 2025, 6, 6, 4.26, "TSMC 3 нм", "2P + 4E", "Apple GPU"),
    ("Apple A19", 2025, 6, 6, 4.26, "TSMC 3 нм", "2P + 4E", "Apple GPU"),
    ("Apple A18 Pro", 2024, 6, 6, 4.05, "TSMC 3 нм", "2P + 4E", "Apple GPU"),
    ("Apple A18", 2024, 6, 6, 4.04, "TSMC 3 нм", "2P + 4E", "Apple GPU"),
    ("Apple A17 Pro", 2023, 6, 6, 3.78, "TSMC 3 нм", "2P + 4E", "Apple GPU"),
    ("Apple A16 Bionic", 2022, 6, 6, 3.46, "TSMC 4 нм", "2P + 4E", "Apple GPU"),
    ("Apple A15 Bionic", 2021, 6, 6, 3.23, "TSMC 5 нм", "2P + 4E", "Apple GPU"),
    ("Apple A14 Bionic", 2020, 6, 6, 3.0, "TSMC 5 нм", "2P + 4E", "Apple GPU"),
    ("Apple A13 Bionic", 2019, 6, 6, 2.65, "TSMC 7 нм", "2P + 4E", "Apple GPU"),
    ("Apple A12 Bionic", 2018, 6, 6, 2.49, "TSMC 7 нм", "2P + 4E", "Apple GPU"),
    ("Apple A11 Bionic", 2017, 6, 6, 2.39, "TSMC 10 нм", "2P + 4E", "Apple GPU"),
]

SEGMENTS = {"d": "настольный ПК", "l": "ноутбук", "m": "Mac", "p": "телефон / планшет"}

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
    (r"0x0*591B", "kbl-h"),
    (r"0x0*59(02|12)", "kbl-s"),
    (r"0x0*59(06|16|1E|26|27)", "kbl-u"),
    (r"0x0*191B", "skl-h"),
    (r"0x0*19(02|12)", "skl-s"),
    (r"0x0*19(06|16|1E|26|27)", "skl-u"),
    (r"0x0*16(06|16|1E|26|2B)", "bdw-u"),
    (r"0x0*04(06|16)", "hsw-h"),
    (r"0x0*04(02|12|1E)", "hsw-s"),
    (r"0x0*0A(06|16|1E|26|2E)", "hsw-u"),
    (r"0x0*01(52|62)", "ivb-s"),
    (r"0x0*01(02|12|22)", "snb-s"),
    (r"0x0*8A5[0-9A-F]", "icl"),
    (r"0x0*318[45]", "glk"),
    (r"0x0*5A8[45]", "apl"),
    (r"0x0*4E[5-7][0-9A-F]", "jsl"),
    # Qualcomm Snapdragon X (Windows на ARM)
    (r"Adreno.{0,8}X1", "x1"),
    # если кода устройства нет (Firefox, macOS) — по названию
    (r"Iris\(R\) Xe|Iris Xe", "tgl adl-p rpl-p"),
    (r"UHD Graphics 620", "kbl-r whl cml-u"),
    (r"UHD Graphics 630", "cfl-s cfl-h cml-s cml-h"),
    (r"UHD Graphics 7[3-7]0", "adl-s rpl-s rkl"),
    (r"UHD Graphics 60[05]", "glk"),
    (r"Iris\(R\) Plus|Iris Plus", "icl"),
    (r"Intel.*Arc(\(TM\))? (Graphics|130V|140V|140T)", "mtl lnl arl-h"),
    # старые «HD Graphics» (без U в начале — иначе спутаются с UHD Graphics)
    (r"(^|[^U])HD Graphics 630", "kbl-s kbl-h"),
    (r"(^|[^U])HD Graphics 620", "kbl-u"),
    (r"(^|[^U])HD Graphics 610", "kbl-s"),
    (r"(^|[^U])HD Graphics 530", "skl-s skl-h"),
    (r"(^|[^U])HD Graphics 520", "skl-u"),
    (r"(^|[^U])HD Graphics 5500", "bdw-u"),
    (r"(^|[^U])HD Graphics 50[05]", "apl"),
    (r"(^|[^U])HD Graphics 4600", "hsw-s hsw-h"),
    (r"(^|[^U])HD Graphics 4400", "hsw-u hsw-s"),
    (r"(^|[^U])HD Graphics (4000|2500)", "ivb-s"),
    (r"(^|[^U])HD Graphics (3000|2000)", "snb-s"),
]

# Модель телефона → чип. Chrome на Android сообщает модель (SM-A546E, Pixel 7…), Samsung Internet — тоже.
# Если у модели в разных странах разные чипы, перечислены оба — выбирает графика.
MODEL_RULES = [
    # Samsung Galaxy A и M
    (r"^SM-A032", "unisoc-sc9863a"),
    (r"^SM-A035", "unisoc-t606"),
    (r"^SM-A025", "qualcomm-snapdragon-450"),
    (r"^SM-A03[7]|^SM-A045|^SM-A125", "mediatek-helio-p35"),
    (r"^SM-A047|^SM-A127|^SM-A13[57]|^SM-A217|^SM-M127", "samsung-exynos-850"),
    (r"^SM-A055", "mediatek-helio-g85"),
    (r"^SM-A057|^SM-A235", "qualcomm-snapdragon-680"),
    (r"^SM-A136|^SM-A226", "mediatek-dimensity-700"),
    (r"^SM-A145", "samsung-exynos-850 mediatek-helio-g80"),
    (r"^SM-A146", "samsung-exynos-1330 mediatek-dimensity-700"),
    (r"^SM-A155|^SM-A165|^SM-A245", "mediatek-helio-g99"),
    (r"^SM-A156", "mediatek-dimensity-6100-plus"),
    (r"^SM-A166", "samsung-exynos-1330 mediatek-dimensity-6300"),
    (r"^SM-A225|^SM-A325|^SM-M325", "mediatek-helio-g80"),
    (r"^SM-A236", "qualcomm-snapdragon-695"),
    (r"^SM-A256|^SM-A336|^SM-A536|^SM-M336|^SM-M346", "samsung-exynos-1280"),
    (r"^SM-A266|^SM-A356|^SM-A546", "samsung-exynos-1380"),
    (r"^SM-A326", "mediatek-dimensity-720"),
    (r"^SM-A346", "mediatek-dimensity-1080"),
    (r"^SM-A366", "qualcomm-snapdragon-6-gen-3"),
    (r"^SM-A515|^SM-M[23]15", "samsung-exynos-9611"),
    (r"^SM-A525|^SM-A725", "qualcomm-snapdragon-720g"),
    (r"^SM-A526", "qualcomm-snapdragon-750g"),
    (r"^SM-A528|^SM-M526", "qualcomm-snapdragon-778g"),
    (r"^SM-A556", "samsung-exynos-1480"),
    (r"^SM-A566", "samsung-exynos-1580"),
    (r"^SM-A715", "qualcomm-snapdragon-730g"),
    (r"^SM-M146", "samsung-exynos-1330"),
    # Samsung Galaxy S, Note, Z
    (r"^SM-S93[168]", "qualcomm-snapdragon-8-elite"),
    (r"^SM-S928|^SM-F956|^SM-F741", "qualcomm-snapdragon-8-gen-3"),
    (r"^SM-S92[16]", "samsung-exynos-2400 qualcomm-snapdragon-8-gen-3"),
    (r"^SM-S721", "samsung-exynos-2400"),
    (r"^SM-S91[168]|^SM-F946|^SM-F731", "qualcomm-snapdragon-8-gen-2"),
    (r"^SM-F936|^SM-F721", "qualcomm-snapdragon-8-plus-gen-1"),
    (r"^SM-S711|^SM-S90[168]", "samsung-exynos-2200 qualcomm-snapdragon-8-gen-1"),
    (r"^SM-G99[0168]", "samsung-exynos-2100 qualcomm-snapdragon-888"),
    (r"^SM-G780", "samsung-exynos-990"),
    (r"^SM-G781", "qualcomm-snapdragon-865"),
    (r"^SM-G98[0-8]|^SM-N98", "samsung-exynos-990 qualcomm-snapdragon-865"),
    (r"^SM-G97[0357]", "samsung-exynos-9820 qualcomm-snapdragon-855"),
    # Google Pixel
    (r"^Pixel 10", "google-tensor-g5"),
    (r"^Pixel 9", "google-tensor-g4"),
    (r"^Pixel 8", "google-tensor-g3"),
    (r"^Pixel 7", "google-tensor-g2"),
    (r"^Pixel 6", "google-tensor-g1"),
    (r"^Pixel 5|^Pixel 4a \(5G\)", "qualcomm-snapdragon-765g"),
    (r"^Pixel 4a$", "qualcomm-snapdragon-730g"),
]

# Самые распространённые модели. Если признаки одинаково подходят нескольким процессорам
# (например, графика Adreno 610 стоит в Snapdragon 680, 685, 665…), первым предлагается распространённый.
POPULAR = {
    "qualcomm-snapdragon-680", "qualcomm-snapdragon-695", "qualcomm-snapdragon-720g", "qualcomm-snapdragon-778g",
    "qualcomm-snapdragon-855", "qualcomm-snapdragon-7s-gen-2", "mediatek-helio-g85", "mediatek-helio-g99",
    "mediatek-helio-p35", "mediatek-dimensity-1080", "unisoc-t606",
    "intel-core-i5-4460", "intel-core-i5-1135g7", "intel-core-i5-1235u", "intel-core-i5-1335u", "intel-core-i5-12400",
    "intel-core-i5-10210u", "intel-core-i5-8250u", "intel-core-i7-10750h", "intel-core-i5-7200u",
    "intel-core-i5-6200u", "amd-ryzen-5-5625u", "amd-ryzen-5-5500u", "amd-ryzen-7-6800h",
}


def _key(name):
    return re.sub(r"[^a-z0-9]+", "-", name.lower().replace("+", " plus ")).strip("-")


VENDORS = {"intel": "Intel", "amd": "AMD", "apple": "Apple", "qualcomm": "Qualcomm", "mediatek": "MediaTek",
           "samsung": "Samsung", "google": "Google", "unisoc": "Unisoc", "hisilicon": "HiSilicon"}


def _vendor(name):
    return name.split()[0].lower()  # intel / amd / apple / qualcomm / mediatek / …


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
    rows = [r + ("",) for r in _ROWS]
    rows += [(name, year, "p", cores, threads, None, boost, None, None, proc, arch, "", "", gpu)
             for name, year, cores, threads, boost, proc, arch, gpu in _MOBILE]
    for name, year, seg, cores, threads, base, boost, l3, tdp, proc, arch, fam, pe, gpu in rows:
        v = _vendor(name)
        k = _key(name)
        assert k not in out, f"повтор в справочнике: {name}"
        out[k] = dict(
            key=k, name=name, vendor=v, year=year, seg=seg, segment=SEGMENTS[seg],
            cores=cores, threads=threads, base=base, boost=boost, l3=l3,
            tdp=_tdp_avg(tdp), tdp_text=_tdp_text(tdp, v), process=proc, arch=arch,
            fam=fam.split(), pe=pe, gpu=gpu, pop=k in POPULAR,
        )
    return out


CATALOG = _build()


def get(key):
    return CATALOG.get(key or "")


def _norm(s):
    s = (s or "").lower().replace("+", "plus")
    s = re.sub(r"\(r\)|\(tm\)|®|™|with radeon graphics|radeon graphics|processor|cpu|@.*$", " ", s)
    return re.sub(r"[^a-z0-9]", "", s)


_NORMED = sorted(((_norm(re.sub(r"^(Intel|AMD|Apple|Qualcomm|MediaTek|Samsung|Google|Unisoc|HiSilicon)\s+(Core\s+)?",
                                "", c["name"])), c) for c in CATALOG.values()),
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


def vendor_of_text(name):
    """Фирма по названию, вписанному от руки: «Snapdragon 8 Gen 3» → qualcomm."""
    low = (name or "").lower()
    for v, words in (("intel", ("intel", "core i", "pentium", "celeron", "xeon")), ("amd", ("amd", "ryzen", "athlon")),
                     ("qualcomm", ("qualcomm", "snapdragon")), ("mediatek", ("mediatek", "dimensity", "helio")),
                     ("samsung", ("exynos",)), ("google", ("tensor",)), ("unisoc", ("unisoc",)),
                     ("hisilicon", ("kirin", "hisilicon")), ("apple", ("apple",))):
        if any(w in low for w in words):
            return v
    return "other"


def for_browser():
    """Компактный справочник для страницы теста (угадывание и поиск)."""
    out = []
    for c in CATALOG.values():
        row = dict(key=c["key"], name=c["name"], vendor=c["vendor"], year=c["year"], seg=c["seg"],
                   cores=c["cores"], threads=c["threads"], boost=c["boost"], tdp=c["tdp"], fam=c["fam"])
        if c["gpu"]:
            row["gpu"] = c["gpu"]
        if c["pop"]:
            row["pop"] = 1
        out.append(row)
    return out
