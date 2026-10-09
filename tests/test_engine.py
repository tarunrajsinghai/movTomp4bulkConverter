from pathlib import Path
import subprocess
import tempfile
import threading
import unittest

from engine import run_batch


class EngineTests(unittest.TestCase):
    def test_stop_finishes_current_video_and_preserves_remaining_input(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            for name in ('a.mov', 'b.mov'):
                subprocess.run(['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i',
                                'testsrc2=size=160x120:rate=10', '-t', '0.3',
                                '-c:v', 'mpeg4', str(folder / name)], check=True)
            stop = threading.Event()
            events = []

            def progress(event):
                events.append(event)
                if event.status == 'converted':
                    stop.set()

            summary = run_batch(folder, on_progress=progress, stop=stop)
            self.assertTrue(summary.cancelled)
            self.assertEqual(summary.total, 2)
            self.assertEqual(summary.converted, 1)
            self.assertEqual([e.status for e in events], ['started', 'converted'])
            self.assertTrue((folder / 'mp4_output/a.mp4').exists())
            self.assertFalse((folder / 'mp4_output/b.mp4').exists())
            self.assertTrue((folder / 'b.mov').exists())
