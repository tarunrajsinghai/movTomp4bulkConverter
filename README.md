# Bulk MOV to MP4 converter

Convert the MOV videos in a folder to MP4 with a Python command-line tool.
It uses FFmpeg to encode H.264 video and AAC audio for broad playback support.
Original files are kept. Each finished video is saved atomically, so a failed
conversion does not leave a partial MP4 or damage an existing output.

## Requirements

- Python 3.10 or newer. No Python packages are needed.
- FFmpeg on your `PATH`, with the `libx264` and AAC encoders.
- FFprobe on your `PATH` to run the tests (included with FFmpeg).

On Ubuntu/Debian, install FFmpeg with `sudo apt-get install ffmpeg`.
On macOS with Homebrew, use `brew install ffmpeg`. On Windows, install
FFmpeg and add its `bin` folder to `PATH`.

## Usage

From the repository directory:

```sh
python3 convert.py "/path/to/videos"
python3 convert.py "/path/to/videos" --recursive --output "/path/to/mp4s"
python3 convert.py "/path/to/videos" --overwrite
python3 convert.py --help
```

On Windows, use `python` instead of `python3` if needed.

By default, output goes to `mp4_output` inside the input folder. Both `.mov`
and `.MOV` files are recognized. Recursive mode preserves relative subfolders
and excludes the output folder from scanning. Files with an existing output
are skipped unless `--overwrite` is provided. A corrupt input is reported and
the remaining videos are still processed. The command exits with status 1 if
any conversion fails, 2 for invalid arguments, or 0 on success (including skips
or an empty folder).

Conversions run sequentially. The default video quality is CRF 23; this is
lossy encoding. Odd video dimensions are padded to even dimensions. Audio
tracks are included when present; subtitles and data tracks are omitted.
Files whose names differ only by `.mov` versus `.MOV` share an output name,
so the later file is skipped unless overwrite is enabled.

## Development checks

```sh
python3 -m unittest discover -s tests -v
```

The tests create short synthetic MOV videos in temporary directories, invoke
the actual converter, and verify the resulting codecs and duration with
FFprobe. They also check recursion, overwrite protection, failure recovery,
and cleanup. No services, credentials, or network access are required.
