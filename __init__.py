from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

from aqt import gui_hooks, mw
from aqt.qt import (
    QAction,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QMessageBox,
    QSpinBox,
    QVBoxLayout,
    QUrl,
    QPageLayout,
    QPageSize,
    QMarginsF,
)

try:
    from PyQt6.QtWebEngineWidgets import QWebEngineView  # type: ignore
except Exception:
    QWebEngineView = None  # type: ignore

from .exporter import build_export_html, export_cards_html

ADDON_PACKAGE = __name__

DEFAULT_CONFIG: Dict[str, Any] = {
    "01_general": {"enabled": True},
    "02_export": {
        "export_mode": "both",            # front / back / both
        "output_format": "html",          # html / pdf
        "pdf_layout": "single",           # single / two_column
        "default_filename": "anki_exporter",
        "copy_media_files": True,
    },
    "04_images": {
        "img_max_width_px": 800,
        "img_max_height_px": 400,
    },
}

# PDF印刷の非同期処理中にGCされないよう保持
_PDF_JOBS: set[object] = set()


def _deep_merge(defaults: Dict[str, Any], user: Dict[str, Any]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for k, dv in defaults.items():
        uv = user.get(k, None)
        if isinstance(dv, dict) and isinstance(uv, dict):
            out[k] = _deep_merge(dv, uv)
        else:
            out[k] = uv if uv is not None else dv
    return out


def get_config() -> Dict[str, Any]:
    try:
        user_conf = mw.addonManager.getConfig(ADDON_PACKAGE)
    except Exception:
        user_conf = None
    if not isinstance(user_conf, dict):
        user_conf = {}
    return _deep_merge(DEFAULT_CONFIG, user_conf)


def _write_config(conf: Dict[str, Any]) -> None:
    sanitized = _deep_merge(DEFAULT_CONFIG, conf)
    try:
        mw.addonManager.writeConfig(ADDON_PACKAGE, sanitized)
    except Exception:
        try:
            mw.addonManager.setConfig(ADDON_PACKAGE, sanitized)
        except Exception:
            pass


def _selected_card_ids(browser) -> list[int]:
    if hasattr(browser, "selected_cards"):
        return list(browser.selected_cards())
    return list(browser.selectedCards())


class ConfigDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Exporter - Settings")
        self.setMinimumWidth(640)

        cfg = get_config()

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        # ---- General
        box_general = QGroupBox("General")
        form_g = QFormLayout(box_general)
        form_g.setVerticalSpacing(10)

        self.enabled_cb = QCheckBox()
        self.enabled_cb.setChecked(bool(cfg.get("01_general", {}).get("enabled", True)))
        form_g.addRow("Enable add-on", self.enabled_cb)
        root.addWidget(box_general)

        # ---- Export
        box_export = QGroupBox("Export")
        form_e = QFormLayout(box_export)
        form_e.setVerticalSpacing(10)

        self.mode_combo = QComboBox()
        self.mode_combo.addItem("Front only (before <hr id=answer>)", "front")
        self.mode_combo.addItem("Back only (after <hr id=answer>)", "back")
        self.mode_combo.addItem("Both (full answer HTML)", "both")
        cur_mode = str(cfg.get("02_export", {}).get("export_mode", "back")).lower()
        i = self.mode_combo.findData(cur_mode)
        self.mode_combo.setCurrentIndex(i if i >= 0 else 1)
        form_e.addRow("Export mode", self.mode_combo)

        self.format_combo = QComboBox()
        self.format_combo.addItem("HTML", "html")
        self.format_combo.addItem("PDF", "pdf")
        cur_fmt = str(cfg.get("02_export", {}).get("output_format", "html")).lower()
        i = self.format_combo.findData(cur_fmt)
        self.format_combo.setCurrentIndex(i if i >= 0 else 0)
        form_e.addRow("Output format", self.format_combo)

        self.pdf_layout_combo = QComboBox()
        self.pdf_layout_combo.addItem("Single column", "single")
        self.pdf_layout_combo.addItem("Two columns", "two_column")
        cur_pl = str(cfg.get("02_export", {}).get("pdf_layout", "single")).lower()
        i = self.pdf_layout_combo.findData(cur_pl)
        self.pdf_layout_combo.setCurrentIndex(i if i >= 0 else 0)
        form_e.addRow("PDF layout", self.pdf_layout_combo)

        self.default_filename = QLineEdit()
        self.default_filename.setText(str(cfg.get("02_export", {}).get("default_filename", "selected_export.html")))
        form_e.addRow("Default output filename", self.default_filename)

        self.copy_media_cb = QCheckBox("Copy media files next to HTML (HTML only)")
        self.copy_media_cb.setChecked(bool(cfg.get("02_export", {}).get("copy_media_files", True)))
        form_e.addRow("", self.copy_media_cb)

        root.addWidget(box_export)

        # ---- Images
        box_img = QGroupBox("Images (CSS max size)")
        form_i = QFormLayout(box_img)
        form_i.setVerticalSpacing(10)

        self.max_w = QSpinBox()
        self.max_w.setRange(100, 5000)
        self.max_w.setSingleStep(50)
        self.max_w.setValue(int(cfg.get("04_images", {}).get("img_max_width_px", 800)))
        form_i.addRow("Max width (px)", self.max_w)

        self.max_h = QSpinBox()
        self.max_h.setRange(100, 5000)
        self.max_h.setSingleStep(50)
        self.max_h.setValue(int(cfg.get("04_images", {}).get("img_max_height_px", 400)))
        form_i.addRow("Max height (px)", self.max_h)

        root.addWidget(box_img)

        note = QLabel("Export is available from Browser right-click menu only.")
        note.setWordWrap(True)
        root.addWidget(note)

        # ---- Buttons (no Export button)
        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
            | QDialogButtonBox.StandardButton.RestoreDefaults
        )
        btns.accepted.connect(self._on_save)
        btns.rejected.connect(self.reject)

        btn_restore = btns.button(QDialogButtonBox.StandardButton.RestoreDefaults)
        if btn_restore:
            btn_restore.clicked.connect(self._on_restore_defaults)

        root.addWidget(btns)

    def _gather_conf(self) -> Dict[str, Any]:
        return {
            "01_general": {"enabled": bool(self.enabled_cb.isChecked())},
            "02_export": {
                "export_mode": str(self.mode_combo.currentData() or "back"),
                "output_format": str(self.format_combo.currentData() or "html"),
                "pdf_layout": str(self.pdf_layout_combo.currentData() or "single"),
                "default_filename": (self.default_filename.text() or "selected_export.html").strip(),
                "copy_media_files": bool(self.copy_media_cb.isChecked()),
            },
            "04_images": {
                "img_max_width_px": int(self.max_w.value()),
                "img_max_height_px": int(self.max_h.value()),
            },
        }

    def _on_restore_defaults(self) -> None:
        self.enabled_cb.setChecked(bool(DEFAULT_CONFIG["01_general"]["enabled"]))

        i = self.mode_combo.findData(DEFAULT_CONFIG["02_export"]["export_mode"])
        self.mode_combo.setCurrentIndex(i if i >= 0 else 1)

        i = self.format_combo.findData(DEFAULT_CONFIG["02_export"]["output_format"])
        self.format_combo.setCurrentIndex(i if i >= 0 else 0)

        i = self.pdf_layout_combo.findData(DEFAULT_CONFIG["02_export"]["pdf_layout"])
        self.pdf_layout_combo.setCurrentIndex(i if i >= 0 else 0)

        self.default_filename.setText(str(DEFAULT_CONFIG["02_export"]["default_filename"]))
        self.copy_media_cb.setChecked(bool(DEFAULT_CONFIG["02_export"]["copy_media_files"]))

        self.max_w.setValue(int(DEFAULT_CONFIG["04_images"]["img_max_width_px"]))
        self.max_h.setValue(int(DEFAULT_CONFIG["04_images"]["img_max_height_px"]))

    def _on_save(self) -> None:
        _write_config(self._gather_conf())
        QMessageBox.information(self, "Saved", "Settings saved.")
        self.accept()


def _show_config_dialog() -> None:
    dlg = ConfigDialog(mw)
    dlg.exec()


def _ensure_ext(name: str, ext: str) -> str:
    n = (name or "").strip()
    if not n:
        n = f"selected_export.{ext}"
    if not n.lower().endswith(f".{ext}"):
        n += f".{ext}"
    return n


def _export_to_pdf(parent, col, card_ids, pdf_path: Path, cfg: Dict[str, Any]) -> None:
    if QWebEngineView is None:
        QMessageBox.critical(parent, "PDF export", "QtWebEngine is not available in this Anki build.")
        return

    html = build_export_html(col, card_ids, cfg)

    # 相対画像の基準は “collection.media” にする（PDFはファイルを横にコピーしなくてOK）
    base_dir = Path(col.media.dir()).resolve()
    base_url = QUrl.fromLocalFile(str(base_dir) + "/")

    view = QWebEngineView()
    _PDF_JOBS.add(view)

    page = view.page()

    def _cleanup() -> None:
        try:
            _PDF_JOBS.discard(view)
            view.deleteLater()
        except Exception:
            pass

    def _on_pdf_finished(*args) -> None:
        # pdfPrintingFinished(filePath, success) のはずだが、環境差があるので args で受ける
        success = bool(args[-1]) if args else True
        if success:
            QMessageBox.information(parent, "PDF export", f"PDF exported:\n{pdf_path}")
        else:
            QMessageBox.critical(parent, "PDF export", "Failed to generate PDF.")
        _cleanup()

    try:
        page.pdfPrintingFinished.connect(_on_pdf_finished)
    except Exception:
        # ここでコケる環境は稀。失敗しても一応続行
        pass

    def _on_load_finished(ok: bool) -> None:
        if not ok:
            QMessageBox.critical(parent, "PDF export", "Failed to render HTML for PDF.")
            _cleanup()
            return

        # A4 / 余白10mm
        layout = QPageLayout(
            QPageSize(QPageSize.PageSizeId.A4),
            QPageLayout.Orientation.Portrait,
            QMarginsF(10, 10, 10, 10),
            QPageLayout.Unit.Millimeter,
        )

        # 非同期でPDF化（完了は pdfPrintingFinished）:contentReference[oaicite:5]{index=5}
        page.printToPdf(str(pdf_path), layout)

    view.loadFinished.connect(_on_load_finished)
    view.setHtml(html, base_url)  # baseUrlが無いと相対リンクが壊れる :contentReference[oaicite:6]{index=6}


def run_export_from_browser(browser) -> None:
    if not mw.col:
        QMessageBox.critical(browser, "Export", "Collection is not loaded.")
        return

    cfg = get_config()
    if not bool(cfg.get("01_general", {}).get("enabled", True)):
        QMessageBox.information(browser, "Export", "Add-on is disabled in settings.")
        return

    card_ids = _selected_card_ids(browser)
    if not card_ids:
        QMessageBox.information(browser, "Export", "No card selected.")
        return

    fmt = str(cfg.get("02_export", {}).get("output_format", "html") or "html").lower().strip()
    if fmt not in {"html", "pdf"}:
        fmt = "html"

    default_name = str(cfg.get("02_export", {}).get("default_filename", "selected_export.html"))
    default_name = _ensure_ext(default_name, "pdf" if fmt == "pdf" else "html")

    if fmt == "pdf":
        out_path_str, _ = QFileDialog.getSaveFileName(
            browser,
            "Export selected cards to PDF",
            default_name,
            "PDF files (*.pdf);;All files (*.*)",
        )
    else:
        out_path_str, _ = QFileDialog.getSaveFileName(
            browser,
            "Export selected cards to HTML",
            default_name,
            "HTML files (*.html *.htm);;All files (*.*)",
        )

    if not out_path_str:
        return

    out_path = Path(out_path_str)

    if fmt == "pdf":
        _export_to_pdf(browser, mw.col, card_ids, out_path, cfg)
        return

    try:
        export_cards_html(mw.col, card_ids, out_path, cfg)
    except Exception as e:
        QMessageBox.critical(browser, "HTML export error", f"There was an error while exporting HTML:\n{e}")
        return

    QMessageBox.information(browser, "HTML export completed", f"HTML exported:\n{out_path}")


def on_browser_will_show_context_menu(browser, menu) -> None:
    cfg = get_config()
    if not bool(cfg.get("01_general", {}).get("enabled", True)):
        return

    act = QAction("Export selected cards…", menu)
    act.triggered.connect(lambda _=False, b=browser: run_export_from_browser(b))
    menu.addAction(act)


def init_addon() -> None:
    try:
        mw.addonManager.setConfigAction(ADDON_PACKAGE, _show_config_dialog)
    except Exception:
        pass

    try:
        gui_hooks.browser_will_show_context_menu.append(on_browser_will_show_context_menu)
    except Exception:
        pass


init_addon()
