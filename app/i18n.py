"""Interface strings in 8 languages. English is the default; tr(key, **fields) formats in the current language.
Each entry lists the languages in LANGS order: en, ru, de, fr, es, zh, ja, ko."""

LANGS = [('en', 'English'), ('ru', 'Русский'), ('de', 'Deutsch'), ('fr', 'Français'), ('es', 'Español'),
         ('zh', '简体中文'), ('ja', '日本語'), ('ko', '한국어')]
CODES = [c for c, _ in LANGS]
# Atelier UI (Inter) has no CJK glyphs: these system fonts follow it in the font-family list
CJK_FONTS = {'zh': 'Microsoft YaHei UI', 'ja': 'Yu Gothic UI', 'ko': 'Malgun Gothic'}

_lang = 'en'


def set_lang(code):
    global _lang
    _lang = code if code in CODES else 'en'


def lang():
    return _lang


def tr(key, **kw):
    row = S[key]
    text = row[CODES.index(_lang)] or row[0]
    return text.format(**kw) if kw else text


S = {
    'lang_tip': ('Interface language', 'Язык интерфейса', 'Sprache der Oberfläche', "Langue de l'interface",
                 'Idioma de la interfaz', '界面语言', '表示言語', '인터페이스 언어'),
    'queue': ('QUEUE', 'ОЧЕРЕДЬ', 'WARTESCHLANGE', "FILE D'ATTENTE", 'COLA', '队列', 'キュー', '대기열'),
    'btn_files': ('Files…', 'Файлы…', 'Dateien…', 'Fichiers…', 'Archivos…', '文件…', 'ファイル…', '파일…'),
    'btn_folder': ('Folder…', 'Папка…', 'Ordner…', 'Dossier…', 'Carpeta…', '文件夹…', 'フォルダー…', '폴더…'),
    'btn_remove': ('Remove', 'Убрать', 'Entfernen', 'Retirer', 'Quitar', '移除', '削除', '제거'),
    'btn_clear': ('Clear', 'Очистить', 'Leeren', 'Vider', 'Vaciar', '清空', 'クリア', '비우기'),
    'drop_title': (
        'Drop textures or a mod folder here',
        'Перетащите сюда текстуры или папку мода',
        'Texturen oder einen Mod-Ordner hierher ziehen',
        'Déposez ici des textures ou un dossier de mod',
        'Arrastra aquí texturas o una carpeta de mod',
        '将贴图或模组文件夹拖放到此处',
        'テクスチャまたは MOD フォルダーをここにドロップ',
        '텍스처나 모드 폴더를 여기로 끌어다 놓으세요'),
    'drop_hint': (
        'DDS, PNG, TGA · folders are scanned with all subfolders, the folder structure is kept',
        'DDS, PNG, TGA · папки сканируются целиком, структура подпапок сохраняется',
        'DDS, PNG, TGA · Ordner werden samt Unterordnern durchsucht, die Struktur bleibt erhalten',
        "DDS, PNG, TGA · les dossiers sont analysés avec leurs sous-dossiers, l'arborescence est conservée",
        'DDS, PNG, TGA · las carpetas se exploran con sus subcarpetas y se conserva la estructura',
        'DDS、PNG、TGA · 会扫描文件夹及其所有子文件夹，并保留目录结构',
        'DDS・PNG・TGA · フォルダーはサブフォルダーごと読み込み、構成をそのまま保持します',
        'DDS, PNG, TGA · 폴더는 하위 폴더까지 모두 검색하며 폴더 구조를 유지합니다'),
    'drop_files': ('Choose files…', 'Выбрать файлы…', 'Dateien wählen…', 'Choisir des fichiers…',
                   'Elegir archivos…', '选择文件…', 'ファイルを選択…', '파일 선택…'),
    'drop_folder': ('Choose folder…', 'Выбрать папку…', 'Ordner wählen…', 'Choisir un dossier…',
                    'Elegir carpeta…', '选择文件夹…', 'フォルダーを選択…', '폴더 선택…'),
    'col_file': ('File', 'Файл', 'Datei', 'Fichier', 'Archivo', '文件', 'ファイル', '파일'),
    'col_part': ('Body part', 'Часть тела', 'Körperteil', 'Partie du corps', 'Parte del cuerpo', '身体部位',
                 '部位', '신체 부위'),
    'col_source': ('Source', 'Исходник', 'Quelle', 'Source', 'Origen', '源文件', '元データ', '원본'),
    'col_fit': ('Layout', 'Раскладка', 'Layout', 'Disposition', 'Distribución', '布局', 'レイアウト', '레이아웃'),
    'col_result': ('Result', 'Результат', 'Ergebnis', 'Résultat', 'Resultado', '结果', '結果', '결과'),
    'part_body': ('Body', 'Тело', 'Körper', 'Corps', 'Cuerpo', '身体', 'ボディ', '바디'),
    'part_hands': ('Hands', 'Руки', 'Hände', 'Mains', 'Manos', '手部', '手', '손'),
    'part_feet': ('Feet', 'Ступни', 'Füße', 'Pieds', 'Pies', '足部', '足', '발'),
    'part_head': ('Face', 'Лицо', 'Gesicht', 'Visage', 'Cara', '面部', '顔', '얼굴'),
    'card_preview': ('PREVIEW', 'ПРЕДПРОСМОТР', 'VORSCHAU', 'APERÇU', 'VISTA PREVIA', '预览', 'プレビュー', '미리 보기'),
    'prev_before': ('Before · {layout}', 'До · {layout}', 'Vorher · {layout}', 'Avant · {layout}',
                    'Antes · {layout}', '转换前 · {layout}', '変換前 · {layout}', '변환 전 · {layout}'),
    'prev_after': ('After · {layout}', 'После · {layout}', 'Nachher · {layout}', 'Après · {layout}',
                   'Después · {layout}', '转换后 · {layout}', '変換後 · {layout}', '변환 후 · {layout}'),
    'layout_vanilla_head': ('vanilla head', 'ванильная голова', 'Vanilla-Kopf', 'tête vanilla', 'cabeza vanilla',
                            '原版头部', 'バニラ頭部', '바닐라 머리'),
    'layout_ube_head': ('UBE head', 'голова UBE', 'UBE-Kopf', 'tête UBE', 'cabeza UBE', 'UBE 头部', 'UBE 頭部',
                        'UBE 머리'),
    'prev_idle': (
        'Select a row in the list to see the result.',
        'Выберите строку в списке, чтобы увидеть результат.',
        'Wählen Sie eine Zeile in der Liste, um das Ergebnis zu sehen.',
        'Sélectionnez une ligne de la liste pour voir le résultat.',
        'Selecciona una fila de la lista para ver el resultado.',
        '在列表中选择一行即可查看结果。',
        'リストの行を選択すると結果を確認できます。',
        '목록에서 행을 선택하면 결과를 볼 수 있습니다.'),
    'prev_busy': ('Rendering preview…', 'Считаю предпросмотр…', 'Vorschau wird berechnet…', "Calcul de l'aperçu…",
                  'Generando vista previa…', '正在生成预览…', 'プレビューを生成中…', '미리 보기 생성 중…'),
    'prev_fail': ('Preview failed: {err}', 'Не удалось построить предпросмотр: {err}',
                  'Vorschau fehlgeschlagen: {err}', "Échec de l'aperçu : {err}", 'Error en la vista previa: {err}',
                  '预览失败：{err}', 'プレビューに失敗しました: {err}', '미리 보기 실패: {err}'),
    'prev_done': (
        'Brass tint marks the UV islands of each layout. Double-click a row to show the result in Explorer.',
        'Латунью подсвечены UV-острова раскладки. Двойной щелчок по строке — открыть результат в проводнике.',
        'Messingfarben markiert sind die UV-Inseln des jeweiligen Layouts. Ein Doppelklick auf eine Zeile zeigt '
        'das Ergebnis im Explorer.',
        "La teinte laiton signale les îlots UV de chaque disposition. Double-cliquez sur une ligne pour afficher "
        "le résultat dans l'Explorateur.",
        'El tono latón marca las islas UV de cada distribución. Haz doble clic en una fila para ver el resultado '
        'en el Explorador.',
        '黄铜色标出各布局的 UV 岛。双击某一行可在资源管理器中查看结果。',
        '真鍮色の部分は各レイアウトの UV アイランドです。行をダブルクリックするとエクスプローラーで結果を表示します。',
        '황동색은 각 레이아웃의 UV 아일랜드를 표시합니다. 행을 두 번 클릭하면 탐색기에서 결과를 엽니다.'),
    'card_options': ('OPTIONS', 'ПАРАМЕТРЫ', 'OPTIONEN', 'OPTIONS', 'OPCIONES', '选项', 'オプション', '옵션'),
    'opt_res': ('Resolution', 'Разрешение', 'Auflösung', 'Résolution', 'Resolución', '分辨率', '解像度', '해상도'),
    'res_source': ('Same as source', 'Как у исходника', 'Wie die Quelle', 'Identique à la source',
                   'Igual que el origen', '与源文件相同', '元と同じ', '원본과 동일'),
    'opt_format': ('Format', 'Формат', 'Format', 'Format', 'Formato', '格式', '形式', '형식'),
    'fmt_auto': ('Auto (same as source)', 'Авто (как у исходника)', 'Automatisch (wie die Quelle)',
                 'Auto (identique à la source)', 'Automático (igual que el origen)', '自动（与源文件相同）',
                 '自動（元と同じ）', '자동(원본과 동일)'),
    'fmt_bc7': ('BC7 — best quality', 'BC7 — лучшее качество', 'BC7 — beste Qualität', 'BC7 — meilleure qualité',
                'BC7 — máxima calidad', 'BC7 — 最佳质量', 'BC7 — 最高画質', 'BC7 — 최고 품질'),
    'fmt_bc3': ('BC3 / DXT5 — with alpha', 'BC3 / DXT5 — с альфой', 'BC3 / DXT5 — mit Alpha',
                'BC3 / DXT5 — avec alpha', 'BC3 / DXT5 — con alfa', 'BC3 / DXT5 — 带 Alpha',
                'BC3 / DXT5 — アルファあり', 'BC3 / DXT5 — 알파 포함'),
    'fmt_bc1': ('BC1 / DXT1 — no alpha', 'BC1 / DXT1 — без альфы', 'BC1 / DXT1 — ohne Alpha',
                'BC1 / DXT1 — sans alpha', 'BC1 / DXT1 — sin alfa', 'BC1 / DXT1 — 无 Alpha',
                'BC1 / DXT1 — アルファなし', 'BC1 / DXT1 — 알파 없음'),
    'fmt_raw': ('Uncompressed (RGBA8)', 'Без сжатия (RGBA8)', 'Unkomprimiert (RGBA8)', 'Non compressé (RGBA8)',
                'Sin comprimir (RGBA8)', '不压缩 (RGBA8)', '非圧縮 (RGBA8)', '비압축 (RGBA8)'),
    'opt_opaque': ('Opaque', 'Непрозрачная', 'Deckend', 'Opaque', 'Opaca', '不透明', '不透明', '불투명'),
    'opaque_auto': ('Auto', 'Авто', 'Automatisch', 'Auto', 'Automático', '自动', '自動', '자동'),
    'opaque_yes': ('Yes — skin, detail maps', 'Да — кожа, детали', 'Ja — Haut, Detailmaps', 'Oui — peau, détails',
                   'Sí — piel, mapas de detalle', '是 — 皮肤、细节贴图', 'はい — 肌、ディテールマップ',
                   '예 — 피부, 디테일 맵'),
    'opaque_no': ('No — overlay with alpha', 'Нет — оверлей с альфой', 'Nein — Overlay mit Alpha',
                  'Non — overlay avec alpha', 'No — overlay con alfa', '否 — 带 Alpha 的叠加层',
                  'いいえ — アルファ付きオーバーレイ', '아니요 — 알파가 있는 오버레이'),
    'opaque_tip': (
        'Opaque textures (skin, detail maps) get the seams between UV islands padded and a solid alpha.\n'
        'Overlays with transparency are carried over as they are.',
        'Непрозрачные текстуры (кожа, детали) получают заполнение швов между UV-островами и сплошную альфу.\n'
        'Оверлеи с прозрачностью переносятся как есть.',
        'Deckende Texturen (Haut, Detailmaps) erhalten aufgefüllte Nähte zwischen den UV-Inseln und einen vollen '
        'Alphakanal.\nOverlays mit Transparenz werden unverändert übertragen.',
        'Les textures opaques (peau, détails) voient leurs coutures entre îlots UV comblées et reçoivent un alpha '
        'plein.\nLes overlays transparents sont transférés tels quels.',
        'Las texturas opacas (piel, mapas de detalle) reciben relleno en las costuras entre islas UV y un alfa '
        'sólido.\nLos overlays con transparencia se trasladan tal cual.',
        '不透明贴图（皮肤、细节贴图）会填充 UV 岛之间的接缝，并使用完全不透明的 Alpha。\n带透明度的叠加层将按原样转换。',
        '不透明テクスチャ（肌、ディテールマップ）は UV アイランド間の継ぎ目を埋め、アルファを完全不透明にします。\n'
        '透過のあるオーバーレイはそのまま変換されます。',
        '불투명 텍스처(피부, 디테일 맵)는 UV 아일랜드 사이의 이음새를 채우고 알파를 완전 불투명으로 만듭니다.\n'
        '투명도가 있는 오버레이는 그대로 변환됩니다.'),
    'opt_output': ('Save to', 'Куда сохранять', 'Speichern unter', 'Enregistrer dans', 'Guardar en', '保存到',
                   '保存先', '저장 위치'),
    'out_hint_custom': (
        'The subfolder structure relative to the added folder is kept.',
        'Структура подпапок относительно добавленной папки сохраняется.',
        'Die Unterordnerstruktur relativ zum hinzugefügten Ordner bleibt erhalten.',
        "L'arborescence relative au dossier ajouté est conservée.",
        'Se conserva la estructura de subcarpetas relativa a la carpeta añadida.',
        '将保留相对于所添加文件夹的子文件夹结构。',
        '追加したフォルダーを基準にサブフォルダー構成を保持します。',
        '추가한 폴더 기준의 하위 폴더 구조가 유지됩니다.'),
    'out_hint_auto': (
        'Leave empty to save into a “{tag}” subfolder next to each source; for a mod folder, into “{tag}\\…” '
        'inside it with the same structure.',
        'Пусто — в подпапку «{tag}» рядом с исходником; для папки мода — в «{tag}\\…» внутри неё, '
        'с той же структурой.',
        'Leer lassen: Speichern im Unterordner „{tag}“ neben der Quelle; bei einem Mod-Ordner in „{tag}\\…“ '
        'darin, mit gleicher Struktur.',
        'Laissez vide pour enregistrer dans un sous-dossier « {tag} » à côté de la source ; pour un dossier de '
        'mod, dans « {tag}\\… » à l\'intérieur, avec la même arborescence.',
        'Déjalo vacío para guardar en una subcarpeta «{tag}» junto al origen; para una carpeta de mod, en '
        '«{tag}\\…» dentro de ella, con la misma estructura.',
        '留空则保存到源文件旁的“{tag}”子文件夹；若添加的是模组文件夹，则保存到其中的“{tag}\\…”，结构保持不变。',
        '空欄の場合は元ファイルの隣の「{tag}」サブフォルダーに保存します。MOD フォルダーの場合はその中の'
        '「{tag}\\…」に同じ構成で保存します。',
        "비워 두면 원본 옆의 '{tag}' 하위 폴더에 저장합니다. 모드 폴더는 그 안의 '{tag}\\…'에 같은 구조로 "
        "저장합니다."),
    'chk_overwrite': ('Overwrite existing files', 'Перезаписывать существующие файлы',
                      'Vorhandene Dateien überschreiben', 'Écraser les fichiers existants',
                      'Sobrescribir archivos existentes', '覆盖已有文件', '既存のファイルを上書き', '기존 파일 덮어쓰기'),
    'chk_open': ('Open the folder when finished', 'Открыть папку по завершении', 'Ordner nach Abschluss öffnen',
                 'Ouvrir le dossier à la fin', 'Abrir la carpeta al terminar', '完成后打开文件夹',
                 '完了したらフォルダーを開く', '완료 후 폴더 열기'),
    'card_how': ('HOW IT WORKS', 'КАК ЭТО РАБОТАЕТ', 'SO FUNKTIONIERT ES', 'FONCTIONNEMENT', 'CÓMO FUNCIONA',
                 '工作原理', '仕組み', '작동 방식'),
    'status_ready': ('Ready', 'Готов к работе', 'Bereit', 'Prêt', 'Listo', '就绪', '準備完了', '준비됨'),
    'status_empty': ('Add textures to begin', 'Добавьте текстуры, чтобы начать', 'Texturen hinzufügen, um zu beginnen',
                     'Ajoutez des textures pour commencer', 'Añade texturas para empezar', '添加贴图以开始',
                     'テクスチャを追加して開始', '텍스처를 추가해 시작하세요'),
    'btn_stop': ('Stop', 'Остановить', 'Stopp', 'Arrêter', 'Detener', '停止', '停止', '중지'),
    'btn_convert': ('Convert', 'Конвертировать', 'Konvertieren', 'Convertir', 'Convertir', '转换', '変換', '변환'),
    'st_queued': ('queued', 'в очереди', 'in der Warteschlange', 'en attente', 'en cola', '排队中', '待機中', '대기 중'),
    'st_waiting': ('waiting', 'ждёт', 'wartet', 'en attente', 'esperando', '等待中', '待機中', '대기 중'),
    'st_converting': ('converting…', 'конвертация…', 'wird konvertiert…', 'conversion…', 'convirtiendo…',
                      '正在转换…', '変換中…', '변환 중…'),
    'st_analyzing': ('analyzing…', 'анализ…', 'Analyse…', 'analyse…', 'analizando…', '分析中…', '解析中…', '분석 중…'),
    'info_error': ('error', 'ошибка', 'Fehler', 'erreur', 'error', '错误', 'エラー', '오류'),
    'st_unreadable': ('unreadable: {err}', 'не читается: {err}', 'nicht lesbar: {err}', 'illisible : {err}',
                      'no se puede leer: {err}', '无法读取：{err}', '読み込めません: {err}', '읽을 수 없음: {err}'),
    'st_normal_warn': ('normal map — check in game', 'карта нормалей — проверьте в игре',
                       'Normal Map – im Spiel prüfen', 'normal map — à vérifier en jeu',
                       'mapa de normales — compruébalo en el juego', '法线贴图 — 请在游戏中检查',
                       'ノーマルマップ — ゲーム内で確認してください', '노멀 맵 — 게임에서 확인하세요'),
    'info_normal': ('normal map', 'нормали', 'Normal Map', 'normal map', 'normales', '法线', 'ノーマル', '노멀'),
    'info_opaque': ('opaque', 'непрозр.', 'deckend', 'opaque', 'opaca', '不透明', '不透明', '불투명'),
    'fit_opaque_tip': ('Opaque texture: it covers the whole layout', 'Непрозрачная текстура: покрывает всю раскладку',
                       'Deckende Textur: deckt das gesamte Layout ab', 'Texture opaque : elle couvre toute la disposition',
                       'Textura opaca: cubre toda la distribución', '不透明贴图：覆盖整个布局',
                       '不透明テクスチャ：レイアウト全体を覆います', '불투명 텍스처: 레이아웃 전체를 덮습니다'),
    'fit_tip': (
        '{fit} of the painted area lies on the UV islands of the chosen source layout.\n'
        'A low value usually means the wrong direction or body part.',
        '{fit} нарисованного лежит на UV-островах выбранной исходной раскладки.\n'
        'Низкое значение обычно значит, что выбрано не то направление или не та часть тела.',
        '{fit} der bemalten Fläche liegen auf den UV-Inseln des gewählten Quell-Layouts.\n'
        'Ein niedriger Wert deutet meist auf die falsche Richtung oder den falschen Körperteil hin.',
        '{fit} de la zone peinte se trouve sur les îlots UV de la disposition source choisie.\n'
        'Une valeur faible indique souvent une mauvaise direction ou partie du corps.',
        'El {fit} del área pintada está sobre las islas UV de la distribución de origen elegida.\n'
        'Un valor bajo suele indicar una dirección o parte del cuerpo incorrecta.',
        '已绘制区域中有 {fit} 位于所选源布局的 UV 岛上。\n数值偏低通常说明转换方向或身体部位选错了。',
        '描画部分の {fit} が、選択した元レイアウトの UV アイランド上にあります。\n'
        '値が低い場合は、変換方向または部位の選択が誤っている可能性があります。',
        '칠해진 영역의 {fit}가 선택한 원본 레이아웃의 UV 아일랜드 위에 있습니다.\n'
        '값이 낮으면 대개 변환 방향이나 신체 부위가 잘못 선택된 것입니다.'),
    'added': ('Files added: {n}', 'Добавлено файлов: {n}', 'Dateien hinzugefügt: {n}', 'Fichiers ajoutés : {n}',
              'Archivos añadidos: {n}', '已添加文件：{n}', '追加したファイル: {n}', '추가된 파일: {n}'),
    'dlg_textures': ('Textures', 'Текстуры', 'Texturen', 'Textures', 'Texturas', '贴图', 'テクスチャ', '텍스처'),
    'dlg_folder': ('Folder with textures', 'Папка с текстурами', 'Ordner mit Texturen', 'Dossier de textures',
                   'Carpeta con texturas', '贴图文件夹', 'テクスチャのフォルダー', '텍스처 폴더'),
    'menu_open_src': ('Open source folder', 'Открыть папку исходника', 'Quellordner öffnen',
                      'Ouvrir le dossier source', 'Abrir la carpeta de origen', '打开源文件夹', '元フォルダーを開く',
                      '원본 폴더 열기'),
    'menu_open_out': ('Show result in Explorer', 'Показать результат в проводнике', 'Ergebnis im Explorer anzeigen',
                      "Afficher le résultat dans l'Explorateur", 'Mostrar el resultado en el Explorador',
                      '在资源管理器中显示结果', 'エクスプローラーで結果を表示', '탐색기에서 결과 보기'),
    'menu_remove': ('Remove from queue', 'Убрать из очереди', 'Aus der Warteschlange entfernen',
                    'Retirer de la file', 'Quitar de la cola', '从队列移除', 'キューから削除', '대기열에서 제거'),
    'clash': (
        'Several files would be written to the same output:\n\n{files}\n\nRemove the extra ones or choose another '
        'folder.',
        'Несколько файлов попадают в один и тот же результат:\n\n{files}\n\nУберите лишние или выберите другую папку.',
        'Mehrere Dateien würden in dieselbe Ausgabedatei geschrieben:\n\n{files}\n\nEntfernen Sie die überzähligen '
        'oder wählen Sie einen anderen Ordner.',
        'Plusieurs fichiers seraient écrits vers la même sortie :\n\n{files}\n\nRetirez les doublons ou choisissez '
        'un autre dossier.',
        'Varios archivos se escribirían en la misma salida:\n\n{files}\n\nQuita los sobrantes o elige otra carpeta.',
        '多个文件将写入同一个输出文件：\n\n{files}\n\n请移除多余的文件或选择其他文件夹。',
        '複数のファイルが同じ出力先に書き込まれます:\n\n{files}\n\n余分なファイルを削除するか、別のフォルダーを選択して'
        'ください。',
        '여러 파일이 같은 출력 파일로 저장됩니다:\n\n{files}\n\n불필요한 파일을 제거하거나 다른 폴더를 선택하세요.'),
    'low_fit': (
        '{n} file(s) do not fit the chosen layout well (for example “{name}”). The direction or body part may be '
        'wrong.\n\nContinue anyway?',
        'У {n} файл(ов) рисунок плохо ложится на выбранную раскладку (например, «{name}»). Возможно, выбрано не то '
        'направление или не та часть тела.\n\nПродолжить?',
        'Bei {n} Datei(en) passt das Motiv schlecht zum gewählten Layout (z. B. „{name}“). Möglicherweise sind '
        'Richtung oder Körperteil falsch.\n\nTrotzdem fortfahren?',
        '{n} fichier(s) correspondent mal à la disposition choisie (par exemple « {name} »). La direction ou la '
        'partie du corps est peut-être incorrecte.\n\nContinuer quand même ?',
        '{n} archivo(s) no encajan bien en la distribución elegida (por ejemplo, «{name}»). Puede que la dirección '
        'o la parte del cuerpo sean incorrectas.\n\n¿Continuar de todos modos?',
        '有 {n} 个文件与所选布局匹配度较低（例如“{name}”）。可能选错了转换方向或身体部位。\n\n仍要继续吗？',
        '{n} 個のファイルが選択したレイアウトにうまく合っていません（例:「{name}」）。変換方向または部位が誤っている'
        '可能性があります。\n\nこのまま続行しますか？',
        "파일 {n}개가 선택한 레이아웃과 잘 맞지 않습니다(예: '{name}'). 변환 방향이나 신체 부위가 잘못되었을 수 "
        "있습니다.\n\n그래도 계속하시겠습니까?"),
    'files_n': ('{n} file(s)', 'файлов: {n}', '{n} Datei(en)', '{n} fichier(s)', '{n} archivo(s)', '{n} 个文件',
                '{n} 個のファイル', '파일 {n}개'),
    'run_progress': ('{name} · {i} of {n}', '{name} · {i} из {n}', '{name} · {i} von {n}', '{name} · {i} sur {n}',
                     '{name} · {i} de {n}', '{name} · {i}/{n}', '{name} · {i}/{n}', '{name} · {i}/{n}'),
    'stopping': ('Stopping after the current file…', 'Останавливаю после текущего файла…',
                 'Wird nach der aktuellen Datei angehalten…', 'Arrêt après le fichier en cours…',
                 'Deteniendo tras el archivo actual…', '将在当前文件完成后停止…', '現在のファイルの処理後に停止します…',
                 '현재 파일 처리 후 중지합니다…'),
    'log_err': ('ERROR', 'ОШИБКА', 'FEHLER', 'ERREUR', 'ERROR', '错误', 'エラー', '오류'),
    'log_skip': ('skipped', 'пропуск', 'übersprungen', 'ignoré', 'omitido', '已跳过', 'スキップ', '건너뜀'),
    'done_ok': ('done: {n}', 'готово: {n}', 'fertig: {n}', 'terminés : {n}', 'completados: {n}', '完成：{n}',
                '完了: {n}', '완료: {n}'),
    'done_skip': ('skipped: {n}', 'пропущено: {n}', 'übersprungen: {n}', 'ignorés : {n}', 'omitidos: {n}',
                  '跳过：{n}', 'スキップ: {n}', '건너뜀: {n}'),
    'done_err': ('errors: {n}', 'ошибок: {n}', 'Fehler: {n}', 'erreurs : {n}', 'errores: {n}', '错误：{n}',
                 'エラー: {n}', '오류: {n}'),
    'done_stopped': ('Stopped', 'Остановлено', 'Angehalten', 'Arrêté', 'Detenido', '已停止', '停止しました', '중지됨'),
    'seconds': ('{s} s', '{s} с', '{s} s', '{s} s', '{s} s', '{s} 秒', '{s} 秒', '{s}초'),
    'close_busy': ('Conversion is still running. Abort and quit?', 'Конвертация ещё идёт. Прервать и выйти?',
                   'Die Konvertierung läuft noch. Abbrechen und beenden?',
                   'La conversion est en cours. Interrompre et quitter ?',
                   'La conversión sigue en curso. ¿Cancelar y salir?', '转换仍在进行。要中止并退出吗？',
                   '変換がまだ実行中です。中断して終了しますか？', '변환이 아직 진행 중입니다. 중단하고 종료할까요?'),
    'err_exists': ('the file already exists (enable “Overwrite”)', 'файл уже есть (включите «Перезаписывать»)',
                   'Datei existiert bereits („Überschreiben“ aktivieren)',
                   'le fichier existe déjà (activez « Écraser »)', 'el archivo ya existe (activa «Sobrescribir»)',
                   '文件已存在（请启用“覆盖”）', 'ファイルが既に存在します（「上書き」を有効にしてください）',
                   "파일이 이미 있습니다('덮어쓰기'를 켜세요)"),
    'err_not_dds': ('not a DDS file', 'не DDS-файл', 'keine DDS-Datei', 'pas un fichier DDS', 'no es un archivo DDS',
                    '不是 DDS 文件', 'DDS ファイルではありません', 'DDS 파일이 아닙니다'),
    'sum_opaque': ('opaque, seams padded', 'непрозрачная, швы заполнены', 'deckend, Nähte aufgefüllt',
                   'opaque, coutures comblées', 'opaca, costuras rellenadas', '不透明，接缝已填充',
                   '不透明・継ぎ目を補完', '불투명, 이음새 채움'),
    # ---- v1.1: one UBE atlas from 3BA body + hands + feet
    'atlas_row': ('UBE atlas · {name}', 'Атлас UBE · {name}', 'UBE-Atlas · {name}', 'Atlas UBE · {name}',
                  'Atlas UBE · {name}', 'UBE 图集 · {name}', 'UBE アトラス · {name}', 'UBE 아틀라스 · {name}'),
    'part_atlas': ('{n} parts', 'частей: {n}', '{n} Teile', '{n} parties', '{n} partes', '{n} 个部位', '{n} 部位',
                   '{n}개 부위'),
    'sum_parts': ('{n} parts in one atlas', 'частей в атласе: {n}', '{n} Teile in einem Atlas',
                  '{n} parties dans un atlas', '{n} partes en un atlas', '{n} 个部位合并为一张图集',
                  '{n} 部位を 1 枚のアトラスに統合', '{n}개 부위를 하나의 아틀라스로'),
    'menu_group': ('Combine into one UBE atlas', 'Объединить в один атлас UBE', 'Zu einem UBE-Atlas zusammenfassen',
                   'Combiner en un seul atlas UBE', 'Combinar en un solo atlas UBE', '合并为一张 UBE 图集',
                   '1 枚の UBE アトラスに統合', '하나의 UBE 아틀라스로 합치기'),
    'menu_ungroup': ('Split the atlas group', 'Разгруппировать атлас', 'Atlas-Gruppe auflösen',
                     "Dissocier le groupe d'atlas", 'Deshacer el grupo de atlas', '取消图集分组',
                     'アトラスのグループを解除', '아틀라스 그룹 해제'),
    'btn_auto_atlas': ('Find atlases', 'Собрать атласы', 'Atlanten finden', 'Trouver les atlas', 'Buscar atlas',
                       '查找图集', 'アトラスを検出', '아틀라스 찾기'),
    'tip_auto_atlas': (
        'Groups the body, hands and feet textures of one set (same folder and matching names, or Body/Hands/Feet '
        'folders) so that each set becomes one UBE atlas.',
        'Объединяет текстуры тела, рук и ступней одного комплекта (одна папка и похожие имена или папки '
        'Body/Hands/Feet), чтобы каждый комплект стал одним атласом UBE.',
        'Fasst Körper-, Hand- und Fußtexturen eines Sets zusammen (gleicher Ordner und passende Namen oder '
        'Body/Hands/Feet-Ordner), sodass aus jedem Set ein UBE-Atlas wird.',
        "Regroupe les textures de corps, mains et pieds d'un même ensemble (même dossier et noms correspondants, ou "
        "dossiers Body/Hands/Feet) pour que chaque ensemble devienne un atlas UBE.",
        'Agrupa las texturas de cuerpo, manos y pies de un mismo conjunto (misma carpeta y nombres coincidentes, o '
        'carpetas Body/Hands/Feet) para que cada conjunto se convierta en un atlas UBE.',
        '将同一套的身体、手部和足部贴图（同一文件夹且名称对应，或位于 Body/Hands/Feet 文件夹中）分为一组，'
        '使每套生成一张 UBE 图集。',
        '同じセットのボディ・手・足のテクスチャ（同じフォルダーで名前が対応しているもの、または Body/Hands/Feet '
        'フォルダー内のもの）をまとめ、セットごとに 1 枚の UBE アトラスにします。',
        '같은 세트의 바디·손·발 텍스처(같은 폴더에서 이름이 대응하거나 Body/Hands/Feet 폴더에 있는 것)를 묶어 '
        '세트마다 하나의 UBE 아틀라스로 만듭니다.'),
    'auto_atlas_done': ('Atlas groups created: {n}', 'Создано групп-атласов: {n}', 'Atlas-Gruppen erstellt: {n}',
                        "Groupes d'atlas créés : {n}", 'Grupos de atlas creados: {n}', '已创建图集分组：{n}',
                        '作成したアトラスグループ: {n}', '생성된 아틀라스 그룹: {n}'),
    'auto_atlas_none': ('No body/hands/feet sets found in the queue.',
                        'В очереди не нашлось комплектов «тело / руки / ступни».',
                        'In der Warteschlange wurden keine Körper/Hände/Füße-Sets gefunden.',
                        'Aucun ensemble corps/mains/pieds trouvé dans la file.',
                        'No se encontraron conjuntos de cuerpo/manos/pies en la cola.',
                        '队列中未找到身体/手部/足部套组。',
                        'キューにボディ/手/足のセットが見つかりませんでした。',
                        '대기열에서 바디/손/발 세트를 찾지 못했습니다.'),
    'group_bad': (
        'An atlas holds at most one body, one hands and one feet texture, and no face: {name}',
        'В атласе может быть не больше одной текстуры тела, одной рук и одной ступней, без лица: {name}',
        'Ein Atlas enthält höchstens je eine Körper-, Hand- und Fußtextur und kein Gesicht: {name}',
        'Un atlas contient au plus une texture de corps, une de mains et une de pieds, sans visage : {name}',
        'Un atlas admite como máximo una textura de cuerpo, una de manos y una de pies, sin cara: {name}',
        '一张图集最多包含身体、手部、足部贴图各一张，且不能包含面部：{name}',
        'アトラスに含められるのはボディ・手・足のテクスチャ各 1 枚までで、顔は含められません: {name}',
        '아틀라스에는 바디·손·발 텍스처를 각각 하나까지만 넣을 수 있으며 얼굴은 넣을 수 없습니다: {name}'),
    'st_in_atlas': ('goes into the atlas', 'входит в атлас', 'geht in den Atlas ein', "intégrée à l'atlas",
                    'va al atlas', '并入图集', 'アトラスに統合', '아틀라스에 포함'),
    'subtitle': (
        'Move overlays and body textures between the 3BA (CBBE), UNP (BHUNP) and UBE layouts',
        'Перенос оверлеев и текстур тела между раскладками 3BA (CBBE), UNP (BHUNP) и UBE',
        'Overlays und Körpertexturen zwischen den UV-Layouts von 3BA (CBBE), UNP (BHUNP) und UBE übertragen',
        'Transférez overlays et textures de corps entre les dispositions UV 3BA (CBBE), UNP (BHUNP) et UBE',
        'Traslada overlays y texturas corporales entre las distribuciones UV de 3BA (CBBE), UNP (BHUNP) y UBE',
        '在 3BA (CBBE)、UNP (BHUNP) 与 UBE 的 UV 布局之间转换叠加层和身体贴图',
        'オーバーレイと身体テクスチャを 3BA (CBBE)・UNP (BHUNP)・UBE の UV レイアウト間で変換します',
        '3BA(CBBE), UNP(BHUNP), UBE UV 레이아웃 간에 오버레이와 바디 텍스처를 변환합니다'),
    'layout_from': (
        'From',
        'Из',
        'Von',
        'De',
        'De',
        '源布局',
        '変換元',
        '원본 레이아웃'),
    'layout_to': (
        'To',
        'В',
        'Nach',
        'Vers',
        'A',
        '目标布局',
        '変換先',
        '대상 레이아웃'),
    'layout_from_tip': (
        'The body the textures were made for',
        'Тело, под которое сделаны текстуры',
        'Der Körper, für den die Texturen gemacht wurden',
        'Le corps pour lequel les textures ont été faites',
        'El cuerpo para el que se hicieron las texturas',
        '贴图原本适配的身体',
        'テクスチャの作成元のボディ',
        '텍스처가 원래 맞춰진 바디'),
    'layout_to_tip': (
        'The body the textures should fit',
        'Тело, под которое их нужно перенести',
        'Der Körper, zu dem die Texturen passen sollen',
        "Le corps auquel les textures doivent s'adapter",
        'El cuerpo al que deben ajustarse las texturas',
        '贴图需要适配的身体',
        'テクスチャを合わせたいボディ',
        '텍스처를 맞출 바디'),
    'swap_tip': (
        'Swap source and target',
        'Поменять местами',
        'Quelle und Ziel tauschen',
        'Inverser source et cible',
        'Intercambiar origen y destino',
        '交换源与目标',
        '変換元と変換先を入れ替え',
        '원본과 대상 바꾸기'),
    'st_split': (
        '{arrow}: each file separately',
        '{arrow}: каждый файл отдельно',
        '{arrow}: jede Datei einzeln',
        '{arrow} : chaque fichier séparément',
        '{arrow}: cada archivo por separado',
        '{arrow}：逐个文件单独转换',
        '{arrow}：ファイルごとに個別変換',
        '{arrow}: 파일별로 따로 변환'),
    'out_placeholder': (
        'Next to the source (subfolder named after the target body)',
        'Рядом с исходником (подпапка с именем целевого тела)',
        'Neben der Quelle (Unterordner nach dem Zielkörper benannt)',
        'À côté de la source (sous-dossier au nom du corps cible)',
        'Junto al origen (subcarpeta con el nombre del cuerpo de destino)',
        '源文件旁（以目标身体命名的子文件夹）',
        '元ファイルの隣（変換先ボディ名のサブフォルダー）',
        '원본 옆 (대상 바디 이름의 하위 폴더)'),
    'how_text': (
        'Each pixel is moved along a UV correspondence map baked from the body meshes. Colour and alpha are not recalculated, so overlays look exactly as their author made them.<br><br><b>Body, hands and feet</b> of 3BA share one UBE atlas. <b>Face</b>: vanilla head ⇄ UBE head.<br>Normal maps are carried over, but the directions stored in them are not rotated, so check them in game.',
        'Каждый пиксель переносится по карте соответствия UV, запечённой с мешей тел. Цвет и альфа не пересчитываются — оверлеи выглядят так же, как задумал автор.<br><br><b>Тело, руки и ступни</b> 3BA сходятся в один атлас UBE. <b>Лицо</b>: ванильная голова ⇄ голова UBE.<br>Карты нормалей переносятся, но направления в них не поворачиваются — проверяйте в игре.',
        'Jeder Pixel wird entlang einer UV-Zuordnungskarte übertragen, die aus den Körper-Meshes gebacken wurde. Farbe und Alpha werden nicht neu berechnet – Overlays sehen genau so aus, wie ihr Autor sie gestaltet hat.<br><br><b>Körper, Hände und Füße</b> von 3BA landen in einem gemeinsamen UBE-Atlas. <b>Gesicht</b>: Vanilla-Kopf ⇄ UBE-Kopf.<br>Normal Maps werden übertragen, die darin gespeicherten Richtungen aber nicht gedreht – bitte im Spiel prüfen.',
        "Chaque pixel est déplacé selon une carte de correspondance UV précalculée à partir des maillages des corps. La couleur et l'alpha ne sont pas recalculés : les overlays restent tels que leur auteur les a conçus.<br><br>Le <b>corps, les mains et les pieds</b> 3BA partagent un seul atlas UBE. <b>Visage</b> : tête vanilla ⇄ tête UBE.<br>Les normal maps sont transférées, mais les directions qu'elles contiennent ne sont pas pivotées : vérifiez-les en jeu.",
        'Cada píxel se traslada según un mapa de correspondencia UV horneado a partir de las mallas de los cuerpos. El color y el alfa no se recalculan: los overlays se ven tal como los diseñó su autor.<br><br>El <b>cuerpo, las manos y los pies</b> de 3BA comparten un único atlas UBE. <b>Cara</b>: cabeza vanilla ⇄ cabeza UBE.<br>Los mapas de normales se trasladan, pero las direcciones que contienen no se rotan: compruébalos en el juego.',
        '每个像素都按照由身体模型烘焙出的 UV 对应图进行迁移。颜色和 Alpha 不会被重新计算，叠加层的效果与作者原作完全一致。<br><br>3BA 的<b>身体、手部和足部</b>共用一张 UBE 图集。<b>面部</b>：原版头部 ⇄ UBE 头部。<br>法线贴图也会迁移，但其中存储的方向不会随之旋转，请在游戏中检查。',
        '各ピクセルは、ボディのメッシュからベイクした UV 対応マップに沿って移されます。色とアルファは再計算されないため、オーバーレイは作者の意図どおりに表示されます。<br><br>3BA の<b>ボディ・手・足</b>は 1 枚の UBE アトラスにまとめられます。<b>顔</b>：バニラ頭部 ⇄ UBE 頭部。<br>ノーマルマップも変換されますが、法線の向きは回転されないため、ゲーム内で確認してください。',
        '각 픽셀은 바디 메시에서 베이크한 UV 대응 맵을 따라 옮겨집니다. 색상과 알파는 다시 계산되지 않으므로 오버레이가 제작자의 의도 그대로 보입니다.<br><br>3BA의 <b>바디, 손, 발</b>은 하나의 UBE 아틀라스를 함께 씁니다. <b>얼굴</b>: 바닐라 머리 ⇄ UBE 머리.<br>노멀 맵도 변환되지만 그 안의 방향은 회전되지 않으니 게임에서 확인하세요.'),
    'how_atlas': (
        'To get <b>one UBE atlas</b> from separate 3BA / UNP body, hands and feet textures, select their rows and choose “Combine into one UBE atlas” in the context menu, or press “Find atlases”.',
        'Чтобы получить <b>один атлас UBE</b> из отдельных текстур тела, рук и ступней 3BA / UNP, выделите их строки и выберите в контекстном меню «Объединить в один атлас UBE» или нажмите «Собрать атласы».',
        'Für <b>einen UBE-Atlas</b> aus getrennten 3BA / UNP-Texturen für Körper, Hände und Füße die Zeilen markieren und im Kontextmenü „Zu einem UBE-Atlas zusammenfassen“ wählen oder auf „Atlanten finden“ klicken.',
        'Pour obtenir <b>un seul atlas UBE</b> à partir de textures 3BA / UNP séparées de corps, mains et pieds, sélectionnez leurs lignes et choisissez « Combiner en un seul atlas UBE » dans le menu contextuel, ou cliquez sur « Trouver les atlas ».',
        'Para obtener <b>un solo atlas UBE</b> a partir de texturas 3BA / UNP separadas de cuerpo, manos y pies, selecciona sus filas y elige «Combinar en un solo atlas UBE» en el menú contextual, o pulsa «Buscar atlas».',
        '若要将分开的 3BA / UNP 身体、手部和足部贴图合成<b>一张 UBE 图集</b>，请选中这些行，在右键菜单中选择“合并为一张 UBE 图集”，或点击“查找图集”。',
        '別々の 3BA / UNP ボディ・手・足テクスチャから<b>1 枚の UBE アトラス</b>を作るには、それらの行を選択して右クリックメニューの「1 枚の UBE アトラスに統合」を選ぶか、「アトラスを検出」を押します。',
        "따로 있는 3BA / UNP 바디·손·발 텍스처로 <b>하나의 UBE 아틀라스</b>를 만들려면 해당 행을 선택하고 우클릭 메뉴에서 '하나의 UBE 아틀라스로 합치기'를 고르거나 '아틀라스 찾기'를 누르세요."),
}

assert all(len(v) == len(LANGS) for v in S.values()), [k for k, v in S.items() if len(v) != len(LANGS)]
