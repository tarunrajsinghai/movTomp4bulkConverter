# Bulk MOV to MP4 converter

Convert the MOV videos in a folder to MP4 with a desktop app or command-line tool.
It uses FFmpeg to encode H.264 video and AAC audio for broad playback support.
Original files are kept. Each finished video is saved atomically, so a failed
conversion does not leave a partial MP4 or damage an existing output.

## Windows 11 desktop app

The Windows x64 installer includes Python, the desktop UI, and FFmpeg. You do
not need to install Python or FFmpeg separately to use the installed app.

1. Open this repository's **Actions** tab and select a successful **Windows
   installer** run for the latest commit.
2. Download **MOV-to-MP4-Windows-Installer** from the run's Artifacts section
   (GitHub requires you to sign in), then extract the ZIP.
3. Run **MOV-to-MP4-Setup-1.0.0-x64.exe** and follow the installer.
4. Open **MOV to MP4 Converter** using its desktop or Start menu shortcut.
5. Browse to your MOV folder, optionally choose an output folder, and click
   **Convert videos**.

The app shows progress by file and a result log. **Include subfolders** retains
their relative paths. **Stop after current video** finishes the active video
before stopping the batch. **Open output folder** takes you to the saved MP4s.
Leaving the output field empty saves to `mp4_output` inside the input folder.
Existing MP4s are skipped unless **Replace existing MP4 files** is selected.

Installation is for the current user and does not need administrator access.
Uninstall from Windows Settings → Apps → Installed apps. Your videos and other
user files are preserved. The installer is unsigned; Windows may display an
unrecognized-publisher warning. It is intended for x64 Windows 10/11.

## Run the UI from source

With Python and FFmpeg installed, run these commands from the project folder:

```powershell
py -m pip install -r requirements-ui.txt
py app.py
```

On macOS/Linux, use `python3` instead of `py`.

## Command-line requirements

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

To test the UI, first install `requirements-ui.txt`, then run:

```sh
python3 -m unittest discover -s tests_ui -v
```

On a Linux machine without a display, prefix the UI test command with
`QT_QPA_PLATFORM=offscreen`. A quick UI launch check is
`python3 app.py --smoke-test` (it opens and closes the window automatically).

The tests create short synthetic MOV videos in temporary directories, invoke
the actual converter, and verify the resulting codecs and duration with
FFprobe. They also check recursion, overwrite protection, failure recovery,
and cleanup. No services, credentials, or network access are required.

## Build the Windows installer

The build can run on Windows or Linux and always produces a Windows x64 EXE.
It uses the full Python runtime and Qt wheels directly, so cross-building does
not require PyInstaller or Wine. Downloaded runtime artifacts have pinned
SHA256 checksums; mismatches stop the build. Licenses and component hashes
are included in the installed application.

On Windows, install Python and NSIS, then build:

```powershell
winget install --exact --id NSIS.NSIS
# Reopen PowerShell after installing NSIS.
py packaging/build_windows.py --makensis "${env:ProgramFiles(x86)}\NSIS\makensis.exe"
```

On Linux, install NSIS with your package manager and run
`python3 packaging/build_windows.py`. Use `--makensis /path/to/makensis` if
the compiler is not on PATH. Build downloads are cached under `build/downloads`
and can be reused with `--cache /path/to/cache`.

The result is `dist/MOV-to-MP4-Setup-1.0.0-x64.exe`, accompanied by a SHA256
checksum and build manifest. The GitHub Actions workflow builds on Windows,
runs CLI and UI integration tests with the bundled Python, checks installation
and uninstall behavior, and uploads the installer only after those checks pass.
This workflow can also be started manually from the Actions tab.
