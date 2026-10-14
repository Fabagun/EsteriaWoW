@echo off
setlocal
if "%~1"=="" exit /b 2
call "C:\Program Files\Microsoft Visual Studio\18\Community\VC\Auxiliary\Build\vcvarsall.bat" x86
if not "%errorlevel%"=="0" exit /b %errorlevel%
if not exist "%~1" mkdir "%~1"
set "race_source=%~dp0..\..\AzerothPlex\build\wxl-core"
cl.exe /nologo /std:c++20 /O2 /EHsc /MT /LD /DWXL_EXTENSION /DWIN32_LEAN_AND_MEAN /DNOMINMAX ^
    /I"%race_source%\include" "%race_source%\extensions\races-64-esteria\MoreRaces.cpp" ^
    /Fo"%~1\MoreRaces.obj" /link /INCREMENTAL:NO /OUT:"%~1\races-64-esteria.dll" ^
    /IMPLIB:"%~1\races-64-esteria.lib"
if not "%errorlevel%"=="0" exit /b %errorlevel%
cl.exe /nologo /std:c++20 /O2 /EHsc /MT "%~dp0TestRaceCapacity.cpp" /Fo"%~1\TestRaceCapacity.obj" ^
    /link /DYNAMICBASE:NO /BASE:0x04000000 /OUT:"%~1\TestRaceCapacity.exe"
if not "%errorlevel%"=="0" exit /b %errorlevel%
"%~1\TestRaceCapacity.exe" "%~1\races-64-esteria.dll"
exit /b %errorlevel%
