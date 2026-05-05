from __future__ import annotations

import json
import html
import os
import re
import shutil
import subprocess
import sys
import urllib.request
from urllib.parse import quote_plus
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
PREFERRED_PYTHON = Path(__file__).resolve().parents[3] / ".venv" / "Scripts" / "python.exe"


def _reexec_with_preferred_python() -> None:
    if not PREFERRED_PYTHON.exists():
        return
    if os.environ.get("NOTEFORGE_REEXEC") == "1":
        return

    current_python = Path(sys.executable).resolve()
    preferred_python = PREFERRED_PYTHON.resolve()
    if current_python == preferred_python:
        return

    os.environ["NOTEFORGE_REEXEC"] = "1"
    result = subprocess.run(
        [str(preferred_python), str(Path(__file__).resolve()), *sys.argv[1:]],
        env=os.environ.copy(),
    )
    raise SystemExit(result.returncode)


_reexec_with_preferred_python()

try:
    import markdown
except ModuleNotFoundError as exc:
    venv_python = PREFERRED_PYTHON
    install_cmd = (
        f'"{venv_python}" -m pip install -r "{BASE_DIR / "requirements.txt"}"'
        if venv_python.exists()
        else "python -m pip install -r requirements.txt"
    )
    raise SystemExit(
        "依存パッケージが不足しています。\n"
        f"次を実行してください:\n{install_cmd}"
    ) from exc
from PySide6.QtCore import QMimeData, QTimer, Qt, QUrl
from PySide6.QtGui import QAction, QIcon, QKeySequence, QTextDocument
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTabWidget,
    QPlainTextEdit,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtWebEngineWidgets import QWebEngineView


class PreviewWebView(QWebEngineView):
    def __init__(self, translate_handler, parent=None):
        super().__init__(parent)
        self._translate_handler = translate_handler

    def contextMenuEvent(self, event):
        menu = QMenu(self)

        act_back = menu.addAction("戻る")
        act_back.setEnabled(self.history().canGoBack())
        act_back.triggered.connect(self.back)

        act_forward = menu.addAction("進む")
        act_forward.setEnabled(self.history().canGoForward())
        act_forward.triggered.connect(self.forward)

        act_reload = menu.addAction("再読み込み")
        act_reload.triggered.connect(self.reload)

        menu.addSeparator()

        act_translate_ja = menu.addAction("日本語に変換（Google翻訳）")
        act_translate_ja.triggered.connect(self._translate_handler)

        menu.exec(event.globalPos())


class MarkdownEditor(QPlainTextEdit):
    def __init__(self, image_dir_getter, markdown_file_opener, status_notifier, parent=None):
        super().__init__(parent)
        self.image_dir_getter = image_dir_getter
        self.markdown_file_opener = markdown_file_opener
        self.status_notifier = status_notifier
        self.setAcceptDrops(True)
        self.setTabChangesFocus(False)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    @staticmethod
    def normalize_plain_text(text: str) -> str:
        return text.replace("\r\n", "\n").replace("\r", "\n").replace("\u2028", "\n").replace("\u2029", "\n")

    def insertFromMimeData(self, source: QMimeData) -> None:
        if source.hasText():
            self.insertPlainText(self.normalize_plain_text(source.text()))
            return
        super().insertFromMimeData(source)

    def wheelEvent(self, event):
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            if event.angleDelta().y() > 0:
                self.zoomIn(1)
            elif event.angleDelta().y() < 0:
                self.zoomOut(1)
            event.accept()
            return
        super().wheelEvent(event)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            return
        super().dragEnterEvent(event)

    def dropEvent(self, event):
        if not event.mimeData().hasUrls():
            super().dropEvent(event)
            return

        local_files = []
        for url in event.mimeData().urls():
            src = Path(url.toLocalFile())
            if src.exists():
                local_files.append(src)

        markdown_files = [
            p for p in local_files if p.suffix.lower() in {".md", ".markdown", ".txt"}
        ]
        image_files = [
            p for p in local_files if p.suffix.lower() in {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg"}
        ]

        if markdown_files:
            self.markdown_file_opener(markdown_files[0])
            if len(markdown_files) > 1:
                self.status_notifier("複数ファイルがドロップされたため、先頭ファイルのみ開きました。", 3000)
            event.acceptProposedAction()
            return

        image_dir = self.image_dir_getter()
        image_dir.mkdir(parents=True, exist_ok=True)

        inserted = []
        for src in image_files:
            dst = image_dir / src.name
            if dst.exists():
                stem, suffix = src.stem, src.suffix
                i = 1
                while dst.exists():
                    dst = image_dir / f"{stem}_{i}{suffix}"
                    i += 1
            shutil.copy2(src, dst)
            inserted.append(f"![]({dst.as_posix()})")

        if inserted:
            self.insertPlainText("\n" + "\n".join(inserted) + "\n")
            event.acceptProposedAction()
        else:
            self.status_notifier("未対応のファイルです。md/txt か画像ファイルをドロップしてください。", 3000)
            super().dropEvent(event)


class NoteForgeWindow(QMainWindow):
    AUTOSAVE_MS = 2000

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Sakura NoteForge")
        self.resize(1400, 900)

        # アイコン設定
        _icon_path = BASE_DIR / "assets" / "noteforge_icon.ico"
        if not _icon_path.exists():
            _icon_path = BASE_DIR / "assets" / "noteforge_icon.png"
        if _icon_path.exists():
            _icon = QIcon(str(_icon_path))
            self.setWindowIcon(_icon)
            app_inst = QApplication.instance()
            if app_inst is not None:
                app_inst.setWindowIcon(_icon)

        self.current_file: Path | None = None
        self.theme_mode: str = "light"  # light | dark
        self._find_text: str = ""
        self._recent_files: list[str] = []
        self.base_dir = BASE_DIR
        self.data_dir = self.base_dir / "data"
        self.autosave_dir = self.data_dir / "autosave"
        self.history_dir = self.data_dir / "history"
        self.autosave_dir.mkdir(parents=True, exist_ok=True)
        self.history_dir.mkdir(parents=True, exist_ok=True)

        # 設定ロード（テーマ・最近開いたファイル）
        settings = self._load_settings()
        self.theme_mode = settings.get("theme", "light")
        self._recent_files = settings.get("recent_files", [])

        self.editor_tabs = QTabWidget()
        self.editor_tabs.setMovable(True)
        self.editor_tabs.setDocumentMode(True)
        self.editor_tabs.setTabsClosable(True)
        self.editor_tabs.currentChanged.connect(self.on_tab_changed)
        self.editor_tabs.tabCloseRequested.connect(self.close_tab)

        self.preview = PreviewWebView(self.translate_preview_to_japanese)
        self.preview.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.outline = QListWidget()
        self.outline.itemClicked.connect(self.jump_to_heading)

        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.addWidget(self._wrap_pane("アウトライン", self.outline, "見出し一覧（# 見出し / 1. 章タイトル）。クリックで本文へ移動"))
        self.splitter.addWidget(self._wrap_pane("Markdown編集", self.editor_tabs, "本文編集。md/txtのD&Dでファイルを開き、画像D&Dで本文へ挿入"))
        self.splitter.addWidget(self._wrap_pane("プレビュー", self.preview, "編集結果の表示（Mermaid/コードハイライト対応）"))
        self.splitter.setSizes([280, 560, 560])

        wrapper = QWidget()
        wrapper_layout = QVBoxLayout(wrapper)
        wrapper_layout.setContentsMargins(0, 0, 0, 0)
        wrapper_layout.addWidget(self.splitter)
        self.setCentralWidget(wrapper)

        self._create_actions()
        self._create_menus()
        # 保存済みテーマをメニューのチェック状態に反映
        self.act_theme_light.setChecked(self.theme_mode == "light")
        self.act_theme_dark.setChecked(self.theme_mode == "dark")

        self.autosave_timer = QTimer(self)
        self.autosave_timer.setInterval(self.AUTOSAVE_MS)
        self.autosave_timer.timeout.connect(self.autosave)

        self._create_editor_tab()
        self._apply_editor_theme()

        self.refresh_preview()
        self._restore_window_state(settings)
        self._update_file_label()

    def _wrap_pane(self, title: str, widget: QWidget, tip: str) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(4)

        label = QLabel(title)
        label.setStyleSheet("font-weight: 600;")
        label.setToolTip(tip)
        widget.setToolTip(tip)

        layout.addWidget(label, 0)
        layout.addWidget(widget, 1)
        return container

    def _current_editor(self) -> MarkdownEditor | None:
        w = self.editor_tabs.currentWidget()
        return w if isinstance(w, MarkdownEditor) else None

    def _editor_text(self, editor: MarkdownEditor | None) -> str:
        if editor is None:
            return ""
        return MarkdownEditor.normalize_plain_text(editor.toPlainText())

    def _editor_file(self, editor: MarkdownEditor) -> Path | None:
        raw = editor.property("file_path")
        if not raw:
            return None
        return Path(str(raw))

    def _set_editor_file(self, editor: MarkdownEditor, path: Path | None) -> None:
        editor.setProperty("file_path", str(path) if path else "")

    def _tab_title_for_editor(self, editor: MarkdownEditor) -> str:
        path = self._editor_file(editor)
        base = path.name if path else "無題"
        if editor.document().isModified():
            return f"* {base}"
        return base

    def _update_tab_title(self, editor: MarkdownEditor) -> None:
        idx = self.editor_tabs.indexOf(editor)
        if idx >= 0:
            self.editor_tabs.setTabText(idx, self._tab_title_for_editor(editor))

    def _create_editor_tab(self, text: str = "", path: Path | None = None, make_current: bool = True) -> MarkdownEditor:
        editor = MarkdownEditor(self.get_image_drop_dir, self.open_markdown_file, self.show_status)
        editor.setPlaceholderText(
            "ここにMarkdownを入力します。\n"
            "例: # 見出し\n\n- 箇条書き\n\n```python\nprint('hello')\n```"
        )
        editor.textChanged.connect(self.on_text_changed)
        editor.document().modificationChanged.connect(lambda _changed, e=editor: self._update_tab_title(e))

        self._set_editor_file(editor, path)
        editor.setPlainText(text)
        editor.document().setModified(False)

        idx = self.editor_tabs.addTab(editor, self._tab_title_for_editor(editor))
        if make_current:
            self.editor_tabs.setCurrentIndex(idx)
            self._focus_editor_later(editor)
        # 現在のテーマをこの新規タブにも適用
        if self.theme_mode == "dark":
            dark_css = "background:#0f1115; color:#f2f2f2; border:1px solid #2b2f36;"
            editor.setStyleSheet(f"QPlainTextEdit {{ {dark_css} selection-background-color:#2f81f7; }}")
        return editor

    def on_tab_changed(self, _index: int) -> None:
        editor = self._current_editor()
        self.current_file = self._editor_file(editor) if editor else None
        self.refresh_preview()
        self.refresh_outline()
        if editor is not None:
            self._focus_editor_later(editor)
        if self.current_file:
            self.setWindowTitle(f"Sakura NoteForge - {self.current_file.name}")
        else:
            self.setWindowTitle("Sakura NoteForge - 無題")
        self._update_file_label()

    def _focus_editor_later(self, editor: MarkdownEditor) -> None:
        def _focus_once() -> None:
            if self._current_editor() is editor:
                editor.setFocus(Qt.FocusReason.OtherFocusReason)

        QTimer.singleShot(0, _focus_once)
        QTimer.singleShot(60, _focus_once)

    def _restore_window_state(self, settings: dict) -> None:
        """settings.json からウィンドウ位置・サイズ・ペイン幅を復元。未記録なら屋中屋表示。"""
        geom = settings.get("geometry")
        sizes = settings.get("splitter_sizes")
        if geom and all(k in geom for k in ("x", "y", "w", "h")):
            self.setGeometry(geom["x"], geom["y"], geom["w"], geom["h"])
        else:
            self.center_on_primary_screen()
        if sizes and len(sizes) == 3:
            self.splitter.setSizes(sizes)

    def closeEvent(self, event) -> None:
        """close 時にウィンドウ状態を追加保存。"""
        g = self.geometry()
        self._save_settings(
            extra={"geometry": {"x": g.x(), "y": g.y(), "w": g.width(), "h": g.height()},
                   "splitter_sizes": self.splitter.sizes()}
        )
        super().closeEvent(event)

    def center_on_primary_screen(self):
        app = QApplication.instance()
        if app is None:
            return
        screen = app.primaryScreen()
        if screen is None:
            return
        rect = screen.availableGeometry()
        frame = self.frameGeometry()
        frame.moveCenter(rect.center())
        self.move(frame.topLeft())

    def _create_actions(self):
        self.act_new_tab = QAction("新規タブ", self)
        self.act_new_tab.setShortcut(QKeySequence.StandardKey.New)
        self.act_new_tab.triggered.connect(self.new_tab)

        self.act_open = QAction("開く", self)
        self.act_open.setShortcut(QKeySequence.StandardKey.Open)
        self.act_open.triggered.connect(self.open_markdown)

        self.act_save = QAction("保存", self)
        self.act_save.setShortcut(QKeySequence.StandardKey.Save)
        self.act_save.triggered.connect(self.save_markdown)

        self.act_save_as = QAction("名前を付けて保存", self)
        self.act_save_as.setShortcut(QKeySequence.StandardKey.SaveAs)
        self.act_save_as.triggered.connect(self.save_markdown_as)

        self.act_export_pdf = QAction("PDFとして出力", self)
        self.act_export_pdf.triggered.connect(self.export_pdf)

        self.act_reload_document = QAction("再読み込み", self)
        self.act_reload_document.setShortcut(QKeySequence("F5"))
        self.act_reload_document.triggered.connect(self.reload_current_document)

        self.act_insert_design_template = QAction("設計テンプレートを挿入", self)
        self.act_insert_design_template.triggered.connect(self.insert_design_template)

        self.act_find = QAction("検索...", self)
        self.act_find.setShortcut("Ctrl+F")
        self.act_find.triggered.connect(self.open_find_dialog)

        self.act_find_next = QAction("次を検索", self)
        self.act_find_next.setShortcut("F3")
        self.act_find_next.triggered.connect(self.find_next)

        self.act_find_prev = QAction("前を検索", self)
        self.act_find_prev.setShortcut("Shift+F3")
        self.act_find_prev.triggered.connect(self.find_previous)

        self.act_replace = QAction("置換...", self)
        self.act_replace.setShortcut("Ctrl+H")
        self.act_replace.triggered.connect(self.open_replace_dialog)

        self.act_theme_light = QAction("ライト", self)
        self.act_theme_light.setCheckable(True)
        self.act_theme_light.setChecked(True)
        self.act_theme_light.triggered.connect(lambda: self.set_theme("light"))

        self.act_theme_dark = QAction("ダーク", self)
        self.act_theme_dark.setCheckable(True)
        self.act_theme_dark.triggered.connect(lambda: self.set_theme("dark"))

        self.act_usage = QAction("使い方", self)
        self.act_usage.triggered.connect(self.show_usage_guide)

    def _create_menus(self):
        menu_file = self.menuBar().addMenu("ファイル")
        menu_file.addAction(self.act_new_tab)
        menu_file.addAction(self.act_open)
        menu_file.addAction(self.act_reload_document)
        menu_file.addAction(self.act_save)
        menu_file.addAction(self.act_save_as)
        menu_file.addSeparator()
        self._menu_recent = menu_file.addMenu("最近開いたファイル")
        self._rebuild_recent_menu()
        menu_file.addSeparator()
        menu_file.addAction(self.act_export_pdf)

        menu_edit = self.menuBar().addMenu("編集")
        menu_edit.addAction(self.act_find)
        menu_edit.addAction(self.act_find_next)
        menu_edit.addAction(self.act_find_prev)
        menu_edit.addSeparator()
        menu_edit.addAction(self.act_replace)

        menu_insert = self.menuBar().addMenu("挿入")
        menu_insert.addAction(self.act_insert_design_template)

        menu_view = self.menuBar().addMenu("表示")
        menu_theme = menu_view.addMenu("テーマ")
        menu_theme.addAction(self.act_theme_light)
        menu_theme.addAction(self.act_theme_dark)

        menu_help = self.menuBar().addMenu("ヘルプ")
        menu_help.addAction(self.act_usage)

    def show_usage_guide(self):
        QMessageBox.information(
            self,
            "Sakura NoteForge 使い方",
            "■ 3ペインの役割\n"
            "- 左: アウトライン（# 見出し / 1. 章タイトル を一覧化）\n"
            "- 中央: Markdown編集\n"
            "- 右: プレビュー\n\n"
            "■ 基本操作\n"
            "1) ファイル > 新規タブ / 開く で作業タブを用意\n"
            "2) 中央ペインで編集\n"
            "3) 右ペインで結果確認（自動反映）\n"
            "4) Ctrl+S で保存\n\n"
            "■ D&D\n"
            "- md/txt を中央へD&D: ファイルを開く\n"
            "- 画像を中央へD&D: ![]() として本文へ挿入\n\n"
            "■ 便利機能\n"
            "- 複数ファイルを開くとタブで切替編集\n"
            "- 左ペインの項目をクリックすると該当行へジャンプ\n"
            "- 挿入 > 設計テンプレートを挿入 で雛形作成\n"
            "- ファイル > PDFとして出力 でPDF化\n\n"
            "■ プレビューのリンク移動\n"
            "- リンクをクリックすると、プレビュー内で移動します\n"
            "- 元のページへ戻る/進む: プレビュー上で右クリック →『戻る』『進む』\n"
            "- 表示更新: プレビュー上で右クリック →『再読み込み』\n"
            "- 日本語変換: プレビュー上で右クリック →『日本語に変換（Google翻訳）』\n"
            "  （同じプレビュー内で本文を直接翻訳表示します）\n"
        )

    def translate_preview_to_japanese(self) -> None:
        js = (
            "(function(){"
            "const s=(window.getSelection&&window.getSelection().toString())||'';"
            "if(s.trim()) return s;"
            "const b=document.body;"
            "return b ? (b.innerText||'') : '';"
            "})();"
        )
        self.preview.page().runJavaScript(js, self._open_translate_text_in_preview)

    def _open_translate_text_in_preview(self, text) -> None:
        txt = str(text or "").strip()
        if not txt:
            self.show_status("翻訳対象テキストが見つかりません", 2500)
            return

        # 変換APIの長さ制限を考慮して先頭のみ利用
        max_chars = 2500
        clipped = txt[:max_chars]

        translated, detected = self._translate_text_with_google(clipped)
        if not translated:
            self.show_status("翻訳に失敗しました（接続または応答形式を確認してください）", 3000)
            return

        translated_html = html.escape(translated).replace("\n", "<br>")
        source_html = html.escape(clipped).replace("\n", "<br>")
        page = f"""
<!doctype html>
<html lang=\"ja\">
<head>
  <meta charset=\"utf-8\">
  <style>
    body {{ font-family: 'Segoe UI', sans-serif; margin: 20px; line-height: 1.7; }}
    .meta {{ color: #666; font-size: 0.9em; margin-bottom: 12px; }}
    .card {{ border: 1px solid #ddd; border-radius: 8px; padding: 14px; margin-bottom: 14px; }}
    h2 {{ margin: 0 0 10px 0; font-size: 1.1em; }}
  </style>
</head>
<body>
  <div class=\"meta\">日本語変換結果（検出言語: {html.escape(detected or 'auto')}）</div>
  <div class=\"card\">
    <h2>翻訳結果（日本語）</h2>
    <div>{translated_html}</div>
  </div>
  <div class=\"card\">
    <h2>元テキスト</h2>
    <div>{source_html}</div>
  </div>
</body>
</html>
"""
        self.preview.setHtml(page)

        if len(txt) > max_chars:
            self.show_status("本文が長いため先頭部分のみ翻訳表示しました", 2500)
        else:
            self.show_status("プレビュー内で日本語変換を表示しました", 2000)

    def _translate_text_with_google(self, text: str) -> tuple[str, str]:
        url = (
            "https://translate.googleapis.com/translate_a/single"
            f"?client=gtx&sl=auto&tl=ja&dt=t&q={quote_plus(text)}"
        )
        try:
            with urllib.request.urlopen(url, timeout=15) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
        except Exception:
            return "", ""

        if not isinstance(payload, list) or not payload:
            return "", ""

        segments = payload[0] if isinstance(payload[0], list) else []
        translated = "".join(
            seg[0] for seg in segments
            if isinstance(seg, list) and len(seg) > 0 and isinstance(seg[0], str)
        )
        detected = payload[2] if len(payload) > 2 and isinstance(payload[2], str) else "auto"
        return translated, detected

    def new_tab(self) -> None:
        self._create_editor_tab()
        self.show_status("新規タブを作成しました", 1500)

    def close_tab(self, index: int) -> None:
        editor = self.editor_tabs.widget(index)
        if isinstance(editor, MarkdownEditor) and editor.document().isModified():
            path = self._editor_file(editor)
            name = path.name if path else "無題"
            reply = QMessageBox.question(
                self,
                "未保存の変更",
                f"「{name}」は変更されています。閉じる前に保存しますか？",
                QMessageBox.StandardButton.Save
                | QMessageBox.StandardButton.Discard
                | QMessageBox.StandardButton.Cancel,
            )
            if reply == QMessageBox.StandardButton.Cancel:
                return
            if reply == QMessageBox.StandardButton.Save:
                self.editor_tabs.setCurrentIndex(index)
                self.save_markdown()
        if self.editor_tabs.count() == 1:
            # 最後のタブは閉じず、内容をリセットして再利用
            editor = self.editor_tabs.currentWidget()
            if isinstance(editor, MarkdownEditor):
                editor.setPlainText("")
                self._set_editor_file(editor, None)
                editor.document().setModified(False)
                self.editor_tabs.setTabText(0, "無題")
            return
        self.editor_tabs.removeTab(index)

    def _settings_path(self) -> Path:
        return self.data_dir / "settings.json"

    def _load_settings(self) -> dict:
        p = self.data_dir / "settings.json"
        if p.exists():
            try:
                return json.loads(p.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {}

    def _save_settings(self, extra: dict | None = None) -> None:
        settings: dict = {
            "theme": self.theme_mode,
            "recent_files": self._recent_files,
        }
        if extra:
            settings.update(extra)
        try:
            self.data_dir.mkdir(parents=True, exist_ok=True)
            self._settings_path().write_text(
                json.dumps(settings, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        except Exception:
            pass

    def _add_recent_file(self, path: Path) -> None:
        s = str(path)
        if s in self._recent_files:
            self._recent_files.remove(s)
        self._recent_files.insert(0, s)
        self._recent_files = self._recent_files[:15]  # 最大15件
        self._save_settings()
        self._rebuild_recent_menu()

    def _rebuild_recent_menu(self) -> None:
        self._menu_recent.clear()
        valid = [p for p in self._recent_files if Path(p).exists()]
        if not valid:
            act = QAction("（履歴なし）", self)
            act.setEnabled(False)
            self._menu_recent.addAction(act)
            return
        for p_str in valid:
            p = Path(p_str)
            act = QAction(p.name, self)
            act.setToolTip(p_str)
            act.triggered.connect(lambda checked=False, _p=p: self.open_markdown_file(_p))
            self._menu_recent.addAction(act)
        self._menu_recent.addSeparator()
        act_clear = QAction("履歴をクリア", self)
        act_clear.triggered.connect(self._clear_recent_files)
        self._menu_recent.addAction(act_clear)

    def _clear_recent_files(self) -> None:
        self._recent_files = []
        self._save_settings()
        self._rebuild_recent_menu()

    def set_theme(self, mode: str) -> None:
        self.theme_mode = mode
        self.act_theme_light.setChecked(mode == "light")
        self.act_theme_dark.setChecked(mode == "dark")
        self._apply_editor_theme()
        self.refresh_preview()
        self._save_settings()

    def _apply_editor_theme(self) -> None:
        if self.theme_mode == "dark":
            dark_css = "background:#0f1115; color:#f2f2f2; border:1px solid #2b2f36;"
            editor_css = f"QPlainTextEdit {{ {dark_css} selection-background-color:#2f81f7; }}"
            self.outline.setStyleSheet(
                f"QListWidget {{ {dark_css} }}"
                "QListWidget::item:selected { background:#2f81f7; color:#ffffff; }"
            )
            for i in range(self.editor_tabs.count()):
                w = self.editor_tabs.widget(i)
                if isinstance(w, MarkdownEditor):
                    w.setStyleSheet(editor_css)
        else:
            for i in range(self.editor_tabs.count()):
                w = self.editor_tabs.widget(i)
                if isinstance(w, MarkdownEditor):
                    w.setStyleSheet("")
            self.outline.setStyleSheet("")

    def open_find_dialog(self) -> None:
        dlg = QDialog(self)
        dlg.setWindowTitle("検索")
        dlg.resize(360, 80)
        layout = QFormLayout(dlg)
        edit = QLineEdit(self._find_text, dlg)
        layout.addRow("検索文字列:", edit)
        btns = QDialogButtonBox(dlg)
        btn_next = btns.addButton("次へ (F3)", QDialogButtonBox.ButtonRole.ActionRole)
        btn_prev = btns.addButton("前へ", QDialogButtonBox.ButtonRole.ActionRole)
        btn_close = btns.addButton("閉じる", QDialogButtonBox.ButtonRole.RejectRole)
        layout.addRow(btns)

        def _next():
            self._find_text = edit.text()
            self._do_find(forward=True)

        def _prev():
            self._find_text = edit.text()
            self._do_find(forward=False)

        btn_next.clicked.connect(_next)
        btn_prev.clicked.connect(_prev)
        btn_close.clicked.connect(dlg.reject)
        edit.returnPressed.connect(_next)
        dlg.exec()

    def _do_find(self, forward: bool = True) -> None:
        editor = self._current_editor()
        if editor is None:
            return
        if not self._find_text:
            return
        flags = QTextDocument.FindFlag(0)
        if not forward:
            flags |= QTextDocument.FindFlag.FindBackward
        found = editor.find(self._find_text, flags)
        if not found:
            # 末尾 or 先頭まで来たら折り返し
            cursor = editor.textCursor()
            if forward:
                cursor.movePosition(cursor.MoveOperation.Start)
            else:
                cursor.movePosition(cursor.MoveOperation.End)
            editor.setTextCursor(cursor)
            editor.find(self._find_text, flags)

    def find_next(self) -> None:
        self._do_find(forward=True)

    def find_previous(self) -> None:
        self._do_find(forward=False)

    def open_replace_dialog(self) -> None:
        dlg = QDialog(self)
        dlg.setWindowTitle("置換")
        dlg.resize(380, 110)
        layout = QFormLayout(dlg)
        edit_find = QLineEdit(self._find_text, dlg)
        edit_replace = QLineEdit("", dlg)
        layout.addRow("検索:", edit_find)
        layout.addRow("置換後:", edit_replace)

        btn_row = QHBoxLayout()
        btn_next = QPushButton("次へ")
        btn_replace = QPushButton("置換")
        btn_replace_all = QPushButton("すべて置換")
        btn_close = QPushButton("閉じる")
        for b in (btn_next, btn_replace, btn_replace_all, btn_close):
            btn_row.addWidget(b)
        layout.addRow(btn_row)

        def _sync():
            self._find_text = edit_find.text()

        def _next():
            _sync()
            self._do_find(forward=True)

        def _replace():
            _sync()
            editor = self._current_editor()
            if editor is None:
                return
            cursor = editor.textCursor()
            if cursor.hasSelection() and cursor.selectedText() == edit_find.text():
                cursor.insertText(edit_replace.text())
            self._do_find(forward=True)

        def _replace_all():
            _sync()
            editor = self._current_editor()
            if editor is None:
                return
            if not edit_find.text():
                return
            text = self._editor_text(editor)
            new_text = text.replace(edit_find.text(), edit_replace.text())
            count = text.count(edit_find.text())
            editor.setPlainText(new_text)
            self.show_status(f"{count} 件置換しました", 3000)

        btn_next.clicked.connect(_next)
        btn_replace.clicked.connect(_replace)
        btn_replace_all.clicked.connect(_replace_all)
        btn_close.clicked.connect(dlg.reject)
        edit_find.returnPressed.connect(_next)
        dlg.exec()

    def on_text_changed(self):
        self.refresh_preview()
        self.refresh_outline()
        self.autosave_timer.start()

    def refresh_preview(self):
        editor = self._current_editor()
        md = self._editor_text(editor)
        editor_had_focus = bool(editor and editor.hasFocus())
        html_body = markdown.markdown(
            md,
            extensions=["fenced_code", "tables", "codehilite", "toc", "nl2br"],
            output_format="html5",
        )

        dark = self.theme_mode == "dark"
        bg = "#0f1115" if dark else "#ffffff"
        fg = "#f2f2f2" if dark else "#202124"
        code_bg = "#171b22" if dark else "#f6f8fa"
        border = "#2b2f36" if dark else "#e5e7eb"
        quote_color = "#a9b1bb" if dark else "#555"
        hl_css = "github-dark" if dark else "github"

        html = f"""
<!doctype html>
<html>
<head>
<meta charset=\"utf-8\" />
<link rel=\"stylesheet\" href=\"https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/{hl_css}.min.css\">
<style>
body {{ font-family: 'Segoe UI', sans-serif; padding: 16px; line-height: 1.6; background:{bg}; color:{fg}; }}
h1, h2, h3, h4, h5, h6 {{ margin-top: 0.5em; margin-bottom: 0.25em; line-height: 1.3; }}
h1 {{ font-size: 1.5em; }}
h2 {{ font-size: 1.25em; }}
h3 {{ font-size: 1.1em; }}
h4, h5, h6 {{ font-size: 1em; }}
pre {{ background: {code_bg}; border:1px solid {border}; padding: 12px; border-radius: 8px; overflow: auto; }}
code {{ font-family: Consolas, monospace; }}
blockquote {{ border-left: 4px solid {border}; margin-left: 0; padding-left: 12px; color: {quote_color}; }}
img {{ max-width: 100%; height: auto; }}
a {{ color: {'#58a6ff' if dark else '#0969da'}; }}
</style>
<script src=\"https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js\"></script>
<script src=\"https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/highlight.min.js\"></script>
<script>
mermaid.initialize({{ startOnLoad: true, theme: '{'dark' if dark else 'default'}' }});
document.addEventListener('DOMContentLoaded', () => {{
  document.querySelectorAll('pre code').forEach((el) => hljs.highlightElement(el));
  document.querySelectorAll('pre code.language-mermaid').forEach((el) => {{
    const div = document.createElement('div');
    div.className = 'mermaid';
    div.textContent = el.textContent;
    el.parentElement.replaceWith(div);
  }});
  if (window.mermaid) mermaid.run();
}});
</script>
</head>
<body>
{html_body}
</body>
</html>
        """
        self.preview.setHtml(html)
        if editor is not None and editor_had_focus:
            QTimer.singleShot(0, editor.setFocus)

    def refresh_outline(self):
        editor = self._current_editor()
        text = self._editor_text(editor)
        self.outline.clear()

        added = 0
        heading_idx = 0  # プレビューHTML内の h1~h6 要素インデックス
        for line_no, line in enumerate(text.splitlines(), start=1):
            h = re.match(r"^(#{1,6})\s+(.+)$", line)
            if h:
                level = len(h.group(1))
                title = h.group(2).strip()
                item = QListWidgetItem(f"{'  ' * (level - 1)}H{level} {title}")
                item.setData(Qt.ItemDataRole.UserRole, line_no)
                item.setData(Qt.ItemDataRole.UserRole + 1, heading_idx)
                self.outline.addItem(item)
                heading_idx += 1
                added += 1
                continue

            n = re.match(r"^\s*(\d+(?:\.\d+)*)(?:[\)\.]\s+|\s+)(.+)$", line)
            if n:
                number = n.group(1)
                title = n.group(2).strip()
                depth = number.count(".")
                item = QListWidgetItem(f"{'  ' * depth}§ {number} {title}")
                item.setData(Qt.ItemDataRole.UserRole, line_no)
                item.setData(Qt.ItemDataRole.UserRole + 1, None)
                self.outline.addItem(item)
                added += 1

        if added == 0:
            placeholder = QListWidgetItem("（見出しがありません。# 見出し または 1. 章タイトル を書くと表示されます）")
            placeholder.setData(Qt.ItemDataRole.UserRole, None)
            placeholder.setData(Qt.ItemDataRole.UserRole + 1, None)
            self.outline.addItem(placeholder)

    def jump_to_heading(self, item: QListWidgetItem):
        editor = self._current_editor()
        if editor is None:
            return
        raw_line = item.data(Qt.ItemDataRole.UserRole)
        if raw_line is None:
            return
        line_no = int(raw_line)
        block = editor.document().findBlockByLineNumber(line_no - 1)
        cursor = editor.textCursor()
        cursor.setPosition(block.position())
        editor.setTextCursor(cursor)
        editor.setFocus()

        # プレビューも対応する見出しへスクロール
        heading_idx = item.data(Qt.ItemDataRole.UserRole + 1)
        if heading_idx is not None:
            js = (
                f"var els = document.querySelectorAll('h1,h2,h3,h4,h5,h6');"
                f"if (els[{heading_idx}]) els[{heading_idx}].scrollIntoView({{behavior:'smooth', block:'start'}});"
            )
            self.preview.page().runJavaScript(js)

    def open_markdown(self):
        path_list, _ = QFileDialog.getOpenFileNames(self, "Markdownを開く", "", "Markdown (*.md);;Text (*.txt)")
        if not path_list:
            return
        for p in path_list:
            self.open_markdown_file(Path(p))

    def open_markdown_file(self, path: Path):
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            text = path.read_text(encoding="cp932")

        # 既に開いている場合はそのタブへ移動
        for i in range(self.editor_tabs.count()):
            w = self.editor_tabs.widget(i)
            if isinstance(w, MarkdownEditor):
                p = self._editor_file(w)
                if p and p.resolve() == path.resolve():
                    self.editor_tabs.setCurrentIndex(i)
                    self.show_status(f"既に開いています: {path.name}", 2500)
                    return

        editor = self._create_editor_tab(text=text, path=path, make_current=True)
        editor.document().setModified(False)
        self.current_file = path
        self.setWindowTitle(f"Sakura NoteForge - {path.name}")
        self._update_file_label()
        self._add_recent_file(path)
        self.show_status(f"開きました: {path}", 3000)

    def reload_current_document(self) -> None:
        editor = self._current_editor()
        if editor is None:
            return

        path = self._editor_file(editor)
        if path is None:
            self.show_status("未保存タブは再読み込みできません（先に保存してください）", 3000)
            return
        if not path.exists():
            self.show_status("ファイルが見つかりません", 3000)
            return

        if editor.document().isModified():
            reply = QMessageBox.question(
                self,
                "再読み込み",
                "未保存の変更があります。破棄してファイルを再読み込みしますか？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            text = path.read_text(encoding="cp932")

        editor.blockSignals(True)
        editor.setPlainText(text)
        editor.blockSignals(False)
        editor.document().setModified(False)
        self._set_editor_file(editor, path)
        self.current_file = path
        self._update_tab_title(editor)
        self.refresh_preview()
        self.refresh_outline()
        self._update_file_label()
        self.show_status(f"再読み込みしました: {path.name}", 2000)

    def _update_file_label(self) -> None:
        if self.current_file:
            self.statusBar().showMessage(str(self.current_file))
        else:
            self.statusBar().showMessage("未保存")

    def show_status(self, message: str, ms: int = 2000):
        self.statusBar().showMessage(message, ms)
        # ms後にファイルパスを復元
        QTimer.singleShot(ms, self._update_file_label)

    def save_markdown(self):
        editor = self._current_editor()
        if editor is None:
            return
        self.current_file = self._editor_file(editor)
        if self.current_file is None:
            self.save_markdown_as()
            return

        self.current_file.write_text(self._editor_text(editor), encoding="utf-8")
        editor.document().setModified(False)
        self._update_tab_title(editor)
        self.write_history_snapshot()
        self._update_file_label()
        self.show_status("保存しました", 2000)
        saved_name = self.current_file.name if self.current_file else "無題"
        QMessageBox.information(self, "保存完了", f"保存しました: {saved_name}")

    def save_markdown_as(self):
        editor = self._current_editor()
        if editor is None:
            return
        path_str, _ = QFileDialog.getSaveFileName(self, "Markdownを保存", "", "Markdown (*.md)")
        if not path_str:
            return
        path = Path(path_str)
        self._set_editor_file(editor, path)
        self._update_tab_title(editor)
        self.current_file = path
        self.save_markdown()
        self.setWindowTitle(f"Sakura NoteForge - {path.name}")

    def autosave(self):
        editor = self._current_editor()
        if editor is None:
            return
        current_file = self._editor_file(editor)
        self.autosave_timer.stop()
        key = current_file.stem if current_file else "untitled"
        safe = re.sub(r"[^a-zA-Z0-9_-]", "_", key)
        autosave_path = self.autosave_dir / f"{safe}.autosave.md"
        autosave_path.write_text(self._editor_text(editor), encoding="utf-8")
        self.show_status(f"自動保存: {autosave_path.name}", 1500)

    def write_history_snapshot(self):
        editor = self._current_editor()
        if editor is None:
            return
        current_file = self._editor_file(editor)
        if current_file is None:
            return
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        target_dir = self.history_dir / current_file.stem
        target_dir.mkdir(parents=True, exist_ok=True)
        snapshot = target_dir / f"{ts}.md"
        snapshot.write_text(self._editor_text(editor), encoding="utf-8")

    def export_pdf(self):
        editor = self._current_editor()
        if editor is None:
            return
        if self._editor_text(editor).strip() == "":
            QMessageBox.information(self, "PDF出力", "本文が空です。")
            return

        initial = self.current_file.with_suffix(".pdf") if self.current_file else Path.home() / "document.pdf"
        path_str, _ = QFileDialog.getSaveFileName(self, "PDFとして保存", str(initial), "PDF (*.pdf)")
        if not path_str:
            return

        self.preview.page().printToPdf(path_str)
        self.show_status("PDF出力を開始しました", 3000)

    def insert_design_template(self):
        editor = self._current_editor()
        if editor is None:
            return
        template = (
            "# ドキュメントタイトル\n\n"
            "## 1. 背景\n"
            "- 課題\n"
            "- 目的\n\n"
            "## 2. 要件\n"
            "- 機能要件\n"
            "- 非機能要件\n\n"
            "## 3. 設計\n"
            "### 3.1 構成\n"
            "### 3.2 データ\n"
            "### 3.3 画面\n\n"
            "## 4. テスト\n"
            "- 観点\n"
            "- ケース\n\n"
            "## 5. リスクと対応\n"
            "- リスク\n"
            "- 対応\n"
        )

        if self._editor_text(editor).strip():
            reply = QMessageBox.question(
                self,
                "設計テンプレート挿入",
                "現在の内容に追記して設計テンプレートを挿入しますか？",
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
            editor.insertPlainText("\n\n" + template)
        else:
            editor.setPlainText(template)

        self.show_status("設計テンプレートを挿入しました", 3000)

    def get_image_drop_dir(self) -> Path:
        editor = self._current_editor()
        current_file = self._editor_file(editor) if editor else None
        if current_file:
            return current_file.parent / "images"
        return self.base_dir / "data" / "images"


def run_app() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("Sakura NoteForge")
    app.setOrganizationName("Sakura")
    win = NoteForgeWindow()

    win.showNormal()
    win.raise_()
    win.activateWindow()

    def _focus_window():
        win.showNormal()
        win.raise_()
        win.activateWindow()

    QTimer.singleShot(200, _focus_window)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(run_app())
