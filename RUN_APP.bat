@echo off
echo.
echo ========================================
echo  Smart Grid Mobile App (Flutter Web)
echo ========================================
echo.
echo Building Flutter web app...
cd "c:\Users\Batikha\Desktop\SMART GRID\smartgrid_simulation\mobile"
flutter build web --dart-define=API_BASE_URL=http://192.168.100.226:8000 --web-renderer skwasm --release

echo.
echo Launching on Edge at localhost:3000...
echo Open http://localhost:3000 in Edge browser when ready
echo.

cd build\web
python -m http.server 3000 --bind 127.0.0.1
