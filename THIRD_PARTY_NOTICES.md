# Bundled components

The Windows installer retains the licenses and notices shipped with its
dependencies. This application uses separate runtime libraries and a separate
FFmpeg executable; users can replace the bundled components.

- CPython 3.13.16 from the Python Software Foundation's python NuGet package.
  License: runtime/python/LICENSE.txt.
  Source: https://github.com/python/cpython/tree/v3.13.16
  Distribution: https://www.nuget.org/packages/python/3.13.16
- PySide6 Essentials and Shiboken6 6.8.3, the Qt for Python bindings.
  License files are retained under runtime/python/Lib/site-packages/*dist-info
  and the shipped Qt package. Qt uses LGPLv3/GPLv3 or commercial licensing;
  the open-source wheels are used.
  Source: https://download.qt.io/official_releases/QtForPython/pyside6/PySide6-6.8.3-src/
  Qt source: https://download.qt.io/official_releases/qt/6.8/6.8.3/
- FFmpeg 8.0.1 essentials build, including libx264, supplied by Gyan.
  This build is GPL-licensed. Its original license and build information are
  retained in third_party/ffmpeg/.
  Distribution and build information:
  https://github.com/GyanD/codexffmpeg/releases/tag/8.0.1
  FFmpeg source: https://ffmpeg.org/releases/ffmpeg-8.0.1.tar.xz
  External library source/build references:
  https://www.gyan.dev/ffmpeg/builds/#libraries

Dependency artifact hashes are recorded in build-manifest.json.
The installer itself is generated with NSIS: https://nsis.sourceforge.io/.
