@echo off

if defined DevEnvDir (EXIT /B 0)
CALL "c:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\Common7\Tools\VsDevCmd.bat" -arch=amd64 -host_arch=amd64
