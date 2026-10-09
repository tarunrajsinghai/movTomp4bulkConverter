"""Desktop interface for bulk MOV to MP4 conversion."""

from pathlib import Path
import sys
import threading

from PySide6.QtCore import QThread, QTimer, QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QFileDialog, QHBoxLayout, QLabel, QLineEdit,
    QMainWindow, QMessageBox, QProgressBar, QPushButton, QTextEdit,
    QVBoxLayout, QWidget,
)

from engine import run_batch


class ConversionWorker(QThread):
    progress = Signal(object)
    result = Signal(object)
    error = Signal(str)

    def __init__(self, folder, output, recursive, overwrite, parent=None):
        super().__init__(parent)
        self.options = (folder, output, recursive, overwrite)
        self.stop = threading.Event()

    def run(self):
        try:
            summary = run_batch(*self.options, on_progress=self.progress.emit, stop=self.stop)
        except Exception as error:
            self.error.emit(str(error))
        else:
            self.result.emit(summary)


class ConverterWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.worker = None
        self.last_output = None
        self.setWindowTitle("MOV to MP4 Converter")
        self.resize(760, 640)
        self.setMinimumSize(620, 530)
        root = QWidget()
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(30, 24, 30, 24)
        layout.setSpacing(14)
        title = QLabel("MOV → MP4")
        title.setObjectName("title")
        layout.addWidget(title)
        subtitle = QLabel("Convert a folder of videos in a few clicks.")
        subtitle.setObjectName("subtitle")
        layout.addWidget(subtitle)
        self.input_path = QLineEdit()
        self.input_path.setPlaceholderText("Choose the folder containing your MOV videos")
        self.input_browse = QPushButton("Browse…")
        self.input_browse.clicked.connect(self.choose_input)
        self._folder_row(layout, "Input folder", self.input_path, self.input_browse)
        self.output_path = QLineEdit()
        self.output_path.setPlaceholderText("Default: mp4_output inside your input folder")
        self.output_browse = QPushButton("Browse…")
        self.output_browse.clicked.connect(self.choose_output)
        self._folder_row(layout, "Save MP4 files to", self.output_path, self.output_browse)
        options = QHBoxLayout()
        self.recursive = QCheckBox("Include subfolders")
        self.overwrite = QCheckBox("Replace existing MP4 files")
        options.addWidget(self.recursive)
        options.addWidget(self.overwrite)
        options.addStretch()
        layout.addLayout(options)
        note = QLabel("Original MOV videos are kept. MP4 files keep the same names.")
        note.setWordWrap(True)
        layout.addWidget(note)
        actions = QHBoxLayout()
        self.start_button = QPushButton("Convert videos")
        self.start_button.setObjectName("primary")
        self.start_button.clicked.connect(self.start_conversion)
        self.stop_button = QPushButton("Stop after current video")
        self.stop_button.setEnabled(False)
        self.stop_button.clicked.connect(self.stop_conversion)
        self.open_button = QPushButton("Open output folder")
        self.open_button.setEnabled(False)
        self.open_button.clicked.connect(self.open_output)
        actions.addWidget(self.start_button)
        actions.addWidget(self.stop_button)
        actions.addStretch()
        layout.addLayout(actions)
        self.progress = QProgressBar()
        self.progress.setRange(0, 1)
        self.progress.setValue(0)
        layout.addWidget(self.progress)
        self.status = QLabel("Choose an input folder to begin.")
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setPlaceholderText("Conversion results will appear here.")
        layout.addWidget(self.log, 1)
        layout.addWidget(self.open_button)
        self.setStyleSheet("""
            QMainWindow { background: #f4f7fb; }
            QWidget { font-family: 'Segoe UI', sans-serif; font-size: 10pt; color: #192b40; }
            QLabel#title { font-size: 26pt; font-weight: 700; }
            QLabel#subtitle { color: #586a7d; margin-bottom: 8px; }
            QLineEdit, QTextEdit { background: white; border: 1px solid #cad4e0;
                border-radius: 6px; padding: 9px; selection-background-color: #d5e9fa; }
            QPushButton { background: white; border: 1px solid #cad4e0;
                border-radius: 6px; padding: 9px 13px; }
            QPushButton:hover { background: #e8eff8; }
            QPushButton#primary { background: #176a58; color: white; border: none; font-weight: 600; }
            QPushButton#primary:hover { background: #105343; }
            QPushButton:disabled { color: #8995a4; background: #e9eef4; }
            QProgressBar { background: #e3eaf2; border: none; border-radius: 5px;
                text-align: center; height: 22px; }
            QProgressBar::chunk { background: #6abea9; border-radius: 5px; }
        """)

    @staticmethod
    def _folder_row(layout, label, field, button):
        layout.addWidget(QLabel(label))
        row = QHBoxLayout()
        row.addWidget(field, 1)
        row.addWidget(button)
        layout.addLayout(row)

    def choose_input(self):
        folder = QFileDialog.getExistingDirectory(self, "Choose input folder", self.input_path.text())
        if folder:
            self.input_path.setText(folder)

    def choose_output(self):
        folder = QFileDialog.getExistingDirectory(self, "Choose output folder", self.output_path.text())
        if folder:
            self.output_path.setText(folder)

    def start_conversion(self):
        if self.worker is not None:
            return
        if not self.input_path.text().strip():
            QMessageBox.warning(self, "Choose a folder", "Please choose an input folder first.")
            return
        folder = Path(self.input_path.text().strip()).expanduser().resolve()
        if not folder.is_dir():
            QMessageBox.warning(self, "Folder not found", "The input folder does not exist. Choose another folder.")
            return
        output_text = self.output_path.text().strip()
        output = Path(output_text).expanduser().resolve() if output_text else folder / "mp4_output"
        self.last_output = output
        self.log.clear()
        self.write_log(f"Saving MP4 videos to: {output}")
        self.status.setText("Scanning for MOV videos…")
        self.progress.setRange(0, 0)
        self._set_running(True)
        self.worker = ConversionWorker(folder, output, self.recursive.isChecked(), self.overwrite.isChecked(), self)
        self.worker.progress.connect(self.on_progress)
        self.worker.result.connect(self.on_result)
        self.worker.error.connect(self.on_error)
        self.worker.finished.connect(self.on_finished)
        self.worker.start()

    def write_log(self, text):
        # Filenames and diagnostics are plain text, never interpreted as HTML.
        self.log.moveCursor(self.log.textCursor().MoveOperation.End)
        self.log.insertPlainText(text + "\n")
        self.log.verticalScrollBar().setValue(self.log.verticalScrollBar().maximum())

    def _set_running(self, running):
        for widget in (self.input_path, self.input_browse, self.output_path, self.output_browse,
                       self.recursive, self.overwrite, self.start_button):
            widget.setEnabled(not running)
        self.stop_button.setEnabled(running)
        self.open_button.setEnabled(not running and self.last_output is not None and self.last_output.is_dir())

    def on_progress(self, event):
        self.progress.setRange(0, event.total)
        self.progress.setValue(event.index - 1 if event.status == "started" else event.index)
        if event.status == "started":
            self.status.setText(f"Converting {event.index} of {event.total}: {event.source.name}")
        else:
            self.write_log(f"{event.status.capitalize()}: {event.source.name}")
            if event.message:
                self.write_log(event.message)

    def on_result(self, summary):
        message = summary.message() if summary.total else "No MOV files found in this folder."
        self.status.setText(message)
        self.write_log(message)
        if not summary.total:
            self.progress.setRange(0, 1)
            self.progress.setValue(0)

    def on_error(self, message):
        self.status.setText("Could not start conversion. See details below.")
        self.write_log(message)
        self.progress.setRange(0, 1)
        self.progress.setValue(0)

    def on_finished(self):
        self.worker.deleteLater()
        self.worker = None
        self._set_running(False)

    def stop_conversion(self):
        if self.worker is not None:
            self.worker.stop.set()
            self.stop_button.setEnabled(False)
            self.status.setText("Stopping after the current video finishes…")

    def open_output(self):
        if self.last_output is not None:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.last_output)))

    def closeEvent(self, event):
        if self.worker is not None:
            QMessageBox.information(self, "Conversion in progress", "Use 'Stop after current video' and wait for it to finish before closing.")
            event.ignore()
        else:
            event.accept()


def main():
    application = QApplication(sys.argv)
    application.setApplicationName("MOV to MP4 Converter")
    window = ConverterWindow()
    window.show()
    if "--smoke-test" in sys.argv:
        QTimer.singleShot(500, application.quit)
    return application.exec()


if __name__ == "__main__":
    sys.exit(main())
