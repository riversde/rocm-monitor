; Custom NSIS script for Windows 11 compatibility
!macro customInit
  ; Windows compatibility handled by electron-builder
!macroend

!macro customInstall
  ; Set install location registry key for proper uninstallation
  WriteRegStr HKLM "SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\GPU Monitor for AI Workloads" "InstallLocation" "$INSTDIR"
!macroend