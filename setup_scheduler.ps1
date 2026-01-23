# Windowsタスクスケジューラに毎朝自動実行タスクを登録するPowerShellスクリプト
# 管理者権限で実行してください

# スクリプトのディレクトリを取得
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$batFile = Join-Path $scriptDir "run_daily.bat"

# タスク名
$taskName = "CryptoPriceDailyRunner"

# タスクが既に存在するか確認
$existingTask = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue

if ($existingTask) {
    Write-Host "既存のタスクが見つかりました。削除します..." -ForegroundColor Yellow
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
}

# タスクのアクション（実行するプログラム）
$action = New-ScheduledTaskAction -Execute $batFile -WorkingDirectory $scriptDir

# タスクのトリガー（毎朝9時00分に実行）
$trigger = New-ScheduledTaskTrigger -Daily -At 9:00AM

# タスクの設定
$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -RunOnlyIfNetworkAvailable `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 10)

# タスクのプリンシパル（現在のユーザーで実行）
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive

# タスクを登録
try {
    Register-ScheduledTask `
        -TaskName $taskName `
        -Action $action `
        -Trigger $trigger `
        -Settings $settings `
        -Principal $principal `
        -Description "毎朝自動実行: Crypto Price Movement Discord Alerting Bot" `
        -Force
    
    Write-Host "`nタスクスケジューラへの登録が完了しました！" -ForegroundColor Green
    Write-Host "タスク名: $taskName" -ForegroundColor Green
    Write-Host "実行時刻: 毎朝 9:00 AM" -ForegroundColor Green
    Write-Host "実行ファイル: $batFile" -ForegroundColor Green
    Write-Host "`nタスクの確認方法:" -ForegroundColor Cyan
    Write-Host "  1. Windowsキー + R を押す" -ForegroundColor Cyan
    Write-Host "  2. 'taskschd.msc' と入力してEnter" -ForegroundColor Cyan
    Write-Host "  3. '$taskName' を検索" -ForegroundColor Cyan
    Write-Host "`n手動で実行時間を変更する場合:" -ForegroundColor Yellow
    Write-Host "  タスクスケジューラで '$taskName' を右クリック -> プロパティ -> トリガー タブ" -ForegroundColor Yellow
} catch {
    Write-Host "`nエラー: タスクの登録に失敗しました。" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    Write-Host "`n管理者権限で実行していることを確認してください。" -ForegroundColor Yellow
    exit 1
}
