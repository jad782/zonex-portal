@echo off
chcp 65001 >nul
title ZONE X - Portal Server
cd /d "%~dp0"
echo ====================================
echo    ZONE X - تشغيل موقع الاشتراكات
echo ====================================
echo.
echo الموقع:        http://127.0.0.1:8001/
echo لوحة الادارة:  http://127.0.0.1:8001/manage/
echo.
echo لا تسكّر هذه النافذة طالما بدك الموقع شغّال.
echo ====================================
echo.
"..\CafeCloud\env\Scripts\python.exe" manage.py runserver 8001
pause
