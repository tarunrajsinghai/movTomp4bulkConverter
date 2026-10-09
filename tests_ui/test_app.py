"""Exercise the actual desktop controls and background conversion worker."""

import json
from pathlib import Path
import subprocess
import tempfile
import time
import unittest
from unittest.mock import patch

from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from app import ConverterWindow


class DesktopTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.application = QApplication.instance() or QApplication([])

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.folder = Path(self.temp.name)
        self.window = ConverterWindow()
        self.window.show()
        self.window.input_path.setText(str(self.folder))

    def tearDown(self):
        if self.window.worker is not None:
            self.window.worker.stop.set()
            self.window.worker.wait(30000)
            self.application.processEvents()
        self.window.close()
        self.temp.cleanup()

    def wait_until_done(self):
        deadline = time.monotonic() + 30
        while self.window.worker is not None and time.monotonic() < deadline:
            QTest.qWait(10)
        self.assertIsNone(self.window.worker, 'conversion worker did not finish')

    def test_convert_button_creates_playable_output_and_restores_controls(self):
        subprocess.run(['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i',
                        'testsrc2=size=160x120:rate=10', '-t', '0.3',
                        '-c:v', 'mpeg4', str(self.folder / 'video.MOV')], check=True)
        self.window.start_button.click()
        self.assertFalse(self.window.start_button.isEnabled())
        self.wait_until_done()
        self.assertTrue(self.window.start_button.isEnabled())
        self.assertTrue(self.window.open_button.isEnabled())
        self.assertFalse(self.window.stop_button.isEnabled())
        self.assertEqual(self.window.progress.value(), 1)
        self.assertIn('1 converted', self.window.status.text())
        output = self.folder / 'mp4_output/video.mp4'
        result = subprocess.run(['ffprobe', '-v', 'error', '-show_streams', '-of',
                                 'json', str(output)], check=True, capture_output=True, text=True)
        self.assertEqual(json.loads(result.stdout)['streams'][0]['codec_name'], 'h264')

    def test_bad_video_reports_failure_without_disabling_the_app(self):
        (self.folder / 'broken.mov').write_bytes(b'invalid video')
        self.window.start_button.click()
        self.wait_until_done()
        self.assertIn('1 failed', self.window.status.text())
        self.assertIn('Failed: broken.mov', self.window.log.toPlainText())
        self.assertTrue(self.window.input_browse.isEnabled())
        self.assertFalse((self.folder / 'mp4_output/broken.mp4').exists())

    def test_missing_ffmpeg_is_reported_and_controls_are_restored(self):
        with patch('engine.find_ffmpeg', side_effect=RuntimeError('FFmpeg missing')):
            self.window.start_button.click()
            self.wait_until_done()
        self.assertIn('Could not start', self.window.status.text())
        self.assertIn('FFmpeg missing', self.window.log.toPlainText())
        self.assertTrue(self.window.start_button.isEnabled())

    def test_invalid_input_does_not_launch_a_worker(self):
        self.window.input_path.setText(str(self.folder / 'missing'))
        with patch('app.QMessageBox.warning') as warning:
            self.window.start_button.click()
        warning.assert_called_once()
        self.assertIsNone(self.window.worker)

    def test_empty_folder_returns_to_idle(self):
        self.window.start_button.click()
        self.wait_until_done()
        self.assertIn('No MOV files', self.window.status.text())
        self.assertEqual(self.window.progress.value(), 0)
        self.assertTrue(self.window.start_button.isEnabled())
