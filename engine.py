"""Shared conversion engine for the desktop app and command-line tool."""

from dataclasses import dataclass
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


@dataclass(frozen=True)
class Progress:
    index: int
    total: int
    source: Path
    destination: Path
    status: str
    message: str = ""


@dataclass
class Summary:
    total: int = 0
    converted: int = 0
    skipped: int = 0
    failed: int = 0
    cancelled: bool = False

    def message(self):
        prefix = "Stopped" if self.cancelled else "Done"
        return f"{prefix}: {self.converted} converted, {self.skipped} skipped, {self.failed} failed."


def find_ffmpeg():
    bundled = Path(__file__).resolve().parent / "runtime" / "ffmpeg.exe"
    executable = str(bundled) if bundled.is_file() else shutil.which("ffmpeg")
    if not executable:
        raise RuntimeError("FFmpeg is required. Install FFmpeg or use the Windows installer, which includes it.")
    return executable


def convert(source, destination, ffmpeg, overwrite=False):
    """Publish only a completed conversion, preserving existing outputs on failure."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".conversion-", suffix=".mp4", dir=destination.parent)
    os.close(fd)
    try:
        result = subprocess.run(
            [
                ffmpeg, "-hide_banner", "-loglevel", "error", "-nostdin", "-y",
                "-i", str(source), "-map", "0:v:0", "-map", "0:a?",
                "-c:v", "libx264", "-crf", "23", "-preset", "medium",
                "-vf", "pad=ceil(iw/2)*2:ceil(ih/2)*2", "-pix_fmt", "yuv420p",
                "-c:a", "aac", "-movflags", "+faststart", temporary,
            ],
            capture_output=True, text=True, errors="replace",
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
        )
        if result.returncode:
            raise RuntimeError(result.stderr.strip() or "FFmpeg conversion failed")
        if overwrite:
            os.replace(temporary, destination)
        elif sys.platform == "win32":
            # Windows rename fails when a target exists, including on FAT/exFAT.
            os.rename(temporary, destination)
        else:
            os.link(temporary, destination)
    finally:
        Path(temporary).unlink(missing_ok=True)


def run_batch(folder, output=None, recursive=False, overwrite=False, on_progress=None, stop=None):
    folder = Path(folder).resolve()
    output = Path(output).resolve() if output is not None else folder / "mp4_output"
    if not folder.is_dir():
        raise ValueError(f"input folder does not exist or is not a directory: {folder}")
    ffmpeg = find_ffmpeg()
    entries = folder.rglob("*") if recursive else folder.iterdir()
    videos = sorted(
        path for path in entries
        if path.is_file() and path.suffix.lower() == ".mov"
        and (output == folder or not path.is_relative_to(output))
    )
    summary = Summary(total=len(videos))
    for index, source in enumerate(videos, 1):
        if stop is not None and stop.is_set():
            summary.cancelled = True
            break
        destination = output / source.relative_to(folder).with_suffix(".mp4")

        def emit(status, message=""):
            if on_progress is not None:
                on_progress(Progress(index, len(videos), source, destination, status, message))

        if destination.exists() and not overwrite:
            summary.skipped += 1
            emit("skipped")
            continue
        emit("started")
        try:
            convert(source, destination, ffmpeg, overwrite)
        except FileExistsError:
            summary.skipped += 1
            emit("skipped")
        except (OSError, RuntimeError) as error:
            summary.failed += 1
            emit("failed", str(error))
        else:
            summary.converted += 1
            emit("converted")
    return summary
