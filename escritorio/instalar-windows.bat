@echo off
REM OmniAgent Control - crea un acceso directo en el Escritorio que abre el panel como app.
set "URL=https://omniagent-control.onrender.com"
set /p URLNUEVA="URL del panel [%URL%]: "
if not "%URLNUEVA%"=="" set "URL=%URLNUEVA%"
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$url='%URL%';" ^
  "$nav=@(\"$env:ProgramFiles\Google\Chrome\Application\chrome.exe\",\"${env:ProgramFiles(x86)}\Google\Chrome\Application\chrome.exe\",\"$env:LocalAppData\Google\Chrome\Application\chrome.exe\",\"${env:ProgramFiles(x86)}\Microsoft\Edge\Application\msedge.exe\",\"$env:ProgramFiles\Microsoft\Edge\Application\msedge.exe\") | Where-Object { Test-Path $_ } | Select-Object -First 1;" ^
  "$lnk=Join-Path ([Environment]::GetFolderPath('Desktop')) 'OmniAgent Control.lnk';" ^
  "$s=(New-Object -ComObject WScript.Shell).CreateShortcut($lnk);" ^
  "if ($nav) { $s.TargetPath=$nav; $s.Arguments='--app=' + $url } else { $s.TargetPath=$url };" ^
  "$s.Description='Centro de mando de OmniAgent - EstrategIA Digital 3.0'; $s.Save(); Write-Host ('Acceso directo creado: ' + $lnk)"
pause
