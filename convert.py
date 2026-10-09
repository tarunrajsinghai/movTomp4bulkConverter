#!/usr/bin/env python3
"""Convert a folder of MOV videos to H.264/AAC MP4 files using FFmpeg."""

import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


def convert(source, destination, ffmpeg, overwrite=False):
    """Publish a completed conversion; never leave a partial destination."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(
        prefix=".conversion-", suffix=".mp4", dir=destination.parent
    )
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
        )
        if result.returncode:
            raise RuntimeError(result.stderr.strip() or "FFmpeg conversion failed")
        if overwrite:
            os.replace(temporary, destination)
        else:
            # Exclusive publication also protects against another process writing
            # the destination after the initial existence check.
            os.link(temporary, destination)
    finally:
        Path(temporary).unlink(missing_ok=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("folder", type=Path, help="folder containing MOV videos")
    parser.add_argument("-o", "--output", type=Path, help="output folder (default: FOLDER/mp4_output)")
    parser.add_argument("-r", "--recursive", action="store_true", help="include subfolders and preserve their structure")
    parser.add_argument("--overwrite", action="store_true", help="replace existing MP4 files after successful conversion")
    args = parser.parse_args(argv)

    folder = args.folder.resolve()
    output = (args.output or folder / "mp4_output").resolve()
    if not folder.is_dir():
        parser.error(f"input folder does not exist or is not a directory: {folder}")
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        parser.error("FFmpeg is required; install it and ensure ffmpeg is on PATH")

    try:
        entries = folder.rglob("*") if args.recursive else folder.iterdir()
        videos = sorted(
            path for path in entries
            if path.is_file() and path.suffix.lower() == ".mov"
            and (output == folder or not path.is_relative_to(output))
        )
    except OSError as error:
        print(f"Cannot scan input: {error}", file=sys.stderr)
        return 1
    if not videos:
        print("No MOV files found.")
        return 0

    converted = skipped = failed = 0
    for source in videos:
        destination = output / source.relative_to(folder).with_suffix(".mp4")
        if destination.exists() and not args.overwrite:
            print(f"Skipped (already exists): {destination}")
            skipped += 1
            continue
        try:
            convert(source, destination, ffmpeg, args.overwrite)
        except FileExistsError:
            print(f"Skipped (already exists): {destination}")
            skipped += 1
        except (OSError, RuntimeError) as error:
            print(f"Failed: {source}\n{error}", file=sys.stderr)
            failed += 1
        else:
            print(f"Converted: {source} -> {destination}")
            converted += 1
    print(f"Done: {converted} converted, {skipped} skipped, {failed} failed.")
    return 1 if failed else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nConversion interrupted.", file=sys.stderr)
        sys.exit(130)
