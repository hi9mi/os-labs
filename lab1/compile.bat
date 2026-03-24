@echo off
chcp 65001 > nul
setlocal enabledelayedexpansion

if "%~1"=="" goto err

set files=
set keys=

:loop
if "%~1"=="" goto done

set arg=%~1

echo %arg% | findstr /B /C:"/" > nul
if not errorlevel 1 (
    set keys=!keys! %arg%
) else (
    set files=!files! %arg%
)

shift
goto loop

:done
echo tcc%files%%keys%
pause
goto end

:err
echo Укажите файлы и ключи, например:
echo compile.bat main.c /O2 test.c /Wall
pause

:end
endlocal
