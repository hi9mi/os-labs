@echo off
chcp 65001 > nul
if "%1"=="" goto err

dir "%1\*.*" /s /b | findstr /R "\.[a-zA-Z]$"
pause
goto end

:err
echo Укажите путь, например C:\ или F:\labs_test\
pause

:end
