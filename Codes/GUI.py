"""
Pipeline GUI — Biological image analysis
==========================================
Dependencies : pip install PyQt6 matplotlib numpy scipy pandas
Run          : python GUI4.py
"""

import sys, os, subprocess, ast, json, re, textwrap, contextlib
import glob as _glob
import shutil

from PyQt6.QtWidgets import (
    QGraphicsView, QGraphicsScene, QGraphicsPixmapItem,
    QApplication, QMainWindow, QWidget, QFrame,
    QHBoxLayout, QVBoxLayout, QGridLayout,
    QSplitter, QListWidget, QListWidgetItem,
    QComboBox, QLabel, QLineEdit, QPushButton,
    QSizePolicy, QToolButton, QStackedWidget,
    QProgressBar, QTextEdit, QScrollArea, QAbstractItemView,
    QCheckBox, QTabWidget, QSlider, QFileDialog, QMessageBox, QGroupBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QDoubleSpinBox, QDialog, QSpinBox,
    QGraphicsEllipseItem, QGraphicsRectItem
)
from PyQt6.QtCore import Qt, QSize, QSettings, QThread, pyqtSignal, QObject, QTimer, QPointF
from PyQt6.QtGui import QColor, QTextCursor, QImage, QPixmap, QPainter, QPen

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
import numpy as np
import scipy.stats as stats
import pandas as pd

base_path = os.path.dirname(os.path.realpath(__file__)) + os.sep
if base_path not in sys.path:
    sys.path.insert(0, base_path)                      # fiji_tools.py, tif_meta.py, setup_environments.py

# ==============================================================================
# COLORS
# ==============================================================================
C = {
    "bg_main":   "#1C1E26",
    "bg_panel":  "#23263A",
    "bg_widget": "#2D3047",
    "accent":    "#5E9BF0",
    "accent_h":  "#7AB3FF",
    "text":      "#E8EAF6",
    "muted":     "#7B82A8",
    "success":   "#3DAF73",
    "error":     "#E05C6A",
    "border":    "#3A3F5C",
    "green":     "#2ECC71",
    "green_h":   "#27AE60",
    "red":       "#E74C3C",
    "red_h":     "#C0392B",
}

STYLESHEET = f"""
    QMainWindow, QWidget {{
        background-color: {C['bg_main']};
        color: {C['text']};
        font-family: 'Segoe UI', 'Helvetica Neue', sans-serif;
        font-size: 13px;
    }}
    QFrame#panel {{
        background-color: {C['bg_panel']};
        border: 1px solid {C['border']};
        border-radius: 10px;
    }}
    QFrame#entry_frame {{
        background-color: {C['bg_main']};
        border: 1px solid {C['border']};
        border-radius: 5px;
    }}
    QLabel {{ background: transparent; border: none; }}
    QLabel#section_title {{
        color: {C['accent']};
        font-size: 10px;
        font-weight: bold;
        letter-spacing: 1.5px;
    }}
    QLabel#param_label {{ color: {C['muted']}; font-size: 11px; }}
    QLabel#ch_label {{
        color: {C['accent']};
        font-weight: bold;
        font-size: 11px;
    }}

    QTabWidget::pane {{
        border: 1px solid {C['border']};
        border-radius: 8px;
        background-color: {C['bg_panel']};
    }}
    QTabBar::tab {{
        background-color: {C['bg_widget']};
        color: {C['muted']};
        border: 1px solid {C['border']};
        border-bottom: none;
        border-radius: 6px 6px 0 0;
        padding: 8px 10px;
        margin-right: 3px;
    }}
    QTabBar::tab:selected {{ background-color: {C['bg_panel']}; color: {C['accent']}; border-color: {C['accent']}; }}
    QTabBar::tab:hover {{ color: {C['text']}; }}

    QListWidget {{
        background-color: {C['bg_widget']};
        border: 1px solid {C['border']};
        border-radius: 6px;
        padding: 4px;
        outline: none;
    }}
    QListWidget::item {{ color: #F0F8FB; padding: 5px 8px; border-radius: 4px; }}
    QListWidget::item:hover  {{ background-color: {C['accent']}22; }}
    QListWidget::item:selected {{ background-color: {C['accent']}44; color: {C['accent_h']}; }}
    QListWidget QScrollBar:vertical {{ width: 5px; background: transparent; }}
    QListWidget QScrollBar::handle:vertical {{ background:{C['border']}; border-radius:3px; }}

    QComboBox {{
        background-color: {C['bg_widget']};
        border: 1px solid {C['border']};
        border-radius: 5px;
        padding: 4px 8px;
        color: {C['text']};
        min-height: 26px;
    }}
    QComboBox:hover {{ border-color: {C['accent']}; }}
    QComboBox::drop-down {{ border: none; width: 18px; }}
    QComboBox QAbstractItemView {{
        background-color: {C['bg_panel']};
        border: 1px solid {C['accent']};
        border-radius: 5px;
        color: {C['text']};
        selection-background-color: {C['accent']}44;
        outline: none;
        padding: 3px;
    }}

    QCheckBox {{ color: {C['text']}; spacing: 8px; }}
    QCheckBox::indicator {{
        width: 16px; height: 16px;
        border: 1.5px solid {C['border']};
        border-radius: 3px;
        background-color: {C['bg_widget']};
    }}
    QCheckBox::indicator:checked {{
        background-color: {C['accent']};
        border-color: {C['accent']};
    }}

    QLineEdit {{
        background-color: {C['bg_widget']};
        border: 1px solid {C['border']};
        border-radius: 5px;
        padding: 4px 8px;
        color: {C['text']};
        min-height: 26px;
    }}
    QLineEdit:focus {{ border-color: {C['accent']}; }}

    QPushButton#run_btn {{
        background-color: {C['green']};
        color: white; border: none; border-radius: 8px;
        font-size: 13px; font-weight: bold;
        padding: 10px 20px; min-height: 38px; min-width: 50px;
    }}
    QPushButton#run_btn:hover {{ background-color: {C['green_h']}; }}
    QPushButton#run_btn:disabled {{ background-color: {C['border']}; color: {C['muted']}; }}

    QPushButton#stop_btn {{
        background-color: {C['red']};
        color: white; border: none; border-radius: 8px;
        font-size: 13px; font-weight: bold;
        padding: 10px 20px; min-height: 38px; min-width: 50px;
    }}
    QPushButton#stop_btn:hover {{ background-color: {C['red_h']}; }}

    QToolButton#nav_btn {{
        background-color: transparent;
        border: 1px solid {C['border']};
        border-radius: 6px;
        color: {C['muted']};
        font-size: 11px;
        padding: 5px 10px;
    }}
    QToolButton#nav_btn:hover {{ border-color: {C['accent']}; color: {C['text']}; }}
    QToolButton#nav_btn:checked {{
        background-color: {C['accent']}22;
        border-color: {C['accent']};
        color: {C['accent']};
    }}

    QProgressBar {{
        background-color: {C['bg_widget']};
        border: 1px solid {C['border']};
        border-radius: 8px;
        text-align: center;
        color: {C['text']};
        font-size: 12px; font-weight: bold;
        min-height: 28px;
    }}
    QProgressBar::chunk {{ background-color: {C['accent']}; border-radius: 7px; }}

    QTextEdit {{
        background-color: {C['bg_widget']};
        border: 1px solid {C['border']};
        border-radius: 6px;
        color: {C['text']};
        font-family: 'Consolas', 'Courier New', monospace;
        font-size: 11px;
        padding: 6px;
    }}
    QScrollArea {{ border: none; background: transparent; }}
    QScrollArea > QWidget > QWidget {{ background: transparent; }}
    QScrollBar:vertical {{ width: 5px; background: transparent; }}
    QScrollBar::handle:vertical {{ background: {C['border']}; border-radius: 3px; }}
    QSplitter::handle {{ background-color: {C['border']}; border-radius:2px; margin:8px 2px; }}
"""

RM_BTN_STYLE = f"""
    QPushButton {{
        background: transparent; border: 1px solid {C['border']};
        border-radius: 4px; color: {C['muted']};
        font-size: 14px; padding: 0;
    }}
    QPushButton:hover {{ border-color: {C['error']}; color: {C['error']}; }}
"""
ADD_BTN_STYLE = f"""
    QPushButton {{
        background: transparent;
        border: 1px dashed {C['border']};
        border-radius: 5px; color: {C['muted']};
        padding: 3px 8px; font-size: 11px; text-align: left;
    }}
    QPushButton:hover {{ border-color: {C['accent']}; color: {C['accent']}; }}
"""


# ==============================================================================
# HELPERS
# ==============================================================================
def titled_label(text):
    l = QLabel(text); l.setObjectName("section_title"); return l
def small_label(text):
    l = QLabel(text); l.setObjectName("param_label"); return l
def combo(options):
    c = NoScrollCombo(); c.addItems(options); return c
def field(placeholder):
    f = QLineEdit(); f.setPlaceholderText(placeholder); return f
def nav_btn(text, checkable=True):
    b = QToolButton()
    b.setObjectName("nav_btn"); b.setText(text); b.setCheckable(checkable)
    b.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
    return b


class NoScrollCombo(QComboBox):
    """ComboBox that ignores scroll wheel unless its popup is open."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._popup_open = False
        # the width follows the layout, not the longest item (long names would push the page wider than its scroll area)
        self.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.setMinimumContentsLength(8)

    def showPopup(self):
        self._popup_open = True
        super().showPopup()

    def hidePopup(self):
        self._popup_open = False
        super().hidePopup()

    def wheelEvent(self, event):
        if self._popup_open:
            super().wheelEvent(event)
        else:
            event.ignore()


# ==============================================================================
# DROPPABLE LIST
# ==============================================================================
class DroppableList(QListWidget):
    def __init__(self, on_dropped, accepted_ext=None):
        super().__init__()
        self.on_dropped   = on_dropped
        self.accepted_ext = accepted_ext or set()
        self.setDragDropMode(QAbstractItemView.DragDropMode.DropOnly)
        self.setDefaultDropAction(Qt.DropAction.CopyAction)
        self.setAcceptDrops(True)

    def _border_style(self, color):
        return (f"QListWidget {{ background-color: {C['bg_widget']};"
                f" border: 1px solid {color}; border-radius: 6px; padding: 4px; }}")

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.setStyleSheet(self._border_style(C['accent']))

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dragLeaveEvent(self, event):
        self.setStyleSheet(self._border_style(C['border']))

    def dropEvent(self, event):
        paths = [url.toLocalFile() for url in event.mimeData().urls()]
        self.on_dropped(paths)
        self.dragLeaveEvent(event)


# ==============================================================================
# FILES PANEL
# ==============================================================================
class FilesPanel(QFrame):
    def __init__(self, on_files_changed=None):
        super().__init__()
        self.setObjectName("panel")
        self._on_files_changed = on_files_changed
        self._paths = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)
        layout.addWidget(titled_label("FILES TO ANALYZE"))

        self.list = DroppableList(on_dropped=self._on_dropped,
                                   accepted_ext={".tif", ".tiff", ".czi"})
        layout.addWidget(self.list)

        del_btn = QPushButton("Remove selected")
        del_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent; border: 1px solid {C['border']};
                border-radius: 5px; color: {C['muted']}; padding: 4px 10px;
            }}
            QPushButton:hover {{ border-color: {C['error']}; color: {C['error']}; }}
        """)
        del_btn.clicked.connect(self._remove_selected)
        layout.addWidget(del_btn)

    def _on_dropped(self, paths):
        accepted = {".tif", ".tiff", ".czi"}
        for p in paths:
            if p in self._paths:
                continue
            ext = "." + p.rsplit(".", 1)[-1].lower() if "." in p else ""
            if ext in accepted or os.path.isdir(p):
                self._paths.append(p)
                name = (os.path.basename(os.path.normpath(p)) + "/"
                        if os.path.isdir(p)
                        else os.path.basename(p))
                item = QListWidgetItem(f"○  {name}")
                item.setForeground(QColor(C["muted"]))
                item.setData(Qt.ItemDataRole.UserRole, p)
                self.list.addItem(item)
        if self._on_files_changed:
            self._on_files_changed(self._paths)

    def update_status(self, path, status):
        icons  = {"ok": "✓", "error": "✗", "running": "▶"}
        colors = {"ok": C["success"], "error": C["error"], "running": C["accent"]}
        for i in range(self.list.count()):
            item = self.list.item(i)
            if item.data(Qt.ItemDataRole.UserRole) == path:
                name = (os.path.basename(os.path.normpath(path)) + "/"
                        if os.path.isdir(path)
                        else os.path.basename(path))
                item.setText(f"{icons.get(status,'○')}  {name}")
                item.setForeground(QColor(colors.get(status, C["muted"])))
                break

    def get_paths(self):
        return list(self._paths)

    def _remove_selected(self):
        rows = [self.list.row(i) for i in self.list.selectedItems()]
        for item in self.list.selectedItems():
            p = item.data(Qt.ItemDataRole.UserRole)
            if p in self._paths:
                self._paths.remove(p)
            self.list.takeItem(self.list.row(item))
        if rows and self.list.count():
            self.list.setCurrentRow(min(min(rows), self.list.count() - 1))
        if self._on_files_changed:
            self._on_files_changed(self._paths)


# ==============================================================================
# PLOT PANEL
# ==============================================================================
class PlotPanel(QFrame):
    def __init__(self):
        super().__init__()
        self.setObjectName("panel")
        self._figures = []
        self._current = -1

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(6)

        nav_style = f"""
            QPushButton {{
                background: {C['bg_widget']}; border: 1px solid {C['border']};
                border-radius: 4px; color: {C['text']}; font-size: 14px; padding: 2px 6px;
            }}
            QPushButton:hover {{ border-color: {C['accent']}; }}
            QPushButton:disabled {{ color: {C['border']}; }}
        """
        nav = QHBoxLayout()
        self._lbl = QLabel("No plot")
        self._lbl.setObjectName("param_label")
        self._lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._btn_prev = QPushButton("←")
        self._btn_next = QPushButton("→")
        self._btn_save = QPushButton("Save data")
        for b in (self._btn_prev, self._btn_next):
            b.setFixedWidth(32); b.setEnabled(False); b.setStyleSheet(nav_style)
        self._btn_save.setFixedWidth(90); self._btn_save.setEnabled(False)
        self._btn_save.setStyleSheet(nav_style)
        self._btn_prev.clicked.connect(self._go_prev)
        self._btn_next.clicked.connect(self._go_next)
        self._btn_save.clicked.connect(self._save_data)
        nav.addWidget(self._btn_prev)
        nav.addWidget(self._lbl, stretch=1)
        nav.addWidget(self._btn_save)
        nav.addWidget(self._btn_next)
        layout.addLayout(nav)

        self.figure = Figure(facecolor=C['bg_panel'])
        self.canvas = FigureCanvasQTAgg(self.figure)
        self.canvas.setMinimumHeight(200)
        self.canvas.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout.addWidget(self.canvas)

    def add_figure(self, distrib_line):
        line     = distrib_line.split("\\")
        distrib  = ast.literal_eval(line[0][8:])
        file_name= line[1]
        means    = ast.literal_eval(line[2])
        std      = ast.literal_eval(line[3])
        weights  = ast.literal_eval(line[4])
        groups   = ast.literal_eval(line[5])
        df_list  = ast.literal_eval(line[6])
        plot_name= line[7]
        type_name = line[8]
        cells_name = line[9]
        
        self._figures.append(("types", [distrib, file_name, means, std, weights, groups, df_list, plot_name, type_name, cells_name]))
        self._current = len(self._figures) - 1
        self._show_current()

    def add_background(self, record):
        """Background study of one image (dict read from the 'background:' line of Newmain)."""
        self._figures.append(("background", record))
        self._current = len(self._figures) - 1
        self._show_current()

    def _save_data(self):
        kind, d = self._figures[self._current]
        if kind == "background":
            rows = d.get("cell_table") or []
            if not rows:
                return
            cols = ["population", "cell", "z_center", "voxels", "mean", "median", "var"]
            default = f"background_s{d.get('channel', '')}_{d.get('file', 'image')}.xlsx"
            out, _ = QFileDialog.getSaveFileName(self, "Save background data", default, "Excel (*.xlsx)")
            if out:
                pd.DataFrame(rows, columns=cols).to_excel(out, index=False, engine="openpyxl")
            return
        if kind != "types":
            return
        plot_name, df_list, groups = d[7], d[6], d[5]
        to_save = pd.DataFrame({"cell_label": df_list[0], "fluo_intensity": df_list[1],
                                groups[0]: df_list[2], groups[1]: df_list[3]})
        to_save.to_excel(plot_name, columns=to_save.columns.tolist(),
                         index=False, engine="openpyxl")

    def _go_prev(self):
        if self._current > 0:
            self._current -= 1; self._show_current()

    def _go_next(self):
        if self._current < len(self._figures) - 1:
            self._current += 1; self._show_current()

    def _draw_background(self, rec):
        """Three small plots: cell means, plane means, histogram of the background voxel values."""
        axes = self.figure.subplots(1, 3)
        for ax in axes:
            ax.set_facecolor(C['bg_widget'])
            ax.tick_params(colors=C['muted'], labelsize=7)
        B = rec.get("B")
        means = sorted(m for m in (rec.get("cell_means") or []) if m is not None)

        ax = axes[0]
        ax.plot(range(len(means)), means, "o", color=C['accent'], markersize=4)
        if B is not None:
            ax.axhline(B, color="red", linestyle="--", linewidth=1)
        ax.set_title("Mean per cell", color=C['text'], fontsize=8)
        ax.set_xlabel("cells, sorted", color=C['muted'], fontsize=7)

        ax = axes[1]
        planes = rec.get("planes") or []
        if planes:
            ax.plot([p[0] for p in planes], [p[1] for p in planes], "-o", color=C['accent'], markersize=3)
        if B is not None:
            ax.axhline(B, color="red", linestyle="--", linewidth=1)
        ax.set_title("Mean per plane", color=C['text'], fontsize=8)
        ax.set_xlabel("plane", color=C['muted'], fontsize=7)

        ax = axes[2]
        hist = rec.get("hist")
        if hist:
            labels = [str(i) for i in range(len(hist) - 1)] + [f"{len(hist) - 1}+"]
            ax.bar(range(len(hist)), hist, color=C['accent'], alpha=0.7)
            ax.set_xticks(range(len(hist)))
            ax.set_xticklabels(labels)
            ax.set_title("Voxel values (% of voxels)", color=C['text'], fontsize=8)
        else:
            ax.text(0.5, 0.5, "n/a (image is not integer)", ha="center", va="center",
                    color=C['muted'], fontsize=8, transform=ax.transAxes)
            ax.set_xticks([]); ax.set_yticks([])

        b_txt = "n/a" if B is None else f"{B:.2f}"
        err = rec.get("error_pct")
        err_txt = "n/a" if err is None else f"{err:.1f}"
        full = str(rec.get("file", ""))
        short = full if len(full) <= 38 else full[:18] + "…" + full[-18:]
        self.figure.suptitle(f"{rec.get('probe', '')}  ·  {short}", color=C['text'], fontsize=8)
        self.figure.text(0.5, 0.005, "\n".join(textwrap.wrap(full, 110)), color=C['muted'], fontsize=5.5,
                         ha="center", va="bottom")
        self.figure.tight_layout(pad=0.5, rect=(0, 0.06, 1, 0.94))
        self.canvas.setToolTip(full)

    def _show_current(self):
        self.figure.clear()
        kind, d = self._figures[self._current]
        if kind == "background":
            self._draw_background(d)
            self.canvas.draw()
            total = len(self._figures)
            self._lbl.setText(f"{self._current + 1} / {total}  (background)")
            self._btn_prev.setEnabled(self._current > 0)
            self._btn_next.setEnabled(self._current < total - 1)
            self._btn_save.setEnabled(bool(d.get("cell_table")))
            return
        self._btn_save.setEnabled(True)
        ax = self.figure.add_subplot(111)
        ax.set_facecolor(C['bg_widget'])
        data, file_name, means, std, weights, groups, type_name , cells_name= d[0], d[1], d[2], d[3], d[4], d[5], d[8], d[9]

        counts, bin_edges = np.histogram(data, bins=max(1, round(len(data) / 2)))
        bin_width = bin_edges[1] - bin_edges[0]
        ax.hist(data, bins=max(1, round(len(data) / 2)), color=C['accent'], alpha=0.6)
        ax.set_ylim(0, counts.max() * 1.20)

        x = np.linspace(min(data), max(data), 300)
        for n, color in enumerate(["yellow", "red"]):
            ax.axvline(means[n], color=color, linestyle="--", linewidth=1.5)
            y = weights[n] * stats.norm.pdf(x, means[n], np.sqrt(std[n])) * len(data) * bin_width
            ax.plot(x, y, color=color, linewidth=1.5, label=groups[n])

        ax.legend()
        ax.set_title(f"{type_name} intensity distribution", color=C['text'], fontsize=9)
        ax.set_xlabel(f"{type_name} intensity", color=C['muted'])
        ax.set_ylabel(f"Number of {cells_name}", color=C['muted'])
        ax.tick_params(colors=C['muted'])
        self.figure.text(0.5, 0.005, "\n".join(textwrap.wrap(str(file_name), 110)), color=C['muted'],
                         fontsize=5.5, ha="center", va="bottom")
        self.figure.tight_layout(pad=0.5, rect=(0, 0.05, 1, 1))
        self.canvas.setToolTip(str(file_name))
        self.canvas.draw()
        total = len(self._figures)
        self._lbl.setText(f"{self._current + 1} / {total}")
        self._btn_prev.setEnabled(self._current > 0)
        self._btn_next.setEnabled(self._current < total - 1)
        self._btn_save.setEnabled(True)


# ==============================================================================
# COLLAPSIBLE SECTION
# ==============================================================================
class CollapsibleSection(QWidget):
    """A header (click to fold / unfold) above a content widget."""
    def __init__(self, title, content, expanded=True):
        super().__init__()
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(4)
        self.header = QToolButton()
        self.header.setObjectName("nav_btn")
        self.header.setCheckable(False)
        self.header.setText(title)
        self.header.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.header.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        self.header.setStyleSheet(f"QToolButton {{ text-align: left; border: 1px solid {C['border']}; border-radius: 6px;"
                                  f" padding: 5px 10px; color: {C['text']}; background: transparent; font-size: 11px; }}"
                                  f"QToolButton:hover {{ border-color: {C['accent']}; }}")
        self.header.clicked.connect(lambda: self.set_expanded(not self.content.isVisible()))
        lay.addWidget(self.header)
        self.content = content
        lay.addWidget(content)
        self._title = title
        self.set_expanded(expanded)

    def set_expanded(self, on):
        self.content.setVisible(on)
        self.header.setText(("▼  " if on else "▶  ") + self._title)


# ==============================================================================
# MODELS PAGE
# One collapsible section per tool (Cellpose, EpySeg, Spotiflow); a model is dropped into the section of the
# tool that made it, so that an analysis can only offer the models of the tool it uses.
# ==============================================================================
def guess_model_source(path):
    """Tool a model file / folder most probably comes from (None if unknown)."""
    if os.path.isdir(path):
        return "Spotiflow"
    ext = os.path.splitext(path)[1].lower()
    if ext in (".h5", ".hdf5"):
        return "EpySeg"
    if ext == ".model":
        return "Weka (Fiji)"
    if ext == "":
        return "Cellpose"
    return None


class ModelsPage(QWidget):
    SETTINGS_KEY = "segmentation_models_by_source"
    OLD_KEY = "segmentation_models"
    changed = pyqtSignal()

    HELP = {
        "Cellpose": "Cellpose models: a file without extension (the file saved by Cellpose training).\n"
                    "Used to segment cells.",
        "EpySeg": "EpySeg models: .h5 files.\nUsed to detect objects (spots).",
        "Weka (Fiji)": "Weka classifiers: .model files saved from Fiji's Trainable Weka Segmentation.\n"
                       "They are applied by Fiji without its interface (Fiji brings its own Java).\n"
                       "Used to segment cells or detect objects.",
        "Spotiflow": "Spotiflow models: a model FOLDER (with its config and weights), made by training Spotiflow.\n"
                     "The pretrained models of Spotiflow are always available (they are downloaded when first used).\n"
                     "Used to detect objects (spots).",
    }

    def __init__(self):
        super().__init__()
        self.settings = QSettings("BioImaging", "Pipeline")
        self._paths = self._load_paths()
        self._versions = self._load_versions()
        self._weka = self._load_weka()
        self.lists = {}
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 4, 0)
        layout.setSpacing(8)
        layout.addWidget(titled_label("MODELS"))
        hint = small_label("Drop each model into the section of the tool that made it.")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        for source in MODEL_SOURCES:
            body = QWidget()
            bl = QVBoxLayout(body)
            bl.setContentsMargins(0, 0, 0, 0)
            bl.setSpacing(4)
            lst = DroppableList(on_dropped=lambda paths, src=source: self._on_dropped(src, paths),
                                accepted_ext=set())
            lst.setMinimumHeight(70)
            lst.setToolTip(self.HELP[source])
            self.lists[source] = lst
            bl.addWidget(lst)
            if source == "Cellpose":
                vrow = QHBoxLayout()
                vrow.addWidget(small_label("Cellpose version of the selected model"))
                self.version_combo = QComboBox()
                for v in (2, 3, 4):
                    self.version_combo.addItem(f"Cellpose {v}", v)
                self.version_combo.setToolTip(
                    "The version of Cellpose that trained the model; it decides which environment runs it\n"
                    "(segment = Cellpose 2, cellpose3, cellpose4). Select models in the list, then choose.")
                self.version_combo.activated.connect(self._set_version_of_selected)
                vrow.addWidget(self.version_combo)
                bl.addLayout(vrow)
                lst.itemSelectionChanged.connect(self._sync_version_combo)
            if source == "Weka (Fiji)":
                frow = QHBoxLayout()
                frow.addWidget(small_label("Fiji"))
                self.fiji_field = QLineEdit(self.settings.value("fiji_path", "") or "")
                self.fiji_field.setPlaceholderText("Fiji.app folder (or its launcher)")
                self.fiji_field.editingFinished.connect(self._fiji_changed)
                fb = QPushButton("Browse…")
                fb.clicked.connect(self._browse_fiji)
                frow.addWidget(self.fiji_field, 1); frow.addWidget(fb)
                bl.addLayout(frow)
                self.fiji_status = small_label("")
                self.fiji_status.setWordWrap(True)
                bl.addWidget(self.fiji_status)
                wrow = QHBoxLayout()
                wrow.addWidget(small_label("Selected model:"))
                self.weka_mode = QComboBox()
                self.weka_mode.addItem("2D, plane by plane", "2d"); self.weka_mode.addItem("3D", "3d")
                self.weka_mode.setToolTip("How the classifier was trained: 2D classifiers are applied plane by plane,\n"
                                          "3D ones to the whole stack. Objects are rebuilt in 3D afterwards.")
                self.weka_class = QSpinBox(); self.weka_class.setRange(1, 20); self.weka_class.setPrefix("class ")
                self.weka_class.setToolTip("Number of the class that is the object (1 = the first class of the classifier).")
                self.weka_mode.activated.connect(self._set_weka_of_selected)
                self.weka_class.valueChanged.connect(self._set_weka_of_selected)
                wrow.addWidget(self.weka_mode); wrow.addWidget(self.weka_class)
                bl.addLayout(wrow)
                lst.itemSelectionChanged.connect(self._sync_weka_widgets)
                self._fiji_changed()
            if source == "Spotiflow":
                note = small_label("Pretrained (always available): " + ", ".join(SPOTIFLOW_PRETRAINED))
                note.setWordWrap(True)
                bl.addWidget(note)
            del_btn = QPushButton("Remove selected")
            del_btn.setStyleSheet(f"""
                QPushButton {{ background: transparent; border: 1px solid {C['border']};
                    border-radius: 5px; color: {C['muted']}; padding: 4px 10px; }}
                QPushButton:hover {{ border-color: {C['error']}; color: {C['error']}; }}
            """)
            del_btn.setToolTip("Removes the selected models from this list (the files are not deleted).")
            del_btn.clicked.connect(lambda _c=False, src=source: self._remove_selected(src))
            bl.addWidget(del_btn)
            section = CollapsibleSection(source, body, expanded=True)
            section.setToolTip(self.HELP[source])
            layout.addWidget(section)
            for p in self._paths[source]:
                self._add_item(source, p)
        layout.addStretch()

        scroll = QScrollArea()
        scroll.setWidget(page)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

    def _load_paths(self):
        """{source: [paths]}; earlier versions saved one list: every model is placed by its look."""
        paths = {s: [] for s in MODEL_SOURCES}
        raw = self.settings.value(self.SETTINGS_KEY, defaultValue=None)
        try:
            data = json.loads(raw) if raw else None
        except (TypeError, ValueError):
            data = None
        if isinstance(data, dict):
            for s in MODEL_SOURCES:
                paths[s] = [p for p in data.get(s, []) if isinstance(p, str)]
            return paths
        old = self.settings.value(self.OLD_KEY, defaultValue=[])
        if isinstance(old, str):
            old = [old]
        for p in old or []:
            paths[guess_model_source(p) or "Cellpose"].append(p)
        return paths

    VERSIONS_KEY = "cellpose_model_versions"
    WEKA_KEY = "weka_model_settings"

    def _load_weka(self):
        try:
            data = json.loads(self.settings.value(self.WEKA_KEY, defaultValue="{}") or "{}")
        except (TypeError, ValueError):
            data = {}
        return data if isinstance(data, dict) else {}

    def weka_of(self, path):
        """{'mode': '2d'|'3d', 'class': n} of a Weka classifier."""
        d = self._weka.get(path, {})
        return {"mode": d.get("mode", "2d") if d.get("mode") in ("2d", "3d") else "2d", "class": int(d.get("class", 1))}

    def fiji_path(self):
        return self.fiji_field.text().strip() if hasattr(self, "fiji_field") else ""

    def _fiji_changed(self):
        import fiji_tools
        path = self.fiji_field.text().strip()
        self.settings.setValue("fiji_path", path)
        if not path:
            self.fiji_status.setText("Give the Fiji location to use Weka models.")
            return
        ok, msg = fiji_tools.check(path)
        self.fiji_status.setText(("✔ " if ok else "✘ ") + msg)

    def _browse_fiji(self):
        d = QFileDialog.getExistingDirectory(self, "Select the Fiji.app folder", self.fiji_field.text() or "")
        if d:
            self.fiji_field.setText(d)
            self._fiji_changed()

    def _set_weka_of_selected(self, *_):
        for item in self.lists["Weka (Fiji)"].selectedItems():
            self._weka[item.data(Qt.ItemDataRole.UserRole)] = {"mode": self.weka_mode.currentData(),
                                                              "class": self.weka_class.value()}
            self._label_item(item)
        self._save()

    def _sync_weka_widgets(self):
        sel = self.lists["Weka (Fiji)"].selectedItems()
        if sel:
            d = self.weka_of(sel[0].data(Qt.ItemDataRole.UserRole))
            self.weka_mode.blockSignals(True); self.weka_class.blockSignals(True)
            self.weka_mode.setCurrentIndex(1 if d["mode"] == "3d" else 0); self.weka_class.setValue(d["class"])
            self.weka_mode.blockSignals(False); self.weka_class.blockSignals(False)

    def _load_versions(self):
        try:
            data = json.loads(self.settings.value(self.VERSIONS_KEY, defaultValue="{}") or "{}")
        except (TypeError, ValueError):
            data = {}
        return {k: int(v) for k, v in data.items() if str(v) in ("2", "3", "4")} if isinstance(data, dict) else {}

    def version_of(self, path):
        """Cellpose version (2, 3 or 4) declared for a model; 2 by default (models made before version 3 existed)."""
        return self._versions.get(path, 2)

    def _set_version_of_selected(self, _i=0):
        v = self.version_combo.currentData()
        for item in self.lists["Cellpose"].selectedItems():
            self._versions[item.data(Qt.ItemDataRole.UserRole)] = v
            self._label_item(item)
        self._save()

    def _sync_version_combo(self):
        sel = self.lists["Cellpose"].selectedItems()
        if sel:
            i = self.version_combo.findData(self.version_of(sel[0].data(Qt.ItemDataRole.UserRole)))
            self.version_combo.setCurrentIndex(max(i, 0))

    def _label_item(self, item):
        path = item.data(Qt.ItemDataRole.UserRole)
        name = os.path.basename(os.path.normpath(path))
        lw = item.listWidget()
        extra = ""
        if lw is self.lists.get("Cellpose"):
            extra = f"   [v{self.version_of(path)}]"
        elif lw is self.lists.get("Weka (Fiji)"):
            w = self.weka_of(path)
            extra = f"   [{w['mode'].upper()}, class {w['class']}]"
        item.setText(f"◈  {name}" + extra)

    def _save(self):
        self.settings.setValue(self.VERSIONS_KEY, json.dumps(self._versions))
        self.settings.setValue(self.WEKA_KEY, json.dumps(self._weka))
        self.settings.setValue(self.SETTINGS_KEY, json.dumps(self._paths))
        self.changed.emit()

    def add_model(self, source, path):
        """Adds a model to a section of the page (used by the training tab)."""
        if path not in self._paths[source]:
            self._paths[source].append(path)
            self._add_item(source, path)
            self._save()

    def _on_dropped(self, source, paths):
        for p in paths:
            guessed = guess_model_source(p)
            if guessed is not None and guessed != source:
                answer = QMessageBox.question(
                    self, "Model source",
                    f"'{os.path.basename(os.path.normpath(p))}' looks like a {guessed} model, "
                    f"but it is dropped in the {source} section.\n\nAdd it to {source} anyway?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No)
                if answer != QMessageBox.StandardButton.Yes:
                    continue
            if p not in self._paths[source]:
                self._paths[source].append(p)
                self._add_item(source, p)
        self._save()

    def _add_item(self, source, path):
        name = os.path.basename(os.path.normpath(path))
        item = QListWidgetItem(f"◈  {name}")
        item.setForeground(QColor(C["accent"]))
        item.setData(Qt.ItemDataRole.UserRole, path)
        item.setToolTip(path)
        self.lists[source].addItem(item)
        if source in ("Cellpose", "Weka (Fiji)"):
            self._label_item(item)

    def _remove_selected(self, source):
        lst = self.lists[source]
        for item in lst.selectedItems():
            p = item.data(Qt.ItemDataRole.UserRole)
            if p in self._paths[source]:
                self._paths[source].remove(p)
            lst.takeItem(lst.row(item))
        self._save()

    def get_model_names(self, source):
        """[(name shown, value)] of the models of one tool. For Spotiflow the value of a pretrained model is its name."""
        lst = self.lists[source]
        out = [(os.path.basename(os.path.normpath(lst.item(i).data(Qt.ItemDataRole.UserRole))),
                lst.item(i).data(Qt.ItemDataRole.UserRole)) for i in range(lst.count())]
        if source == "Spotiflow":
            out += [(f"{n} (pretrained)", n) for n in SPOTIFLOW_PRETRAINED]
        return out


# ==============================================================================
# CHANNEL STATE
# ==============================================================================
class ChannelState(QObject):
    """
    Shared object that all AnalysisEntry instances read.
    Tracks which channel indices have a "Cells" role so that
    Cell type marker entries can show the right checkboxes.

    We track a list of (channel_idx, entry_ref) pairs so that
    multiple Cells entries on the same channel all register.
    """
    changed = pyqtSignal()

    def __init__(self):
        super().__init__()
        # List of (channel_idx, entry_object) for every Cells entry
        self._cells_entries = []
        self._marker_entries = []

    def register_cells(self, channel_idx, entry):
        """Called by an AnalysisEntry when its role becomes Cells."""
        self._cells_entries.append((channel_idx, entry))
        self.changed.emit()

    def unregister_cells(self, entry):
        """Called by an AnalysisEntry when its role changes away from Cells."""
        self._cells_entries = [(i, e) for i, e in self._cells_entries if e is not entry]
        self.changed.emit()

    def get_cells_channels(self):
        """Returns list of (channel_idx, entry) for all Cells entries."""
        return list(self._cells_entries)

    def get_types_for_cells(self, cells_entry_ref):
        """Return list of type names declared for a given cells entry."""
        types = []
        for _, entry in self._marker_entries:
            for (ch_idx, ref), cb in entry.cells_checkboxes.items():
                if ref is cells_entry_ref and cb.isChecked():
                    for f in [entry.g1_field, entry.g2_field, entry.mk_field]:
                        v = f.text().strip()
                        if v and v not in types:
                            types.append(v)
        return types

    def register_marker(self, entry):
        if entry not in [e for _, e in self._marker_entries]:
            self._marker_entries.append((id(entry), entry))
        self.changed.emit()

    def unregister_marker(self, entry):
        self._marker_entries = [(i, e) for i, e in self._marker_entries if e is not entry]


# ==============================================================================
# ANALYSIS ENTRY
# One role + its sub-params for one channel.
# A ChannelRow contains one or more of these.
# ==============================================================================
# Norm-against option labels — defined as constants to avoid Unicode encoding
# issues on Windows where Qt may return the codepoint rather than the glyph.
NORM_NONE    = "No normalisation"
NORM_EXCEPT  = "All except..."
NORM_ONLY    = "Only..."
NORM_MODES   = [NORM_NONE, NORM_EXCEPT, NORM_ONLY]

# Background correction (preprocessing: applied before the absolute and relative results)
BG_NONE      = "No correction"
BG_PER_IMAGE = "Per image"
BG_PER_CELL  = "Per cell"
BG_RING      = "Morisaki and Stasevich method"
BG_MODES     = [BG_NONE, BG_PER_IMAGE, BG_PER_CELL, BG_RING]
RING_GAP_DEFAULT, RING_WIDTH_DEFAULT = "4", "3"

# Absolute quantification (number of molecules): independent of the relative comparison, both can be used together
ABS_NONE     = "No absolute quantification"
ABS_CALIB    = "Quantification from one molecule"
ABS_LEGACY   = {"Intensity of one molecule from isolated molecules": ABS_CALIB,     # names used by earlier presets
                "Intensity of one molecule given": ABS_NONE}
ABS_MODES    = [ABS_NONE, ABS_CALIB]
DET_MODEL    = "EpySeg model"
DET_SPOTIFLOW = "Spotiflow"
SMFISH_TYPES = ["exonic probe", "intronic probe"]
MODEL_SOURCES = ["Cellpose", "EpySeg", "Spotiflow", "Weka (Fiji)"]
SRC_WEKA = "Weka (Fiji)"
SPOTIFLOW_PRETRAINED = ["smfish_3d", "synth_3d", "general", "fluo_live"]
ABS_UNITS    = ["RNA", "fluorophores"]

CHANNEL_ROLES = ["None", "Cells", "Objects", "Cell type marker", "Protein of interest"]

class CropSettingsDialog(QDialog):
    """Settings of the per-cell crops export (one tif per cell, or per cell and slice)."""
    def __init__(self, settings=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Cell crops settings")
        st = {"margin": 10, "margin_unit": "px", "mode": "3d", "channels": [], "extra_slices": 1, "pad": True}
        st.update(settings or {})
        lay = QGridLayout(self)
        lay.addWidget(QLabel("Margin around the cell"), 0, 0)
        self.margin = QDoubleSpinBox(); self.margin.setRange(0, 10000); self.margin.setDecimals(2)
        self.margin.setValue(float(st["margin"]))
        self.unit = QComboBox(); self.unit.addItem("pixels", "px"); self.unit.addItem("µm", "um")
        self.unit.setCurrentIndex(1 if st["margin_unit"] == "um" else 0)
        self.unit.setToolTip("In µm the margin is converted with the pixel size of the image;\n"
                             "if the pixel size is unknown the export is skipped (use pixels).")
        lay.addWidget(self.margin, 0, 1); lay.addWidget(self.unit, 0, 2)
        lay.addWidget(QLabel("Output"), 1, 0)
        self.mode = QComboBox()
        self.mode.addItem("One 3D stack per cell", "3d"); self.mode.addItem("One 2D image per slice", "2d")
        self.mode.setCurrentIndex(1 if st["mode"] == "2d" else 0)
        lay.addWidget(self.mode, 1, 1, 1, 2)
        lay.addWidget(QLabel("Channels of the base file"), 2, 0)
        self.channels = QLineEdit(", ".join(str(c) for c in st["channels"]))
        self.channels.setPlaceholderText("all  (or e.g. 0, 2 — numbers start at 0)")
        lay.addWidget(self.channels, 2, 1, 1, 2)
        lay.addWidget(QLabel("Extra slices before / after"), 3, 0)
        self.extra = QSpinBox(); self.extra.setRange(0, 50); self.extra.setValue(int(st["extra_slices"]))
        lay.addWidget(self.extra, 3, 1)
        self.pad = QCheckBox("Complete image borders with zeros")
        self.pad.setChecked(bool(st["pad"]))
        self.pad.setToolTip("Crops that go past the image are completed with 0 (otherwise they are cut at the border).")
        lay.addWidget(self.pad, 4, 0, 1, 3)
        info = QLabel("Files: <population>_crops/<image>_cell<n>.tif  (or ..._cell<n>_z<k>.tif)")
        info.setWordWrap(True)
        lay.addWidget(info, 5, 0, 1, 3)
        row = QHBoxLayout()
        ok = QPushButton("OK"); cancel = QPushButton("Cancel")
        ok.clicked.connect(self.accept); cancel.clicked.connect(self.reject)
        row.addStretch(); row.addWidget(cancel); row.addWidget(ok)
        lay.addLayout(row, 6, 0, 1, 3)

    def settings(self):
        chans = []
        for tok in self.channels.text().replace(";", ",").split(","):
            tok = tok.strip()
            if tok.isdigit():
                chans.append(int(tok))
        return {"margin": self.margin.value(), "margin_unit": self.unit.currentData(), "mode": self.mode.currentData(),
                "channels": chans, "extra_slices": self.extra.value(), "pad": self.pad.isChecked()}

    def summary(self):
        st = self.settings()
        return (f"{'3D stack' if st['mode'] == '3d' else '2D slices'}, margin {st['margin']:g} "
                f"{'px' if st['margin_unit'] == 'px' else 'µm'}, ±{st['extra_slices']} slice(s)")


class AnalysisEntry(QWidget):
    """
    Represents one analysis role for a channel.
    Contains a role combo + the sub-params specific to that role.

    HOW THE REMOVE SIGNAL WORKS:
    remove_requested is a pyqtSignal that carries a reference to self (object).
    When × is clicked, we emit this signal with self as the payload.
    ChannelRow receives it and knows exactly which entry to delete.

    HOW VISIBILITY WORKS:
    All sub-param widgets are created at __init__ time and hidden.
    _on_role() shows only the widgets relevant to the selected role.
    This avoids recreating widgets on every role change.
    """
    remove_requested = pyqtSignal(object)

    def __init__(self, channel_idx, models_page, state, show_remove=True):
        super().__init__()
        self.channel_idx = channel_idx
        self.models_page = models_page
        self.state       = state
        self._prev_role  = "None"   # tracks previous role for state registration

        # Listen to state changes to refresh Cell type checkboxes
        self.state.changed.connect(self._refresh_checkboxes)
        models_page.changed.connect(self._refresh_models)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(3)

        # ---- Role selector row ----
        role_row = QHBoxLayout()
        role_row.setSpacing(6)

        self.role_combo = NoScrollCombo()
        self.role_combo.setToolTip("What this channel (or this analysis of the channel) is:\n"
                                   "Cells: cell segmentation. Objects: spots (RNA molecules, transcription sites).\n"
                                   "Protein of interest: mean fluorescence per cell. Cell type marker: classifies the cells\n"
                                   "into two groups from the intensity of a marker.")
        self.role_combo.addItems(CHANNEL_ROLES)
        self.role_combo.currentTextChanged.connect(self._on_role)
        role_row.addWidget(self.role_combo, stretch=1)

        if show_remove:
            rm = QPushButton("×")
            rm.setFixedSize(22, 22)
            rm.setStyleSheet(RM_BTN_STYLE)
            rm.clicked.connect(lambda: self.remove_requested.emit(self))
            role_row.addWidget(rm)

        outer.addLayout(role_row)

        # ---- Sub-params frame ----
        self.sub_frame = QFrame()
        self.sub_frame.setObjectName("entry_frame")
        self.sub_frame.setVisible(False)

        sub = QGridLayout(self.sub_frame)
        sub.setContentsMargins(8, 6, 8, 6)
        sub.setSpacing(5)
        sub.setColumnStretch(0, 1)
        sub.setColumnStretch(1, 2)

        # Model source / model / name — for Cells and Objects
        self.src_label = small_label("Model source")
        self.src_combo = NoScrollCombo()
        self.src_combo.setToolTip(
            "The tool that makes the segmentation / detection.\n"
            "The list of models below only shows the models of this tool (see the Models page).\n"
            "Greyed tools are not connected yet.")
        self.src_combo.currentIndexChanged.connect(lambda _i: self._on_source_changed())
        sub.addWidget(self.src_label, 0, 0)
        sub.addWidget(self.src_combo, 0, 1)

        self.model_label = small_label("Model")
        self.model_combo = NoScrollCombo()
        self.model_combo.addItem("— no model —")
        self.model_combo.setToolTip("Model used by the tool above. Add models in the Models page, in the section of their tool.")
        sub.addWidget(self.model_label, 1, 0)
        sub.addWidget(self.model_combo, 1, 1)

        self.name_label = small_label("Name")   # "Cells name" or "Objects name"
        self.name_field = field("e.g. Neuroblasts")
        self.name_field.setToolTip("Name of this population. It prefixes the columns of the data table and the output files,\n"
                                   "so it must be different for every analysis.")
        sub.addWidget(self.name_label, 2, 0)
        sub.addWidget(self.name_field, 2, 1)

        self.sf_label = small_label("Cells shrinking factor")
        self.sf_field = field("0 = no shrinking")
        self.sf_field.setText("0")
        self.sf_field.setToolTip(
            "Each cell is shrunk, plane by plane, so that spots just outside it are not attributed to it.\n"
            "0.15 keeps the pixels farther than 15 % of the largest distance to the edge from the border.\n"
            "0 (default) = the cells are not shrunk.")
        sub.addWidget(self.sf_label, 3, 0)
        sub.addWidget(self.sf_field, 3, 1)

        self.size_label = small_label("Cells minimum pixels")
        self.size_field = field("0 = no minimum")
        self.size_field.setText("0")
        self.size_field.setToolTip(
            "Cells with fewer voxels than this (all planes together) are removed: it eliminates small false\n"
            "positives. 0 (default) = no cell is removed.")
        sub.addWidget(self.size_label, 4, 0)
        sub.addWidget(self.size_field, 4, 1)

        self.sm_label = small_label("smFISH type")
        self.sm_combo = NoScrollCombo()
        self.sm_combo.addItems(SMFISH_TYPES)
        self.sm_combo.setToolTip(
            "exonic probe: the probe labels the whole mRNA. Every spot of a cell is kept (single molecules and\n"
            "transcription sites); the number of molecules can be estimated from the single molecules.\n"
            "intronic probe: the probe labels nascent RNA only. At most 2 spots (the transcription sites) are kept per cell,\n"
            "chosen by probability then brightness. There are no isolated molecules, so no absolute quantification.")
        sub.addWidget(self.sm_label, 5, 0)
        sub.addWidget(self.sm_combo, 5, 1)

        self.thr_label = small_label("Probability threshold")
        self.thr_field = field("model default")
        self.thr_field.setToolTip(
            "Spotiflow: minimum probability for a point to be kept (between 0 and 1).\n"
            "Empty = the threshold that was optimised for the model.")
        sub.addWidget(self.thr_label, 6, 0)
        sub.addWidget(self.thr_field, 6, 1)

        self.ap_label = small_label("Aperture (PSF sigmas)")
        self.ap_field = field("3")
        self.ap_field.setText("3")
        self.ap_field.setToolTip(
            "A point has no size: the region summed around it is an ellipsoid whose radii are this many standard\n"
            "deviations of the PSF (in x, y and z). 3 contains about 97 % of the signal of a molecule.\n"
            "Smaller = less background and less signal; larger = more signal but neighbouring spots overlap.")
        sub.addWidget(self.ap_label, 7, 0)
        sub.addWidget(self.ap_field, 7, 1)

        self.means_check = QCheckBox("Get objects intensities means")
        self.means_check.setToolTip("Adds the Mean columns (Mean, BgSub_Mean, Normalized_Mean) to the data table.\n"
                                    "Without it, only the sums (and the maximum and volume) are given.")
        sub.addWidget(self.means_check, 8, 0, 1, 2)

        self.coords_check = QCheckBox("Get cells 3D coordinates")
        self.coords_check.setToolTip(
            "Adds the column ZYX_cell_coordinates to the data table, right after the cell labels:\n"
            "centre of each cell (centre of mass of its mask) as 'z, y, x', in pixels, with a decimal point.")
        sub.addWidget(self.coords_check, 9, 0, 1, 2)

        self.crop_settings = None
        self.crop_check = QCheckBox("Export cell crops")
        self.crop_check.setToolTip("Saves each cell (with a margin) as its own tif in '<cells name>_crops/'.")
        self.crop_btn = QPushButton("Crop settings…")
        self.crop_btn.clicked.connect(self._edit_crops)
        self.crop_lbl = QLabel("")
        self.crop_lbl.setWordWrap(True)
        self.crop_check.toggled.connect(self._crop_toggled)
        sub.addWidget(self.crop_check, 10, 0)
        sub.addWidget(self.crop_btn, 10, 1)
        sub.addWidget(self.crop_lbl, 11, 0, 1, 2)

        # Protein of interest name
        self.prot_label = small_label("Protein name")
        self.prot_field = field("e.g. Chinmo")
        self.prot_field.setToolTip("Name of the protein: the mean fluorescence of the channel is given per cell in a column with this name.")
        sub.addWidget(self.prot_label, 0, 0)
        sub.addWidget(self.prot_field, 0, 1)

        # Cell type marker fields
        self.marker_label = small_label("Marker name")
        self.marker_field = field("e.g. Asense")
        self.marker_field.setToolTip("Name of the marker. The cells are split into two groups by the mean intensity of this channel\n"
                                     "(mixture of two Gaussians).")
        self.g1_label     = small_label("Group 1 name")
        self.g1_field     = field("e.g. Type I")
        self.g1_field.setToolTip("Name of the first group of cells.")
        self.g2_label     = small_label("Group 2 name")
        self.g2_field     = field("e.g. Type II")
        self.g2_field.setToolTip("Name of the second group of cells.")
        self.mk_label     = small_label("Marked group")
        self.mk_field     = field("e.g. Type I")
        self.mk_field.setToolTip("Which of the two groups carries the marker (the brighter one).")
        sub.addWidget(self.marker_label, 0, 0); sub.addWidget(self.marker_field, 0, 1)
        sub.addWidget(self.g1_label,     1, 0); sub.addWidget(self.g1_field,     1, 1)
        sub.addWidget(self.g2_label,     2, 0); sub.addWidget(self.g2_field,     2, 1)
        sub.addWidget(self.mk_label,     3, 0); sub.addWidget(self.mk_field,     3, 1)

        # Associated cells checkboxes — for Cell type marker
        self.cells_assoc_label = small_label("Associated cells channel")
        self.checks_container  = QWidget()
        self.checks_layout     = QVBoxLayout(self.checks_container)
        self.checks_layout.setContentsMargins(0, 0, 0, 0)
        self.checks_layout.setSpacing(2)
        self.cells_checkboxes  = {}   # {(channel_idx, entry_ref): QCheckBox}
        sub.addWidget(self.cells_assoc_label, 4, 0, 1, 2)
        sub.addWidget(self.checks_container,  5, 0, 1, 2)

        outer.addWidget(self.sub_frame)
        self._show_widgets_for("None")

    # --------------------------------------------------------------------------
    def _edit_crops(self):
        dlg = CropSettingsDialog(self.crop_settings, self)
        if dlg.exec():
            self.crop_settings = dlg.settings()
        self._update_crop_label()

    def _crop_toggled(self, on):
        if on and self.crop_settings is None:
            self._edit_crops()
            if self.crop_settings is None:
                self.crop_settings = CropSettingsDialog().settings()
        self._update_crop_label()

    def _update_crop_label(self):
        on = self.crop_check.isChecked()
        self.crop_btn.setEnabled(on)
        if on:
            d = CropSettingsDialog(self.crop_settings)
            self.crop_lbl.setText(d.summary())
        else:
            self.crop_lbl.setText("")

    def _show_widgets_for(self, role):
        """Show only the sub-param widgets relevant to `role`."""
        is_cells   = role == "Cells"
        is_objects = role == "Objects"
        is_marker  = role == "Cell type marker"
        is_prot    = role == "Protein of interest"
        has_model  = is_cells or is_objects
        source     = self.src_combo.currentData() if has_model else None
        spotiflow  = is_objects and source == "Spotiflow"

        self.sub_frame.setVisible(role != "None")

        for w in (self.src_label, self.src_combo, self.model_label, self.model_combo, self.name_label, self.name_field):
            w.setVisible(has_model)
        for w in (self.sf_label, self.sf_field, self.size_label, self.size_field, self.coords_check,
                  self.crop_check, self.crop_btn, self.crop_lbl):
            w.setVisible(is_cells)
        for w in (self.sm_label, self.sm_combo, self.means_check):
            w.setVisible(is_objects)
        for w in (self.thr_label, self.thr_field, self.ap_label, self.ap_field):
            w.setVisible(spotiflow)

        if is_cells:
            self.name_label.setText("Cells name")
            self.name_field.setPlaceholderText("e.g. Neuroblasts")
        elif is_objects:
            self.name_label.setText("Objects name")
            self.name_field.setPlaceholderText("e.g. Spots")

        self.prot_label.setVisible(is_prot)
        self.prot_field.setVisible(is_prot)

        for w in [self.marker_label, self.marker_field,
                  self.g1_label, self.g1_field,
                  self.g2_label, self.g2_field,
                  self.mk_label, self.mk_field,
                  self.cells_assoc_label, self.checks_container]:
            w.setVisible(is_marker)

    def _fill_sources(self, role):
        """Tools offered as 'Model source' for a role; the ones that are not connected yet are greyed."""
        if role == "Cells":
            items = [("Cellpose", "Cellpose", True), ("Weka (Fiji)", SRC_WEKA, True),
                     ("EpySeg (not available yet)", "EpySeg", False)]
        else:
            items = [("EpySeg", "EpySeg", True), ("Spotiflow", "Spotiflow", True), ("Weka (Fiji)", SRC_WEKA, True),
                     ("Cellpose (not available yet)", "Cellpose", False),
                     ("FISH-quant (not available yet)", "FISH-quant", False)]
        self.src_combo.blockSignals(True)
        self.src_combo.clear()
        for text, data, enabled in items:
            self.src_combo.addItem(text, userData=data)
            self.src_combo.model().item(self.src_combo.count() - 1).setEnabled(enabled)
        self.src_combo.setCurrentIndex(0)
        self.src_combo.blockSignals(False)

    def set_source(self, source):
        i = self.src_combo.findData(source)
        if i >= 0 and self.src_combo.model().item(i).isEnabled():
            self.src_combo.setCurrentIndex(i)

    def _on_source_changed(self):
        self._refresh_models()
        self._show_widgets_for(self.role_combo.currentText())

    def _on_role(self, role):
        # Unregister previous Cells registration if needed
        if self._prev_role == "Cells":
            self.state.unregister_cells(self)
        # Register if new role is Cells
        if role == "Cells":
            self.state.register_cells(self.channel_idx, self)
        if role in ("Cells", "Objects"):
            self._fill_sources(role)
            self._refresh_models()

        self._show_widgets_for(role)

        if role == "Cell type marker":
            self.state.register_marker(self)
            self._refresh_checkboxes()
        elif self._prev_role == "Cell type marker":
            self.state.unregister_marker(self)

        self._prev_role = role

    def _refresh_models(self):
        """Models of the chosen source only; the model that was selected stays selected if it is still there."""
        previous = self.model_combo.currentData()
        self.model_combo.clear()
        source = self.src_combo.currentData()
        models = self.models_page.get_model_names(source) if source in MODEL_SOURCES else []
        for name, value in models:
            self.model_combo.addItem(name, userData=value)
        if not models:
            self.model_combo.addItem("— no model —")
        elif previous is not None:
            i = self.model_combo.findData(previous)
            if i >= 0:
                self.model_combo.setCurrentIndex(i)

    def _refresh_checkboxes(self):
        """
        Rebuild the list of "Associated cells" checkboxes.
        Called when state.changed fires (any Cells entry added/removed).
        Only runs if this entry's role is Cell type marker.
        """
        if self.role_combo.currentText() != "Cell type marker":
            return

        # Remember which entries were checked
        previously_checked = {
            key for key, cb in self.cells_checkboxes.items()
            if cb.isChecked()
        }

        for cb in self.cells_checkboxes.values():
            self.checks_layout.removeWidget(cb)
            cb.setParent(None)
        self.cells_checkboxes.clear()

        cells = self.state.get_cells_channels()
        self.cells_assoc_label.setVisible(bool(cells))
        self.checks_container.setVisible(bool(cells))

        for ch_idx, entry_ref in cells:
            if entry_ref is self:
                continue
            name = entry_ref.name_field.text() or f"Channel {ch_idx}"
            key  = (ch_idx, entry_ref)
            cb   = QCheckBox(f"Ch {ch_idx} — {name}")
            cb.setChecked(key in previously_checked)
            self.checks_layout.addWidget(cb)
            self.cells_checkboxes[key] = cb

    def get_params(self):
        """
        Returns a dict for this single analysis.
        The channel index is NOT included here — ChannelRow adds it.
        """
        role = self.role_combo.currentText()
        p = {"role": role}

        if role == "Cells":
            p["model_source"] = self.src_combo.currentData()
            p["model_path"]   = self.model_combo.currentData()
            p["cells_name"]   = self.name_field.text()
            p["shrink_factor"] = self.sf_field.text().strip() or "0"
            p["min_size"]      = self.size_field.text().strip() or "0"
            p["cell_coordinates"] = "True" if self.coords_check.isChecked() else "False"
            if p["model_source"] == "Cellpose":
                p["model_version"] = self.models_page.version_of(p["model_path"])
            elif p["model_source"] == SRC_WEKA:
                w = self.models_page.weka_of(p["model_path"])
                p["weka_mode"], p["weka_class"] = w["mode"], w["class"]
            p["export_crops"] = "True" if self.crop_check.isChecked() else "False"
            if self.crop_check.isChecked():
                p["crop_settings"] = self.crop_settings or CropSettingsDialog().settings()
        elif role == "Objects":
            source = self.src_combo.currentData()
            p["model_source"] = source
            p["detection"]    = DET_SPOTIFLOW if source == "Spotiflow" else DET_MODEL
            p["model_path"]   = self.model_combo.currentData()
            if source == SRC_WEKA:
                w = self.models_page.weka_of(p["model_path"])
                p["weka_mode"], p["weka_class"] = w["mode"], w["class"]
            p["objects_name"] = self.name_field.text()
            p["smfish_type"]  = self.sm_combo.currentText()
            p["spotiflow_prob_thresh"] = self.thr_field.text().strip()
            p["aperture_sigmas"] = self.ap_field.text().strip() or "3"
            p["get_means"]       = "True" if self.means_check.isChecked() else "False"
        elif role == "Protein of interest":
            p["prot_name"] = self.prot_field.text()
        elif role == "Cell type marker":
            acc = [
                ch_idx for (ch_idx, _), cb in self.cells_checkboxes.items()
                if cb.isChecked()
            ]
            acc.sort()
            p.update({
                "prot_name": self.marker_field.text(),
                "group1":    self.g1_field.text(),
                "group2":    self.g2_field.text(),
                "marked":    self.mk_field.text(),
                "associated_cells_channels": acc
            })
        return p

    def cleanup(self):
        """Must be called before deleting an entry to unregister from state."""
        if self._prev_role == "Cells":
            self.state.unregister_cells(self)


# ==============================================================================
# CHANNEL ROW
# Container for one channel's analyses.
# Holds one or more AnalysisEntry widgets + an "Add analysis" button.
# ==============================================================================
class ChannelRow(QWidget):
    def __init__(self, idx, models_page, state):
        super().__init__()
        self.idx         = idx
        self.models_page = models_page
        self.state       = state
        self._entries    = []

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(4)

        # Channel label
        lbl = QLabel(f"Channel {idx}")
        lbl.setObjectName("ch_label")
        outer.addWidget(lbl)

        # Container for AnalysisEntry widgets
        self.entries_container = QWidget()
        self.entries_layout    = QVBoxLayout(self.entries_container)
        self.entries_layout.setContentsMargins(8, 0, 0, 0)
        self.entries_layout.setSpacing(4)
        outer.addWidget(self.entries_container)

        # "Add analysis" button — only visible when at least one entry has a role
        self.add_btn = QPushButton("＋  Add analysis")
        self.add_btn.setStyleSheet(ADD_BTN_STYLE)
        self.add_btn.setVisible(False)
        self.add_btn.clicked.connect(self._add_entry)
        outer.addWidget(self.add_btn)

        # Visual separator between channels
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"color: {C['border']}; max-height: 1px;")
        outer.addWidget(sep)

        # One default entry, no remove button (can't remove the only entry)
        self._add_entry(show_remove=False)

        # When the first entry's role changes, maybe show "Add analysis"
        self._entries[0].role_combo.currentTextChanged.connect(self._on_first_role_changed)

    def _on_first_role_changed(self, role):
        # Show "Add analysis" once a real role is chosen for this channel
        self.add_btn.setVisible(role != "None")

    def _add_entry(self, show_remove=True):
        entry = AnalysisEntry(self.idx, self.models_page, self.state,
                              show_remove=show_remove)
        entry.remove_requested.connect(self._remove_entry)
        self._entries.append(entry)
        self.entries_layout.addWidget(entry)

    def _remove_entry(self, entry):
        if len(self._entries) <= 1:
            return
        entry.cleanup()   # unregister from state before removing
        self._entries.remove(entry)
        self.entries_layout.removeWidget(entry)
        entry.setParent(None)

    def get_params(self):
        """
        Returns one dict per analysis entry, each with the channel index.
        Multiple entries produce multiple dicts with the same channel index.

        Example with 2 entries on channel 1:
        [
          {"channel": 1, "role": "Cells", "model_path": "...", "cells_name": "Neuroblasts"},
          {"channel": 1, "role": "Protein of interest", "prot_name": "Miranda"}
        ]
        """
        result = []
        for entry in self._entries:
            p = entry.get_params()
            if p["role"] != "None":           # skip unset entries
                p["channel"] = self.idx       # inject channel index
                result.append(p)
        return result


# ==============================================================================
# PARAMS PANEL
# ==============================================================================
class ParamsPanel(QFrame):
    def __init__(self):
        super().__init__()
        self.setObjectName("panel")
        self.settings = QSettings("BioImaging", "Pipeline")

        outer = QVBoxLayout(self)
        outer.setContentsMargins(12, 12, 12, 12)
        outer.setSpacing(8)
        outer.addWidget(titled_label("PARAMETERS"))

        nav_row = QHBoxLayout()
        nav_row.setSpacing(6)
        self.adv_btn    = nav_btn("▶ Advanced")
        self.models_btn = nav_btn("◈ Models")
        self.adv_btn.setToolTip("Technical parameters: Z step, background correction, absolute quantification,\n"
                                "relative comparison, optics.")
        self.models_btn.setToolTip("The segmentation / detection models, grouped by tool (Cellpose, EpySeg, Spotiflow).")
        self.adv_btn.clicked.connect(
            lambda checked: self._switch(1, checked, self.models_btn))
        self.models_btn.clicked.connect(
            lambda checked: self._switch(2, checked, self.adv_btn))
        nav_row.addWidget(self.adv_btn)
        nav_row.addWidget(self.models_btn)
        outer.addLayout(nav_row)

        self.stack = QStackedWidget()
        outer.addWidget(self.stack)

        # Shared objects — created once, passed to every row/entry
        self.state       = ChannelState()
        self.models_page = ModelsPage()

        # ---- Page 0: channel rows ----
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        scroll_layout.setContentsMargins(0, 0, 4, 0)
        scroll_layout.setSpacing(10)

        self.channel_rows = [
            ChannelRow(i, self.models_page, self.state)
            for i in range(4)
        ]
        for row in self.channel_rows:
            scroll_layout.addWidget(row)
        scroll_layout.addStretch()

        scroll = QScrollArea()
        scroll.setWidget(scroll_widget)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.stack.addWidget(scroll)      # index 0

        # ---- Page 1: advanced params ----
        # WHY THE PARAMS TOOK TOO MUCH SPACE:
        # setRowStretch(4, 1) was on the same row as zstep_field (row 4).
        # The stretch was applied to a row that already had a widget,
        # so nothing pushed content up. Fix: use row 5 for the stretch.
        adv      = QWidget()
        adv_grid = QGridLayout(adv)
        adv_grid.setContentsMargins(4, 4, 4, 4)
        adv_grid.setSpacing(8)
        adv_grid.setColumnStretch(0, 1)
        adv_grid.setColumnStretch(1, 1)

        adv_grid.addWidget(small_label("Z-Step (µm)"), 0, 0)
        self.zstep_field = field("default: 0.44")
        self.zstep_field.setToolTip("Distance between two planes of the stack, in µm. Empty = read from the image.")
        adv_grid.addWidget(self.zstep_field, 0, 1)

        _sep = QFrame()
        _sep.setFrameShape(QFrame.Shape.HLine)
        _sep.setStyleSheet(f"color: {C['border']};")
        adv_grid.addWidget(_sep, 1, 0, 1, 2)

        # ---- Step 1: background correction (preprocessing) ----
        adv_grid.addWidget(small_label("1. Background correction"), 2, 0)
        self.bg_combo = NoScrollCombo()
        self.bg_combo.addItems(BG_MODES)
        self.bg_combo.setToolTip(
            "The background of every image is always measured and shown in the plots and in the summary.\n"
            "'Per image' subtracts it from the spot intensities (Mean - B, Sum - N x B) and adds\n"
            "columns BgSub_... and bg_value to the data table.\n"
            "'Per cell' uses the level of each cell (shrunk towards the image level for small cells),\n"
            "plus the profile along Z when it is significant.\n"
            "'Morisaki and Stasevich method' subtracts, for each spot, the mean of a ring around it\n"
            "(drawn in the planes of the spot, other spots excluded). If the ring is too small,\n"
            "the background of the image is used.\n"
            "The results below (absolute and relative) are computed on the corrected intensities.")
        self.bg_combo.currentTextChanged.connect(lambda _t: self._update_bg_visibility())
        adv_grid.addWidget(self.bg_combo, 2, 1)

        self.ring_gap_label = small_label("Ring: distance (px)")
        self.ring_gap_field = field(RING_GAP_DEFAULT)
        self.ring_gap_field.setText(RING_GAP_DEFAULT)
        self.ring_gap_field.setToolTip("Distance between the spot and the inside of the ring.\n"
                                       "Too small: the ring contains the halo of the spot (background overestimated).")
        adv_grid.addWidget(self.ring_gap_label, 3, 0)
        adv_grid.addWidget(self.ring_gap_field, 3, 1)
        self.ring_width_label = small_label("Ring: width (px)")
        self.ring_width_field = field(RING_WIDTH_DEFAULT)
        self.ring_width_field.setText(RING_WIDTH_DEFAULT)
        self.ring_width_field.setToolTip("Width of the ring. A wider ring contains more voxels: a less noisy background.")
        adv_grid.addWidget(self.ring_width_label, 4, 0)
        adv_grid.addWidget(self.ring_width_field, 4, 1)

        _sep = QFrame()
        _sep.setFrameShape(QFrame.Shape.HLine)
        _sep.setStyleSheet(f"color: {C['border']};")
        adv_grid.addWidget(_sep, 5, 0, 1, 2)

        # ---- Step 2: absolute result (number of molecules) ----
        adv_grid.addWidget(small_label("2. Absolute quantification"), 6, 0)
        self.abs_combo = NoScrollCombo()
        self.abs_combo.addItems(ABS_MODES)
        self.abs_combo.setToolTip(
            "Quantification from one molecule: number of molecules per spot = background-corrected Sum /\n"
            "intensity of one molecule. The intensity of one molecule is measured in each image, from the objects\n"
            "of the same channel: the objects clearly larger than a molecule (clusters, transcription sites,\n"
            "judged by their size compared to the PSF) are put aside, the median of the others is taken.\n"
            "Needs a background correction (step 1) and the optics of the image (see Optics below).\n"
            "Only for exonic probes (an intronic probe has no isolated molecules).\n"
            "Independent of the relative comparison (step 3).")
        self.abs_combo.currentTextChanged.connect(lambda _t: self._update_abs_visibility())
        adv_grid.addWidget(self.abs_combo, 6, 1)

        self.abs_unit_label = small_label("Counted molecules")
        self.abs_unit_combo = NoScrollCombo()
        self.abs_unit_combo.addItems(ABS_UNITS)
        self.abs_unit_combo.setToolTip("What is counted. Names the column: <probe>_RNA_count or <probe>_fluorophores_count.")
        adv_grid.addWidget(self.abs_unit_label, 7, 0)
        adv_grid.addWidget(self.abs_unit_combo, 7, 1)
        self.abs_note = small_label("Not computed for objects of an intronic probe.")
        self.abs_note.setWordWrap(True)
        adv_grid.addWidget(self.abs_note, 8, 0, 1, 2)

        _sep = QFrame()
        _sep.setFrameShape(QFrame.Shape.HLine)
        _sep.setStyleSheet(f"color: {C['border']};")
        adv_grid.addWidget(_sep, 9, 0, 1, 2)

        # ---- Step 3: relative result (comparison with a reference population) ----
        adv_grid.addWidget(small_label("3. Relative comparison"), 10, 0)
        self.norm_against_combo = NoScrollCombo()
        self.norm_against_combo.addItems(NORM_MODES)
        self.norm_against_combo.setToolTip("Divides each spot by the mean of a reference population (Normalized columns).\n"
                                           "'All except...': the reference is every spot NOT in the chosen population / type.\n"
                                           "'Only...': the reference is the spots of the chosen population / type.\n"
                                           "A spot is never divided by itself. Independent of the absolute quantification (step 2).")
        self.norm_against_combo.currentTextChanged.connect(self._on_norm_against)
        adv_grid.addWidget(self.norm_against_combo, 10, 1)

        self.norm_cells_label = small_label("Cell population")
        self.norm_cells_combo = NoScrollCombo()
        self.norm_cells_combo.setToolTip("Population of cells the reference spots are taken from (a population defined by a Cells analysis).")
        self.norm_cells_combo.currentIndexChanged.connect(self._on_norm_cells_changed)
        adv_grid.addWidget(self.norm_cells_label, 11, 0)
        adv_grid.addWidget(self.norm_cells_combo, 11, 1)

        self.norm_type_label = small_label("Cell type (optional)")
        self.norm_type_combo = NoScrollCombo()
        self.norm_type_combo.setToolTip("Restricts the reference to the cells of one type (from a Cell type marker). 'Any type' = all.")
        self.norm_type_combo.currentTextChanged.connect(self._on_norm_type_changed)
        self._saved_norm_type = ""
        adv_grid.addWidget(self.norm_type_label, 12, 0)
        adv_grid.addWidget(self.norm_type_combo, 12, 1)

        self.norm_3d_label = small_label("3D normalisation")
        self.norm_3d_check = QCheckBox("Use 3D (per z-slice)")
        self.norm_3d_check.setToolTip("Each spot is divided by the reference spots at the same depth (their centre within the Z range of the spot,\n"
                                      "widened by 0.5 plane until at least one reference is found), instead of all the reference spots.")
        adv_grid.addWidget(self.norm_3d_label, 13, 0)
        adv_grid.addWidget(self.norm_3d_check, 13, 1)

        _sep = QFrame()
        _sep.setFrameShape(QFrame.Shape.HLine)
        _sep.setStyleSheet(f"color: {C['border']};")
        adv_grid.addWidget(_sep, 14, 0, 1, 2)
        optics_body = QWidget()
        og = QGridLayout(optics_body)
        og.setContentsMargins(4, 4, 4, 4)
        og.setSpacing(6)
        og.setColumnStretch(0, 1)
        og.setColumnStretch(1, 1)
        intro = small_label("Read from the image when possible. Fill a field to replace the value of the image, "
                            "or when the image does not give it. They give the size of the PSF (aperture of the points, "
                            "size check of the single molecules).")
        intro.setWordWrap(True)
        og.addWidget(intro, 0, 0, 1, 2)
        self.optics_fields = {}
        for i, (key, text, tip) in enumerate([
                ("na", "Numerical aperture", "Numerical aperture of the objective (e.g. 1.2 for a 40x water objective)."),
                ("refractive_index", "Refractive index", "Refractive index of the immersion medium (water 1.333, oil 1.518)."),
                ("emission_nm", "Emission (nm)", "Centre of the detection band of the channel, in nm (e.g. 605 for Quasar 570 detected 560-650)."),
                ("excitation_nm", "Excitation (nm)", "Laser wavelength used for the channel, in nm (e.g. 561)."),
                ("pinhole_au", "Pinhole (Airy units)", "Size of the confocal pinhole in Airy units (1 AU is the usual). Without it the PSF would be computed as for a widefield microscope.")]):
            og.addWidget(small_label(text), 1 + i, 0)
            f = field("from the image"); f.setToolTip(tip)
            og.addWidget(f, 1 + i, 1)
            self.optics_fields[key] = f
        self.optics_section = CollapsibleSection("Optics", optics_body, expanded=False)
        self.optics_section.setToolTip("Acquisition parameters used to compute the PSF. They are read from the image;\n"
                                       "open this section to replace them or to fill the ones the image does not give.")
        adv_grid.addWidget(self.optics_section, 15, 0, 1, 2)

        self._update_bg_visibility()
        self._update_abs_visibility()
        self._update_norm_visibility()

        # An empty row with stretch pushes all content to the top
        adv_grid.setRowStretch(40, 1)

        adv_scroll = QScrollArea()
        adv_scroll.setWidget(adv)
        adv_scroll.setWidgetResizable(True)
        adv_scroll.setFrameShape(QFrame.Shape.NoFrame)
        adv_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.stack.addWidget(adv_scroll)  # index 1

        # ---- Page 2: models ----
        self.stack.addWidget(self.models_page)  # index 2

        # ---- Presets bar ----
        preset_row = QHBoxLayout()
        preset_row.setSpacing(4)
        self._preset_combo = NoScrollCombo()
        self._preset_combo.setPlaceholderText("— presets —")
        self._preset_combo.setToolTip("Loads a saved set of parameters.")
        self._preset_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        preset_row.addWidget(self._preset_combo)

        save_p_btn = QPushButton("Save")
        save_p_btn.setFixedWidth(46)
        save_p_btn.setStyleSheet(f"QPushButton {{ background:transparent; border:1px solid {C['border']};"
                                 f" border-radius:4px; color:{C['muted']}; padding:3px; font-size:11px; }}"
                                 f"QPushButton:hover {{ border-color:{C['accent']}; color:{C['accent']}; }}")
        save_p_btn.setToolTip("Saves the current parameters (channels, background, absolute, optics, normalisation) as a preset.")
        save_p_btn.clicked.connect(self._save_preset)
        preset_row.addWidget(save_p_btn)

        del_p_btn = QPushButton("Del")
        del_p_btn.setFixedWidth(36)
        del_p_btn.setStyleSheet(f"QPushButton {{ background:transparent; border:1px solid {C['border']};"
                                f" border-radius:4px; color:{C['muted']}; padding:3px; font-size:11px; }}"
                                f"QPushButton:hover {{ border-color:{C['error']}; color:{C['error']}; }}")
        del_p_btn.setToolTip("Deletes the selected preset.")
        del_p_btn.clicked.connect(self._delete_preset)
        preset_row.addWidget(del_p_btn)

        outer.insertLayout(1, preset_row)   # insert just below PARAMETERS title
        self._preset_combo.currentTextChanged.connect(self._load_preset)
        self._refresh_preset_combo()

    PRESET_KEY = "param_presets"

    def _refresh_preset_combo(self):
        self._preset_combo.blockSignals(True)
        self._preset_combo.clear()
        presets = self._get_presets()
        for name in sorted(presets.keys()):
            self._preset_combo.addItem(name)
        self._preset_combo.blockSignals(False)

    def _get_presets(self):
        raw = self.settings.value(self.PRESET_KEY, defaultValue="{}")
        try:
            return json.loads(raw) if isinstance(raw, str) else {}
        except Exception:
            return {}

    def _save_preset(self):
        from PyQt6.QtWidgets import QInputDialog
        name, ok = QInputDialog.getText(self, "Save preset", "Preset name:")
        if not ok or not name.strip():
            return
        name = name.strip()
        presets = self._get_presets()
        presets[name] = self.get_params()
        self.settings.setValue(self.PRESET_KEY, json.dumps(presets))
        self._refresh_preset_combo()
        self._preset_combo.setCurrentText(name)

    def _delete_preset(self):
        name = self._preset_combo.currentText()
        if not name:
            return
        presets = self._get_presets()
        if name in presets:
            del presets[name]
            self.settings.setValue(self.PRESET_KEY, json.dumps(presets))
        self._refresh_preset_combo()

    # ---- Normalisation (Advanced page) ----

    def _on_norm_against(self, mode):
        self._refresh_norm_pop_combo()
        self._update_norm_visibility()

    def _on_norm_cells_changed(self, _idx):
        self._refresh_norm_type_combo()
        self._update_norm_visibility()

    def _on_norm_type_changed(self, text):
        if text and text != "Any type":
            self._saved_norm_type = text

    def _update_bg_visibility(self):
        ring = self.bg_combo.currentText() == BG_RING
        for w in (self.ring_gap_label, self.ring_gap_field, self.ring_width_label, self.ring_width_field):
            w.setVisible(ring)

    def _update_abs_visibility(self):
        mode = self.abs_combo.currentText()
        for w in (self.abs_unit_label, self.abs_unit_combo, self.abs_note):
            w.setVisible(mode == ABS_CALIB)

    def _update_norm_visibility(self):
        mode = self.norm_against_combo.currentText()
        needs_cells = mode in (NORM_EXCEPT, NORM_ONLY)
        self.norm_cells_label.setVisible(needs_cells)
        self.norm_cells_combo.setVisible(needs_cells)
        needs_type = needs_cells and self.norm_cells_combo.currentData() is not None
        self.norm_type_label.setVisible(needs_type)
        self.norm_type_combo.setVisible(needs_type)
        needs_3d = mode != NORM_NONE
        self.norm_3d_label.setVisible(needs_3d)
        self.norm_3d_check.setVisible(needs_3d)

    def _refresh_norm_pop_combo(self):
        prev_text = self.norm_cells_combo.currentText()
        mode = self.norm_against_combo.currentText()
        self.norm_cells_combo.blockSignals(True)
        self.norm_cells_combo.clear()
        if mode != NORM_EXCEPT:
            self.norm_cells_combo.addItem("All cells", None)
        for ch_idx, entry_ref in self.state.get_cells_channels():
            name = entry_ref.name_field.text() or f"Channel {ch_idx}"
            self.norm_cells_combo.addItem(name, (ch_idx, entry_ref))
        idx = self.norm_cells_combo.findText(prev_text)
        if idx >= 0:
            self.norm_cells_combo.setCurrentIndex(idx)
        self.norm_cells_combo.blockSignals(False)
        self._refresh_norm_type_combo()

    def _refresh_norm_type_combo(self):
        self.norm_type_combo.blockSignals(True)
        self.norm_type_combo.clear()
        self.norm_type_combo.addItem("Any type", None)
        data = self.norm_cells_combo.currentData()
        if data is not None:
            _, entry_ref = data
            types = self.state.get_types_for_cells(entry_ref)
            for t in types:
                if t:
                    self.norm_type_combo.addItem(t, t)
        if self._saved_norm_type:
            idx = self.norm_type_combo.findText(self._saved_norm_type)
            if idx >= 0:
                self.norm_type_combo.setCurrentIndex(idx)
        self.norm_type_combo.blockSignals(False)

    def _load_preset(self, name):
        if not name:
            return
        presets = self._get_presets()
        if name not in presets:
            return
        data = presets[name]
        self._preset_warnings = []
        # Apply zstep
        self.zstep_field.setText(str(data.get("zstep", "")))
        # Restore normalisation block (Advanced page)
        norm_data = data.get("normalisation", {})
        self.norm_against_combo.setCurrentText(norm_data.get("norm_against", NORM_NONE))
        norm_3d_val = norm_data.get("norm_3d", "False")
        self.norm_3d_check.setChecked(norm_3d_val is True or str(norm_3d_val).strip() == "True")
        bg_data = data.get("background", {})
        self.bg_combo.setCurrentText(bg_data.get("method", BG_NONE))
        self.ring_gap_field.setText(str(bg_data.get("ring_gap", RING_GAP_DEFAULT)))
        self.ring_width_field.setText(str(bg_data.get("ring_width", RING_WIDTH_DEFAULT)))
        abs_data = data.get("absolute", {})
        mode = abs_data.get("mode", ABS_NONE)
        self.abs_combo.setCurrentText(ABS_LEGACY.get(mode, mode))
        self.abs_unit_combo.setCurrentText(abs_data.get("unit", ABS_UNITS[0]))
        opt = data.get("optics", {})
        for key, fld in self.optics_fields.items():
            fld.setText(str(opt.get(key, "")))
        self._update_bg_visibility()
        self._update_abs_visibility()
        norm_cells_name = norm_data.get("norm_cells_name", "")
        norm_type = norm_data.get("norm_cell_type", "")
        self._saved_norm_type = norm_type if norm_type and norm_type != "Any type" else ""
        channels = data.get("channels", [])
        # Reset all rows first
        for row in self.channel_rows:
            for entry in row._entries:
                entry.role_combo.setCurrentText("None")
        # Apply loaded params
        for ch_data in channels:
            ch_idx = ch_data.get("channel", 0)
            if ch_idx >= len(self.channel_rows):
                continue
            row = self.channel_rows[ch_idx]
            # Use first entry or add one
            if not row._entries:
                continue
            entry = row._entries[0]
            role = ch_data.get("role", "None")
            entry.role_combo.setCurrentText(role)
            if role == "Cells":
                entry.name_field.setText(ch_data.get("cells_name", ""))
                entry.sf_field.setText(str(ch_data.get("shrink_factor", "")).strip() or "0")
                entry.size_field.setText(str(ch_data.get("min_size", "")).strip() or "0")
                entry.coords_check.setChecked(str(ch_data.get("cell_coordinates", "False")) == "True")
                entry.crop_settings = ch_data.get("crop_settings") or CropSettingsDialog().settings()
                entry.crop_check.setChecked(str(ch_data.get("export_crops", "False")) == "True")
                entry._update_crop_label()
                self._restore_model(entry, ch_data, "Cellpose")
            elif role == "Objects":
                entry.name_field.setText(ch_data.get("objects_name", ""))
                kind = ch_data.get("smfish_type")
                if kind not in SMFISH_TYPES:                    # earlier presets: 'max spots per cell'
                    kind = SMFISH_TYPES[1] if str(ch_data.get("max_spots/cell", "")).strip() == "2" else SMFISH_TYPES[0]
                    if str(ch_data.get("max_spots/cell", "")).strip() not in ("", "2"):
                        self._preset_warnings.append(f"{ch_data.get('objects_name', 'Objects')}: 'max spots per cell' = "
                                                     f"{ch_data.get('max_spots/cell')} no longer exists; set to exonic probe.")
                entry.sm_combo.setCurrentText(kind)
                entry.thr_field.setText(str(ch_data.get("spotiflow_prob_thresh", "")))
                entry.ap_field.setText(str(ch_data.get("aperture_sigmas", "3")))
                entry.means_check.setChecked(str(ch_data.get("get_means", "False")) == "True")
                source = ch_data.get("model_source") or (DET_SPOTIFLOW if ch_data.get("detection") == DET_SPOTIFLOW else "EpySeg")
                self._restore_model(entry, dict(ch_data, model_source=source), "EpySeg")
            elif role == "Protein of interest":
                entry.prot_field.setText(ch_data.get("prot_name", ""))
            elif role == "Cell type marker":
                entry.marker_field.setText(ch_data.get("prot_name", ""))
                entry.g1_field.setText(ch_data.get("group1", ""))
                entry.g2_field.setText(ch_data.get("group2", ""))
                entry.mk_field.setText(ch_data.get("marked", ""))
                # Restore associated_cells_channels checkboxes (first pass — may be overwritten by state.changed)
                acc = ch_data.get("associated_cells_channels", [])
                for (key_ch_idx, _), cb in entry.cells_checkboxes.items():
                    cb.setChecked(key_ch_idx in acc)

        # Second pass: re-apply associated_cells_channels after all roles/state are stable
        for ch_data in channels:
            ch_idx = ch_data.get("channel", 0)
            if ch_idx >= len(self.channel_rows):
                continue
            row = self.channel_rows[ch_idx]
            if not row._entries:
                continue
            entry = row._entries[0]
            if entry.role_combo.currentText() == "Cell type marker":
                acc = ch_data.get("associated_cells_channels", [])
                for (key_ch_idx, _), cb in entry.cells_checkboxes.items():
                    cb.setChecked(key_ch_idx in acc)

        # Last step: the cell populations and types now exist, so the normalisation choice can be restored
        self._refresh_norm_pop_combo()
        if norm_cells_name:
            idx_c = self.norm_cells_combo.findText(norm_cells_name)
            if idx_c >= 0:
                self.norm_cells_combo.setCurrentIndex(idx_c)
        self._refresh_norm_type_combo()
        self._update_norm_visibility()
        if self._preset_warnings:
            QMessageBox.warning(self, "Preset", "\n".join(self._preset_warnings))

    def _restore_model(self, entry, ch_data, default_source):
        """Source then model of an entry; a model that is no longer in the Models page is reported."""
        entry.set_source(ch_data.get("model_source") or default_source)
        model_path = ch_data.get("model_path")
        if not model_path:
            return
        i = entry.model_combo.findData(model_path)
        if i >= 0:
            entry.model_combo.setCurrentIndex(i)
        else:
            self._preset_warnings.append(
                f"Model not found in the Models page ({entry.src_combo.currentData()}): {model_path}\n"
                f"Choose another model for '{ch_data.get('cells_name') or ch_data.get('objects_name') or 'this analysis'}'.")

    def highlight_optics(self, keys):
        """Opens the Optics section and outlines the fields the image does not give."""
        for k, f in self.optics_fields.items():
            f.setStyleSheet(f"border: 1px solid {C['error']};" if k in keys else "")
        if keys:
            self.optics_section.set_expanded(True)
            self.adv_btn.setChecked(True)
            self.models_btn.setChecked(False)
            self.stack.setCurrentIndex(1)

    def _switch(self, page_idx, checked, other_btn):
        other_btn.setChecked(False)
        self.stack.setCurrentIndex(page_idx if checked else 0)

    def get_params(self):
        """
        Flattens all channel rows into a single list of analysis dicts.
        Each dict has a "channel" key. Multiple dicts can share the same channel.
        """
        all_channels = []
        for row in self.channel_rows:
            all_channels.extend(row.get_params())   # extend, not append

        # Read normalisation from the Advanced-page widgets (independent of channels)
        norm_mode = self.norm_against_combo.currentText()
        if norm_mode in (NORM_EXCEPT, NORM_ONLY):
            self._refresh_norm_pop_combo()   # cells may have been (re)named since the mode was chosen
        norm_3d_str = "True" if self.norm_3d_check.isChecked() else "False"
        norm_cells = self.norm_cells_combo.currentText() if norm_mode in (NORM_EXCEPT, NORM_ONLY) else ""
        if norm_mode in (NORM_EXCEPT, NORM_ONLY):
            self._refresh_norm_type_combo()
        t = self._saved_norm_type if self._saved_norm_type else self.norm_type_combo.currentText()
        norm_type = t if t and t != "Any type" else ""

        uses_weka = any(c.get("model_source") == SRC_WEKA for c in all_channels)
        return {
            "channels":      all_channels,
            "fiji_path":     self.models_page.fiji_path() if uses_weka else "",
            "zstep":         self.zstep_field.text(),
            "background":    {"method": self.bg_combo.currentText(),
                               "ring_gap": self.ring_gap_field.text().strip() or RING_GAP_DEFAULT,
                               "ring_width": self.ring_width_field.text().strip() or RING_WIDTH_DEFAULT},
            "absolute":      {"mode": self.abs_combo.currentText(),
                               "unit": self.abs_unit_combo.currentText(),
                               },
            "optics":        {k: f.text().strip() for k, f in self.optics_fields.items() if f.text().strip()},
            "normalisation": {
                "norm_against":    norm_mode,
                "norm_3d":         norm_3d_str,
                "norm_cells_name": norm_cells,
                "norm_cell_type":  norm_type,
            },
        }


# ==============================================================================
# WORKER THREAD
# ==============================================================================
class AnalysisWorker(QThread):
    progress   = pyqtSignal(int, int, str)
    log        = pyqtSignal(str)
    finished   = pyqtSignal()
    file_done  = pyqtSignal(str, str)
    plot_ready = pyqtSignal(str)
    background_ready = pyqtSignal(str)
    calibration_ready = pyqtSignal(str)

    def __init__(self, files, params):
        super().__init__()
        self.files    = files
        self.params   = params
        self._running = True
        self._process = None

    def stop(self):
        self._running = False
        if self._process is not None:
            if sys.platform == "win32":
                # kills Newmain.py and the segmentation / detection processes it started
                subprocess.run(["taskkill", "/F", "/T", "/PID", str(self._process.pid)],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            else:
                self._process.terminate()

    @staticmethod
    def _find_conda_python(env_name):
        """
        Locate the Python interpreter for a conda environment.
        Works on Windows (Anaconda 26, various install locations) and macOS/Linux.
        """
        try:                                                  # the logic of setup_environments.py (conda, CONDA_EXE, ...)
            if base_path not in sys.path:
                sys.path.insert(0, base_path)
            import setup_environments as _se
            found = _se.find_env_python(env_name)
            if found:
                return found
        except Exception:
            pass
        home = os.path.expanduser("~")

        if sys.platform == "win32":
            exe = "python.exe"
            # Possible Anaconda/Miniconda root directories on Windows
            roots = [
                os.path.join(home, "anaconda3"),
                os.path.join(home, "miniconda3"),
                os.path.join(home, "AppData", "Local", "anaconda3"),
                os.path.join(home, "AppData", "Local", "miniconda3"),
                r"C:\ProgramData\anaconda3",
                r"C:\ProgramData\miniconda3",
                r"C:\anaconda3",
                r"C:\miniconda3",
            ]
        else:
            exe = "python"
            roots = [
                os.path.join(home, "anaconda3"),
                os.path.join(home, "miniconda3"),
                os.path.join(home, "opt", "anaconda3"),
                "/opt/anaconda3",
                "/opt/miniconda3",
                "/Applications/anaconda3",
            ]

        for root in roots:
            if sys.platform == "win32":
                candidate = os.path.join(root, "envs", env_name, exe)
            else:
                candidate = os.path.join(root, "envs", env_name, "bin", exe)
            if os.path.isfile(candidate):
                return candidate

        # Last resort: ask conda itself where the env lives
        import shutil
        conda_exe = shutil.which("conda")
        if conda_exe:
            try:
                import json as _json
                r = subprocess.run(
                    [conda_exe, "env", "list", "--json"],
                    text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
                )
                data = _json.loads(r.stdout)
                for env_path in data.get("envs", []):
                    if os.path.basename(env_path) == env_name:
                        if sys.platform == "win32":
                            candidate = os.path.join(env_path, exe)
                        else:
                            candidate = os.path.join(env_path, "bin", exe)
                        if os.path.isfile(candidate):
                            return candidate
            except Exception:
                pass

        # Absolute fallback: hope it's on PATH
        return exe

    def _conda_python(self, env_name):
        return self._find_conda_python(env_name)

    def run(self):
        import json
        total = len(self.files)
        self.log.emit(f"Starting — {total} file(s)")
        run_params = dict(self.params)
        run_params["envs"] = {n: self._conda_python(n) for n in ("segment", "cellpose3", "cellpose4", "chinmospots", "spotiflow")}

        for i, path in enumerate(self.files):
            if not self._running:
                self.log.emit("Stopped by user."); break

            name = os.path.basename(os.path.normpath(path))
            self.log.emit(f"[{i+1}/{total}] {name}")
            self.progress.emit(i, total, path)

            try:
                # Normalise path separators for the current platform
                norm_path = os.path.normpath(path)
                norm_base = os.path.normpath(base_path)
                self._process = subprocess.Popen(
                    [self._conda_python("spots_analysis"), "-u",
                     os.path.join(norm_base, "Newmain.py"),
                     norm_base, json.dumps(run_params), norm_path],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    bufsize=1, text=True,
                    # On Windows, avoid the shell so paths with spaces are safe
                    shell=False,
                )
                for line in iter(self._process.stdout.readline, ""):
                    if not self._running:
                        self._process.terminate(); break
                    if line.startswith("distrib:"):
                        self.plot_ready.emit(line.rstrip())
                    elif line.startswith("background:"):
                        self.background_ready.emit(line.rstrip())      # record of the background study (json)
                    elif line.startswith("calibration:"):
                        self.calibration_ready.emit(line.rstrip())
                    else:
                        self.log.emit(line.rstrip())
                self._process.stdout.close()
                rc = self._process.wait()
                self._process = None
                if rc != 0:
                    self.file_done.emit(path, "error")
                    self.log.emit(f"  ✗ {name}: process exited with code {rc}")
                else:
                    self.file_done.emit(path, "ok")
                    self.log.emit(f"  ✓ {name}")

            except Exception as e:
                self.file_done.emit(path, "error")
                self.log.emit(f"  ✗ {name}: {e}")

        self.progress.emit(total, total, "")
        self.log.emit("Done.")
        self.finished.emit()


# ==============================================================================
# CHECKS BEFORE AN ANALYSIS: conda environments, optical parameters of the images
# ==============================================================================
def required_envs(params):
    """Environments needed by the chosen parameters (the others are not checked)."""
    need = ["spots_analysis"]
    for ch in params.get("channels", []):
        if ch.get("model_source") == SRC_WEKA and ch["role"] in ("Cells", "Objects"):
            continue                                   # Fiji brings its own Java; the analysis environment runs the rest
        if ch["role"] == "Cells":
            need.append({2: "segment", 3: "cellpose3", 4: "cellpose4"}.get(int(float(str(ch.get("model_version", 2)))), "segment"))
        elif ch["role"] == "Objects":
            need.append("spotiflow" if ch.get("model_source") == "Spotiflow" else "chinmospots")
    return list(dict.fromkeys(need))


def env_python(env_name):
    """Python of a conda environment, or None if the environment does not exist."""
    found = AnalysisWorker._find_conda_python(env_name)
    return found if found and os.path.isfile(found) else None


class EnvInstaller(QThread):
    """Creates and fills the missing conda environments with the functions of setup_environments.py."""
    log = pyqtSignal(str)
    done = pyqtSignal(bool, str)

    def __init__(self, names):
        super().__init__()
        self.names = names

    def run(self):
        try:
            if base_path not in sys.path:
                sys.path.insert(0, base_path)
            import setup_environments as se
        except ImportError:
            self.done.emit(False, "setup_environments.py was not found next to the GUI.")
            return
        emit = self.log.emit

        class _Writer:
            def write(self, text):
                for line in str(text).splitlines():
                    line = re.sub(r"\x1b\[[0-9;]*m", "", line).rstrip()
                    if line.strip():
                        emit(line)
            def flush(self):
                pass

        try:
            conda = se.find_conda(None)
        except RuntimeError as e:
            self.done.emit(False, str(e))
            return
        failed = []
        with contextlib.redirect_stdout(_Writer()):
            for name in self.names:
                cfg = se.ENVS[name]
                print(f"=== Environment '{name}' ===")
                ok = se.create_env(conda, name, cfg["python"]) and se.install_env(conda, name, cfg["pip_steps"]) \
                    and se.verify_env(conda, name, se.VERIFY.get(name, []))
                if not ok:
                    failed.append(name)
        if failed:
            self.done.emit(False, "Installation failed for: " + ", ".join(failed) +
                           ". See the log; you can also run setup_environments.py by hand.")
        else:
            self.done.emit(True, "")


def optics_problems(files, params):
    """{image: {objects name: [missing parameter names]}} for the analyses that need the PSF."""
    needs_psf = params.get("absolute", {}).get("mode") == ABS_CALIB or \
        any(c["role"] == "Objects" and c.get("model_source") == "Spotiflow" for c in params.get("channels", []))
    if not needs_psf:
        return {}
    try:
        if base_path not in sys.path:
            sys.path.insert(0, base_path)
        import optics
    except Exception:
        return {}
    problems = {}
    for folder in files:
        name = os.path.basename(os.path.normpath(folder))
        try:
            tifs = [n for n in os.listdir(folder) if n.lower().endswith(".tif")]
        except OSError:
            continue
        tifs = [t for t in tifs if t[:-4] == name] or (tifs if len(tifs) == 1 else [])
        if not tifs:
            continue
        for ch in params["channels"]:
            if ch["role"] != "Objects":
                continue
            try:
                acq = optics.merge_overrides(optics.read_acquisition(os.path.join(folder, tifs[0]), int(ch["channel"])),
                                             params.get("optics", {}))
            except Exception:
                continue
            missing = optics.missing_for_psf(acq, need_pinhole=True)
            if missing:
                problems.setdefault(name, {})[ch["objects_name"]] = missing
    return problems


OPTICS_LABELS = {"na": "numerical aperture", "refractive_index": "refractive index", "emission_nm": "emission wavelength",
                 "excitation_nm": "excitation wavelength", "pinhole_au": "pinhole (Airy units)"}


# ==============================================================================
# BOTTOM BAR
# ==============================================================================
class BottomBar(QWidget):
    def __init__(self, on_run, on_stop):
        super().__init__()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        self.bar = QProgressBar()
        self.bar.setRange(0, 100); self.bar.setValue(0); self.bar.setFormat("0")
        layout.addWidget(self.bar, stretch=1)

        self.btn_stack = QStackedWidget()
        self.btn_stack.setFixedWidth(160)

        self.run_btn = QPushButton("▶  Analyze")
        self.run_btn.setToolTip("Analyses every file of the list with the parameters on the right.\n"
                                "The environments and the optical parameters needed are checked first.")
        self.run_btn.setObjectName("run_btn")
        self.run_btn.setEnabled(False)
        self.run_btn.clicked.connect(on_run)

        self.stop_btn = QPushButton("■  Stop")
        self.stop_btn.setObjectName("stop_btn")
        self.stop_btn.clicked.connect(on_stop)

        self.btn_stack.addWidget(self.run_btn)
        self.btn_stack.addWidget(self.stop_btn)
        layout.addWidget(self.btn_stack)

    def set_running(self, running):
        self.btn_stack.setCurrentIndex(1 if running else 0)

    def set_run_enabled(self, enabled):
        self.run_btn.setEnabled(enabled)

    def set_progress(self, value, total, _=""):
        if total == 0: return
        self.bar.setRange(0, total); self.bar.setValue(value)
        self.bar.setFormat(f"{value}/{total}  ({int(value/total*100)}%)")


# ==============================================================================
# LOG PANEL
# ==============================================================================
class LogPanel(QFrame):
    def __init__(self):
        super().__init__()
        self.setObjectName("panel")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(6)
        layout.addWidget(titled_label("LOG"))
        self.text = QTextEdit()
        self.text.setReadOnly(True)
        layout.addWidget(self.text)

    def append(self, line):
        # plain text, so that spaces (tables) are kept and '<' or '&' are not read as HTML
        self.text.moveCursor(QTextCursor.MoveOperation.End)
        if line.startswith("\x01"):
            # progress bar update: replaces the previous update instead of adding a line
            line = line[1:]
            if getattr(self, "_progress_open", False):
                cur = self.text.textCursor()
                cur.movePosition(QTextCursor.MoveOperation.PreviousBlock)
                cur.movePosition(QTextCursor.MoveOperation.End, QTextCursor.MoveMode.KeepAnchor)
                cur.removeSelectedText()
                self.text.setTextCursor(cur)
            self._progress_open = True
        else:
            self._progress_open = False
        self.text.insertPlainText(line + "\n")
        self.text.verticalScrollBar().setValue(
            self.text.verticalScrollBar().maximum())


# ==============================================================================
# DATA EXPLORER TAB
# ==============================================================================

def detect_col_type(col_name, series):
    n = col_name.lower()
    if "label" in n:
        return "label"
    if "typing" in n:
        return "typing"
    if "number" in n:
        return "count"
    if pd.api.types.is_numeric_dtype(series):
        return "numeric"
    if series.dropna().nunique() <= 30:
        return "typing"
    return "numeric"


class FilterRow(QWidget):
    """
    One filter: [column] [operator] [value] [×]

    FIX — value widget size:
    The val_stack was set with stretch=1 which made it fill all remaining
    space. Now it has setMaximumWidth(130) so it stays the same visual
    width as the column and operator combos.

    FIX — "is not empty" truncated:
    op_combo width is set dynamically: wider (120px) for label columns
    whose operators are long strings, narrower (60px) for others.
    """
    changed        = pyqtSignal()
    remove_clicked = pyqtSignal(object)

    OPS_LABEL   = ["is not empty", "is empty"]
    OPS_TYPING  = ["==", "!="]
    OPS_COUNT   = ["==", ">=", "<=", ">", "<"]
    OPS_NUMERIC = [">=", "<=", ">", "<", "=="]

    def __init__(self, columns, col_types, raw_df):
        super().__init__()
        self._col_types = col_types
        self._df        = raw_df

        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(4)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)

        self.col_combo = QComboBox()
        for cb in (self.col_combo,):
            cb.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
            cb.setMinimumContentsLength(4)
        self.col_combo.addItems(columns)
        row.addWidget(self.col_combo, stretch=3)

        self.op_combo = QComboBox()
        self.op_combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.op_combo.setMinimumContentsLength(2)
        row.addWidget(self.op_combo, stretch=1)

        # FIX: use setMaximumWidth instead of stretch=1
        self.val_stack = QStackedWidget()
        self.val_stack.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self.val_combo = QComboBox()
        self.val_combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.val_combo.setMinimumContentsLength(3)
        self.val_field = QLineEdit()
        self.val_field.setMinimumWidth(40)
        self.val_field.setPlaceholderText("value")
        self.val_stack.addWidget(self.val_combo)   # page 0 — categorical
        self.val_stack.addWidget(self.val_field)   # page 1 — numeric
        row.addWidget(self.val_stack, stretch=2)

        rm = QPushButton("×")
        rm.setFixedSize(22, 22)
        rm.setStyleSheet(RM_BTN_STYLE)
        rm.clicked.connect(lambda: self.remove_clicked.emit(self))
        row.addWidget(rm)

        self.col_combo.currentTextChanged.connect(self._on_col_changed)
        self.op_combo.currentTextChanged.connect(self.changed)
        self.val_combo.currentTextChanged.connect(self.changed)
        self.val_field.textChanged.connect(self.changed)

        if self.col_combo.count():
            self._on_col_changed(self.col_combo.currentText())

    def _on_col_changed(self, col):
        col_type = self._col_types.get(col, "numeric")

        # FIX: widen op_combo for label type (long operator strings)

        self.op_combo.blockSignals(True)
        self.op_combo.clear()
        if col_type == "label":
            self.op_combo.addItems(self.OPS_LABEL)
            self.val_stack.setCurrentIndex(0)
            self.val_combo.blockSignals(True)
            self.val_combo.clear()
            self.val_combo.blockSignals(False)
        elif col_type == "typing":
            self.op_combo.addItems(self.OPS_TYPING)
            self.val_stack.setCurrentIndex(0)
            self.val_combo.blockSignals(True)
            self.val_combo.clear()
            if self._df is not None and col in self._df.columns:
                vals = sorted(self._df[col].dropna().astype(str).unique().tolist())
                self.val_combo.addItems(vals)
            self.val_combo.blockSignals(False)
        elif col_type == "count":
            self.op_combo.addItems(self.OPS_COUNT)
            self.val_stack.setCurrentIndex(1)
            self.val_field.setPlaceholderText("integer")
        else:
            self.op_combo.addItems(self.OPS_NUMERIC)
            self.val_stack.setCurrentIndex(1)
            self.val_field.setPlaceholderText("number")
        self.op_combo.setMinimumContentsLength(11 if col_type == "label" else 2)   # "is not empty" must stay readable
        self.op_combo.blockSignals(False)
        self.changed.emit()

    def get_filter(self):
        col      = self.col_combo.currentText()
        op       = self.op_combo.currentText()
        col_type = self._col_types.get(col, "numeric")
        if col_type == "label":
            return (col, op, None, col_type)
        if col_type == "typing":
            val = self.val_combo.currentText()
            return (col, op, val, col_type) if val else None
        val = self.val_field.text().strip()
        return (col, op, val, col_type) if val else None


class DataTable(QFrame):
    def __init__(self):
        super().__init__()
        self.setObjectName("panel")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(6)

        self._status = QLabel("No data loaded")
        self._status.setObjectName("param_label")
        layout.addWidget(self._status)

        self._text = QTextEdit()
        self._text.setReadOnly(True)
        self._text.setStyleSheet(f"""
            QTextEdit {{
                background-color: {C['bg_widget']};
                border: 1px solid {C['border']};
                border-radius: 6px; color: {C['text']};
                font-family: 'Consolas','Courier New',monospace;
                font-size: 11px; padding: 6px;
            }}
            QScrollBar:vertical {{ width:5px; background:transparent; }}
            QScrollBar::handle:vertical {{ background:{C['border']}; border-radius:3px; }}
            QScrollBar:horizontal {{ height:5px; background:transparent; }}
            QScrollBar::handle:horizontal {{ background:{C['border']}; border-radius:3px; }}
        """)
        layout.addWidget(self._text)

    def show_df(self, df, max_rows=200):
        if df is None or df.empty:
            self._status.setText("No results")
            self._text.setHtml("")
            return
        shown = df.head(max_rows)
        total = len(df)
        self._status.setText(
            f"{total:,} rows · {len(df.columns)} columns"
            + (f" · showing first {max_rows}" if total > max_rows else "")
        )
        bg  = C['bg_widget']; hdr = C['bg_panel']
        txt = C['text'];      bdr = C['border']
        html = (f'<div style="overflow-x:auto;">'
                f'<table style="border-collapse:collapse;white-space:nowrap;'
                f'font-family:Consolas,monospace;font-size:11px;color:{txt};">')
        html += f'<tr style="background:{hdr};">'
        for col in shown.columns:
            html += (f'<th style="padding:4px 10px;border:1px solid {bdr};'
                     f'color:{C["accent"]};text-align:left;">{col}</th>')
        html += "</tr>"
        for i, (_, row) in enumerate(shown.iterrows()):
            row_bg = bg if i % 2 == 0 else hdr
            html += f'<tr style="background:{row_bg};">'
            for val in row:
                disp = "" if pd.isna(val) else str(val)
                html += (f'<td style="padding:3px 10px;border:1px solid {bdr};'
                         f'white-space:nowrap;">{disp}</td>')
            html += "</tr>"
        html += "</table></div>"
        self._text.setHtml(html)


class DataExplorer(QWidget):
    """
    Data Explorer tab.

    FIX — ffill on label columns:
    Label columns (*_labels) mark the start of a new cell's data.
    When cell N1 ends, its label column becomes NaN for the remaining
    spot rows of that section. Forward-filling would propagate the last
    N1 label into the N2 section, causing the "22 behind every N2 label"
    bug. Fix: we do NOT ffill label columns globally. Instead we ffill
    only typing and count columns, and we do it GROUP-WISE per cell,
    grouping on the first non-null label in each block.

    FIX — source_file shows folder name:
    os.path.dirname(p) gives the parent folder path;
    .split(os.sep)[-1] gives just the folder name (last component).
    """
    DATA_PREFIX = "data_"

    def __init__(self):
        super().__init__()
        self._raw_df    = None
        self._ffill_df  = None
        self._filtered  = None
        self._col_types = {}
        self._loaded_paths = []
        self._path_dfs  = {}          # path -> dataframe read from that Excel file (never read twice)
        self._cell_cols = set()       # columns that hold one value per cell (first row of the cell block)
        self._prop_df   = None

        main = QVBoxLayout(self)
        main.setContentsMargins(10, 10, 10, 10)
        main.setSpacing(8)

        # Top bar
        top = QHBoxLayout(); top.setSpacing(8)
        imp_btn = QPushButton("＋  Import folders / Excel files")
        imp_btn.setStyleSheet(f"""
            QPushButton {{
                background:{C['bg_widget']}; border:1px solid {C['accent']};
                border-radius:6px; color:{C['accent']};
                padding:5px 12px; font-weight:bold;
            }}
            QPushButton:hover {{ background:{C['accent']}22; }}
        """)
        imp_btn.clicked.connect(self._import_dialog)
        top.addWidget(imp_btn)
        self._status_lbl = QLabel("No data loaded")
        self._status_lbl.setObjectName("param_label")
        top.addWidget(self._status_lbl, stretch=1)
        self._group_btn = QPushButton("\U0001f50d  Detect groups")
        self._group_btn.setStyleSheet(f"""
            QPushButton {{ background:{C['bg_widget']}; border:1px solid {C['border']};
                border-radius:6px; color:{C['muted']}; padding:5px 10px; font-size:11px; }}
            QPushButton:hover {{ border-color:{C['accent']}; color:{C['accent']}; }}
        """)
        self._group_btn.clicked.connect(self._detect_groups)
        top.addWidget(self._group_btn)
        main.addLayout(top)

        # File list + remove button
        files_row = QHBoxLayout(); files_row.setSpacing(6)
        self._files_list = DroppableList(
            on_dropped=self._on_dropped,
            accepted_ext={".xlsx", ".xls", ""}
        )
        self._files_list.setMaximumHeight(90)
        files_row.addWidget(self._files_list, stretch=1)
        rm_btn = QPushButton("Remove\nselected")
        rm_btn.setFixedWidth(80)
        rm_btn.setStyleSheet(f"""
            QPushButton {{
                background:transparent; border:1px solid {C['border']};
                border-radius:5px; color:{C['muted']}; padding:4px; font-size:11px;
            }}
            QPushButton:hover {{ border-color:{C['error']}; color:{C['error']}; }}
        """)
        rm_btn.clicked.connect(self._remove_selected_file)
        files_row.addWidget(rm_btn)
        main.addLayout(files_row)

        # Splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(8)

        # Filter panel
        fp = QFrame(); fp.setObjectName("panel")
        fp_l = QVBoxLayout(fp)
        fp_l.setContentsMargins(10, 10, 10, 10)
        fp_l.setSpacing(6)
        fp_l.addWidget(titled_label("SOURCE FILE"))
        src_row = QHBoxLayout(); src_row.setSpacing(4)
        self._src_mode = QComboBox()
        self._src_mode.addItems(["All files", "Only", "All except"])
        self._src_mode.setFixedWidth(90)
        self._src_combo = QComboBox()
        self._src_combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self._src_combo.setMinimumContentsLength(8)
        self._src_combo.setEnabled(False)
        src_row.addWidget(self._src_mode)
        src_row.addWidget(self._src_combo, stretch=1)
        fp_l.addLayout(src_row)
        self._src_mode.currentTextChanged.connect(self._on_src_mode)
        self._src_combo.currentTextChanged.connect(lambda _t: self._apply_filters())
        fp_l.addWidget(titled_label("FILTERS  (AND)"))
        add_f = QPushButton("＋  Add filter")
        add_f.setStyleSheet(ADD_BTN_STYLE)
        add_f.clicked.connect(self._add_filter)
        fp_l.addWidget(add_f)
        self._filter_container = QWidget()
        self._filter_vlayout   = QVBoxLayout(self._filter_container)
        self._filter_vlayout.setContentsMargins(0, 0, 0, 0)
        self._filter_vlayout.setSpacing(4)
        self._filter_vlayout.addStretch()
        fscroll = QScrollArea()
        fscroll.setWidget(self._filter_container)
        fscroll.setWidgetResizable(True)
        fscroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        fp_l.addWidget(fscroll, stretch=1)
        splitter.addWidget(fp)

        # Results panel
        rp = QWidget()
        rp_l = QVBoxLayout(rp)
        rp_l.setContentsMargins(0, 0, 0, 0)
        rp_l.setSpacing(6)
        # Proportions close bar (hidden until proportions are shown)
        self._prop_bar = QWidget()
        prop_bar_l = QHBoxLayout(self._prop_bar)
        prop_bar_l.setContentsMargins(0, 0, 0, 0)
        prop_bar_l.setSpacing(6)
        self._prop_title_lbl = QLabel("Proportions")
        self._prop_title_lbl.setObjectName("param_label")
        prop_bar_l.addWidget(self._prop_title_lbl, stretch=1)
        self._prop_save_btn = QPushButton("\U0001f4be  Save")
        self._prop_save_btn.setStyleSheet(f"""
            QPushButton {{ background:{C['bg_widget']}; border:1px solid {C['border']};
                border-radius:5px; color:{C['text']}; padding:3px 8px; font-size:11px; }}
            QPushButton:hover {{ border-color:{C['accent']}; color:{C['accent']}; }}
        """)
        self._prop_save_btn.clicked.connect(self._save_proportions)
        prop_bar_l.addWidget(self._prop_save_btn)
        close_prop_btn = QPushButton("✕")
        close_prop_btn.setFixedSize(22, 22)
        close_prop_btn.setStyleSheet(f"""
            QPushButton {{ background:transparent; border:none; color:{C['muted']}; font-size:14px; }}
            QPushButton:hover {{ color:{C['error']}; }}
        """)
        close_prop_btn.clicked.connect(self._close_proportions)
        prop_bar_l.addWidget(close_prop_btn)
        self._prop_bar.setVisible(False)
        rp_l.addWidget(self._prop_bar)
        self._table = DataTable()
        rp_l.addWidget(self._table, stretch=1)

        bar = QHBoxLayout(); bar.setSpacing(6)
        bar.addWidget(small_label("Column:"))
        self._extract_combo = QComboBox()
        self._extract_combo.setMinimumWidth(160)
        bar.addWidget(self._extract_combo)

        def mk_btn(text, bg, hover, fg="white"):
            b = QPushButton(text)
            b.setStyleSheet(f"""
                QPushButton {{
                    background:{bg}; color:{fg}; border:1px solid {C['border']};
                    border-radius:5px; padding:5px 10px; font-weight:bold;
                }}
                QPushButton:hover {{ background:{hover}; }}
            """)
            return b

        self._export_btn = mk_btn("Export all", C['green'],   C['green_h'])
        self._prop_btn   = mk_btn("Proportions", C['accent'],  C['accent_h'])
        self._copy_btn   = mk_btn("Copy column", C['bg_widget'], C['bg_panel'], C['text'])
        self._means_btn  = mk_btn("Copy means by sample", C['bg_widget'], C['bg_panel'], C['text'])
        self._means_btn.setToolTip("Mean of the chosen column for each sample (source file), one value per line, "
                                   "in the order of the files. Per-cell columns count each cell once.")
        self._means_btn.clicked.connect(self._copy_means_by_sample)
        self._export_btn.clicked.connect(self._export_all)
        self._prop_btn.clicked.connect(self._show_proportions)
        self._copy_btn.clicked.connect(self._copy_column)
        for b in (self._export_btn, self._prop_btn, self._copy_btn, self._means_btn):
            bar.addWidget(b)
        bar.addStretch()
        rp_l.addLayout(bar)
        splitter.addWidget(rp)
        splitter.setSizes([360, 740])
        main.addWidget(splitter, stretch=1)

    # ---- Import ----

    def _import_dialog(self):
        from PyQt6.QtWidgets import QFileDialog
        folder = QFileDialog.getExistingDirectory(self, "Select folder")
        if folder:
            self._on_dropped([folder])

    def _on_dropped(self, paths):
        excel_paths = []
        for p in paths:
            if os.path.isdir(p):
                for root, dirs, files in os.walk(p):
                    for f in files:
                        if (f.startswith(self.DATA_PREFIX)
                                and f.endswith((".xlsx", ".xls"))
                                and not f.startswith("~")):
                            excel_paths.append(os.path.join(root, f))
            elif (os.path.basename(p).startswith(self.DATA_PREFIX)
                  and p.endswith((".xlsx", ".xls"))):
                excel_paths.append(p)
        new = [p for p in excel_paths if p not in self._loaded_paths]
        if new:
            self._load_excels(new)

    def _load_excels(self, paths):
        dfs = []; col_sets = []; errors = []
        for p in paths:
            try:
                if p not in self._path_dfs:
                    df = pd.read_excel(p)
                    # parent folder name = sample name
                    folder_name = os.path.basename(os.path.dirname(p))
                    df["source_file"] = folder_name
                    df["_cell_uid"] = self._cell_ids(df, p)
                    self._path_dfs[p] = df
                df = self._path_dfs[p]
                folder_name = df["source_file"].iloc[0] if len(df) else os.path.basename(os.path.dirname(p))
                dfs.append(df)
                col_sets.append(set(df.columns) - {"source_file", "_cell_uid"})
                self._loaded_paths.append(p)
                item = QListWidgetItem(f"✓  {folder_name} / {os.path.basename(p)}")
                item.setForeground(QColor(C["success"]))
                item.setData(Qt.ItemDataRole.UserRole, p)
                self._files_list.addItem(item)
            except Exception as e:
                errors.append(str(e))

        if not dfs:
            self._status_lbl.setText("No valid files" + (f": {errors[0]}" if errors else ""))
            return

        if len(col_sets) > 1:
            ref  = col_sets[0]
            diff = [s for s in col_sets[1:] if s != ref]
            if diff:
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.warning(
                    self, "Column mismatch",
                    "Some files have different columns.\n"
                    "Re-run analyses together with identical parameters\n"
                    "so column names are consistent across all folders."
                )

        all_dfs = [self._path_dfs[p] for p in self._loaded_paths]
        self._raw_df = pd.concat(all_dfs, ignore_index=True, join="outer")

        self._col_types = {
            col: detect_col_type(col, self._raw_df[col])
            for col in self._raw_df.columns if col != "_cell_uid"
        }
        self._find_cell_columns()

        # FIX — ffill only typing and count columns, never label columns.
        # Label columns mark cell identity boundaries and must stay NaN
        # between cell blocks. Forward-filling them would propagate a
        # label from one population (N1) into another population's rows (N2).
        #
        # For typing/count: ffill is safe because these values belong to
        # the cell identified by the label in the same row-block.
        self._ffill_df = self._raw_df.copy()
        safe_fill_cols = [c for c, t in self._col_types.items()
                          if t in ("typing", "count")]
        for col in safe_fill_cols:
            self._ffill_df[col] = self._ffill_df[col].ffill()

        current = self._extract_combo.currentText()
        self._extract_combo.clear()
        useful = [c for c, t in self._col_types.items()
                  if t in ("numeric", "count", "typing", "label")]
        self._extract_combo.addItems(useful)
        if current in useful:
            self._extract_combo.setCurrentText(current)

        cur_src = self._src_combo.currentText()
        self._src_combo.blockSignals(True)
        self._src_combo.clear()
        self._src_combo.addItems(list(dict.fromkeys(self._raw_df["source_file"].tolist())))
        if cur_src:
            self._src_combo.setCurrentText(cur_src)
        self._src_combo.blockSignals(False)

        n = len(self._loaded_paths)
        r = len(self._raw_df)
        self._status_lbl.setText(
            f"{n} file(s) · {r:,} rows · {len(self._raw_df.columns)} columns"
            + (f" · {len(errors)} error(s)" if errors else "")
        )
        self._apply_filters()

    def _remove_selected_file(self):
        selected = self._files_list.selectedItems()
        if not selected:
            return
        rows = [self._files_list.row(item) for item in selected]
        for item in selected:
            p = item.data(Qt.ItemDataRole.UserRole)
            if p in self._loaded_paths:
                self._loaded_paths.remove(p)
            self._path_dfs.pop(p, None)
            self._files_list.takeItem(self._files_list.row(item))

        if not self._loaded_paths:
            self._raw_df = None; self._ffill_df = None
            self._filtered = None; self._col_types = {}; self._cell_cols = set()
            self._src_combo.clear()
            self._table.show_df(None)
            self._status_lbl.setText("No data loaded")
            return

        # the next file is selected, so that pressing the button again removes it too
        self._files_list.setCurrentRow(min(min(rows), self._files_list.count() - 1))
        saved = list(self._loaded_paths)
        self._loaded_paths = []
        self._raw_df = None
        self._files_list.blockSignals(True)
        keep_row = self._files_list.currentRow()
        self._files_list.clear()
        self._load_excels(saved)
        self._files_list.blockSignals(False)
        self._files_list.setCurrentRow(min(keep_row, self._files_list.count() - 1))

    # ---- Cells ----

    def _cell_ids(self, df, path):
        """One identifier per cell block of an Excel file: (file, number of the block).
        A block starts at each row where a cell label column (a *_labels column that has no *_number/cell
        companion, i.e. not a spot label column) is filled. The cell number alone is NOT unique across files."""
        cols = list(df.columns)
        spot_label_cols = {c[:-len("_number/cell")] + "_labels" for c in cols if c.endswith("_number/cell")}
        cell_label_cols = [c for c in cols if c.endswith("_labels") and c not in spot_label_cols]
        if not cell_label_cols:                          # unknown layout: every row is its own cell
            start = pd.Series(True, index=df.index)
        else:
            start = df[cell_label_cols].notna().any(axis=1)
            if len(start):
                start.iloc[0] = True
        block = start.cumsum()
        return [f"{path}|{b}" for b in block]

    def _find_cell_columns(self):
        """Columns with one value per cell: filled only on the first row of the cell block (other rows empty)."""
        df = self._raw_df
        self._cell_cols = {"source_file", "group"}
        if df is None or "_cell_uid" not in df.columns:
            return
        first = ~df["_cell_uid"].duplicated()
        for c in df.columns:
            if c in ("source_file", "_cell_uid"):
                continue
            if df.loc[~first, c].isna().all() and df.loc[first, c].notna().any():
                self._cell_cols.add(c)

    def _one_per_unit(self, df, col):
        """Values of one column without double counting: once per cell for a per-cell column, once per
        spot (non-empty row) for a per-spot column."""
        if col in self._cell_cols and "_cell_uid" in df.columns:
            df = df.drop_duplicates(subset="_cell_uid")
        return df[col].dropna()

    def _on_src_mode(self, mode):
        self._src_combo.setEnabled(mode != "All files")
        self._apply_filters()

    # ---- Filters ----

    def _add_filter(self):
        if self._raw_df is None:
            return
        cols = [c for c in self._raw_df.columns if c not in ("source_file", "_cell_uid")]
        row  = FilterRow(cols, self._col_types, self._ffill_df)
        row.changed.connect(self._apply_filters)
        row.remove_clicked.connect(self._remove_filter)
        idx = self._filter_vlayout.count() - 1
        self._filter_vlayout.insertWidget(idx, row)
        self._apply_filters()

    def _remove_filter(self, w):
        w.setParent(None)
        self._apply_filters()

    def _collect_filters(self):
        active = []
        for i in range(self._filter_vlayout.count()):
            item = self._filter_vlayout.itemAt(i)
            w    = item.widget() if item else None
            if isinstance(w, FilterRow):
                f = w.get_filter()
                if f:
                    active.append(f)
        return active

    def _apply_filters(self):
        if self._ffill_df is None:
            return
        df = self._ffill_df.copy()

        mode = self._src_mode.currentText()
        src = self._src_combo.currentText()
        if mode != "All files" and src:
            df = df[df["source_file"] == src] if mode == "Only" else df[df["source_file"] != src]

        for col, op, val, col_type in self._collect_filters():
            if col not in df.columns:
                continue
            try:
                if col_type == "label":
                    if op == "is not empty":
                        df = df[df[col].notna() & (df[col].astype(str).str.strip() != "nan")]
                    else:
                        df = df[df[col].isna() | (df[col].astype(str).str.strip() == "nan")]
                elif col_type == "typing":
                    mask = df[col].astype(str) == str(val)
                    df   = df[mask if op == "==" else ~mask]
                else:
                    num = float(val)
                    ops_map = {"==": df[col]==num, "!=": df[col]!=num,
                               ">=": df[col]>=num, "<=": df[col]<=num,
                               ">":  df[col]>num,  "<":  df[col]<num}
                    if op in ops_map:
                        df = df[ops_map[op]]
            except (ValueError, TypeError):
                pass

        self._filtered = df
        self._table.show_df(df.drop(columns=["_cell_uid"], errors="ignore"))

    # ---- Export / proportions ----

    def _export_all(self):
        if self._filtered is None or self._filtered.empty:
            return
        from PyQt6.QtWidgets import QFileDialog
        path, _ = QFileDialog.getSaveFileName(
            self, "Export to Excel", "export.xlsx", "Excel (*.xlsx)")
        if path:
            self._filtered.drop(columns=["_cell_uid"], errors="ignore").to_excel(path, index=False, engine="openpyxl")

    def _show_proportions(self):
        if self._filtered is None or self._filtered.empty:
            return
        col = self._extract_combo.currentText()
        if col not in self._filtered.columns:
            return
        col_type = self._col_types.get(col, "numeric")
        series   = self._one_per_unit(self._filtered, col)
        unit     = "cells" if col in self._cell_cols else "spots"
        if col_type in ("count", "numeric") and series.nunique() > 10:
            try:
                counts = pd.cut(series, bins=5).value_counts().sort_index()
            except Exception:
                counts = series.value_counts().sort_index()
        else:
            counts = series.value_counts()
        # Sort by value ascending — try numeric sort first, fall back to string sort
        try:
            order = pd.to_numeric(counts.index.astype(str), errors="raise")
            counts = counts.iloc[order.argsort()]
        except (ValueError, TypeError):
            counts = counts.sort_index(key=lambda x: x.astype(str))
        total = counts.sum()
        self._prop_df = pd.DataFrame({
            "value":      counts.index.astype(str),
            "count":      counts.values,
            "proportion": [f"{v:.2f} %" for v in counts.values / total * 100],
        })
        self._table.show_df(self._prop_df)
        self._prop_title_lbl.setText(
            f"Proportions of '{col}'  ·  {total:,} {unit}  ·  {len(self._prop_df)} categories"
        )
        self._prop_bar.setVisible(True)
        self._status_lbl.setText(
            f"Proportions of '{col}' · {total:,} {unit} · {len(self._prop_df)} categories"
        )

    def _save_proportions(self):
        if self._prop_df is None:
            return
        from PyQt6.QtWidgets import QFileDialog
        col = self._extract_combo.currentText()
        path, _ = QFileDialog.getSaveFileName(
            self, "Save proportions", f"proportions_{col}.xlsx", "Excel (*.xlsx)")
        if path:
            self._prop_df.to_excel(path, index=False, engine="openpyxl")

    def _close_proportions(self):
        self._prop_bar.setVisible(False)
        self._prop_df = None
        self._table.show_df(self._filtered.drop(columns=["_cell_uid"], errors="ignore"))
        n = len(self._loaded_paths)
        r = len(self._raw_df) if self._raw_df is not None else 0
        cols = len(self._raw_df.columns) if self._raw_df is not None else 0
        self._status_lbl.setText(f"{n} file(s) · {r:,} rows · {cols} columns")

    def _detect_groups(self):
        """
        Analyse folder names loaded in source_file column.

        Strategy: split names only on '_' (not on '-') so that tokens like
        'E-L3' and 'L-L3' are preserved as whole tokens.  A token is
        "discriminating" if it appears in at least one name but not in all
        of them, meaning it distinguishes at least one group from the rest.

        The dialog lets the user pick a token and immediately previews which
        folders map to which group label.  On confirm a 'group' column is
        added to the dataframe.
        """
        if self._raw_df is None or "source_file" not in self._raw_df.columns:
            return
        names = self._raw_df["source_file"].dropna().unique().tolist()
        if len(names) < 2:
            return

        from collections import Counter

        # Split on '_' only — preserves hyphenated tokens like 'E-L3'
        def tokenise(s):
            return [t for t in str(s).split("_") if t]

        all_tokens_flat = [t for n in names for t in tokenise(n)]
        token_counts = Counter(all_tokens_flat)
        total_names = len(names)

        # Discriminating = present in some but not all folders, length >= 2
        discriminating = sorted(
            {t for t, c in token_counts.items() if 1 <= c < total_names and len(t) >= 2},
            key=lambda t: (-token_counts[t], t)
        )

        if not discriminating:
            QMessageBox.information(
                self, "Detect groups",
                "No discriminating tokens found between folder names.\n"
                "Folder names are either identical or share no '_'-delimited token\n"
                "that is exclusive to a subset of folders."
            )
            return

        from PyQt6.QtWidgets import QDialog, QDialogButtonBox, QListWidget, QLabel as QL
        dlg = QDialog(self)
        dlg.setWindowTitle("Detect groups")
        dlg.setMinimumWidth(460)
        dlg_l = QVBoxLayout(dlg)
        dlg_l.addWidget(QL(
            "Select the token that distinguishes groups.\n"
            "Folders containing it → group A; others → group B."
        ))
        lst = QListWidget()
        for t in discriminating[:30]:
            fw  = sum(1 for n in names if t in tokenise(n))
            fnw = total_names - fw
            lst.addItem(f"{t}   ({fw} with / {fnw} without)")
        lst.setCurrentRow(0)
        dlg_l.addWidget(lst)

        preview_lbl = QL("")
        preview_lbl.setWordWrap(True)
        preview_lbl.setObjectName("param_label")
        dlg_l.addWidget(preview_lbl)

        def update_preview():
            row = lst.currentRow()
            if row < 0 or row >= len(discriminating):
                return
            tok = discriminating[row]
            lines = []
            for n in names:
                grp = tok if tok in tokenise(n) else f"not {tok}"
                lines.append(f"  {n}  →  {grp}")
            preview_lbl.setText("Preview:\n" + "\n".join(lines))

        lst.currentRowChanged.connect(update_preview)
        update_preview()

        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(dlg.accept)
        btns.rejected.connect(dlg.reject)
        dlg_l.addWidget(btns)

        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        row = lst.currentRow()
        if row < 0 or row >= len(discriminating):
            return
        token = discriminating[row]

        def assign_group(src):
            return token if token in tokenise(str(src)) else f"not {token}"

        self._raw_df["group"]   = self._raw_df["source_file"].apply(assign_group)
        self._ffill_df["group"] = self._ffill_df["source_file"].apply(assign_group)
        self._col_types["group"] = "typing"
        self._cell_cols.add("group")

        current = self._extract_combo.currentText()
        self._extract_combo.clear()
        useful = [c for c, t in self._col_types.items()
                  if t in ("numeric", "count", "typing", "label")]
        self._extract_combo.addItems(useful)
        if current in useful:
            self._extract_combo.setCurrentText(current)
        self._apply_filters()
        n_a = sum(1 for n in names if token in tokenise(n))
        n_b = total_names - n_a
        self._status_lbl.setText(
            self._status_lbl.text() + f"  ·  group: '{token}' ({n_a}) vs 'not {token}' ({n_b})"
        )

    def _copy_column(self):
        if self._filtered is None or self._filtered.empty:
            return
        col = self._extract_combo.currentText()
        if col not in self._filtered.columns:
            return
        # Separate replicates by a blank line
        lines = []
        if "source_file" in self._filtered.columns:
            for _src, grp in self._filtered.groupby("source_file", sort=False):
                lines.extend(str(v) for v in self._one_per_unit(grp, col).tolist())
                lines.append("")
            if lines and lines[-1] == "":
                lines.pop()
        else:
            lines = [str(v) for v in self._filtered[col].dropna().tolist()]
        QApplication.clipboard().setText("\n".join(lines))


    def _copy_means_by_sample(self):
        """Mean of the chosen column for each sample (source file), one per line, in the order of the files."""
        if self._filtered is None or self._filtered.empty:
            return
        col = self._extract_combo.currentText()
        if col not in self._filtered.columns:
            return
        vals = []
        for src, grp in self._filtered.groupby("source_file", sort=False):
            series = pd.to_numeric(self._one_per_unit(grp, col), errors="coerce").dropna()
            vals.append((src, float(series.mean()) if len(series) else float("nan"), len(series)))
        if not vals or all(np.isnan(v[1]) for v in vals):
            self._status_lbl.setText(f"'{col}' has no numeric values")
            return
        QApplication.clipboard().setText("\n".join("" if np.isnan(m) else f"{m:.6g}" for _s, m, _n in vals))
        self._status_lbl.setText(f"Means of '{col}' copied ({len(vals)} samples): "
                                 + " · ".join(f"{s}: {m:.4g} (n={n})" for s, m, n in vals))


# ==============================================================================
# VIEWER TAB
# ==============================================================================

EXCLUDED_PREFIXES = ("masks", "chinmo_threshold", "composite_", "detected",
                     "merge_threshold", "merge", "shrinked")

CHANNEL_COLORS = ["#00FFFF", "#FFFF00", "#00FF00", "#FF00FF", "#FFA500", "#FF0000",
                  "#FF69B4", "#00CED1", "#ADFF2F", "#FF4500"]

def is_base_tif(filename):
    name = os.path.basename(filename).lower()
    return name.endswith((".tif", ".tiff")) and not any(name.startswith(p) for p in EXCLUDED_PREFIXES)

def find_folder_files(folder):
    files = os.listdir(folder)
    composite = next((f for f in files if f.startswith("composite_") and f.endswith((".tif", ".tiff"))), None)
    base = next((f for f in files if is_base_tif(f)), None)
    data = next((f for f in files if f.startswith("data_") and f.endswith((".xlsx", ".xls"))), None)
    return (
        os.path.join(folder, composite) if composite else None,
        os.path.join(folder, base) if base else None,
        os.path.join(folder, data) if data else None,
    )


class FastImageView(QGraphicsView):
    """Image display of the viewer. Zoom = mouse wheel (around the cursor), pan = drag, click = pick a pixel.
    Only the part of the image that is visible (plus a margin) is computed, at the resolution of the screen:
    the cost of a redraw depends on the size of the window, not on the size of the image.
    provider(x0, y0, x1, y1, step) -> (base_rgba or None, comp_rgba or None): uint8 (h, w, 4) arrays of the
    region [y0:y1:step, x0:x1:step]."""
    clicked = pyqtSignal(int, int)
    step_z = pyqtSignal(int)
    zoom_key = pyqtSignal()

    def __init__(self):
        super().__init__()
        # folders dropped on the image are handled by the tab that contains this view
        self.setAcceptDrops(False)
        self.viewport().setAcceptDrops(False)
        self._busy = QLabel("", self)
        self._busy.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._busy.setStyleSheet(f"background-color: rgba(20,22,30,200); color: {C['text']}; font-size: 18px;")
        self._busy.hide()
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)
        self._items = []
        for z in (0, 1):
            it = QGraphicsPixmapItem()
            it.setTransformationMode(Qt.TransformationMode.FastTransformation)   # no smoothing: true pixels
            it.setZValue(z)
            self._scene.addItem(it)
            self._items.append(it)
        self._keep = [None, None]                          # numpy buffers behind the pixmaps
        self._provider = None
        self.setBackgroundBrush(QColor(C["bg_main"]))
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._press = None
        self._size = None                                  # (H, W) of the image
        self._fitted = False
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(12)
        self._timer.timeout.connect(self._render)
        self.horizontalScrollBar().valueChanged.connect(self.request_render)
        self.verticalScrollBar().valueChanged.connect(self.request_render)

    def show_busy(self, text):
        """Message over the image (loading, compiling); the interface stays responsive."""
        self._busy.setText(text)
        self._busy.setGeometry(self.rect())
        self._busy.raise_()
        self._busy.show()
        QApplication.processEvents()

    def hide_busy(self):
        self._busy.hide()

    def zoom_to(self, x, y, scale):
        """Absolute zoom (screen pixels per image pixel) centred on (x, y); near an edge the view stops at the edge."""
        if self._size is None:
            return
        self.resetTransform()
        self.scale(scale, scale)
        self._fitted = False
        self.centerOn(QPointF(x, y))
        self.request_render()

    def set_source(self, shape, provider):
        """New image (shape (H, W)) or None; the view is fitted when the shape changes."""
        self._provider = provider
        if shape is None:
            self._size = None
            for it in self._items:
                it.setVisible(False)
            return
        if shape != self._size:
            self._size = shape
            self._scene.setSceneRect(0, 0, shape[1], shape[0])
            self.fit()
        self.request_render()

    def request_render(self, *_a):
        """Redraw soon; several requests within a few ms give one redraw."""
        self._timer.start()

    def render_now(self):
        self._timer.stop()
        self._render()

    def _render(self):
        if self._size is None or self._provider is None:
            return
        H, W = self._size
        vis = self.mapToScene(self.viewport().rect()).boundingRect()
        mx, my = vis.width() * 0.1, vis.height() * 0.1
        scale = max(self.transform().m11(), 1e-6)
        step = max(1, int(round(1.0 / scale)))
        x0 = max(0, int(vis.left() - mx)); y0 = max(0, int(vis.top() - my))
        x1 = min(W, int(np.ceil(vis.right() + mx))); y1 = min(H, int(np.ceil(vis.bottom() + my)))
        x0 -= x0 % step; y0 -= y0 % step
        if x1 <= x0 or y1 <= y0:
            return
        layers = self._provider(x0, y0, x1, y1, step)
        for k, (item, arr) in enumerate(zip(self._items, layers)):
            if arr is None:
                item.setVisible(False)
                self._keep[k] = None
                continue
            arr = np.ascontiguousarray(arr)
            h, w = arr.shape[:2]
            img = QImage(arr.data, w, h, 4 * w, QImage.Format.Format_RGBA8888)
            item.setPixmap(QPixmap.fromImage(img))
            self._keep[k] = arr
            item.setPos(x0, y0)
            item.setScale(step)
            item.setVisible(True)

    def fit(self):
        if self._size is None:
            return
        self.resetTransform()
        self.fitInView(self._scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)
        self._fitted = True
        self.request_render()

    def actual_size(self):
        self.resetTransform()
        self._fitted = False
        self.request_render()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._busy.isVisible():
            self._busy.setGeometry(self.rect())
        if self._fitted:
            self.fit()
        else:
            self.request_render()

    def wheelEvent(self, event):
        if self._size is None:
            return
        factor = 1.25 if event.angleDelta().y() > 0 else 0.8
        current = self.transform().m11()
        if (factor > 1 and current > 60) or (factor < 1 and current < 0.02):
            return
        self.scale(factor, factor)
        self._fitted = False
        self.request_render()

    def mousePressEvent(self, event):
        self._press = event.position() if event.button() == Qt.MouseButton.LeftButton else None
        self.setFocus()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        if self._press is not None and event.button() == Qt.MouseButton.LeftButton:
            moved = (event.position() - self._press).manhattanLength()
            if moved < 4 and self._size is not None:
                pt = self.mapToScene(event.position().toPoint())
                x, y = int(np.floor(pt.x())), int(np.floor(pt.y()))
                if 0 <= x < self._size[1] and 0 <= y < self._size[0]:
                    self.clicked.emit(x, y)
        self._press = None

    def mouseDoubleClickEvent(self, event):
        self.fit()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Right:
            self.step_z.emit(1)
        elif event.key() == Qt.Key.Key_Left:
            self.step_z.emit(-1)
        elif event.key() == Qt.Key.Key_Z:
            self.zoom_key.emit()
        else:
            super().keyPressEvent(event)


class FolderLoader(QThread):
    """Reads the files of an analysis folder in the background (the window stays responsive)."""
    loaded = pyqtSignal(object)

    def __init__(self, folder, token):
        super().__init__()
        self.folder, self.token = folder, token

    def run(self):
        out = {"folder": self.folder, "token": self.token, "errors": []}
        composite_path, base_path, data_path = find_folder_files(self.folder)
        import tifffile
        out["composite"] = out["base"] = out["data"] = out["meas"] = None
        out["data_path"] = data_path
        out["meas_path"] = None
        if composite_path:
            try:
                arr = tifffile.imread(composite_path)
                if arr.ndim == 2:
                    arr = arr[np.newaxis, np.newaxis]
                elif arr.ndim == 3:
                    arr = arr[:, np.newaxis, :, :]          # (Z, Y, X) -> (Z, 1, Y, X)
                out["composite"] = arr                      # native type (uint16 most of the time): 4x less memory
            except Exception as e:
                out["errors"].append(f"Could not load composite:\n{e}")
        if base_path:
            try:
                out["base"] = tifffile.imread(base_path)
            except Exception as e:
                out["errors"].append(f"Could not load base image:\n{e}")
        if data_path:
            try:
                out["data"] = pd.read_excel(data_path, engine="openpyxl")
            except Exception as e:
                out["errors"].append(f"Could not load data file:\n{e}")
        out["meas_all"] = {}
        for mf in sorted(_glob.glob(os.path.join(self.folder, "*intensity-measurements.xlsx"))):
            m = re.search(r"-(\d+)intensity-measurements\.xlsx$", mf)
            try:
                if m:
                    out["meas_all"][int(m.group(1))] = pd.read_excel(mf, engine="openpyxl")
            except Exception:
                pass
        meas_files = _glob.glob(os.path.join(self.folder, "*intensity-measurements.xlsx"))
        if meas_files:
            try:
                out["meas"] = pd.read_excel(meas_files[0], engine="openpyxl")
                out["meas_path"] = meas_files[0]
            except Exception as e:
                out["errors"].append(f"Could not load intensity measurements:\n{e}")
        self.loaded.emit(out)


VIEWER_DIR = os.path.join(os.path.expanduser("~"), ".pipeline_viewer")     # pending changes and backups (not in the analysis folders)
HALO_ITERATIONS_DEFAULT, HALO_VALUE_DEFAULT = 15, 7                           # as in Newmain.py (composite)


def journal_files(folder):
    """(journal file, backup folder) of an analysis folder; they live in the home directory of the user."""
    import hashlib
    key = hashlib.sha1(os.path.abspath(folder).encode("utf-8")).hexdigest()[:16]
    return os.path.join(VIEWER_DIR, "journals", key + ".json"), os.path.join(VIEWER_DIR, "backups", key)


def _label_text(v):
    """Typing value as text, '1.0' -> '1' (Excel turns numbers into floats)."""
    if isinstance(v, float) and v == int(v):
        return str(int(v))
    return str(v).strip()


def add_halos(target, mask, cell_labels, iterations, value):
    """Halo of each cell (in the plane of each slice), inside its bounding box only. Same drawing as Newmain.py."""
    from scipy import ndimage
    from scipy.ndimage import binary_dilation, generate_binary_structure
    struct = generate_binary_structure(2, 1)[np.newaxis, :, :]
    boxes = ndimage.find_objects(mask.astype(np.int32))
    height, width = mask.shape[1:]
    for label in cell_labels:
        box = boxes[label - 1] if 0 < label <= len(boxes) else None
        if box is None:
            continue
        zs, ys, xs = box
        ys = slice(max(ys.start - iterations, 0), min(ys.stop + iterations, height))
        xs = slice(max(xs.start - iterations, 0), min(xs.stop + iterations, width))
        cell = mask[zs, ys, xs] == label
        halo = binary_dilation(cell, structure=struct, iterations=iterations) & ~cell
        target[zs, ys, xs][halo] = value


def rebuild_composite(path, ops, df, seg_cols, typing_cols, spot_cols, record):
    """
    Applies the changes of the viewer to the composite file: spots validated / invalidated (moved between the
    'invalid' and 'valid' channels of the probe) and halos of the cell-type markers whose type was changed.
    Mirrors the construction of the composite in Newmain.py (channels: cells | halos | invalid, valid spots).
    Returns a list of warnings.
    """
    import tifffile
    warnings = []
    comp = tifffile.imread(path)
    if comp.ndim != 4:
        raise ValueError(f"The composite has {comp.ndim} dimensions, (Z, C, Y, X) expected.")
    n_ch = comp.shape[1]
    n_seg = len(seg_cols)
    n_probes = max(1, len(spot_cols))
    inv_idx, val_idx = n_ch - 2 * n_probes, n_ch - 2 * n_probes + 1

    final = {}
    for op in ops:
        if op["op"] == "valid":
            final[int(op["spot"])] = bool(op["valid"])
    if final and inv_idx >= 0:
        inv, val = comp[:, inv_idx], comp[:, val_idx]
        top = int(max(inv.max(), val.max()))
        to_valid = np.zeros(top + 1, bool)
        to_invalid = np.zeros(top + 1, bool)
        for spot, valid in final.items():
            if spot <= top:
                (to_valid if valid else to_invalid)[spot] = True
        m = to_valid[inv.astype(np.int64)]
        val[m] = inv[m]
        inv[m] = 0
        m = to_invalid[val.astype(np.int64)]
        inv[m] = val[m]
        val[m] = 0

    iterations = (record.get("halo") or {}).get("iterations", HALO_ITERATIONS_DEFAULT)
    value = (record.get("halo") or {}).get("value", HALO_VALUE_DEFAULT)
    for col in sorted({op["col"] for op in ops if op["op"] == "type"}):
        if col not in typing_cols:
            continue
        marker = col[:-len("_typing")]
        halo_idx = n_seg + typing_cols.index(col)
        if halo_idx >= n_ch - 2 * n_probes:
            warnings.append(f"No halo channel found for {marker}.")
            continue
        # populations of this marker = those whose cells have a type
        pops = []
        for k, sc in enumerate(seg_cols):
            rows = df[df[sc].notna()]
            if len(rows) and rows[col].notna().any():
                pops.append((k, sc))
        info = (record.get("cell_types") or {}).get(marker)
        group2 = _label_text(info["group2"]) if info else None
        if group2 is None:                      # old analysis: find the type that has a halo in the composite
            best, score = None, 0.0
            for t in sorted({_label_text(v) for v in df[col].dropna()}):
                hits = total = 0
                for k, sc in pops:
                    rows = df[df[sc].notna() & df[col].apply(lambda v: _label_text(v) == t if pd.notna(v) else False)]
                    for lab in rows[sc].astype(int).tolist()[:20]:
                        mask = comp[:, k] == lab
                        if not mask.any():
                            continue
                        zs, ys, xs = [np.flatnonzero(mask.any(axis=ax)) for ax in ((1, 2), (0, 2), (0, 1))]
                        sub = (slice(zs[0], zs[-1] + 1), slice(max(ys[0] - 2, 0), ys[-1] + 3), slice(max(xs[0] - 2, 0), xs[-1] + 3))
                        total += 1
                        hits += bool(((comp[:, halo_idx][sub] == value) & (comp[:, k][sub] != lab)).any())
                if total and hits / total > score:
                    best, score = t, hits / total
            if best is None or score < 0.5:
                warnings.append(f"The type with a halo could not be found for {marker}: its halo was not redrawn.")
                continue
            group2 = best
        halo = np.zeros(comp.shape[:1] + comp.shape[2:], dtype=comp.dtype)
        for k, sc in pops:
            rows = df[df[sc].notna() & df[col].notna()]
            cells = [int(lab) for lab, t in zip(rows[sc], rows[col]) if _label_text(t) == group2]
            add_halos(halo, comp[:, k], cells, iterations, value)
        comp[:, halo_idx] = halo

    tmp = path + ".tmp"
    import tif_meta                                    # keep Info / pixel size / z step of the composite
    tifffile.imwrite(tmp, comp, imagej=True, **tif_meta.parent_kwargs(path, axes="ZCYX"))
    os.replace(tmp, path)
    return warnings


def _blank(v):
    return v is None or (isinstance(v, float) and np.isnan(v)) or (isinstance(v, str) and v.strip() == "")


def recompute_table(df, meas_by_prefix, record, seg_cols, typ_cols, spot_cols):
    """
    Recomputes, for every spot of the data table, the values that depend on the spot itself and on the other spots:
      - raw values (Sum, Max, Volume, Mean) from the intensity measurements file;
      - BgSub_*, bg_value and the absolute count (BgSub_Sum / intensity of one molecule);
      - Normalized_*: the mean of the reference spots is recomputed with the CURRENT cell types and spot cells
        (the reference = spots of the cells of the chosen type / population, as in Newmain.py), then every
        normalised value is redone, including those of spots that were not touched;
      - the number of spots of every cell.
    meas_by_prefix: {probe name: intensity measurements DataFrame}. Same rules and rounding as Newmain.py.
    Returns (df, warnings).
    """
    warnings = []
    df = df.copy()
    if not spot_cols:
        return df, warnings
    n = len(df)
    # cell blocks: a row where a cell label is written starts a block
    pop_cols = [c for c in seg_cols if "spot" not in c.lower()]
    start = np.zeros(n, dtype=bool)
    for c in pop_cols:
        if c in df.columns:
            start |= ~df[c].map(_blank).to_numpy()
    block = np.cumsum(start) - 1                                   # -1 before the first cell
    cell_of_row = {}                                               # row -> (population, cell label) of its block
    block_cell = {}
    for c in pop_cols:
        if c not in df.columns:
            continue
        for r in np.flatnonzero(~df[c].map(_blank).to_numpy()):
            block_cell[int(block[r])] = (c[:-len("_labels")], int(float(df[c].iloc[r])))
    cell_of_row = {r: block_cell.get(int(block[r])) for r in range(n)}
    start_rows = {bc: r for r, bc in ((int(r), cell_of_row[int(r)]) for r in np.flatnonzero(start)) if bc}

    rel = record.get("relative_comparison", {}) or {}
    against = str(rel.get("norm_against", ""))
    do_norm = against in ("Only...", "All except...")
    norm_3d = bool(rel.get("norm_3d"))
    norm_pop, norm_type = rel.get("population", "") or "", rel.get("cell_type", "") or ""
    abs_q = record.get("absolute_quantification", {}) or {}
    unit = abs_q.get("unit")
    one_molecule = abs_q.get("intensity_of_one_molecule") or {}
    channels_of = record.get("probe_channels", {}) or {}

    # type of every cell (current values of the table)
    cell_type = {}
    if do_norm and norm_type:
        marker = next((m for m, g in (record.get("cell_types") or {}).items()
                       if norm_type in (g.get("group1"), g.get("group2"))), None)
        col = f"{marker}_typing" if marker else None
        if col is None or col not in df.columns:
            warnings.append("The cell type used for the normalisation was not found in the table: normalised values "
                            "were not recomputed.")
            do_norm = False
        else:
            for bc, r in start_rows.items():
                v = df[col].iloc[r]
                cell_type[bc] = "" if _blank(v) else _label_text(v)

    for sc in spot_cols:
        pfx = sc[:-len("_labels")]
        meas = meas_by_prefix.get(pfx)
        label_rows = np.flatnonzero(~df[sc].map(_blank).to_numpy())
        # number of spots of every cell
        ncol = f"{pfx}_number/cell"
        if ncol in df.columns:
            counts = {}
            for r in label_rows:
                counts[int(block[r])] = counts.get(int(block[r]), 0) + 1
            df[ncol] = df[ncol].astype(object)
            for bc, r in start_rows.items():
                df.iloc[r, df.columns.get_loc(ncol)] = counts.get(int(block[r]), 0)
        if meas is None or not len(label_rows):
            if meas is None:
                warnings.append(f"No intensity measurements found for {pfx}: its values were not recomputed.")
            continue
        m = meas.set_index("Label")
        has_bg = {"Background", "NumberOfVoxels"} <= set(m.columns)
        if not has_bg:
            warnings.append(f"The intensity measurements of {pfx} have no background columns (analysis made with an "
                            "older version): run the analysis again to complete it. Raw values only were recomputed.")
        labels = df[sc].iloc[label_rows].astype(float).astype(int).to_numpy()
        def put(column, values):
            if column in df.columns:
                df[column] = df[column].astype(object)
                df.iloc[label_rows, df.columns.get_loc(column)] = values
        lab_ok = np.isin(labels, m.index.to_numpy())
        if not lab_ok.all():
            warnings.append(f"{pfx}: some spot labels are not in the measurements file; they were left unchanged.")
        sel = label_rows[lab_ok]
        labels = labels[lab_ok]
        label_rows = sel
        mm = m.loc[labels]
        put(f"{pfx}_Sum_intensity", np.round(mm["Sum"].to_numpy(float), 2))
        put(f"{pfx}_Max_intensity", np.round(mm["Max"].to_numpy(float), 2))
        put(f"{pfx}_Volume", np.round(mm["Volume"].to_numpy(float), 2))
        put(f"{pfx}_Mean_intensity", np.round(mm["Mean"].to_numpy(float), 2))
        if not has_bg:
            continue
        b = mm["Background"].to_numpy(float)
        bg_sum = mm["Sum"].to_numpy(float) - mm["NumberOfVoxels"].to_numpy(float) * b
        put(f"{pfx}_BgSub_Mean_intensity", np.round(mm["Mean"].to_numpy(float) - b, 2))
        put(f"{pfx}_BgSub_Sum_intensity", np.round(bg_sum, 2))
        put(f"{pfx}_bg_value", np.round(b, 3))
        I1 = one_molecule.get(pfx)
        if unit and I1:
            put(f"{pfx}_{unit}_count", np.round(bg_sum / float(I1), 2))
        # relative comparison
        if do_norm and f"{pfx}_Normalized_Sum_intensity" in df.columns:
            num = int(m.index.max())
            idx = lambda arr: np.asarray(arr, dtype=float)
            full = m.reindex(np.arange(1, num + 1))
            mean_n = idx(full["Mean"]) - idx(full["Background"])
            sum_n = idx(full["Sum"]) - idx(full["NumberOfVoxels"]) * idx(full["Background"])
            z, zmin, zmax = idx(full["CenterOfMass.Z"]), idx(full["ZMin"]), idx(full["ZMax"])
            parents = {}
            for lab, txt in zip(full.index, full["ParentCells"].fillna("").astype(str)):
                parents[int(lab)] = [(a.rsplit(":", 1)[0], int(float(a.rsplit(":", 1)[1]))) for a in txt.split(";") if ":" in a]
            for r in label_rows:                               # spots in the table: where they are NOW
                parents[int(float(df[sc].iloc[r]))] = []
            for r in label_rows:
                bc = cell_of_row.get(int(r))
                if bc:
                    parents[int(float(df[sc].iloc[r]))].append(bc)

            def is_target(plist):
                for pop, cell in plist:
                    if norm_pop not in ("", "All cells") and pop != norm_pop:
                        continue
                    if norm_type and cell_type.get((pop, cell)) != norm_type:
                        continue
                    return True
                return False
            target = np.array([is_target(parents.get(i, [])) for i in range(1, num + 1)])
            is_ref = target if against == "Only..." else ~target
            out_sum, out_mean = [], []
            for lab in labels:
                i = int(lab) - 1
                ref = is_ref.copy()
                ref[i] = False
                if norm_3d:
                    with np.errstate(invalid="ignore"):
                        gap = np.maximum(np.maximum(zmin[i] - z, z - zmax[i]), 0.0)
                    gap = np.where(ref & ~np.isnan(z), gap, np.inf)
                    nearest = gap.min()
                    chosen = gap <= np.ceil(nearest * 2) / 2 if np.isfinite(nearest) else np.zeros(num, dtype=bool)
                else:
                    chosen = ref
                if not chosen.any():
                    out_mean.append(np.nan); out_sum.append(np.nan); continue
                rm, rs = mean_n[chosen].mean(), sum_n[chosen].mean()
                out_mean.append(round(mean_n[i] / rm, 2) if rm > 0 else np.nan)
                out_sum.append(round(sum_n[i] / rs, 2) if rs > 0 else np.nan)
            put(f"{pfx}_Normalized_Sum_intensity", out_sum)
            put(f"{pfx}_Normalized_Mean_intensity", out_mean)
    return df, warnings


class CompileWorker(QThread):
    finished_job = pyqtSignal(str)

    def __init__(self, job):
        super().__init__()
        self.job = job

    def run(self):
        try:
            self.finished_job.emit(self.job() or "")
        except Exception as e:
            self.finished_job.emit("ERROR: " + str(e))


class ViewerTab(QWidget):
    def __init__(self):
        super().__init__()
        self._composite = None   # ndarray (Z, C, Y, X)
        self._base = None        # ndarray (Y,X) or (Z,Y,X) or (Z,C,Y,X)
        self._data_df = None     # pandas DataFrame
        self._data_path = None   # path to xlsx for saving
        self._folder = None
        self._z = 0
        self._n_z = 1
        self._n_ch = 0
        self._seg_cols = []      # e.g. ["N1_labels","N2_labels"]
        self._spot_cols = []     # e.g. ["Spots_labels"]
        self._typing_cols = []   # e.g. ["Chinmo_typing","Asense_typing"]
        self._ch_checkboxes = []
        self._ch_names = []
        self._range_cache = {}     # ("b" or "c", z, channel) -> (min, max) of a slice
        # Base image per-channel display params (ImageJ style)
        self._base_ch_params = []   # list of dicts: {enabled, color, min_pct, max_pct, color_btn}
        self._base_n_ch = 0
        # Intensity measurements file
        self._meas_df = None
        self._meas_all = {}
        self._meas_path = None
        self._load_token = 0
        self._loader = None
        self._ops = []                 # changes made in the viewer and not compiled yet (see the journal)
        self._record = {}              # analysis_parameters_<image>.json
        self._data_mtime = None
        self._compiler = None
        self._selected_center = None   # (x, y) of the cell or spot that was clicked, for "Zoom cell"
        self._last_click = None        # (x, y, z) of the last click

        self.setAcceptDrops(True)
        self._build_ui()

    @property
    def _spot_col(self):
        return self._spot_cols[0] if self._spot_cols else "Spots_labels"

    @property
    def _spot_prefix(self):
        return self._spot_col[:-len("_labels")]

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        if urls:
            path = urls[0].toLocalFile()
            if os.path.isdir(path):
                self._load_folder(path)
            else:
                parent = os.path.dirname(path)
                if os.path.isdir(parent):
                    self._load_folder(parent)

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------
    def _build_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(8)

        # ---- Left sidebar ----
        sidebar = QFrame()
        sidebar.setObjectName("panel")
        sidebar.setFixedWidth(220)
        sb_lay = QVBoxLayout(sidebar)
        sb_lay.setContentsMargins(10, 10, 10, 10)
        sb_lay.setSpacing(8)

        sb_lay.addWidget(titled_label("FOLDER"))

        load_btn = QPushButton("Open Folder…")
        load_btn.clicked.connect(self._browse_folder)
        load_btn.setStyleSheet(f"QPushButton {{ background-color: {C['accent']}; color: white; "
                               f"border: none; border-radius: 6px; padding: 6px 10px; }}"
                               f"QPushButton:hover {{ background-color: {C['accent_h']}; }}")
        sb_lay.addWidget(load_btn)

        self._folder_lbl = QLabel("No folder loaded")
        self._folder_lbl.setObjectName("param_label")
        self._folder_lbl.setWordWrap(True)
        sb_lay.addWidget(self._folder_lbl)

        sb_lay.addWidget(titled_label("CHANNELS"))
        self._ch_scroll = QScrollArea()
        self._ch_scroll.setWidgetResizable(True)
        self._ch_scroll.setMinimumHeight(120)
        self._ch_scroll.setMaximumHeight(200)
        self._ch_inner = QWidget()
        self._ch_layout = QVBoxLayout(self._ch_inner)
        self._ch_layout.setContentsMargins(0, 0, 0, 0)
        self._ch_layout.setSpacing(4)
        self._ch_scroll.setWidget(self._ch_inner)
        sb_lay.addWidget(self._ch_scroll)

        sb_lay.addWidget(titled_label("OPACITY"))
        self._opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self._opacity_slider.setRange(0, 100)
        self._opacity_slider.setValue(70)
        self._opacity_slider.valueChanged.connect(self._update_comp)
        sb_lay.addWidget(self._opacity_slider)

        sb_lay.addWidget(titled_label("Z SLICE"))
        self._z_slider = QSlider(Qt.Orientation.Horizontal)
        self._z_slider.setRange(0, 0)
        self._z_slider.setValue(0)
        self._z_slider.valueChanged.connect(self._on_z_changed)
        sb_lay.addWidget(self._z_slider)
        self._z_lbl = QLabel("Z: 0 / 0")
        self._z_lbl.setObjectName("param_label")
        sb_lay.addWidget(self._z_lbl)

        sb_lay.addWidget(titled_label("CELL POPULATION"))
        self._pop_combo = QComboBox()
        sb_lay.addWidget(self._pop_combo)

        sb_lay.addWidget(titled_label("BASE IMAGE"))
        self._base_ch_scroll = QScrollArea()
        self._base_ch_scroll.setWidgetResizable(True)
        self._base_ch_scroll.setMinimumHeight(80)
        self._base_ch_scroll.setMaximumHeight(200)
        self._base_ch_inner = QWidget()
        self._base_ch_layout = QVBoxLayout(self._base_ch_inner)
        self._base_ch_layout.setContentsMargins(0, 0, 0, 0)
        self._base_ch_layout.setSpacing(4)
        self._base_ch_scroll.setWidget(self._base_ch_inner)
        sb_lay.addWidget(self._base_ch_scroll)

        sb_lay.addWidget(titled_label("CHANGES"))
        self._pending_lbl = QLabel("No pending changes")
        self._pending_lbl.setObjectName("param_label")
        self._pending_lbl.setWordWrap(True)
        sb_lay.addWidget(self._pending_lbl)
        self._compile_btn = QPushButton("Compile changes")
        self._compile_btn.setToolTip("Writes the changes made in the viewer into the data table and redraws the "
                                     "halos and the valid / invalid spots of the composite.")
        self._compile_btn.setEnabled(False)
        self._compile_btn.clicked.connect(self._compile_changes)
        self._compile_btn.setStyleSheet(f"QPushButton {{ background-color: {C['success']}; color: white; border: none;"
                                        f" border-radius: 6px; padding: 6px 10px; }}"
                                        f"QPushButton:hover {{ background-color: {C['green_h']}; }}"
                                        f"QPushButton:disabled {{ background-color: {C['bg_widget']}; color: {C['muted']}; }}")
        sb_lay.addWidget(self._compile_btn)

        sb_lay.addStretch()

        # ---- Center canvas ----
        canvas_widget = QWidget()
        canvas_lay = QVBoxLayout(canvas_widget)
        canvas_lay.setContentsMargins(0, 0, 0, 0)

        self._view = FastImageView()
        self._view.clicked.connect(self._show_cell_info)
        self._view.step_z.connect(lambda d: self._z_slider.setValue(
            max(0, min(self._n_z - 1, self._z + d))))
        tools = QHBoxLayout(); tools.setSpacing(6)
        for text, tip, fn in (("Fit", "Fit the image in the window (double click on the image does the same)", self._view.fit),
                              ("1:1", "Show the image pixel for pixel", self._view.actual_size),
                              ("Save view", "Save the displayed image as a PNG", self._save_view)):
            btn = QPushButton(text); btn.setToolTip(tip); btn.clicked.connect(fn)
            btn.setStyleSheet(f"QPushButton {{ background:{C['bg_widget']}; border:1px solid {C['border']};"
                              f" border-radius:5px; color:{C['text']}; padding:3px 10px; font-size:11px; }}"
                              f"QPushButton:hover {{ border-color:{C['accent']}; }}")
            tools.addWidget(btn)
        zoom_btn = QPushButton("Zoom cell")
        zoom_btn.setToolTip("Zoom on the selected cell (or spot) with the zoom set on the right; on the centre of "
                            "the image if nothing is selected. Key: Z")
        zoom_btn.clicked.connect(self._zoom_selection)
        zoom_btn.setStyleSheet(tools.itemAt(0).widget().styleSheet())
        tools.addWidget(zoom_btn)
        self._zoom_spin = QDoubleSpinBox()
        self._zoom_spin.setRange(1.0, 40.0)
        self._zoom_spin.setSingleStep(0.5)
        self._zoom_spin.setValue(4.0)
        self._zoom_spin.setSuffix(" ×")
        self._zoom_spin.setToolTip("Zoom used by 'Zoom cell' (screen pixels per image pixel; 1 = 1:1)")
        tools.addWidget(self._zoom_spin)
        self._view.zoom_key.connect(self._zoom_selection)
        tools.addWidget(small_label("wheel = zoom · drag = move · click = info · ←/→ = slice · Z = zoom cell"))
        tools.addStretch()
        canvas_lay.addLayout(tools)
        canvas_lay.addWidget(self._view, stretch=1)

        # ---- Right info panel ----
        self._info_scroll = QScrollArea()
        self._info_scroll.setWidgetResizable(True)
        self._info_scroll.setMinimumWidth(320)
        self._info_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._info_scroll.setStyleSheet("QScrollArea { border: none; }")
        self._info_inner = QWidget()
        self._info_lay = QVBoxLayout(self._info_inner)
        self._info_lay.setContentsMargins(6, 6, 6, 6)
        self._info_lay.setSpacing(8)
        self._info_lay.addWidget(small_label("Click a cell to see its info"))
        self._info_lay.addStretch()
        self._info_scroll.setWidget(self._info_inner)

        root.addWidget(sidebar)
        split = QSplitter(Qt.Orientation.Horizontal)
        split.setChildrenCollapsible(False)
        split.setHandleWidth(8)
        split.addWidget(canvas_widget)
        split.addWidget(self._info_scroll)
        split.setStretchFactor(0, 3)
        split.setStretchFactor(1, 2)
        split.setSizes([780, 460])
        root.addWidget(split, stretch=1)

    # ------------------------------------------------------------------
    # Folder loading
    # ------------------------------------------------------------------
    def _browse_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select analysis folder")
        if folder:
            self._load_folder(folder)

    def _load_folder(self, folder):
        """Starts the reading of the folder in the background; _apply_loaded fills the viewer."""
        self._load_token += 1
        self._folder = folder
        self._folder_lbl.setText(os.path.basename(folder))
        self._view.show_busy("Loading data…")
        self._loader = FolderLoader(folder, self._load_token)
        self._loader.loaded.connect(self._apply_loaded)
        self._loader.start()

    def _apply_loaded(self, d):
        if d["token"] != self._load_token:                 # an older request, a newer folder was chosen since
            return
        for message in d["errors"]:
            QMessageBox.warning(self, "Load error", message)

        self._composite = d["composite"]
        if self._composite is not None:
            self._n_z, self._n_ch = self._composite.shape[0], self._composite.shape[1]
        else:
            self._n_z, self._n_ch = 1, 0
        self._base = d["base"]
        if self._composite is None and self._base is not None:
            self._n_z = self._base.shape[0] if self._base.ndim >= 3 else 1

        self._data_df = d["data"]
        self._data_path = d["data_path"] if d["data"] is not None else None
        self._seg_cols, self._spot_cols, self._typing_cols = [], [], []
        if self._data_df is not None:
            cols = list(self._data_df.columns)
            label_cols = [c for c in cols if c.endswith("_labels")]
            # a probe has a "<name>_number/cell" column next to its "<name>_labels"
            self._spot_cols = [c for c in label_cols if c[:-len("_labels")] + "_number/cell" in cols]
            self._seg_cols = [c for c in label_cols if c not in self._spot_cols]
            self._typing_cols = [c for c in cols if c.endswith("_typing")]
        self._meas_df, self._meas_path = d["meas"], d["meas_path"]
        self._meas_all = d.get("meas_all", {})

        self._range_cache.clear()
        self._selected_center = None
        self._last_click = None
        self._view._size = None                     # new folder: fit the image again
        self._z = 0
        self._z_slider.setRange(0, max(0, self._n_z - 1))
        self._z_slider.setValue(0)
        self._z_lbl.setText(f"Z: 0 / {max(0, self._n_z - 1)}")

        self._build_channel_checkboxes()
        self._build_pop_combo()
        self._build_base_channel_controls()
        self._after_folder_loaded()
        self._render_now()
        self._view.hide_busy()

    def _after_folder_loaded(self):
        """Reads the parameters of the analysis and replays the changes that were made and not compiled yet."""
        self._ops = []
        self._record = {}
        try:
            rec = next((f for f in os.listdir(self._folder) if f.startswith("analysis_parameters_") and f.endswith(".json")), None)
            if rec:
                with open(os.path.join(self._folder, rec), encoding="utf-8") as fh:
                    self._record = json.load(fh)
        except Exception:
            self._record = {}
        self._data_mtime = os.path.getmtime(self._data_path) if self._data_path and os.path.isfile(self._data_path) else None
        try:
            jfile, _ = journal_files(self._folder)
            if os.path.isfile(jfile) and self._data_df is not None:
                with open(jfile, encoding="utf-8") as fh:
                    saved = json.load(fh)
                if self._data_mtime is not None and abs(saved.get("data_mtime", -1) - self._data_mtime) < 2:
                    for op in saved.get("ops", []):
                        self._apply_op(op)
                        self._ops.append(op)
                else:                                      # the data table was written again since: obsolete changes
                    os.remove(jfile)
        except Exception as e:
            QMessageBox.warning(self, "Pending changes", f"The pending changes could not be read:\n{e}")
        self._update_pending_label()

    # ------------------------------------------------------------------
    # Changes: applied at once to the table in memory, kept in a journal (outside the analysis folder) and written
    # into the data table and the composite by "Compile changes"
    # ------------------------------------------------------------------
    def _update_pending_label(self):
        n = len(self._ops)
        self._pending_lbl.setText(f"{n} pending change{'s' if n > 1 else ''}" if n else "No pending changes")
        self._compile_btn.setEnabled(n > 0)

    def _record_op(self, op):
        self._apply_op(op)
        self._ops.append(op)
        try:
            jfile, _ = journal_files(self._folder)
            os.makedirs(os.path.dirname(jfile), exist_ok=True)
            with open(jfile, "w", encoding="utf-8") as fh:
                json.dump({"folder": os.path.abspath(self._folder), "data_mtime": self._data_mtime, "ops": self._ops}, fh)
        except OSError as e:
            QMessageBox.warning(self, "Pending changes", f"The change could not be kept for later:\n{e}")
        self._update_pending_label()

    def _spot_state(self, spot, from_composite):
        """Valid state of a spot, with the pending changes on top of what the composite says."""
        for op in reversed(self._ops):
            if op["op"] == "valid" and int(op["spot"]) == int(spot):
                return bool(op["valid"])
        return from_composite

    def _cell_of_position(self, df, pos):
        """(label column, label) of the cell whose block of rows contains the row at this position."""
        starts = np.flatnonzero(self._starts(df).to_numpy()[:pos + 1])
        row = df.iloc[int(starts[-1])]
        for sc in self._seg_cols:
            if pd.notna(row.get(sc)):
                return sc, int(row[sc])
        return None, None

    def _remove_spot(self, df, spot):
        rows = np.flatnonzero((df[self._spot_col] == spot).to_numpy())
        if not len(rows):
            return df
        pos = int(rows[0])
        sc, lab = self._cell_of_position(df, pos)
        for c in self._spot_columns(df):
            df.iloc[pos, df.columns.get_loc(c)] = np.nan
        if sc is not None:
            blk = self._block_positions(df, sc, lab)
            if blk is not None:
                empty = [q for q in range(blk[0] + 1, blk[1]) if df.iloc[q].isna().all()]
                if empty:
                    df = df.drop(df.index[empty]).reset_index(drop=True)
            df = self._count_spots(df, sc, lab)
        return df

    def _apply_op(self, op):
        df = self._data_df
        if df is None:
            return
        kind = op["op"]
        if kind == "type":
            blk = self._block_positions(df, op["pop"], op["cell"])
            if blk is not None and op["col"] in df.columns:
                df[op["col"]] = df[op["col"]].astype(object)
                df.iloc[blk[0], df.columns.get_loc(op["col"])] = op["value"]
        elif kind == "valid":
            spot = int(op["spot"])
            present = bool((df[self._spot_col] == spot).any())
            if op["valid"] and not present:
                pfx = self._spot_prefix
                values = {self._spot_col: float(spot)}
                if self._meas_df is not None:
                    row = self._meas_df[self._meas_df["Label"] == spot]
                    if not row.empty:
                        m = row.iloc[0]
                        for field, column in (("Mean", f"{pfx}_Mean_intensity"), ("Sum", f"{pfx}_Sum_intensity"),
                                              ("Max", f"{pfx}_Max_intensity"), ("Volume", f"{pfx}_Volume")):
                            if column in df.columns and field in m:
                                values[column] = m[field]
                self._data_df = self._put_spot(df, op["pop"], int(op["cell"]), values)
            elif not op["valid"] and present:
                self._data_df = self._remove_spot(df, spot)
        elif kind == "cell":
            spot = int(op["spot"])
            rows = np.flatnonzero((df[self._spot_col] == spot).to_numpy())
            if len(rows):
                sc, src = self._cell_of_position(df, int(rows[0]))
                if sc is not None and src != int(op["to"]):
                    self._data_df = self._move_spot(df, sc, spot, src, int(op["to"]))

    def _refresh_info(self):
        if self._last_click:
            self._show_cell_info(self._last_click[0], self._last_click[1])

    def _compile_changes(self):
        if not self._ops or self._data_df is None or self._data_path is None:
            return
        self._view.show_busy("Compiling changes…")
        self._compile_btn.setEnabled(False)
        df, ops, path = self._data_df.copy(), list(self._ops), self._data_path
        composite_path = find_folder_files(self._folder)[0]
        seg, typ, spots, record = list(self._seg_cols), list(self._typing_cols), list(self._spot_cols), dict(self._record)
        meas_all = dict(self._meas_all)
        _, backup_dir = journal_files(self._folder)

        def job():
            os.makedirs(backup_dir, exist_ok=True)               # first state of the data table, kept once
            saved = os.path.join(backup_dir, os.path.basename(path))
            if not os.path.exists(saved):
                shutil.copy2(path, saved)
            warnings = []
            by_prefix = {}
            for sc in spots:
                pfx = sc[:-len("_labels")]
                ch = (record.get("probe_channels") or {}).get(pfx)
                if ch is not None and int(ch) in meas_all:
                    by_prefix[pfx] = meas_all[int(ch)]
                elif len(spots) == 1 and len(meas_all) == 1:
                    by_prefix[pfx] = next(iter(meas_all.values()))
            new_df, rw = recompute_table(df, by_prefix, record, seg, typ, spots)
            warnings += rw
            try:
                new_df.to_excel(path, index=False, engine="openpyxl")
            except PermissionError:
                raise RuntimeError("Please close the opened Excel file of the data table and compile again.")
            if composite_path and any(o["op"] in ("valid", "type") for o in ops):
                warnings += rebuild_composite(composite_path, ops, new_df, seg, typ, spots, record)
            return "\n".join(warnings)

        self._compiler = CompileWorker(job)
        self._compiler.finished_job.connect(self._on_compiled)
        self._compiler.start()

    def _on_compiled(self, message):
        if message.startswith("ERROR: "):
            self._view.hide_busy()
            self._update_pending_label()
            QMessageBox.critical(self, "Compile changes", message[len("ERROR: "):])
            return
        try:
            jfile, _ = journal_files(self._folder)
            if os.path.isfile(jfile):
                os.remove(jfile)
        except OSError:
            pass
        self._ops = []
        self._load_folder(self._folder)
        if message:
            QMessageBox.information(self, "Compile changes", message)

    def _zoom_selection(self):
        if self._view._size is None:
            return
        H, W = self._view._size
        x, y = self._selected_center if self._selected_center else (W / 2.0, H / 2.0)
        self._view.zoom_to(x + 0.5, y + 0.5, self._zoom_spin.value())

    def _build_channel_checkboxes(self):
        # Clear old
        for cb in self._ch_checkboxes:
            cb.setParent(None)
        self._ch_checkboxes.clear()

        n = self._n_ch
        n_seg = len(self._seg_cols)
        n_typ = len(self._typing_cols)

        # Detect spot prefix from non-seg label columns
        spot_prefix = "Spots"
        if self._data_df is not None:
            spot_label_cols = [c for c in self._data_df.columns
                               if c.endswith("_labels") and c not in self._seg_cols]
            if spot_label_cols:
                spot_prefix = spot_label_cols[0].replace("_labels", "")

        ch_names = []
        for i in range(n):
            if i < n_seg:
                ch_names.append(self._seg_cols[i].replace("_labels", ""))
            elif i == n - 2 and n >= 2:
                ch_names.append(f"{spot_prefix} invalid")
            elif i == n - 1:
                ch_names.append(f"{spot_prefix} valid")
            elif i - n_seg < n_typ:
                ch_names.append(self._typing_cols[i - n_seg].replace("_typing", ""))
            else:
                ch_names.append(f"Ch {i}")
        self._ch_names = ch_names

        for i in range(n):
            color = CHANNEL_COLORS[i % len(CHANNEL_COLORS)]
            cb = QCheckBox(ch_names[i])
            cb.setChecked(True)
            cb.setStyleSheet(f"QCheckBox {{ color: {color}; }}"
                             f"QCheckBox::indicator:checked {{ background-color: {color}; border-color: {color}; }}")
            cb.stateChanged.connect(self._update_comp)
            self._ch_checkboxes.append(cb)
            self._ch_layout.addWidget(cb)

    def _build_pop_combo(self):
        self._pop_combo.clear()
        for col in self._seg_cols:
            if "spot" in col.lower():
                continue
            name = col.replace("_labels", "")
            self._pop_combo.addItem(name, col)
        # Add spot selection modes (last 2 composite channels)
        if self._n_ch >= 2:
            spot_prefix = "Spots"
            if self._data_df is not None:
                spot_label_cols = [c for c in self._data_df.columns
                                   if c.endswith("_labels") and c not in self._seg_cols]
                if spot_label_cols:
                    spot_prefix = spot_label_cols[0].replace("_labels", "")
            self._pop_combo.addItem(f"{spot_prefix} (valid)", "__spots_valid__")
            self._pop_combo.addItem(f"{spot_prefix} (invalid)", "__spots_invalid__")

    def _build_base_channel_controls(self):
        """Build per-channel ImageJ-style controls for the base image."""
        # Clear old controls
        for p in self._base_ch_params:
            for w in ["enabled", "color_btn", "min_pct", "max_pct"]:
                if w in p and p[w] is not None:
                    p[w].setParent(None)
        self._base_ch_params.clear()
        while self._base_ch_layout.count():
            item = self._base_ch_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if self._base is None:
            return

        arr = self._base
        if arr.ndim == 2:
            self._base_n_ch = 1
        elif arr.ndim == 3:
            self._base_n_ch = 1  # treat as single-channel Z stack
        elif arr.ndim == 4:
            self._base_n_ch = arr.shape[1]
        else:
            self._base_n_ch = 1

        default_colors = [[1.0, 1.0, 1.0],   # gray
                          [0.0, 1.0, 1.0],   # cyan
                          [1.0, 1.0, 0.0],   # yellow
                          [0.0, 1.0, 0.0],   # green
                          [1.0, 0.0, 1.0],   # magenta
                          [1.0, 0.5, 0.0]]   # orange

        for i in range(self._base_n_ch):
            color = default_colors[i % len(default_colors)]
            ch_name = f"Ch {i}" if self._base_n_ch > 1 else "Base"

            # Row: checkbox + color button + name
            row_w = QWidget()
            row_l = QHBoxLayout(row_w)
            row_l.setContentsMargins(0, 0, 0, 0)
            row_l.setSpacing(4)

            enabled = QCheckBox(ch_name)
            enabled.setChecked(True)

            def _make_color_hex(c):
                return "#{:02X}{:02X}{:02X}".format(int(c[0]*255), int(c[1]*255), int(c[2]*255))

            color_btn = QPushButton()
            color_btn.setFixedSize(18, 18)
            color_btn.setStyleSheet(f"background-color: {_make_color_hex(color)}; border: 1px solid {C['border']}; border-radius: 3px;")

            row_l.addWidget(enabled)
            row_l.addStretch()
            row_l.addWidget(color_btn)
            self._base_ch_layout.addWidget(row_w)

            # Min/max sliders
            min_sl = QSlider(Qt.Orientation.Horizontal)
            min_sl.setRange(0, 100)
            min_sl.setValue(0)
            max_sl = QSlider(Qt.Orientation.Horizontal)
            max_sl.setRange(0, 100)
            max_sl.setValue(100)

            min_row = QWidget()
            min_l = QHBoxLayout(min_row)
            min_l.setContentsMargins(0, 0, 0, 0)
            min_l.addWidget(small_label("min"))
            min_l.addWidget(min_sl)
            self._base_ch_layout.addWidget(min_row)

            max_row = QWidget()
            max_l = QHBoxLayout(max_row)
            max_l.setContentsMargins(0, 0, 0, 0)
            max_l.addWidget(small_label("max"))
            max_l.addWidget(max_sl)
            self._base_ch_layout.addWidget(max_row)

            param = {"enabled": enabled, "color": list(color), "color_btn": color_btn,
                     "min_pct": min_sl, "max_pct": max_sl}
            self._base_ch_params.append(param)

            # Connect signals
            enabled.stateChanged.connect(self._update_base)
            min_sl.valueChanged.connect(self._update_base)
            max_sl.valueChanged.connect(self._update_base)

            # Color button click — open color dialog
            def _make_color_cb(p, btn):
                def _on_color():
                    from PyQt6.QtWidgets import QColorDialog
                    from PyQt6.QtGui import QColor
                    cur = QColor(int(p["color"][0]*255), int(p["color"][1]*255), int(p["color"][2]*255))
                    chosen = QColorDialog.getColor(cur, self, "Pick channel color")
                    if chosen.isValid():
                        p["color"] = [chosen.redF(), chosen.greenF(), chosen.blueF()]
                        hex_c = "#{:02X}{:02X}{:02X}".format(chosen.red(), chosen.green(), chosen.blue())
                        btn.setStyleSheet(f"background-color: {hex_c}; border: 1px solid {C['border']}; border-radius: 3px;")
                        self._update_base()
                return _on_color
            color_btn.clicked.connect(_make_color_cb(param, color_btn))

    # ------------------------------------------------------------------
    # Display
    # ------------------------------------------------------------------
    def _get_base_slices(self):
        """Return list of 2D arrays, one per base channel at current Z."""
        if self._base is None:
            return []
        arr = self._base
        if arr.ndim == 2:
            return [arr]
        elif arr.ndim == 3:
            return [arr[min(self._z, arr.shape[0]-1)]]
        elif arr.ndim == 4:
            z_idx = min(self._z, arr.shape[0]-1)
            return [arr[z_idx, c] for c in range(arr.shape[1])]
        return []

    def _slice_range(self, kind, z, c, sl):
        key = (kind, z, c)
        hit = self._range_cache.get(key)
        if hit is None:
            hit = (float(sl.min()), float(sl.max()))
            self._range_cache[key] = hit
        return hit

    def _region_base(self, x0, y0, x1, y1, step):
        """Base image of the region as uint8 RGBA, with the contrast of each channel."""
        slices = self._get_base_slices()
        if not slices:
            return None
        acc = None
        for i, full in enumerate(slices):
            if i >= len(self._base_ch_params):
                break
            p = self._base_ch_params[i]
            if not p["enabled"].isChecked():
                continue
            mn, mx = self._slice_range("b", self._z, i, full)
            lo = p["min_pct"].value() / 100.0
            hi = max(p["max_pct"].value() / 100.0, lo + 1e-6)
            ramp = np.clip((np.arange(1024) / 1023.0 - lo) / (hi - lo), 0, 1)
            lut = np.rint(ramp[:, None] * np.asarray(p["color"])[None, :] * 255.0).astype(np.uint8)   # (1024, 3)
            region = full[y0:y1:step, x0:x1:step]
            q = ((region.astype(np.float32) - mn) * (1023.0 / ((mx - mn) or 1.0))).astype(np.uint16)
            acc = self._accumulate(acc, q, lut)
        h, w = slices[0][y0:y1:step, x0:x1:step].shape
        rgba = np.empty((h, w, 4), dtype=np.uint8)
        self._planes_to_rgb(rgba, acc)
        rgba[..., 3] = 255
        return rgba

    @staticmethod
    def _accumulate(acc, index, lut):
        """acc (3, h, w) uint16 += lut[index], component by component (1-D takes are much faster than row gathers)."""
        if acc is None:
            acc = np.zeros((3,) + index.shape, dtype=np.uint16)
        for k in range(3):
            column = lut[:, k]
            if column.any():
                acc[k] += np.take(column, index)
        return acc

    @staticmethod
    def _planes_to_rgb(rgba, acc):
        for k in range(3):
            if acc is None:
                rgba[..., k] = 0
            else:
                np.minimum(acc[k], 255, out=acc[k])
                rgba[..., k] = acc[k]

    def _region_composite(self, x0, y0, x1, y1, step):
        if self._composite is None or self._n_ch == 0:
            return None
        opacity = self._opacity_slider.value() / 100.0
        z_idx = min(self._z, self._composite.shape[0] - 1)
        acc = None
        ramp = np.arange(256, dtype=np.float32)[:, None] * opacity
        for i in range(self._n_ch):
            if i >= len(self._ch_checkboxes) or not self._ch_checkboxes[i].isChecked():
                continue
            full = self._composite[z_idx, i]
            _mn, mx = self._slice_range("c", z_idx, i, full)
            region = full[y0:y1:step, x0:x1:step]
            idx = (region.astype(np.float32) * (255.0 / mx)).astype(np.uint8) if mx > 0 else np.zeros(region.shape, np.uint8)
            col = np.array([int(CHANNEL_COLORS[i % len(CHANNEL_COLORS)][k:k + 2], 16) / 255.0 for k in (1, 3, 5)],
                           dtype=np.float32)
            lut = np.rint(ramp * col[None, :]).astype(np.uint8)         # (256, 3)
            acc = self._accumulate(acc, idx, lut)
        h, w = self._composite[z_idx, 0, y0:y1:step, x0:x1:step].shape
        rgba = np.zeros((h, w, 4), dtype=np.uint8)
        if acc is not None:
            self._planes_to_rgb(rgba, acc)
            np.maximum(np.maximum(rgba[..., 0], rgba[..., 1]), rgba[..., 2], out=rgba[..., 3])
        return rgba

    def _provide(self, x0, y0, x1, y1, step):
        return self._region_base(x0, y0, x1, y1, step), self._region_composite(x0, y0, x1, y1, step)

    def _image_shape(self):
        if self._composite is not None:
            return tuple(self._composite.shape[2:])
        slices = self._get_base_slices()
        return tuple(slices[0].shape) if slices else None

    def _update_display(self, *_args):
        """Asks for a redraw of the visible part (changes within a few ms are grouped)."""
        self._view.request_render()

    _update_base = _update_comp = _update_display

    def _render_now(self):
        self._view.set_source(self._image_shape(), self._provide)
        self._view.render_now()

    def _save_view(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save the view", "view.png", "PNG (*.png)")
        if path:
            self._view.viewport().grab().save(path)

    def _on_z_changed(self, val):
        self._z = val
        self._z_lbl.setText(f"Z: {val} / {max(0, self._n_z - 1)}")
        self._update_display()

    # ------------------------------------------------------------------
    # Click handler
    # ------------------------------------------------------------------
    def _spot_channels(self):
        """(invalid channel, valid channel) of the first probe in the composite: the last two channels of each probe."""
        n_probes = max(1, len(self._spot_cols))
        return self._composite.shape[1] - 2 * n_probes, self._composite.shape[1] - 2 * n_probes + 1

    def _panel_group(self, title):
        grp = QGroupBox(title)
        grp.setStyleSheet(f"QGroupBox {{ color: {C['accent']}; border: 1px solid {C['border']};"
                          f" border-radius: 6px; margin-top: 6px; padding-top: 10px; }}"
                          f"QGroupBox::title {{ subcontrol-origin: margin; left: 8px; }}")
        return grp

    def _probe_columns(self, df):
        """Columns of the probe that are shown for a spot (as in the data table), without the label and the count."""
        pfx = self._spot_prefix
        return [c for c in self._spot_columns(df) if c != self._spot_col]

    def _short(self, column):
        return column[len(self._spot_prefix) + 1:].replace("_intensity", "")

    @staticmethod
    def _fmt(v, decimals=2):
        try:
            if pd.isna(v) or v == "":
                return "-"
            return f"{float(v):.{decimals}f}"
        except (TypeError, ValueError):
            return str(v)

    def _show_cell_info(self, x, y):
        # Clear old info
        while self._info_lay.count():
            item = self._info_lay.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)
                w.deleteLater()

        def done(text=None):
            if text:
                self._info_lay.addWidget(small_label(text))
            self._info_lay.addStretch()

        if self._composite is None:
            return done("No composite loaded")
        pop_idx = self._pop_combo.currentIndex()
        if pop_idx < 0:
            return done("No cell population selected")

        col_name = self._pop_combo.itemData(pop_idx)  # e.g. "N1_labels" or "__spots_valid__"
        z_idx = min(self._z, self._composite.shape[0] - 1)
        H, W = self._composite.shape[2], self._composite.shape[3]
        if x < 0 or x >= W or y < 0 or y >= H:
            return done("Click outside image bounds")
        self._last_click = (x, y, z_idx)
        self._selected_center = None

        # ---------------- a spot ----------------
        if col_name in ("__spots_valid__", "__spots_invalid__"):
            inv_ch, val_ch = self._spot_channels()
            ch_idx = val_ch if col_name == "__spots_valid__" else inv_ch
            if ch_idx < 0 or ch_idx >= self._composite.shape[1]:
                return done("Channel out of range")
            spot_lbl = int(self._composite[z_idx, ch_idx, y, x])
            if spot_lbl == 0:
                return done("No spot at this position")
            self._selected_center = (x, y)
            self._info_lay.addWidget(titled_label(f"SPOT  {spot_lbl}"))

            df = self._data_df
            in_data = df is not None and self._spot_col in df.columns and bool((df[self._spot_col] == spot_lbl).any())
            composite_valid = col_name == "__spots_valid__"
            valid_now = self._spot_state(spot_lbl, composite_valid)

            # cell of the spot: from the data, otherwise the cell of the composite at this position
            cell_pop, cell_lbl = None, None
            if in_data:
                rows = np.flatnonzero((df[self._spot_col] == spot_lbl).to_numpy())
                cell_pop, cell_lbl = self._cell_of_position(df, int(rows[0]))
            else:
                for k, sc in enumerate(self._seg_cols):
                    if k < self._composite.shape[1] and int(self._composite[z_idx, k, y, x]) > 0:
                        cell_pop, cell_lbl = sc, int(self._composite[z_idx, k, y, x])
                        break
            if cell_lbl is not None:
                lw = QLabel(f"Cell ({cell_pop.replace('_labels', '')}): {cell_lbl}")
                lw.setObjectName("param_label")
                self._info_lay.addWidget(lw)

            if df is not None and cell_pop is not None:
                cb_valid = QCheckBox("Valid spot (kept in the data)")
                cb_valid.setChecked(valid_now)
                cb_valid.toggled.connect(lambda state, s=spot_lbl, p=cell_pop, c=cell_lbl:
                                         self._on_valid_toggled(s, state, p, c))
                self._info_lay.addWidget(cb_valid)

                if in_data:                              # change of cell
                    choices = sorted({int(v) for v in df[cell_pop].dropna().tolist() if str(v).strip() != ""})
                    row = QHBoxLayout()
                    row.addWidget(small_label("Belongs to cell"))
                    combo = NoScrollCombo()
                    combo.addItems([str(c) for c in choices])
                    combo.setCurrentText(str(cell_lbl))
                    combo.setToolTip("Moves the spot to another cell of the same population (number of spots per cell "
                                     "updated). Applied at once, written by 'Compile changes'.")
                    combo.activated.connect(lambda _i, s=spot_lbl, cb=combo, p=cell_pop, c=cell_lbl:
                                            self._on_spot_cell(s, cb.currentText(), p, c))
                    row.addWidget(combo, stretch=1)
                    self._info_lay.addLayout(row)

            # what the data table contains for this spot
            grp = self._panel_group("Data")
            lay = QVBoxLayout(grp)
            if in_data:
                r = df[df[self._spot_col] == spot_lbl].iloc[0]
                for c in self._probe_columns(df):
                    lw = QLabel(f"{self._short(c)}: {self._fmt(r[c])}")
                    lw.setObjectName("param_label")
                    lay.addWidget(lw)
            else:
                lay.addWidget(small_label("This spot is not in the data (invalid). Measured:"))
                if self._meas_df is not None:
                    mrow = self._meas_df[self._meas_df["Label"] == spot_lbl]
                    if not mrow.empty:
                        for field in ("Mean", "Sum", "Max", "Volume"):
                            if field in mrow.columns:
                                lw = QLabel(f"{field}: {self._fmt(mrow.iloc[0][field])}")
                                lw.setObjectName("param_label")
                                lay.addWidget(lw)
            self._info_lay.addWidget(grp)
            return done()

        # ---------------- a cell ----------------
        seg_ch_idx = self._seg_cols.index(col_name) if col_name in self._seg_cols else 0
        if seg_ch_idx >= self._composite.shape[1]:
            return done("Seg channel index out of range")

        label_val = int(self._composite[z_idx, seg_ch_idx, y, x])
        if label_val == 0:
            return done("No cell at this position")

        self._info_lay.addWidget(titled_label(f"CELL  {label_val}"))
        lw = QLabel(f"Population: {self._pop_combo.currentText()}")
        lw.setObjectName("param_label")
        self._info_lay.addWidget(lw)

        cell_mask_all = self._composite[:, seg_ch_idx] == label_val          # (Z, Y, X)
        ys, xs = np.nonzero(cell_mask_all.any(axis=0))
        if len(ys):
            self._selected_center = (float(xs.mean()), float(ys.mean()))

        if self._data_df is None:
            return done("No data file loaded")

        block = self._block_positions(self._data_df, col_name, label_val)
        cell_rows = self._data_df.iloc[block[0]:block[1]] if block else self._data_df.iloc[0:0]
        if cell_rows.empty:
            return done(f"Label {label_val} not found in data")

        # editable types: applied at once
        self._typing_widgets = {}
        if self._typing_cols:
            grp = self._panel_group("Cell Typing")
            grp_lay = QVBoxLayout(grp)
            grp_lay.setSpacing(6)
            for tc in self._typing_cols:
                if tc not in cell_rows.columns:
                    continue
                grp_lay.addWidget(small_label(tc.replace("_typing", "")))
                vals = sorted({_label_text(v) for v in self._data_df[tc].dropna().tolist()})
                cur_vals = cell_rows[tc].dropna().unique()
                current = _label_text(cur_vals[0]) if len(cur_vals) > 0 else ""
                cb = NoScrollCombo()
                cb.addItems(vals)
                idx = cb.findText(current)
                if idx >= 0:
                    cb.setCurrentIndex(idx)
                cb.activated.connect(lambda _i, tc=tc, cb=cb, cur=current: self._on_type_changed(
                    tc, cb.currentText(), col_name, label_val, cur))
                self._typing_widgets[tc] = cb
                grp_lay.addWidget(cb)
            self._info_lay.addWidget(grp)

        # spots of the cell: the rows of the data, plus the invalid spots found in the cell in the composite
        spot_rows = pd.DataFrame()
        if self._spot_col in cell_rows.columns:
            mask = cell_rows[self._spot_col].notna() & (cell_rows[self._spot_col].astype(str) != "no_site")
            spot_rows = cell_rows[mask]

        valid_labels, invalid_labels = set(), set()
        if self._composite.shape[1] >= 2 and self._spot_cols:
            inv_ch, val_ch = self._spot_channels()
            if inv_ch >= 0:
                valid_labels = set(np.unique(self._composite[:, val_ch][cell_mask_all].astype(int)).tolist()) - {0}
                invalid_labels = set(np.unique(self._composite[:, inv_ch][cell_mask_all].astype(int)).tolist()) - {0}
        df_spot_labels = set(spot_rows[self._spot_col].dropna().astype(int).tolist()) if not spot_rows.empty else set()
        extra_invalid = sorted(l for l in invalid_labels if l not in df_spot_labels and not self._spot_state(l, False))
        # spots validated in the viewer whose row does not exist yet in this block are already in the data (see _apply_op)

        if not spot_rows.empty or extra_invalid:
            grp2 = self._panel_group("Spots")
            grp2_lay = QVBoxLayout(grp2)
            data_cols = self._probe_columns(self._data_df)
            tbl = QTableWidget(len(spot_rows) + len(extra_invalid), 2 + len(data_cols))
            tbl.setHorizontalHeaderLabels(["Label", "Valid"] + [self._short(c) for c in data_cols])
            tbl.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
            tbl.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
            tbl.setMinimumHeight(60 + 30 * min(len(spot_rows) + len(extra_invalid), 5))
            tbl.setStyleSheet(
                f"QTableWidget {{ background-color: {C['bg_widget']}; color: {C['text']};"
                f" border: 1px solid {C['border']}; gridline-color: {C['border']}; }}"
                f"QHeaderView::section {{ background-color: {C['bg_panel']}; color: {C['muted']}; "
                f"border: none; padding: 4px; }}"
                f"QScrollBar:vertical {{ background: {C['bg_panel']}; width: 8px; }}"
                f"QScrollBar::handle:vertical {{ background: {C['border']}; border-radius: 4px; }}"
                f"QScrollBar:horizontal {{ background: {C['bg_panel']}; height: 8px; }}"
                f"QScrollBar::handle:horizontal {{ background: {C['border']}; border-radius: 4px; }}")
            row_i = 0
            entries = [(int(r[self._spot_col]), r) for _, r in spot_rows.iterrows()] + [(l, None) for l in extra_invalid]
            for spot_lbl, r in entries:
                tbl.setItem(row_i, 0, QTableWidgetItem(str(spot_lbl)))
                for j, c in enumerate(data_cols):
                    tbl.setItem(row_i, 2 + j, QTableWidgetItem(self._fmt(r[c]) if r is not None else "-"))
                cb_valid = QCheckBox()
                cb_valid.setChecked(r is not None and self._spot_state(spot_lbl, spot_lbl in valid_labels or r is not None))
                cb_valid.toggled.connect(lambda state, s=spot_lbl: self._on_valid_toggled(s, state, col_name, label_val))
                cell_w = QWidget()
                cell_l = QHBoxLayout(cell_w)
                cell_l.setContentsMargins(0, 0, 0, 0)
                cell_l.setAlignment(Qt.AlignmentFlag.AlignCenter)
                cell_l.addWidget(cb_valid)
                tbl.setCellWidget(row_i, 1, cell_w)
                row_i += 1
            grp2_lay.addWidget(tbl)
            self._info_lay.addWidget(grp2)
        done()

    # ---- reactions to the widgets of the info panel ----

    def _on_type_changed(self, column, value, pop, cell, current):
        if value and value != current:
            self._record_op({"op": "type", "col": column, "pop": pop, "cell": int(cell), "value": value})
            QTimer.singleShot(0, self._refresh_info)

    def _on_valid_toggled(self, spot, state, pop, cell):
        self._record_op({"op": "valid", "spot": int(spot), "valid": bool(state), "pop": pop, "cell": int(cell)})
        QTimer.singleShot(0, self._refresh_info)

    def _on_spot_cell(self, spot, text, pop, current_cell):
        try:
            target = int(text)
        except ValueError:
            return
        if target != int(current_cell):
            self._record_op({"op": "cell", "spot": int(spot), "to": target, "pop": pop})
            QTimer.singleShot(0, self._refresh_info)

    # ---- data table helpers (one block of rows per cell, one row per spot) ----

    def _starts(self, df):
        cols = [c for c in self._seg_cols if c in df.columns]
        if not cols:
            return pd.Series(True, index=df.index)
        st = df[cols].notna().any(axis=1)
        if len(st):
            st.iloc[0] = True
        return st

    def _block_positions(self, df, col_name, label):
        """(first position, end position) of the rows of one cell, or None."""
        hits = np.flatnonzero((df[col_name] == label).to_numpy())
        if not len(hits):
            return None
        start = int(hits[0])
        nxt = np.flatnonzero(self._starts(df).to_numpy()[start + 1:])
        return start, (start + 1 + int(nxt[0]) if len(nxt) else len(df))

    def _spot_columns(self, df):
        pfx = self._spot_prefix
        return [c for c in df.columns if c.startswith(pfx + "_") and c != f"{pfx}_number/cell"]

    def _count_spots(self, df, col_name, label):
        blk = self._block_positions(df, col_name, label)
        if blk is None:
            return df
        n = int(df.iloc[blk[0]:blk[1]][self._spot_col].notna().sum())
        if f"{self._spot_prefix}_number/cell" in df.columns:
            df.iloc[blk[0], df.columns.get_loc(f"{self._spot_prefix}_number/cell")] = n
        return df

    def _put_spot(self, df, col_name, dst_label, values):
        """Writes the values of one spot (dict column -> value) in the first free row of the block of a cell, or in a
        new row added at the end of the block. Returns the dataframe."""
        blk = self._block_positions(df, col_name, dst_label)
        if blk is None:
            return df
        spot_cols = self._spot_columns(df)
        free = [p for p in range(blk[0], blk[1]) if pd.isna(df.iloc[p][self._spot_col])]
        if free:
            for c in spot_cols:
                df.iloc[free[0], df.columns.get_loc(c)] = values.get(c, np.nan)
        else:
            new = {c: np.nan for c in df.columns}
            new.update({c: values.get(c, np.nan) for c in spot_cols})
            df = pd.concat([df.iloc[:blk[1]], pd.DataFrame([new]), df.iloc[blk[1]:]], ignore_index=True)
        return self._count_spots(df, col_name, dst_label)

    def _move_spot(self, df, col_name, spot_lbl, src_label, dst_label):
        blk = self._block_positions(df, col_name, src_label)
        if blk is None or src_label == dst_label:
            return df
        rows = np.flatnonzero((df.iloc[blk[0]:blk[1]][self._spot_col] == spot_lbl).to_numpy())
        if not len(rows):
            return df
        pos = blk[0] + int(rows[0])
        spot_cols = self._spot_columns(df)
        values = {c: df.iloc[pos, df.columns.get_loc(c)] for c in spot_cols}
        for c in spot_cols:
            df.iloc[pos, df.columns.get_loc(c)] = np.nan
        df = self._put_spot(df, col_name, dst_label, values)
        blk = self._block_positions(df, col_name, src_label)          # remove the rows left empty in the old cell
        if blk is not None:
            empty = [p for p in range(blk[0] + 1, blk[1]) if df.iloc[p].isna().all()]
            if empty:
                df = df.drop(df.index[empty]).reset_index(drop=True)
        return self._count_spots(df, col_name, src_label)


# ==============================================================================
# MAIN WINDOW
# ==============================================================================
# ==============================================================================
# SPOTIFLOW TRAINING TAB: crops of an image, annotation of spots, refinement of the pretrained 3D smFISH model
# ==============================================================================
def _iter_output(pipe):
    """(text, is_update) for the output of a child process; is_update = line ended with a lone '\\r' (progress bar)."""
    buffer = b""
    while True:
        chunk = os.read(pipe.fileno(), 65536)
        if not chunk:
            break
        buffer += chunk
        while True:
            m = re.search(rb"\r\n|\n|\r", buffer)
            if m is None or (m.group() == b"\r" and m.end() == len(buffer)):
                break
            line, buffer = buffer[:m.start()], buffer[m.end():]
            yield line.decode("utf-8", "replace").rstrip(), m.group() == b"\r"
    if buffer:
        yield buffer.decode("utf-8", "replace").rstrip(), False


class AnnotationView(QGraphicsView):
    """
    One slice of a stack with points drawn on it.
      annotate mode: left click adds a point, right click removes the nearest one, middle button drags the image
      crop mode:     left drag draws the rectangle of a crop
    Mouse wheel changes the slice, Ctrl + wheel zooms.
    """
    add_point = pyqtSignal(int, int)            # x, y (pixel indices)
    remove_point = pyqtSignal(int, int)
    rect_drawn = pyqtSignal(int, int, int, int)  # x0, y0, x1, y1
    step_z = pyqtSignal(int)

    def __init__(self):
        super().__init__()
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)
        self._pix = QGraphicsPixmapItem()
        self._scene.addItem(self._pix)
        self._markers = []
        self._rect_item = None
        self._mode = "annotate"
        self._buffer = None
        self._press = None
        self._pan = None
        self._size = None
        self.setBackgroundBrush(QColor("#101218"))
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, False)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setMouseTracking(True)

    def set_mode(self, mode):
        self._mode = mode
        self.setCursor(Qt.CursorShape.CrossCursor)
        if mode != "crop":
            self.clear_rect()

    def set_slice(self, arr, lo, hi):
        """arr: 2D array. lo / hi: display range."""
        h, w = arr.shape
        scaled = np.clip((arr.astype(np.float32) - lo) / max(hi - lo, 1e-9), 0, 1)
        self._buffer = np.ascontiguousarray((scaled * 255).astype(np.uint8))
        img = QImage(self._buffer.data, w, h, w, QImage.Format.Format_Grayscale8)
        self._pix.setPixmap(QPixmap.fromImage(img))
        first = self._size is None
        self._size = (h, w)
        self._scene.setSceneRect(0, 0, w, h)
        if first:
            self.fit()

    def reset(self):
        self._size = None
        self.clear_points()
        self.clear_rect()

    def fit(self):
        if self._size:
            self.fitInView(self._scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

    def clear_points(self):
        for item in self._markers:
            self._scene.removeItem(item)
        self._markers = []

    def set_points(self, layers):
        """layers: list of (points [(x, y, alpha 0-1)], color hex, on-screen radius)."""
        self.clear_points()
        for pts, color, radius in layers:
            for x, y, alpha in pts:
                c = QColor(color)
                c.setAlphaF(max(0.0, min(1.0, alpha)))
                item = QGraphicsEllipseItem(-radius, -radius, 2 * radius, 2 * radius)
                item.setFlag(QGraphicsEllipseItem.GraphicsItemFlag.ItemIgnoresTransformations, True)
                item.setPen(QPen(c, 1.6))
                item.setPos(x + 0.5, y + 0.5)
                item.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
                self._scene.addItem(item)
                self._markers.append(item)

    def clear_rect(self):
        if self._rect_item is not None:
            self._scene.removeItem(self._rect_item)
            self._rect_item = None

    def show_rect(self, x0, y0, x1, y1):
        self.clear_rect()
        self._rect_item = QGraphicsRectItem(min(x0, x1), min(y0, y1), abs(x1 - x0), abs(y1 - y0))
        pen = QPen(QColor("#FFD43B"), 1.5)
        pen.setCosmetic(True)
        self._rect_item.setPen(pen)
        self._scene.addItem(self._rect_item)

    def _pixel(self, event):
        p = self.mapToScene(event.position().toPoint())
        return int(np.floor(p.x())), int(np.floor(p.y()))

    def _inside(self, x, y):
        return self._size is not None and 0 <= y < self._size[0] and 0 <= x < self._size[1]

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.MiddleButton:
            self._pan = event.position().toPoint()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
        elif event.button() == Qt.MouseButton.LeftButton:
            self._press = event.position().toPoint()
        elif event.button() == Qt.MouseButton.RightButton and self._mode == "annotate":
            x, y = self._pixel(event)
            if self._inside(x, y):
                self.remove_point.emit(x, y)
        event.accept()

    def mouseMoveEvent(self, event):
        if self._pan is not None:
            d = event.position().toPoint() - self._pan
            self._pan = event.position().toPoint()
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - d.x())
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - d.y())
        elif self._press is not None and self._mode == "crop":
            a = self.mapToScene(self._press)
            b = self.mapToScene(event.position().toPoint())
            self.show_rect(a.x(), a.y(), b.x(), b.y())
        event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.MiddleButton:
            self._pan = None
            self.setCursor(Qt.CursorShape.CrossCursor)
        elif event.button() == Qt.MouseButton.LeftButton and self._press is not None:
            start, self._press = self._press, None
            end = event.position().toPoint()
            moved = (end - start).manhattanLength() > 4
            if self._mode == "crop" and moved and self._size:
                a, b = self.mapToScene(start), self.mapToScene(end)
                h, w = self._size
                x0, x1 = sorted((int(max(0, min(w, np.floor(a.x())))), int(max(0, min(w, np.ceil(b.x()))))) if a.x() <= b.x()
                                else (int(max(0, min(w, np.floor(b.x())))), int(max(0, min(w, np.ceil(a.x()))))))
                y0, y1 = sorted((int(max(0, min(h, np.floor(a.y())))), int(max(0, min(h, np.ceil(b.y()))))) if a.y() <= b.y()
                                else (int(max(0, min(h, np.floor(b.y())))), int(max(0, min(h, np.ceil(a.y()))))))
                if x1 - x0 >= 2 and y1 - y0 >= 2:
                    self.show_rect(x0, y0, x1, y1)
                    self.rect_drawn.emit(x0, y0, x1, y1)
            elif self._mode == "annotate" and not moved:
                x, y = self._pixel(event)
                if self._inside(x, y):
                    self.add_point.emit(x, y)
        event.accept()

    def wheelEvent(self, event):
        delta = event.angleDelta().y()
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            self.scale(1.15 if delta > 0 else 1 / 1.15, 1.15 if delta > 0 else 1 / 1.15)
        elif delta:
            self.step_z.emit(-1 if delta > 0 else 1)
        event.accept()

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.MiddleButton or self._mode == "view":
            self.fit()
        event.accept()


class TrainWorker(QThread):
    log = pyqtSignal(str)
    done = pyqtSignal(bool, str)         # success, model folder or message

    def __init__(self, python_exe, session, name, epochs):
        super().__init__()
        self.python_exe, self.session, self.name, self.epochs = python_exe, session, name, epochs
        self._process = None

    def stop(self):
        if self._process is not None:
            self._process.terminate()

    def run(self):
        cmd = [self.python_exe, "-u", os.path.join(base_path, "train_spotiflow.py"), self.session, self.name,
               str(self.epochs)]
        tail, model = [], None
        try:
            self._process = subprocess.Popen(cmd, cwd=base_path, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            for text, update in _iter_output(self._process.stdout):
                if text.startswith("MODEL_SAVED "):
                    model = text[len("MODEL_SAVED "):].strip()
                tail.append(text)
                self.log.emit(("\x01" if update else "") + text[:500])
            code = self._process.wait()
        except Exception as e:                                   # noqa: BLE001
            self.done.emit(False, str(e))
            return
        if code == 0 and model:
            self.done.emit(True, model)
        else:
            self.done.emit(False, "Training failed (exit code {}).\n{}".format(code, "\n".join(tail[-12:])))


class SpotiflowTrainTab(QWidget):
    """
    Session of training of a Spotiflow 3D model: 1) crops of an image (train/ and val/), 2) a click on every spot,
    3) refinement of the pretrained smFISH 3D model with these crops, 4) the new model applied to the crops.
    """
    model_ready = pyqtSignal(str)
    SETS = ("train", "val")
    COLOR_NOW, COLOR_NEAR, COLOR_PRED = "#2ECC71", "#FFD43B", "#FF9F1C"

    def __init__(self):
        super().__init__()
        self._session = None
        self._src = None            # (Z, C, Y, X) of the image the crops are taken from
        self._src_path = None
        self._channel = 0
        self._crop = None           # open crop: dict(set, stem, data, points)
        self._preds = {}            # (set, stem) -> array (N, 3) predicted by the new model
        self._z = 0
        self._range = (0.0, 1.0)
        self._rect = None
        self._worker = None
        self._build_ui()

    # ---------------------------------------------------------------- UI
    def _build_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        side = QFrame(); side.setObjectName("panel"); side.setFixedWidth(300)
        sl = QVBoxLayout(side); sl.setContentsMargins(10, 10, 10, 10); sl.setSpacing(6)

        sl.addWidget(titled_label("SESSION"))
        b = QPushButton("Choose session folder…"); b.clicked.connect(self._choose_session); sl.addWidget(b)
        self._session_lbl = QLabel("No session folder"); self._session_lbl.setObjectName("param_label")
        self._session_lbl.setWordWrap(True); sl.addWidget(self._session_lbl)

        sl.addWidget(titled_label("IMAGE"))
        b = QPushButton("Open image (czi / tif)…"); b.clicked.connect(self._open_image); sl.addWidget(b)
        self._image_lbl = QLabel("No image"); self._image_lbl.setObjectName("param_label")
        self._image_lbl.setWordWrap(True); sl.addWidget(self._image_lbl)
        row = QHBoxLayout(); row.addWidget(small_label("smFISH channel"))
        self._channel_combo = QComboBox(); self._channel_combo.activated.connect(self._channel_changed)
        row.addWidget(self._channel_combo, 1); sl.addLayout(row)

        sl.addWidget(titled_label("NEW CROP"))
        hint_crop = small_label("Drag a rectangle on the image, choose the planes, then add it to train/ or val/.")
        hint_crop.setWordWrap(True); sl.addWidget(hint_crop)
        row = QHBoxLayout(); row.addWidget(small_label("Planes"))
        self._z0 = QSpinBox(); self._z1 = QSpinBox()
        for sp in (self._z0, self._z1):
            sp.setRange(0, 0)
        row.addWidget(self._z0); row.addWidget(small_label("to")); row.addWidget(self._z1); sl.addLayout(row)
        self._rect_lbl = small_label("No rectangle"); sl.addWidget(self._rect_lbl)
        row = QHBoxLayout()
        self._to_train = QPushButton("Add to train/"); self._to_val = QPushButton("Add to val/")
        self._to_train.clicked.connect(lambda: self._make_crop("train"))
        self._to_val.clicked.connect(lambda: self._make_crop("val"))
        row.addWidget(self._to_train); row.addWidget(self._to_val); sl.addLayout(row)

        sl.addWidget(titled_label("CROPS"))
        self._list = QListWidget(); self._list.setMinimumHeight(120)
        self._list.itemSelectionChanged.connect(self._list_selected); sl.addWidget(self._list, 1)
        row = QHBoxLayout()
        self._back = QPushButton("Back to image"); self._back.clicked.connect(self._back_to_image)
        self._delete = QPushButton("Delete crop"); self._delete.clicked.connect(self._delete_crop)
        row.addWidget(self._back); row.addWidget(self._delete); sl.addLayout(row)
        self._counts = small_label(""); self._counts.setWordWrap(True); sl.addWidget(self._counts)

        sl.addWidget(titled_label("TRAINING"))
        row = QHBoxLayout(); row.addWidget(small_label("Model name"))
        self._name = QLineEdit("spotiflow_model"); row.addWidget(self._name, 1); sl.addLayout(row)
        row = QHBoxLayout(); row.addWidget(small_label("Epochs"))
        self._epochs = QSpinBox(); self._epochs.setRange(1, 2000); self._epochs.setValue(100)
        self._epochs.setToolTip("Number of passes over the training crops. The model is refined from the pretrained "
                                "3D smFISH model; 100 epochs on about ten crops took a few minutes.")
        row.addWidget(self._epochs); sl.addLayout(row)
        self._train_btn = QPushButton("Train model"); self._train_btn.clicked.connect(self._train)
        self._train_btn.setStyleSheet(f"QPushButton {{ background-color: {C['success']}; color: white; border: none; "
                                      f"border-radius: 6px; padding: 6px 10px; }}")
        sl.addWidget(self._train_btn)

        # centre: view + slice slider + display range
        centre = QVBoxLayout()
        self._status = QLabel("Choose a session folder, then open an image.")
        self._status.setObjectName("param_label"); centre.addWidget(self._status)
        self._view = AnnotationView()
        self._view.add_point.connect(self._add_point); self._view.remove_point.connect(self._remove_point)
        self._view.rect_drawn.connect(self._rect_drawn); self._view.step_z.connect(lambda d: self._z_slider.setValue(self._z + d))
        centre.addWidget(self._view, 1)
        row = QHBoxLayout()
        self._z_slider = QSlider(Qt.Orientation.Horizontal); self._z_slider.setRange(0, 0)
        self._z_slider.valueChanged.connect(self._z_changed)
        self._z_lbl = QLabel("Z 0 / 0"); self._z_lbl.setMinimumWidth(70)
        row.addWidget(self._z_lbl); row.addWidget(self._z_slider, 1); centre.addLayout(row)
        row = QHBoxLayout(); row.addWidget(small_label("Display min / max"))
        self._lo = QSlider(Qt.Orientation.Horizontal); self._hi = QSlider(Qt.Orientation.Horizontal)
        for s_, v in ((self._lo, 0), (self._hi, 700)):
            s_.setRange(0, 1000); s_.setValue(v); s_.valueChanged.connect(self._redraw)
        row.addWidget(self._lo, 1); row.addWidget(self._hi, 1)
        self._show_ann = QCheckBox("Annotations"); self._show_ann.setChecked(True)
        self._show_pred = QCheckBox("New model"); self._show_pred.setChecked(True)
        for c_ in (self._show_ann, self._show_pred):
            c_.stateChanged.connect(self._redraw); row.addWidget(c_)
        b = QPushButton("Fit"); b.clicked.connect(self._view.fit); row.addWidget(b)
        centre.addLayout(row)
        hint = small_label("Annotate: left click = add a spot at this plane, right click = remove the nearest, "
                           "wheel = plane, Ctrl + wheel = zoom, middle button = move. Green = this plane, "
                           "yellow = spots of the planes around, orange = spots found by the new model.")
        hint.setWordWrap(True); centre.addWidget(hint)
        self._log = LogPanel(); self._log.setMaximumHeight(170); centre.addWidget(self._log)

        root.addWidget(side); root.addLayout(centre, 1)
        self._view.set_mode("view")
        self._update_buttons()

    # ---------------------------------------------------------------- session / files
    def _folder(self, sub):
        return os.path.join(self._session, sub)

    def _choose_session(self):
        d = QFileDialog.getExistingDirectory(self, "Session folder (train/, val/ and models/ are created in it)")
        if not d:
            return
        self._session = d
        for sub in self.SETS + ("models",):
            os.makedirs(self._folder(sub), exist_ok=True)
        self._session_lbl.setText(d)
        self._refresh_list()
        self._update_buttons()

    def _spot_file(self, sub, stem):
        return os.path.join(self._folder(sub), stem + ".csv")

    def _read_points(self, sub, stem):
        f = self._spot_file(sub, stem)
        if not os.path.isfile(f):
            return []
        try:
            df = pd.read_csv(f)
            return df[["z", "y", "x"]].to_numpy(float).tolist() if len(df) else []
        except Exception:                                         # noqa: BLE001
            return []

    def _write_points(self):
        if self._crop is None:
            return
        pts = np.array(self._crop["points"], float).reshape(-1, 3)
        pd.DataFrame({"z": pts[:, 0], "y": pts[:, 1], "x": pts[:, 2]}).to_csv(
            self._spot_file(self._crop["set"], self._crop["stem"]), index=False)

    def _crops_in(self, sub):
        if not self._session or not os.path.isdir(self._folder(sub)):
            return []
        return sorted(os.path.splitext(f)[0] for f in os.listdir(self._folder(sub)) if f.lower().endswith((".tif", ".tiff")))

    def _refresh_list(self):
        self._list.blockSignals(True)
        self._list.clear()
        counts = {}
        for sub in self.SETS:
            n_spots = 0
            for stem in self._crops_in(sub):
                n = len(self._read_points(sub, stem)); n_spots += n
                it = QListWidgetItem(f"{sub}/{stem}   ({n} spots)")
                it.setData(Qt.ItemDataRole.UserRole, (sub, stem))
                self._list.addItem(it)
                if self._crop and self._crop["set"] == sub and self._crop["stem"] == stem:
                    it.setSelected(True)
            counts[sub] = (len(self._crops_in(sub)), n_spots)
        self._list.blockSignals(False)
        self._counts.setText("train/: {} crops, {} spots   |   val/: {} crops, {} spots".format(
            counts["train"][0], counts["train"][1], counts["val"][0], counts["val"][1]))

    def _update_buttons(self):
        has_s = self._session is not None
        has_img = self._src is not None
        self._to_train.setEnabled(has_s and has_img and self._rect is not None)
        self._to_val.setEnabled(has_s and has_img and self._rect is not None)
        self._back.setEnabled(self._crop is not None and has_img)
        self._delete.setEnabled(self._crop is not None)
        self._train_btn.setEnabled(has_s and self._worker is None)

    # ---------------------------------------------------------------- image
    def _open_image(self):
        path, _ = QFileDialog.getOpenFileName(self, "Image", "", "Images (*.czi *.tif *.tiff)")
        if not path:
            return
        if self._session is None:
            QMessageBox.information(self, "Session", "Choose the session folder first: the converted image and the crops go there.")
            return
        try:
            if path.lower().endswith(".czi"):
                os.makedirs(self._folder("source"), exist_ok=True)
                out = os.path.join(self._folder("source"), os.path.splitext(os.path.basename(path))[0] + ".tif")
                if not os.path.isfile(out):
                    self._status.setText("Converting the czi…"); QApplication.processEvents()
                    py = env_python("spots_analysis") or sys.executable
                    r = subprocess.run([py, os.path.join(base_path, "tif_meta.py"), "convert", path, out],
                                       capture_output=True, text=True)
                    if r.returncode != 0:
                        raise RuntimeError((r.stderr or r.stdout)[-600:])
                path = out
            import tifffile
            try:
                data = tifffile.memmap(path)
            except Exception:                                      # noqa: BLE001
                data = tifffile.imread(path)
            if data.ndim == 3:
                data = data[:, None]
            if data.ndim != 4:
                raise ValueError(f"Expected a stack (Z, C, Y, X) or (Z, Y, X), got shape {data.shape}.")
        except Exception as e:                                     # noqa: BLE001
            QMessageBox.critical(self, "Image", f"Could not open the image:\n{e}")
            self._status.setText("")
            return
        self._src, self._src_path, self._crop = data, path, None
        self._image_lbl.setText(f"{os.path.basename(path)}\n{data.shape[0]} planes, {data.shape[1]} channels, "
                                f"{data.shape[2]}x{data.shape[3]} px")
        self._channel_combo.clear()
        for c in range(data.shape[1]):
            self._channel_combo.addItem(f"Channel {c}", c)
        self._channel = 0
        self._show_source()

    def _channel_changed(self, _i=0):
        self._channel = self._channel_combo.currentData()
        if self._crop is None:
            self._show_source()

    def _stack_range(self, arr):
        sample = np.asarray(arr[::max(1, arr.shape[0] // 8)])
        sample = sample[:, ::max(1, sample.shape[1] // 256), ::max(1, sample.shape[2] // 256)]
        lo, hi, p998 = np.percentile(sample, [0.1, 99.99, 99.8])
        hi = float(max(hi, lo + 1))
        self._lo.blockSignals(True); self._hi.blockSignals(True)           # default display: up to the 99.8th percentile
        self._lo.setValue(0); self._hi.setValue(int(max(50, min(1000, (p998 - lo) / (hi - lo) * 1000))))
        self._lo.blockSignals(False); self._hi.blockSignals(False)
        return float(lo), hi

    def _show_source(self):
        if self._src is None:
            return
        self._crop = None
        self._rect = None
        self._view.reset()
        self._view.set_mode("crop")
        vol = self._src[:, self._channel]
        self._range = self._stack_range(vol)
        for sp in (self._z0, self._z1):
            sp.setRange(0, vol.shape[0] - 1)
        self._z0.setValue(0); self._z1.setValue(vol.shape[0] - 1)
        self._rect_lbl.setText("No rectangle")
        self._z_slider.blockSignals(True); self._z_slider.setRange(0, vol.shape[0] - 1)
        self._z = vol.shape[0] // 2; self._z_slider.setValue(self._z); self._z_slider.blockSignals(False)
        self._status.setText("Whole image: drag a rectangle to define a crop.")
        self._refresh_list(); self._update_buttons(); self._redraw()
        self._view.fit()

    def _back_to_image(self):
        self._show_source()

    def _rect_drawn(self, x0, y0, x1, y1):
        self._rect = (x0, y0, x1, y1)
        self._rect_lbl.setText(f"x {x0}–{x1}, y {y0}–{y1}  ({x1 - x0} x {y1 - y0} px)")
        self._update_buttons()

    def _make_crop(self, sub):
        if self._src is None or self._rect is None or self._session is None:
            return
        x0, y0, x1, y1 = self._rect
        z0, z1 = sorted((self._z0.value(), self._z1.value()))
        data = np.array(self._src[z0:z1 + 1, self._channel, y0:y1, x0:x1])
        stem_base = os.path.splitext(os.path.basename(self._src_path))[0] + f"_c{self._channel}"
        k = 1
        while any(os.path.exists(os.path.join(self._folder(s), f"{stem_base}_crop{k:02d}{ext}"))
                  for s in self.SETS for ext in (".tif", ".csv")):
            k += 1
        stem = f"{stem_base}_crop{k:02d}"
        import tif_meta
        tif_meta.write_like(os.path.join(self._folder(sub), stem + ".tif"), data, self._src_path, axes="ZYX",
                            channels=[self._channel])
        self._crop = {"set": sub, "stem": stem, "data": data, "points": []}
        self._write_points()
        self._open_crop(sub, stem, data)

    def _open_crop(self, sub, stem, data=None):
        if data is None:
            import tifffile
            data = tifffile.imread(os.path.join(self._folder(sub), stem + ".tif"))
            if data.ndim == 2:
                data = data[None]
        self._crop = {"set": sub, "stem": stem, "data": data, "points": self._read_points(sub, stem)}
        self._rect = None
        self._view.reset()
        self._view.set_mode("annotate")
        self._range = self._stack_range(data)
        self._z_slider.blockSignals(True); self._z_slider.setRange(0, data.shape[0] - 1)
        self._z = data.shape[0] // 2; self._z_slider.setValue(self._z); self._z_slider.blockSignals(False)
        small = data.shape[0] < 16 or data.shape[1] < 64 or data.shape[2] < 64
        self._status.setText(f"Annotating {sub}/{stem}  ({data.shape[0]} planes, {data.shape[2]} x {data.shape[1]} px)"
                             + ("  — small crop: the model may learn little from it" if small else ""))
        self._refresh_list(); self._update_buttons(); self._redraw()
        self._view.fit()

    def _list_selected(self):
        items = self._list.selectedItems()
        if not items:
            return
        sub, stem = items[0].data(Qt.ItemDataRole.UserRole)
        if self._crop and (self._crop["set"], self._crop["stem"]) == (sub, stem):
            return
        self._write_points()
        self._open_crop(sub, stem)

    def _delete_crop(self):
        if self._crop is None:
            return
        sub, stem = self._crop["set"], self._crop["stem"]
        if QMessageBox.question(self, "Delete crop", f"Delete {sub}/{stem} and its spots?") != QMessageBox.StandardButton.Yes:
            return
        for ext in (".tif", ".csv"):
            try:
                os.remove(os.path.join(self._folder(sub), stem + ext))
            except OSError:
                pass
        self._crop = None
        if self._src is not None:
            self._show_source()
        else:
            self._view.reset(); self._refresh_list(); self._update_buttons()

    # ---------------------------------------------------------------- display / annotation
    def _z_changed(self, z):
        self._z = z
        self._redraw()

    def _redraw(self, *_):
        if self._crop is not None:
            vol = self._crop["data"]
        elif self._src is not None:
            vol = self._src[:, self._channel]
        else:
            return
        z = min(self._z, vol.shape[0] - 1)
        lo0, hi0 = self._range
        lo = lo0 + (hi0 - lo0) * self._lo.value() / 1000.0
        hi = lo0 + (hi0 - lo0) * max(self._hi.value(), self._lo.value() + 1) / 1000.0
        self._view.set_slice(np.asarray(vol[z]), lo, hi)
        self._z_lbl.setText(f"Z {z} / {vol.shape[0] - 1}")
        layers = []
        if self._crop is not None:
            if self._show_ann.isChecked():
                now = [(p[2], p[1], 1.0) for p in self._crop["points"] if int(round(p[0])) == z]
                near = [(p[2], p[1], 0.55 if abs(p[0] - z) == 1 else 0.3) for p in self._crop["points"]
                        if 0 < abs(int(round(p[0])) - z) <= 2]
                layers += [(near, self.COLOR_NEAR, 4), (now, self.COLOR_NOW, 7)]
            pred = self._preds.get((self._crop["set"], self._crop["stem"]))
            if pred is not None and self._show_pred.isChecked():
                layers.append(([(p[2], p[1], 1.0) for p in pred if abs(p[0] - z) <= 1], self.COLOR_PRED, 10))
        self._view.set_points(layers)

    def _add_point(self, x, y):
        if self._crop is None:
            return
        self._crop["points"].append([float(self._z), float(y), float(x)])
        self._write_points(); self._after_edit()

    def _remove_point(self, x, y):
        if self._crop is None or not self._crop["points"]:
            return
        pts = np.array(self._crop["points"])
        d = np.hypot(pts[:, 2] - (x + 0.5), pts[:, 1] - (y + 0.5)) + 3.0 * np.abs(pts[:, 0] - self._z)
        i = int(np.argmin(d))
        if d[i] <= 12 and abs(pts[i, 0] - self._z) <= 2:
            self._crop["points"].pop(i)
            self._write_points(); self._after_edit()

    def _after_edit(self):
        self._refresh_list()
        self._redraw()

    # ---------------------------------------------------------------- training
    def _train(self):
        if self._session is None or self._worker is not None:
            return
        self._write_points()
        n = {sub: sum(len(self._read_points(sub, s)) for s in self._crops_in(sub)) for sub in self.SETS}
        if not n["train"] or not n["val"]:
            QMessageBox.information(self, "Training", "Both train/ and val/ need at least one crop with annotated spots.")
            return
        name = re.sub(r"[^\w\-.]+", "_", self._name.text().strip()) or "spotiflow_model"
        if os.path.exists(os.path.join(self._folder("models"), name)):
            QMessageBox.information(self, "Training", f"A model named '{name}' already exists in this session. Choose another name.")
            return
        py = env_python("spotiflow")
        if py is None:
            QMessageBox.warning(self, "Training", "The 'spotiflow' environment was not found.\nCreate it with "
                                "setup_environments.py (python setup_environments.py --only spotiflow).")
            return
        self._log.text.clear()
        self._log.append(f"Training {name}: {n['train']} spots in train/, {n['val']} in val/")
        self._worker = TrainWorker(py, self._session, name, self._epochs.value())
        self._worker.log.connect(self._log.append)
        self._worker.done.connect(self._train_done)
        self._train_btn.setEnabled(False); self._train_btn.setText("Training…")
        self._worker.start()

    def _train_done(self, ok, message):
        self._worker = None
        self._train_btn.setText("Train model"); self._update_buttons()
        if not ok:
            self._log.append("✗ " + message)
            QMessageBox.warning(self, "Training", message)
            return
        self._log.append(f"✔ Model saved in {message}")
        self._load_predictions(message)
        self.model_ready.emit(message)
        if self._crop is not None:
            self._redraw()
        elif self._list.count():
            self._list.setCurrentRow(0)
        QMessageBox.information(self, "Training", "The model is trained and was added to the Spotiflow models of the "
                                "Models page.\nOrange rings show the spots it finds on your crops.")

    def _load_predictions(self, model_dir):
        self._preds = {}
        folder = os.path.join(model_dir, "predictions")
        if not os.path.isdir(folder):
            return
        for f in os.listdir(folder):
            if f.endswith(".csv") and "_" in f:
                sub, stem = f[:-4].split("_", 1)
                try:
                    self._preds[(sub, stem)] = pd.read_csv(os.path.join(folder, f))[["z", "y", "x"]].to_numpy(float)
                except Exception:                                  # noqa: BLE001
                    pass


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Pipeline — Biological Image Analysis")
        self.setMinimumSize(QSize(960, 620))
        screen = QApplication.primaryScreen()
        avail = screen.availableGeometry() if screen is not None else None
        width, height = (1400, 900) if avail is None else (min(1400, int(avail.width() * 0.96)),
                                                           min(900, int(avail.height() * 0.94)))
        self.resize(width, height)
        self._worker = None

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)

        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        main_layout.addWidget(self.tabs, stretch=1)

        # ---- Tab: Analysis ----
        analysis_page   = QWidget()
        analysis_layout = QVBoxLayout(analysis_page)
        analysis_layout.setContentsMargins(8, 8, 8, 8)
        analysis_layout.setSpacing(8)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(8)

        left_col    = QWidget()
        left_layout = QVBoxLayout(left_col)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(12)
        self.log_panel  = LogPanel()
        self.plot_panel = PlotPanel()
        left_layout.addWidget(self.log_panel,  stretch=1)
        left_layout.addWidget(self.plot_panel, stretch=2)

        right_col    = QWidget()
        right_layout = QVBoxLayout(right_col)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(12)
        self.files_panel  = FilesPanel(on_files_changed=self._on_files_changed)
        self.params_panel = ParamsPanel()
        right_layout.addWidget(self.files_panel,  stretch=1)
        right_layout.addWidget(self.params_panel, stretch=3)

        splitter.addWidget(left_col)
        splitter.addWidget(right_col)
        splitter.setSizes([650, 450])
        analysis_layout.addWidget(splitter, stretch=1)

        self.bottom = BottomBar(on_run=self._on_run, on_stop=self._on_stop)
        analysis_layout.addWidget(self.bottom)
        self.tabs.addTab(analysis_page, "⚙  Analysis")

        self.viewer_tab = ViewerTab()
        self.tabs.addTab(self.viewer_tab, "🔬  Viewer")

        self.data_explorer = DataExplorer()
        self.tabs.addTab(self.data_explorer, "📊  Data Explorer")

        self.train_tab = SpotiflowTrainTab()
        self.tabs.addTab(self.train_tab, "🎯  Spotiflow training")
        self.train_tab.model_ready.connect(lambda p: self.params_panel.models_page.add_model("Spotiflow", p))

        self.setStyleSheet(STYLESHEET)

    def _on_files_changed(self, paths):
        self.bottom.set_run_enabled(len(paths) > 0)
        self.bottom.set_progress(0, len(paths))

    def _on_run(self):
        files  = self.files_panel.get_paths()
        params = self.params_panel.get_params()
        if not files: return

        # 1. parameters of the images the PSF needs
        problems = optics_problems(files, params)
        self.params_panel.highlight_optics(set())
        if problems:
            keys = {k for per_image in problems.values() for miss in per_image.values() for k in miss}
            lines = [f"• {img} — {obj}: " + ", ".join(OPTICS_LABELS.get(k, k) for k in miss)
                     for img, per_image in problems.items() for obj, miss in per_image.items()]
            box = QMessageBox(self)
            box.setIcon(QMessageBox.Icon.Warning)
            box.setWindowTitle("Optical parameters not found")
            box.setText("Some parameters of the images could not be found in their metadata:\n\n" + "\n".join(lines[:12]) +
                        ("\n…" if len(lines) > 12 else "") +
                        "\n\nEnter them yourself in Advanced › Optics (the missing fields are outlined), "
                        "then start the analysis again.\nWithout them the PSF is wrong or replaced by default values.")
            fix = box.addButton("Fill them in", QMessageBox.ButtonRole.AcceptRole)
            box.addButton("Continue anyway", QMessageBox.ButtonRole.DestructiveRole)
            box.setDefaultButton(fix)
            box.exec()
            if box.clickedButton() is fix:
                self.params_panel.highlight_optics(keys)
                return

        # 1b. Fiji for the Weka models
        if any(c.get("model_source") == SRC_WEKA for c in params.get("channels", [])):
            import fiji_tools
            ok, msg = fiji_tools.check(params.get("fiji_path", ""))
            if not ok:
                QMessageBox.warning(self, "Fiji needed", "Weka models are applied by Fiji.\n\n" + msg +
                                    "\n\nSet its location in the Models page, Weka (Fiji) section.")
                return

        # 2. conda environments
        missing = [n for n in required_envs(params) if env_python(n) is None]
        if missing:
            answer = QMessageBox.question(
                self, "Missing environments",
                "These conda environments are needed and not installed:\n\n• " + "\n• ".join(missing) +
                "\n\nInstall them now? It needs an internet connection and can take several minutes "
                "(the log shows the progress; it cannot be interrupted).",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.Yes)
            if answer != QMessageBox.StandardButton.Yes:
                return
            self.log_panel.append("=" * 44)
            self.log_panel.append("Installing the environments: " + ", ".join(missing))
            self.bottom.set_running(True)
            self._installer = EnvInstaller(missing)
            self._installer.log.connect(self.log_panel.append)
            self._installer.done.connect(lambda ok, msg, f=files, p=params: self._after_install(ok, msg, f, p))
            self._installer.start()
            return
        self._start_analysis(files, params)

    def _after_install(self, ok, message, files, params):
        self.bottom.set_running(False)
        if not ok:
            self.log_panel.append("✗ " + message)
            QMessageBox.warning(self, "Environments", message)
            return
        self.log_panel.append("Environments installed.")
        self._start_analysis(files, params)

    def _on_log(self, line):
        if line.startswith("WARNING"):
            self._warnings.append(line)
        self.log_panel.append(line)

    def _start_analysis(self, files, params):
        self.log_panel.append("=" * 44)
        self._bg_records = []
        self._warnings = []
        self._worker = AnalysisWorker(files, params)
        self._worker.progress.connect(self.bottom.set_progress)
        self._worker.log.connect(self._on_log)
        self._worker.file_done.connect(self.files_panel.update_status)
        self._worker.finished.connect(self._on_finished)
        self._worker.plot_ready.connect(self.plot_panel.add_figure)
        self._worker.background_ready.connect(self._on_background)
        self._worker.calibration_ready.connect(self._on_calibration)
        self._calib_records = []
        self.bottom.set_running(True)
        self._worker.start()

    def _on_stop(self):
        if self._worker: self._worker.stop()

    def _on_background(self, line):
        try:
            record = json.loads(line[len("background:"):])
        except ValueError:
            return
        if not hasattr(self, "_bg_records"):
            self._bg_records = []
        self._bg_records.append(record)
        self.plot_panel.add_background(record)

    def _on_calibration(self, line):
        try:
            self._calib_records.append(json.loads(line[len("calibration:"):]))
        except ValueError:
            pass

    def _calibration_summary(self):
        rows = [f"{'image':<28} {'probe':<10} {'1 molecule':>10} {'error':>7} {'CV':>5} {'n':>4} {'too big':>7} {'too small':>9}"]
        for r in self._calib_records:
            if r.get("intensity") is None:
                rows.append(f"{str(r.get('file', ''))[:28]:<28} {str(r.get('probe', ''))[:10]:<10} not computed: {r.get('reason', 'too few isolated objects')}")
                continue
            rows.append(f"{str(r.get('file', ''))[:28]:<28} {str(r.get('probe', ''))[:10]:<10} {r['intensity']:>10.1f} "
                        f"{r.get('se_pct', float('nan')):>6.1f}% {r.get('cv', float('nan')):>5.2f} {r.get('n_used', 0):>4} "
                        f"{r.get('n_too_big', 0):>7} {r.get('n_too_small', 0):>9}")
        rows.append("1 molecule = corrected Sum of an isolated molecule (median); error = standard error of this median (bootstrap);"
                    " CV = spread between molecules; too big / small = objects excluded from the reference only (kept in the results).")
        return rows

    def _background_summary(self):
        """One line per image and probe: lets the user judge the background of the whole session."""
        def num(x, fmt):
            return "-" if x is None else format(x, fmt)
        rows = [f"{'image':<28} {'probe':<10} {'B':>6} {'cells':>5} {'spot':>6} {'B/spot':>7} {'error':>8}"]
        for r in self._bg_records:
            ratio = None if not r.get("typical_spot_mean") or r.get("B") is None \
                else 100 * r["B"] / r["typical_spot_mean"]
            err = r.get("error_pct")
            if err is not None and err != err:        # NaN
                err = None
            ring_mode = r.get("method") == BG_RING
            rows.append(f"{str(r.get('file', ''))[:28]:<28} {str(r.get('probe', ''))[:10]:<10} "
                        f"{num(r.get('B'), '.2f'):>6} {r.get('n_cells', 0):>5} "
                        f"{num(r.get('typical_spot_mean'), '.2f'):>6} {('-' if ratio is None else format(ratio, '.0f') + '%'):>7} "
                        f"{('ring' if ring_mode else '-' if err is None else '+/-' + format(err, '.1f') + '%'):>8}")
        rows.append("B = background per voxel; spot = typical mean of the kept spots; "
                    "error = variation of the background (between cells or along Z) as a % of the corrected signal.")
        for r in self._bg_records:
            if r.get("method") == BG_RING and r.get("ring_fallback"):
                rows.append(f"{r.get('file', '')} {r.get('probe', '')}: {r['ring_fallback']} of {r.get('n_spots', '?')} "
                            "kept spots had a ring too small and used the image background.")
        return rows

    def _on_finished(self):
        self.bottom.set_running(False)
        if getattr(self, "_bg_records", None):
            self.log_panel.append("=" * 44)
            self.log_panel.append("BACKGROUND SUMMARY")
            for row in self._background_summary():
                self.log_panel.append(row)
        if getattr(self, "_calib_records", None):
            self.log_panel.append("=" * 44)
            self.log_panel.append("CALIBRATION SUMMARY")
            for row in self._calibration_summary():
                self.log_panel.append(row)
        if getattr(self, "_warnings", None):
            self.log_panel.append("=" * 44)
            self.log_panel.append("WARNINGS")
            for w in dict.fromkeys(self._warnings):
                self.log_panel.append(w)
        self.log_panel.append("=" * 44)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
