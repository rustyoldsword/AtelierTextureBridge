# Atelier Texture Bridge — 3BA ⇄ UNP ⇄ UBE

**English.** A standalone Windows 10/11 tool that moves Skyrim body overlays and skin textures between the
**3BA / CBBE**, **UNP / BHUNP** (both with the vanilla head) and **UBE** UV layouts, in any direction. No Blender
needed: pixels are moved along UV correspondence maps baked once from the body meshes, so colour and alpha stay exactly
as authored. Drag in textures or a whole mod folder, pick From and To, press **Convert**. Body, hands and feet textures can be
combined into one UBE atlas (**Find atlases**). Interface in English, Russian, German, French, Spanish, Chinese,
Japanese and Korean. Details below are in Russian.

---

Standalone-программа для Windows 10/11: переносит оверлеи и текстуры тела между раскладками
**3BA / CBBE**, **UNP / BHUNP** (у обоих ванильная голова) и **UBE** — в любом направлении. Blender не нужен.

## Как пользоваться
1. Запустите `AtelierTextureBridge.exe`. Устанавливать ничего не нужно.
2. Вверху справа выберите, **из** какой раскладки и **в** какую переносить (3BA / CBBE, UNP / BHUNP, UBE).
   Кнопка ⇄ меняет их местами.
3. Перетащите в окно `.dds`, `.png` или `.tga`, либо целую папку мода. Папка сканируется вместе с подпапками.
4. Проверьте колонку **«Часть тела»** (тело / руки / ступни / лицо). Часть угадывается по имени файла и папке
   (`Face`, `Hands`, `Feet` — как у SlaveTats).
5. Нажмите **«Конвертировать»**.

По умолчанию результат пишется в подпапку с именем целевого тела (`UBE\`, `3BA\` или `UNP\`) рядом с исходником. Для папки мода — внутрь неё,
с той же структурой подпапок. Исходники программа не трогает.

Язык интерфейса переключается справа вверху: English (по умолчанию), Русский, Deutsch, Français, Español,
简体中文, 日本語, 한국어. Строки лежат в `app/i18n.py`.

Для скриптов есть консольный режим (код выхода 0 = успех, итог пишется в `<dst>.log`):
```
AtelierTextureBridge.exe --cli 3ba-unp|unp-ube|... body|hands|feet|head <src> <dst> [--res 2048] [--format BC7_UNORM]
```

## Колонка «Раскладка»
Показывает, какая доля нарисованного лежит на UV-островах выбранной исходной раскладки.
⚠ ниже 50 % обычно означает, что выбрано не то направление или не та часть тела.
Высокий процент сам по себе ничего не гарантирует: раскладки сильно перекрываются. Смотрите предпросмотр.

## Один атлас UBE из нескольких текстур 3BA / UNP (с 1.1)
В UBE тело, руки и ступни лежат в одной текстуре, а в 3BA и UNP — в разных. Чтобы получить один файл:
- нажмите **«Собрать атласы»**: программа сама находит комплекты (`femalebody_1` + `femalehands_1` в одной папке
  или одинаковые имена в папках `Body/Hands/Feet` у SlaveTats);
- либо выделите строки и выберите в контекстном меню **«Объединить в один атлас UBE»**.

Группа показывается одной строкой «Атлас UBE · <имя тела>». Результат получает имя текстуры тела.
«Разгруппировать» возвращает строки обратно. В направлениях не в UBE файлы группы конвертируются по отдельности.

## Что важно знать
- **«Тело» включает ступни.** В CBBE и UNP ступни нарисованы прямо на текстуре тела (пальцы и подошвы в верхних углах
  `femalebody_1.dds`), поэтому «Тело» переносит тело и ступни, в любом направлении. До 1.1 ступни с текстуры тела терялись.
  «Ступни» отдельно — для оверлеев только на ступнях (область Feet у SlaveTats).
- **Руки из UBE — отдельным файлом автоматически (с 1.2).** В UBE руки лежат в атласе тела, а у 3BA и UNP — в своей
  текстуре. Поэтому текстура UBE с частью «Тело» при переводе в 3BA / UNP даёт два файла: тело (со ступнями) и рядом
  руки (`femalebody_1` → `femalehands_1`, без «body» в имени — суффикс `_hands`). Выключается галочкой
  «Из UBE заодно делать текстуру рук». В консольном режиме часть по-прежнему задаётся явно.
- Руки из UBE в 3BA / UNP всегда мягче оригинала: в атласе UBE на них в ~3 раза меньше пикселей по стороне.
- **Лицо**: ванильная голова ⇄ голова UBE. У 3BA и UNP голова одна и та же (ванильная), лицо между ними не меняется.
- **UNP:** карты сделаны по эталонному телу BHUNP (UUNP-раскладка — у UNP, UUNP и BHUNP она общая). Формы CBBE и UNP
  разные: тело UNP обтягивается по поверхности CBBE (одна обтяжка на оба направления), и карты 3BA ⇄ UNP взаимно
  обратны с той же точностью, что 3BA ⇄ UBE (круговой тест ~0,4–0,5 px на 4K).
- Непрозрачные текстуры (кожа, детали) получают заполнение швов и сплошную альфу. Режим «Авто» определяет их сам.
- Карты нормалей переносятся, но направления в них не поворачиваются, поэтому проверяйте их в игре.
- Мужские меши в конвертере не участвуют: только женские тела 3BA, UNP и UBE.

## Как это устроено (для сборки)
- `tools/bake_maps.py` — запускается в Blender на `StencilTool.blend` (UBE Texture Conversion Tool от Grognak) и
  запекает 8 карт соответствия UV 4096 px (по 4 на каждое направление).
- `tools/nif_geom.py` — читает вершины, UV и треугольники из NIF Skyrim SE (в том числе скиннинговых, из
  `NiSkinPartition`) — без NIF-плагина для Blender.
- `tools/bake_unp.py` — кладёт BHUNP-тело, руки и ступни в ту же сцену, обтягивает каждое направление по поверхности
  тела CBBE (Shrinkwrap, ближайшая точка; одна обтяжка на оба направления) и запекает 6 карт 3BA ⇄ UNP. UNP ⇄ UBE собирается из них в приложении.
- `tools/pack_maps.py` — чистит выбросы, сжимает карты в `app/maps/*.npz` (uint16) и печатает круговой тест точности.
- `app/core.py` — конвертация: premultiplied-bilinear выборка по карте, DDS через texconv.
- `app/main.py` — интерфейс (PyQt6, тема Dwemer Atelier из MO2, шрифт Atelier UI).
- `build.py` — сборка PyInstaller → `dist/AtelierTextureBridge/` + zip.

```
python -m venv venv
venv\Scripts\python.exe -m pip install PyQt6 numpy pillow pyinstaller
blender.exe -b <путь>\StencilTool.blend --python tools\bake_maps.py -- 4096 maps_raw
venv\Scripts\python.exe tools\nif_geom.py "<BHUNP ShapeData>\BHUNP 3BBB Advanced Ver 4.nif" unp\bhunp_body.npz   # + Hands Ver 3, Feet
blender.exe -b <путь>\StencilTool.blend --python tools\bake_unp.py -- 4096 maps_raw unp NEAREST_SURFACEPOINT single
venv\Scripts\python.exe tools\pack_maps.py
venv\Scripts\python.exe build.py
```
Готовые карты уже лежат в `app/maps`: для обычной сборки достаточно последней строки, Blender не нужен.

## Благодарности и лицензии
- Меши для карт UV — из UBE Texture Conversion Tool от Grognak (`StencilTool.blend`) и BHUNP (Baka Haeun UNP)
  от Bakafactory.
- `texconv.exe` — Microsoft DirectXTex, MIT.
- Шрифт Atelier UI — Inter 4.1 (Rasmus Andersson), SIL Open Font License 1.1 (`app/assets/font/OFL.txt`).
- PyQt6 / Qt 6 — GPLv3 / LGPLv3; NumPy — BSD; Pillow — HPND.
- Сама программа — GPL-3.0 (`LICENSE`).
