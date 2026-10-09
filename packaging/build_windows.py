#!/usr/bin/env python3
"""Build an offline Windows x64 installer on Windows or Linux with NSIS."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import urllib.request
import zipfile


ROOT = Path(__file__).resolve().parents[1]
VERSION = "1.0.0"
ASSETS = [
    (
        "python.3.13.16.nupkg",
        "https://api.nuget.org/v3-flatcontainer/python/3.13.16/python.3.13.16.nupkg",
        "95fad176338f1d6a799e45946488063f4aa61764e6cff2f132ddeffbf7a04c34",
    ),
    (
        "ffmpeg-8.0.1-essentials_build.zip",
        "https://github.com/GyanD/codexffmpeg/releases/download/8.0.1/ffmpeg-8.0.1-essentials_build.zip",
        "e2aaeaa0fdbc397d4794828086424d4aaa2102cef1fb6874f6ffd29c0b88b673",
    ),
]
WHEELS = {
    "PySide6-Essentials": (
        "PySide6_Essentials-6.8.3-cp39-abi3-win_amd64.whl",
        "3c0fae5550aff69f2166f46476c36e0ef56ce73d84829eac4559770b0c034b07",
    ),
    "shiboken6": (
        "shiboken6-6.8.3-cp39-abi3-win_amd64.whl",
        "bca3a94513ce9242f7d4bbdca902072a1631888e0aa3a8711a52cc5dbe93588f",
    ),
}


def download(cache, name, url, expected):
    destination = cache / name
    if not destination.exists():
        print(f"Downloading {name}…", flush=True)
        temporary = destination.with_suffix(destination.suffix + ".download")
        try:
            with urllib.request.urlopen(url, timeout=120) as source, temporary.open("wb") as target:
                shutil.copyfileobj(source, target)
            if hashlib.sha256(temporary.read_bytes()).hexdigest() != expected:
                raise RuntimeError(f"Checksum mismatch for {name}")
            temporary.replace(destination)
        finally:
            temporary.unlink(missing_ok=True)
    if hashlib.sha256(destination.read_bytes()).hexdigest() != expected:
        raise RuntimeError(f"Checksum mismatch for cached {name}; remove it and retry")
    print(f"Verified {name}", flush=True)
    return destination


def extract(archive, target, prefix=""):
    """Safely extract only files below the archive's selected prefix."""
    target.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive) as bundle:
        for member in bundle.infolist():
            if member.is_dir() or not member.filename.startswith(prefix):
                continue
            relative = member.filename[len(prefix):]
            if not relative:
                continue
            destination = (target / relative).resolve()
            if not destination.is_relative_to(target.resolve()):
                raise RuntimeError(f"Unsafe archive path: {member.filename}")
            destination.parent.mkdir(parents=True, exist_ok=True)
            with bundle.open(member) as source, destination.open("wb") as output:
                shutil.copyfileobj(source, output)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, default=ROOT / "build" / "downloads")
    parser.add_argument("--makensis", default=shutil.which("makensis"))
    args = parser.parse_args()
    if not args.makensis:
        parser.error("NSIS is required. Install NSIS and put makensis on PATH, or use --makensis.")
    cache = args.cache.resolve()
    cache.mkdir(parents=True, exist_ok=True)
    assets = {name: download(cache, name, url, checksum) for name, url, checksum in ASSETS}
    for package, (filename, checksum) in WHEELS.items():
        with urllib.request.urlopen(f"https://pypi.org/pypi/{package}/6.8.3/json", timeout=30) as response:
            metadata = json.load(response)
        wheel = next(item for item in metadata["urls"] if item["filename"] == filename)
        if wheel["digests"]["sha256"] != checksum:
            raise RuntimeError(f"PyPI checksum differs from the pin for {filename}")
        assets[filename] = download(cache, filename, wheel["url"], checksum)

    stage = ROOT / "build" / "windows" / "app"
    if stage.exists():
        shutil.rmtree(stage)
    runtime = stage / "runtime"
    python = runtime / "python"
    extract(assets["python.3.13.16.nupkg"], python, "tools/")
    # No pip or headers are needed. Keep the stdlib, license, and runtime DLLs.
    for directory in ("Lib/site-packages", "Scripts", "include", "libs"):
        shutil.rmtree(python / directory, ignore_errors=True)
    for filename, _ in WHEELS.values():
        extract(assets[filename], python / "Lib" / "site-packages")
    with zipfile.ZipFile(assets["ffmpeg-8.0.1-essentials_build.zip"]) as bundle:
        prefix = "ffmpeg-8.0.1-essentials_build/"
        for executable in ("ffmpeg.exe", "ffprobe.exe"):
            (runtime / executable).write_bytes(bundle.read(prefix + "bin/" + executable))
        notices = stage / "third_party" / "ffmpeg"
        notices.mkdir(parents=True)
        for filename in ("LICENSE", "LICENSE.txt", "README", "README.txt"):
            if prefix + filename in bundle.namelist():
                (notices / filename).write_bytes(bundle.read(prefix + filename))
    for filename in ("app.py", "engine.py", "convert.py", "README.md", "THIRD_PARTY_NOTICES.md"):
        shutil.copy2(ROOT / filename, stage / filename)
    (stage / "launch.cmd").write_text(
        '@echo off\r\nstart "" "%~dp0runtime\\python\\pythonw.exe" "%~dp0app.py"\r\n',
        encoding="utf-8",
    )
    manifest = {
        "application_version": VERSION,
        "platform": "windows-x64",
        "sha256": {
            name: hashlib.sha256(path.read_bytes()).hexdigest()
            for name, path in assets.items()
        },
    }
    (stage / "build-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    required = (
        python / "pythonw.exe", python / "python.exe", python / "python313.dll",
        python / "Lib/site-packages/PySide6/QtWidgets.pyd",
        python / "Lib/site-packages/PySide6/plugins/platforms/qwindows.dll",
        python / "Lib/site-packages/PySide6/msvcp140.dll",
        runtime / "ffmpeg.exe", runtime / "ffprobe.exe", notices / "LICENSE",
    )
    for path in required:
        if not path.is_file():
            raise RuntimeError(f"Missing required payload: {path}")
    dist = ROOT / "dist"
    dist.mkdir(exist_ok=True)
    output = dist / f"MOV-to-MP4-Setup-{VERSION}-x64.exe"
    define = "/D" if os.name == "nt" else "-D"
    subprocess.run([
        args.makensis, f"{define}PAYLOAD={stage}", f"{define}OUTPUT={output}",
        f"{define}VERSION={VERSION}", str(ROOT / "packaging" / "installer.nsi"),
    ], check=True)
    if output.read_bytes()[:2] != b"MZ":
        raise RuntimeError("Installer is not a Windows executable")
    checksum = hashlib.sha256(output.read_bytes()).hexdigest()
    output.with_suffix(".exe.sha256").write_text(f"{checksum}  {output.name}\n")
    shutil.copy2(stage / "build-manifest.json", dist / "build-manifest.json")
    print(f"Created {output} ({output.stat().st_size / 1024 / 1024:.1f} MB)", flush=True)
    print(f"SHA256: {checksum}", flush=True)


if __name__ == "__main__":
    main()
