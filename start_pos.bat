@echo off
REM Navigate to your Django project directory
cd "C:\Users\eng Ally M.Danga\supermarket_pos"

REM Start the Waitress server in a new window.
REM Make sure to adjust the WSGI path if your project name differs.
start "" waitress-serve --listen=*:8000 supermarket_pos.wsgi:application

REM Wait for 10 seconds to let the server start up
timeout /t 10

REM Open Google Chrome to access the POS page
start chrome http://127.0.0.1:8000
