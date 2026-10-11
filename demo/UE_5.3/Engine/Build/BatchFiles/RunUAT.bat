@echo off
rem Fake RunUAT that proxies to the python stub next to it.
python "%~dp0_fake_uat.py" %*
