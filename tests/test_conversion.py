"""Integration checks using real FFmpeg and FFprobe processes."""

import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "convert.py"


class ConversionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        for tool in ("ffmpeg", "ffprobe"):
            if not shutil.which(tool):
                raise RuntimeError(f"{tool} is required for integration tests")

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name) / "input videos"
        self.folder.mkdir()

    def fixture(self, name="sample.mov", audio=False):
        path = self.folder / name
        path.parent.mkdir(parents=True, exist_ok=True)
        command = ["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "testsrc2=size=160x120:rate=10"]
        if audio:
            command += ["-f", "lavfi", "-i", "sine=frequency=440:sample_rate=44100", "-c:a", "pcm_s16le"]
        command += ["-t", "0.5", "-c:v", "mpeg4", str(path)]
        subprocess.run(command, check=True, capture_output=True)
        return path

    def run_cli(self, *args):
        return subprocess.run([sys.executable, str(SCRIPT), str(self.folder), *map(str, args)], capture_output=True, text=True)

    def probe(self, path):
        result = subprocess.run(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)], check=True, capture_output=True, text=True)
        return json.loads(result.stdout)

    def test_bulk_audio_and_silent_videos(self):
        original = self.fixture("with audio.MOV", audio=True)
        before = original.read_bytes()
        self.fixture("silent.mov")
        result = self.run_cli()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("2 converted", result.stdout)
        output = self.folder / "mp4_output"
        info = self.probe(output / "with audio.mp4")
        self.assertEqual([s["codec_name"] for s in info["streams"]], ["h264", "aac"])
        self.assertGreaterEqual(float(info["format"]["duration"]), 0.4)
        self.assertEqual(len(self.probe(output / "silent.mp4")["streams"]), 1)
        self.assertEqual(original.read_bytes(), before)

    def test_recursion_and_output_exclusion(self):
        self.fixture("nested/clip.MOV")
        self.fixture("mp4_output/ignored.mov")
        flat = self.run_cli()
        self.assertIn("No MOV files", flat.stdout)
        recursive = self.run_cli("--recursive")
        self.assertEqual(recursive.returncode, 0, recursive.stderr)
        self.assertTrue((self.folder / "mp4_output/nested/clip.mp4").is_file())
        self.assertFalse((self.folder / "mp4_output/mp4_output").exists())

    def test_skip_and_overwrite(self):
        self.fixture()
        output = Path(self.temp.name) / "custom output"
        output.mkdir()
        destination = output / "sample.mp4"
        destination.write_bytes(b"existing output")
        skipped = self.run_cli("-o", output)
        self.assertEqual(skipped.returncode, 0, skipped.stderr)
        self.assertIn("1 skipped", skipped.stdout)
        self.assertEqual(destination.read_bytes(), b"existing output")
        overwritten = self.run_cli("-o", output, "--overwrite")
        self.assertEqual(overwritten.returncode, 0, overwritten.stderr)
        self.assertEqual(self.probe(destination)["streams"][0]["codec_name"], "h264")
        self.assertEqual(list(output.glob(".conversion-*")), [])

    def test_failure_preserves_output_and_continues(self):
        (self.folder / "broken.mov").write_bytes(b"invalid video")
        self.fixture("valid.mov")
        output = self.folder / "mp4_output"
        output.mkdir()
        existing = output / "broken.mp4"
        existing.write_bytes(b"preserve me")
        result = self.run_cli("--overwrite")
        self.assertEqual(result.returncode, 1)
        self.assertIn("1 converted, 0 skipped, 1 failed", result.stdout)
        self.assertIn("broken.mov", result.stderr)
        self.assertEqual(existing.read_bytes(), b"preserve me")
        self.assertTrue((output / "valid.mp4").is_file())
        self.assertEqual(list(output.glob(".conversion-*")), [])

    def test_empty_and_invalid_input(self):
        self.assertEqual(self.run_cli().returncode, 0)
        result = subprocess.run([sys.executable, str(SCRIPT), str(self.folder / "missing")], capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn("input folder does not exist", result.stderr)


if __name__ == "__main__":
    unittest.main()
