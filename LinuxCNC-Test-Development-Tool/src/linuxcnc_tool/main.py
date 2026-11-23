from __future__ import annotations
import sys, os, time, platform
from datetime import datetime
from pathlib import Path

try:
    import psutil
except ImportError:
    psutil = None

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QListWidget, QStackedWidget, QTextEdit, QLineEdit, QGridLayout,
    QFrame, QMessageBox, QFileDialog, QProgressBar, QTabWidget
)
from . import diagnostics as diag
from . import analyzer, reporting

APP_NAME = "LinuxCNC Test & Development Tool"

STYLE = """
QMainWindow, QWidget { background: #0b1420; color: #e8f1fa; font-family: 'DejaVu Sans'; font-size: 10pt; }
QLabel#title { font-size: 20pt; font-weight: bold; color: #f4f8fc; }
QLabel#subtitle { color: #8dcdf4; font-size: 10pt; }
QListWidget { background: #101e2d; border: 1px solid #29445b; padding: 5px; }
QListWidget::item { padding: 12px 8px; border-bottom: 1px solid #203548; }
QListWidget::item:selected { background: #075a9d; color: white; }
QPushButton { background: #18344b; border: 1px solid #39749b; border-radius: 5px; padding: 8px 12px; color: white; }
QPushButton:hover { background: #20577b; }
QPushButton:pressed { background: #0878bd; }
QTextEdit, QLineEdit { background: #07101a; border: 1px solid #31516a; border-radius: 4px; padding: 7px; color: #d8edf9; selection-background-color: #0878bd; }
QFrame#panel { background: #101e2b; border: 1px solid #2a526d; border-radius: 7px; }
QLabel#paneltitle { color: #71caff; font-weight: bold; font-size: 11pt; }
QProgressBar { border: 1px solid #31516a; border-radius: 4px; text-align: center; background: #07101a; }
QProgressBar::chunk { background: #08a6e8; }
QTabWidget::pane { border: 1px solid #31516a; }
QTabBar::tab { background: #152b3e; padding: 8px 14px; border: 1px solid #31516a; }
QTabBar::tab:selected { background: #075a9d; }
"""

def panel(title: str):
    frame = QFrame()
    frame.setObjectName("panel")
    lay = QVBoxLayout(frame)
    head = QLabel(title)
    head.setObjectName("paneltitle")
    lay.addWidget(head)
    return frame, lay

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} v1.1.0")
        self.resize(1440, 900)
        central = QWidget()
        self.setCentralWidget(central)
        outer = QVBoxLayout(central)
        header = QHBoxLayout()
        titlebox = QVBoxLayout()
        title = QLabel(APP_NAME); title.setObjectName("title")
        subtitle = QLabel("Configuration  •  Test  •  Diagnostics  •  Hardware  •  Network  •  Performance")
        subtitle.setObjectName("subtitle")
        titlebox.addWidget(title); titlebox.addWidget(subtitle)
        header.addLayout(titlebox); header.addStretch()
        self.connection_label = QLabel("● LinuxCNC status: checking")
        self.connection_label.setStyleSheet("color:#8fd5ff;font-weight:bold;padding:8px;")
        header.addWidget(self.connection_label)
        outer.addLayout(header)

        body = QHBoxLayout()
        self.nav = QListWidget()
        self.pages = QStackedWidget()
        names = ["Overview", "System Health Check", "HAL Test", "I/O Test", "Fieldbus Test",
                 "Drive / Servo Test", "Spindle Test", "Simulation", "Diagnostics",
                 "System & Performance", "Configuration", "Tools", "Examples", "Documentation"]
        self.nav.addItems(names)
        self.nav.setFixedWidth(220)
        for name in names:
            self.pages.addWidget(self.make_page(name))
        self.nav.currentRowChanged.connect(self.pages.setCurrentIndex)
        self.nav.setCurrentRow(0)
        body.addWidget(self.nav); body.addWidget(self.pages, 1)
        outer.addLayout(body, 1)

        footer = QLabel("Read-only diagnostics by default • No motion commands are sent • v1.1.0")
        footer.setStyleSheet("color:#7895aa;padding:4px;")
        outer.addWidget(footer)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh_live)
        self.timer.start(3000)
        self.refresh_live()

    def make_page(self, name):
        page = QWidget(); root = QVBoxLayout(page)
        if name in ("Overview", "System & Performance"):
            row = QHBoxLayout()
            for title_text, value in [("LinuxCNC", "Detection"), ("CPU / Memory", "Live monitoring"), ("Network", "Interfaces / Ping"), ("EtherCAT", "Master / Slaves")]:
                box, lay = panel(title_text); lay.addWidget(QLabel(value)); row.addWidget(box)
            root.addLayout(row)
            tabs = QTabWidget()
            for tab_name, content in [
                ("System", self.system_text),
                ("CPU / Memory", self.resource_text),
                ("Network", diag.network_info),
                ("EtherCAT", diag.ethercat_info),
                ("HAL", diag.hal_info),
                ("Real-time", analyzer.realtime_details),
                ("Hardware", analyzer.hardware_inventory),
            ]:
                w = QWidget(); vl = QVBoxLayout(w); txt = QTextEdit(); txt.setReadOnly(True)
                if tab_name == "System": self.system_view = txt
                elif tab_name == "CPU / Memory": self.resource_view = txt
                elif tab_name == "Network": self.network_view = txt
                elif tab_name == "EtherCAT": self.ethercat_view = txt
                elif tab_name == "HAL": self.hal_view = txt
                elif tab_name == "Real-time": self.rt_view = txt
                elif tab_name == "Hardware": self.hardware_view = txt
                vl.addWidget(txt)
                tabs.addTab(w, tab_name)
            ping_page = QWidget(); ping_layout = QVBoxLayout(ping_page)
            ping_row = QHBoxLayout()
            self.ping_host = QLineEdit("8.8.8.8")
            self.ping_host.setPlaceholderText("Hostname or IP address")
            ping_button = QPushButton("Run ping test")
            ping_button.clicked.connect(self.run_ping)
            ping_row.addWidget(QLabel("Host:")); ping_row.addWidget(self.ping_host, 1); ping_row.addWidget(ping_button)
            ping_layout.addLayout(ping_row)
            self.ping_output = QTextEdit(); self.ping_output.setReadOnly(True)
            self.ping_output.setPlainText("Enter a hostname or IP address and run the test. Uses the system ping utility.")
            ping_layout.addWidget(self.ping_output)
            tabs.addTab(ping_page, "Ping Test")
            root.addWidget(tabs, 1)
            buttons = QHBoxLayout()
            for label, fn in [("Run full scan", self.full_scan), ("Start latency-histogram", self.start_latency), ("Save TXT report", self.save_report), ("Export PDF", self.save_pdf)]:
                b = QPushButton(label); b.clicked.connect(fn); buttons.addWidget(b)
            root.addLayout(buttons)
        elif name == "Diagnostics":
            self.add_output_page(root, "Diagnostics and real-time analyzer", analyzer.realtime_details)
            b = QPushButton("Run diagnostics"); b.clicked.connect(self.full_scan); root.addWidget(b)
        elif name == "System Health Check":
            self.add_output_page(root, "System Health Check", analyzer.health_report)
            buttons = QHBoxLayout()
            for label, fn in [("Run health check", lambda: self.set_output(analyzer.health_report())),
                              ("Hardware inventory", lambda: self.set_output(analyzer.hardware_inventory())),
                              ("Real-time details", lambda: self.set_output(analyzer.realtime_details())),
                              ("Export PDF", self.save_pdf)]:
                b = QPushButton(label); b.clicked.connect(fn); buttons.addWidget(b)
            root.addLayout(buttons)
        elif name == "HAL Test":
            self.add_output_page(root, "HAL components and pins", diag.hal_info)
            b = QPushButton("Refresh HAL"); b.clicked.connect(lambda: self.set_output(diag.hal_info())); root.addWidget(b)
        elif name == "Fieldbus Test":
            self.add_output_page(root, "EtherCAT master and slave status", diag.ethercat_info)
            b = QPushButton("Scan EtherCAT"); b.clicked.connect(lambda: self.set_output(diag.ethercat_info())); root.addWidget(b)
        elif name == "System & Performance":
            pass
        elif name == "I/O Test":
            self.add_static(root, "I/O inspection", "This release provides read-only HAL inspection. Physical output toggling is intentionally disabled to avoid unexpected machine movement.")
            b = QPushButton("Inspect HAL I/O"); b.clicked.connect(lambda: self.show_message(diag.hal_info())); root.addWidget(b)
        elif name == "Drive / Servo Test":
            self.add_static(root, "Drive / Servo", "Read-only status is available through configured HAL pins and fieldbus diagnostics. No enable, jog, homing or motion commands are issued by this tool.")
        elif name == "Spindle Test":
            self.add_static(root, "Spindle", "Spindle status can be inspected through HAL and fieldbus data. This version does not command spindle start/stop or speed.")
        elif name == "Simulation":
            self.add_static(root, "Simulation", "Use your LinuxCNC simulator configuration for offline testing. This tool does not modify machine configuration.")
        elif name == "Configuration":
            self.add_output_page(root, "LinuxCNC and host configuration", diag.system_info)
        elif name == "Tools":
            self.add_static(root, "Utilities", "Available utilities: hardware inventory, network inspection, EtherCAT scan, HAL inspection and LinuxCNC latency-histogram launcher.")
            for label, fn in [("Hardware inventory", lambda: self.show_message(diag.hardware_info())),
                              ("Network details", lambda: self.show_message(diag.ethernet_details())),
                              ("Routes", lambda: self.show_message(diag.routes_info()))]:
                b = QPushButton(label); b.clicked.connect(fn); root.addWidget(b)
        elif name == "Examples":
            self.add_static(root, "Examples", "Example HAL and LinuxCNC configurations should be tested in a simulator first. No machine-specific example is enabled by default.")
        elif name == "Documentation":
            self.add_static(root, "Documentation", "See README.md for installation, supported checks, safety notes and GitHub publishing instructions.")
        else:
            self.add_static(root, name, "Select a diagnostic module from the navigation panel.")
        return page

    def add_output_page(self, root, title, getter):
        frame, lay = panel(title); self.output = QTextEdit(); self.output.setReadOnly(True)
        lay.addWidget(self.output); root.addWidget(frame, 1)
        self.output_getter = getter
        b = QPushButton("Refresh"); b.clicked.connect(lambda: self.set_output(getter())); root.addWidget(b)
        self.set_output(getter())

    def add_static(self, root, title, text):
        frame, lay = panel(title); label = QLabel(text); label.setWordWrap(True); lay.addWidget(label); root.addWidget(frame); root.addStretch()

    def set_output(self, text):
        if hasattr(self, "output"): self.output.setPlainText(str(text))

    def show_message(self, text):
        dlg = QMessageBox(self); dlg.setWindowTitle("Diagnostic result"); dlg.setText(str(text)[:12000]); dlg.setStandardButtons(QMessageBox.Ok); dlg.exec()

    def system_text(self):
        return "\n".join(f"{k}: {v}" for k,v in diag.system_info().items())

    def resource_text(self):
        if not psutil: return "psutil is not installed. Install requirements.txt to enable CPU and memory monitoring."
        vm = psutil.virtual_memory(); sm = psutil.swap_memory()
        return (f"CPU usage: {psutil.cpu_percent(interval=0.2)}%\n"
                f"CPU cores: {psutil.cpu_count(logical=False)} physical / {psutil.cpu_count()} logical\n"
                f"RAM: {vm.percent}% used ({vm.used/1024**3:.2f} / {vm.total/1024**3:.2f} GiB)\n"
                f"Swap: {sm.percent}% used ({sm.used/1024**3:.2f} / {sm.total/1024**3:.2f} GiB)")

    def refresh_live(self):
        try:
            self.connection_label.setText("● LinuxCNC: " + ("available" if __import__("shutil").which("linuxcnc") else "not found"))
            if hasattr(self, "resource_view"): self.resource_view.setPlainText(self.resource_text())
            if hasattr(self, "system_view"): self.system_view.setPlainText(self.system_text())
        except Exception as exc:
            self.connection_label.setText(f"● Monitor warning: {exc}")

    def full_scan(self):
        report = [
            "===== SYSTEM HEALTH =====", analyzer.health_report(),
            "\n===== REAL-TIME ANALYZER =====", analyzer.realtime_details(),
            "\n===== HARDWARE INVENTORY =====", analyzer.hardware_inventory(),
            "\n===== SYSTEM =====", self.system_text(),
            "\n===== CPU / MEMORY =====", self.resource_text(),
            "\n===== REAL-TIME =====", analyzer.realtime_details(),
            "\n===== NETWORK =====", diag.network_info(),
            "\n===== ETHERCAT =====", diag.ethercat_info(),
            "\n===== HAL =====", diag.hal_info(),
            "\n===== HARDWARE =====", diag.hardware_info(),
        ]
        combined = "\n".join(report)
        for attr in ("system_view","rt_view","network_view","ethercat_view","hal_view"):
            if hasattr(self, attr):
                if attr == "system_view": self.system_view.setPlainText(self.system_text())
                elif attr == "rt_view": self.rt_view.setPlainText(analyzer.realtime_details())
                elif attr == "network_view": self.network_view.setPlainText(diag.network_info())
                elif attr == "ethercat_view": self.ethercat_view.setPlainText(diag.ethercat_info())
                elif attr == "hal_view": self.hal_view.setPlainText(diag.hal_info())
        self.last_report = combined
        self.statusBar().showMessage("System scan completed. Missing tools or unconfigured subsystems are reported as unavailable.", 10000)

    def run_ping(self):
        host = self.ping_host.text().strip() if hasattr(self, "ping_host") else ""
        result = diag.ping_host(host, count=4)
        if hasattr(self, "ping_output"):
            self.ping_output.setPlainText(result)

    def start_latency(self):
        ok, msg = diag.launch_latency_histogram()
        self.statusBar().showMessage(msg, 10000)
        if not ok: self.show_message(msg)

    def save_pdf(self):
        if not hasattr(self, "last_report"): self.full_scan()
        path, _ = QFileDialog.getSaveFileName(self, "Export PDF system report", "linuxcnc-system-report.pdf", "PDF report (*.pdf)")
        if path:
            try:
                reporting.create_pdf(path, APP_NAME + " – System Health Report", self.last_report)
                self.statusBar().showMessage(f"PDF report saved: {path}", 8000)
            except Exception as exc:
                self.show_message(f"PDF export failed: {exc}")

    def save_report(self):
        if not hasattr(self, "last_report"): self.full_scan()
        path, _ = QFileDialog.getSaveFileName(self, "Save system report", "linuxcnc-system-report.txt", "Text report (*.txt)")
        if path:
            Path(path).write_text(
                f"{APP_NAME} v1.1.0\nGenerated: {datetime.now().isoformat(timespec='seconds')}\n\n{self.last_report}\n",
                encoding="utf-8"
            )
            self.statusBar().showMessage(f"Report saved: {path}", 8000)

def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setStyleSheet(STYLE)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
