#!/usr/bin/env python3
"""Convert a folder of MOV videos to H.264/AAC MP4 files using FFmpeg."""

import argparse
from pathlib import Path
import sys

from engine import run_batch


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("folder", type=Path, help="folder containing MOV videos")
    parser.add_argument("-o", "--output", type=Path, help="output folder (default: FOLDER/mp4_output)")
    parser.add_argument("-r", "--recursive", action="store_true", help="include subfolders and preserve their structure")
    parser.add_argument("--overwrite", action="store_true", help="replace existing MP4 files after successful conversion")
    args = parser.parse_args(argv)

    def report(event):
        if event.status == "converted":
            print(f"Converted: {event.source} -> {event.destination}")
        elif event.status == "skipped":
            print(f"Skipped (already exists): {event.destination}")
        elif event.status == "failed":
            print(f"Failed: {event.source}\n{event.message}", file=sys.stderr)

    try:
        summary = run_batch(args.folder, args.output, args.recursive, args.overwrite, report)
    except ValueError as error:
        parser.error(str(error))
    except (OSError, RuntimeError) as error:
        print(str(error), file=sys.stderr)
        return 1
    if not summary.total:
        print("No MOV files found.")
    else:
        print(summary.message())
    return 1 if summary.failed else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nConversion interrupted.", file=sys.stderr)
        sys.exit(130)
