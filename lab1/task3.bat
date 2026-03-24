@echo off
chcp 65001 > nul
if "%1"=="" goto err

dir "%1\a*" /s /b 2>nul
dir "%1\ba*" /s /b 2>nul
pause
goto end

:err
echo Укажите путь, например C:\ или F:\labs_test\
pause

:end
