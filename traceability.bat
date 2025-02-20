@echo off
cd /d "C:\Users\lenovo\Documents\FourF"
echo Activating Virtual Environment...
call .\myenv\Scripts\activate

echo Starting Modbus Communication...
start cmd /k "python manage.py start_modbus"

timeout /t 1

echo Starting Django Server...
start cmd /k "python manage.py runserver 0.0.0.0:8000"

timeout /t 3

echo Opening Web Page in Full Screen on Microsoft Edge...
start msedge --kiosk http://127.0.0.1:8000 --edge-kiosk-type=fullscreen --disable-pinch
exit
