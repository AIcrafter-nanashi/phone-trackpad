@echo off
echo Phone Trackpad - ファイアウォール設定
echo =====================================
netsh advfirewall firewall delete rule name="Phone Trackpad 8765" >nul 2>&1
netsh advfirewall firewall add rule name="Phone Trackpad 8765" dir=in action=allow protocol=TCP localport=8765
if %errorlevel% == 0 (
    echo.
    echo [成功] ポート 8765 を開放しました。
    echo Phone Trackpad を起動できます。
) else (
    echo.
    echo [失敗] 管理者として実行してください。
    echo このファイルを右クリック → 管理者として実行
)
echo.
pause
