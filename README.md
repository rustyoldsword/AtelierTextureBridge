# Atelier Texture Bridge — 3BA ⇄ UBE

**English.** A standalone Windows 10/11 tool that moves Skyrim body overlays and skin textures between the
**3BA / CBBE** (plus vanilla head) UV layout and **UBE**, in both directions. No Blender needed: pixels are moved
along UV correspondence maps baked once from the two meshes, so colour and alpha stay exactly as authored.
Drag in textures or a whole mod folder, pick the direction, press **Convert**. Body, hands and feet textures can be
combined into one UBE atlas (**Find atlases**). Interface in English, Russian, German, French, Spanish, Chinese,
Japanese and Korean. Details below are in Russian.

---

Standalone-программа для Windows 10/11: переносит оверлеи и текстуры тела между раскладками
**3BA / CBBE** (и ванильной головы) и **UBE**. Работает в обе стороны. Blender не нужен.

## Как пользоваться
1. Запустите `AtelierTextureBridge.exe`. Устанавливать ничего не нужно.
2. Вверху справа выберите направление: **3BA → UBE** или **UBE → 3BA**.
3. Перетащите в окно `.dds`, `.png` или `.tga`, либо целую папку мода. Папка сканируется вместе с подпапками.
4. Проверьте колонку **«Часть тела»** (тело / руки / ступни / лицо). Часть угадывается по имени файла и папке
   (`Face`, `Hands`, `Feet` — как у SlaveTats).
5. Нажмите **«Конвертировать»**.

По умолчанию результат пишется в подпапку `UBE\` (или `3BA\`) рядом с исходником. Для папки мода — внутрь неё,
с той же структурой подпапок. Исходники программа не трогает.

Язык интерфейса переключается справа вверху: English (по умолчанию), Русский, Deutsch, Français, Español,
简体中文, 日本語, 한국어. Строки лежат в `app/i18n.py`.

Для скриптов есть консольный режим (код выхода 0 = успех, итог пишется в `<dst>.log`):
```
AtelierTextureBridge.exe --cli to_ube|to_3ba body|hands|feet|head <src> <dst> [--res 2048] [--format BC7_UNORM]
```

## Колонка «Раскладка»
Показывает, какая доля нарисованного лежит на UV-островах выбранной исходной раскладки.
⚠ ниже 50 % обычно означает, что выбрано не то направление или не та часть тела.
Высокий процент сам по себе ничего не гарантирует: раскладки сильно перекрываются. Смотрите предпросмотр.

## Один атлас UBE из нескольких текстур 3BA (с 1.1)
В UBE тело, руки и ступни лежат в одной текстуре, а в 3BA — в разных. Чтобы получить один файл:
- нажмите **«Собрать атласы»**: программа сама находит комплекты (`femalebody_1` + `femalehands_1` в одной папке
  или одинаковые имена в папках `Body/Hands/Feet` у SlaveTats);
- либо выделите строки и выберите в контекстном меню **«Объединить в один атлас UBE»**.

Группа показывается одной строкой «Атлас UBE · <имя тела>». Результат получает имя текстуры тела.
«Разгруппировать» возвращает строки обратно. В направлении UBE → 3BA файлы группы конвертируются по отдельности.

## Что важно знать
- **«Тело» включает ступни.** В CBBE ступни нарисованы прямо на текстуре тела (пальцы и подошвы в верхних углах
  `femalebody_1.dds`), поэтому «Тело» переносит тело и ступни, в обе стороны. До 1.1 ступни с текстуры тела терялись.
  «Ступни» отдельно — для оверлеев только на ступнях (область Feet у SlaveTats).
- В обратную сторону атлас UBE раскладывается в отдельный файл для каждой части: поставьте одну и ту же текстуру
  дважды, как «Тело» и как «Руки».
- **Лицо**: ванильная голова ⇄ голова UBE.
- Непрозрачные текстуры (кожа, детали) получают заполнение швов и сплошную альфу. Режим «Авто» определяет их сам.
- Карты нормалей переносятся, но направления в них не поворачиваются, поэтому проверяйте их в игре.
- Мужские меши в конвертере не участвуют: только женское тело 3BA и UBE.

## Как это устроено (для сборки)
- `tools/bake_maps.py` — запускается в Blender на `StencilTool.blend` (UBE Texture Conversion Tool от Grognak) и
  запекает 8 карт соответствия UV 4096 px (по 4 на каждое направление).
- `tools/pack_maps.py` — чистит выбросы, сжимает карты в `app/maps/*.npz` (uint16) и печатает круговой тест точности.
- `app/core.py` — конвертация: premultiplied-bilinear выборка по карте, DDS через texconv.
- `app/main.py` — интерфейс (PyQt6, тема Dwemer Atelier из MO2, шрифт Atelier UI).
- `build.py` — сборка PyInstaller → `dist/AtelierTextureBridge/` + zip.

```
python -m venv venv
venv\Scripts\python.exe -m pip install PyQt6 numpy pillow pyinstaller
blender.exe -b <путь>\StencilTool.blend --python tools\bake_maps.py -- 4096 maps_raw
venv\Scripts\python.exe tools\pack_maps.py
venv\Scripts\python.exe build.py
```
Готовые карты уже лежат в `app/maps`: для обычной сборки достаточно последней строки, Blender не нужен.

## Благодарности и лицензии
- Меши для карт UV — из UBE Texture Conversion Tool от Grognak (`StencilTool.blend`).
- `texconv.exe` — Microsoft DirectXTex, MIT.
- Шрифт Atelier UI — Inter 4.1 (Rasmus Andersson), SIL Open Font License 1.1 (`app/assets/font/OFL.txt`).
- PyQt6 / Qt 6 — GPLv3 / LGPLv3; NumPy — BSD; Pillow — HPND.
