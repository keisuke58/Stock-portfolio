@echo off
REM 毎日実行用バッチファイル
REM このファイルはWindowsタスクスケジューラから呼び出されます

REM スクリプトのディレクトリに移動
cd /d "%~dp0"

REM Pythonのパスを検出（環境変数から）
python --version >nul 2>&1
if errorlevel 1 (
    echo エラー: Pythonが見つかりません。Pythonがインストールされ、PATHに追加されていることを確認してください。
    exit /b 1
)

REM ログファイルに実行時刻を記録
echo ======================================== >> run_daily.log
echo 実行開始: %date% %time% >> run_daily.log
echo ======================================== >> run_daily.log

REM Pythonスクリプトを実行
python run_daily.py config.json >> run_daily.log 2>&1

REM 終了コードを確認
if errorlevel 1 (
    echo エラー: スクリプトの実行中にエラーが発生しました。 >> run_daily.log
    exit /b 1
) else (
    echo 実行完了: %date% %time% >> run_daily.log
)

exit /b 0
