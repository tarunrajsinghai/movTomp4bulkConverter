Unicode True
!include "MUI2.nsh"
!include "x64.nsh"

Name "MOV to MP4 Converter"
OutFile "${OUTPUT}"
InstallDir "$LOCALAPPDATA\Programs\MOV to MP4 Converter"
InstallDirRegKey HKCU "Software\MOVtoMP4Converter" "InstallDir"
RequestExecutionLevel user
SetCompressor /SOLID lzma
SetCompressorDictSize 32
ShowInstDetails show
ShowUninstDetails show

VIProductVersion "${VERSION}.0"
VIAddVersionKey "ProductName" "MOV to MP4 Converter"
VIAddVersionKey "FileDescription" "MOV to MP4 Converter Installer"
VIAddVersionKey "FileVersion" "${VERSION}"
VIAddVersionKey "ProductVersion" "${VERSION}"
VIAddVersionKey "LegalCopyright" "MOV to MP4 Converter contributors"

!define MUI_ABORTWARNING
!define MUI_FINISHPAGE_RUN "$INSTDIR\runtime\python\pythonw.exe"
!define MUI_FINISHPAGE_RUN_PARAMETERS '$\"$INSTDIR\app.py$\"'
!define MUI_FINISHPAGE_RUN_TEXT "Launch MOV to MP4 Converter"
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_LANGUAGE "English"

Function .onInit
    ${IfNot} ${RunningX64}
        MessageBox MB_ICONSTOP "This installer requires 64-bit Windows."
        Abort
    ${EndIf}
    SetRegView 64
    SetShellVarContext current
FunctionEnd

Section "Application"
    SetOutPath "$INSTDIR"
    File /r "${PAYLOAD}/*"
    WriteUninstaller "$INSTDIR\Uninstall.exe"
    CreateDirectory "$SMPROGRAMS\MOV to MP4 Converter"
    CreateShortCut "$SMPROGRAMS\MOV to MP4 Converter\MOV to MP4 Converter.lnk" "$INSTDIR\runtime\python\pythonw.exe" '"$INSTDIR\app.py"'
    CreateShortCut "$SMPROGRAMS\MOV to MP4 Converter\Uninstall.lnk" "$INSTDIR\Uninstall.exe"
    CreateShortCut "$DESKTOP\MOV to MP4 Converter.lnk" "$INSTDIR\runtime\python\pythonw.exe" '"$INSTDIR\app.py"'
    WriteRegStr HKCU "Software\MOVtoMP4Converter" "InstallDir" "$INSTDIR"
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\MOVtoMP4Converter" "DisplayName" "MOV to MP4 Converter"
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\MOVtoMP4Converter" "DisplayVersion" "${VERSION}"
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\MOVtoMP4Converter" "UninstallString" '"$INSTDIR\Uninstall.exe"'
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\MOVtoMP4Converter" "DisplayIcon" "$INSTDIR\runtime\python\pythonw.exe"
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\MOVtoMP4Converter" "InstallLocation" "$INSTDIR"
    WriteRegDWORD HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\MOVtoMP4Converter" "NoModify" 1
    WriteRegDWORD HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\MOVtoMP4Converter" "NoRepair" 1
SectionEnd

Function un.onInit
    SetRegView 64
    SetShellVarContext current
FunctionEnd

Section "Uninstall"
    Delete "$DESKTOP\MOV to MP4 Converter.lnk"
    Delete "$SMPROGRAMS\MOV to MP4 Converter\MOV to MP4 Converter.lnk"
    Delete "$SMPROGRAMS\MOV to MP4 Converter\Uninstall.lnk"
    RMDir "$SMPROGRAMS\MOV to MP4 Converter"
    ; Remove only application-owned paths. Preserve videos and other user files.
    RMDir /r "$INSTDIR\runtime"
    RMDir /r "$INSTDIR\third_party"
    RMDir /r "$INSTDIR\__pycache__"
    Delete "$INSTDIR\app.py"
    Delete "$INSTDIR\engine.py"
    Delete "$INSTDIR\convert.py"
    Delete "$INSTDIR\launch.cmd"
    Delete "$INSTDIR\README.md"
    Delete "$INSTDIR\THIRD_PARTY_NOTICES.md"
    Delete "$INSTDIR\build-manifest.json"
    Delete "$INSTDIR\Uninstall.exe"
    RMDir "$INSTDIR"
    DeleteRegKey HKCU "Software\MOVtoMP4Converter"
    DeleteRegKey HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\MOVtoMP4Converter"
SectionEnd
