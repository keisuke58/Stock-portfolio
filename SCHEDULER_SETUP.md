# 毎朝自動実行の設定方法

このドキュメントでは、`run_daily.py`を毎朝自動実行するための設定方法を説明します。

## 方法1: PowerShellスクリプトを使用（推奨）

### 手順

1. **PowerShellを管理者権限で開く**
   - Windowsキーを押す
   - "PowerShell"と入力
   - "Windows PowerShell"を右クリック
   - "管理者として実行"を選択

2. **スクリプトを実行**
   ```powershell
   cd C:\Users\nishi\git\Crypto-Price-Movement-Discord-Alerting-Bot
   .\setup_scheduler.ps1
   ```

3. **実行ポリシーのエラーが出る場合**
   ```powershell
   Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
   ```
   その後、再度 `.\setup_scheduler.ps1` を実行

### 設定内容

- **実行時刻**: 毎朝 9:00 AM
- **タスク名**: `CryptoPriceDailyRunner`
- **ログファイル**: `run_daily.log`（実行履歴が記録されます）

## 方法2: 手動でタスクスケジューラに登録

### 手順

1. **タスクスケジューラを開く**
   - Windowsキー + R を押す
   - `taskschd.msc` と入力してEnter

2. **基本タスクの作成**
   - 右側の「基本タスクの作成」をクリック
   - 名前: `CryptoPriceDailyRunner`
   - 説明: `毎朝自動実行: Crypto Price Movement Discord Alerting Bot`

3. **トリガーの設定**
   - 「毎日」を選択
   - 開始時刻: `09:00:00`
   - 繰り返し: `毎日`

4. **操作の設定**
   - 「プログラムの開始」を選択
   - プログラム/スクリプト: `C:\Users\nishi\git\Crypto-Price-Movement-Discord-Alerting-Bot\run_daily.bat`
   - 開始場所: `C:\Users\nishi\git\Crypto-Price-Movement-Discord-Alerting-Bot`

5. **完了**
   - 「完了」をクリック

## 実行時間の変更方法

1. タスクスケジューラを開く
2. `CryptoPriceDailyRunner` を検索
3. 右クリック -> 「プロパティ」
4. 「トリガー」タブを選択
5. トリガーを選択して「編集」
6. 開始時刻を変更して「OK」

## ログの確認

実行履歴は `run_daily.log` ファイルに記録されます。

```powershell
# ログを確認
Get-Content run_daily.log -Tail 50
```

## タスクの無効化/削除

### 無効化（一時停止）
```powershell
Disable-ScheduledTask -TaskName "CryptoPriceDailyRunner"
```

### 有効化（再開）
```powershell
Enable-ScheduledTask -TaskName "CryptoPriceDailyRunner"
```

### 削除
```powershell
Unregister-ScheduledTask -TaskName "CryptoPriceDailyRunner" -Confirm:$false
```

## 手動実行（テスト）

タスクスケジューラに登録する前に、手動で実行して動作確認できます：

```cmd
cd C:\Users\nishi\git\Crypto-Price-Movement-Discord-Alerting-Bot
run_daily.bat
```

または：

```cmd
python run_daily.py config.json
```

## トラブルシューティング

### Pythonが見つからないエラー

- Pythonがインストールされているか確認
- PATH環境変数にPythonが追加されているか確認
- バッチファイル内のPythonパスを直接指定する場合:
  ```batch
  C:\Python310\python.exe run_daily.py config.json
  ```

### タスクが実行されない

1. タスクスケジューラでタスクの状態を確認
2. 「履歴」タブでエラーメッセージを確認
3. `run_daily.log` でエラー内容を確認
4. 手動実行で動作確認

### ネットワークエラー

- タスクの設定で「ネットワーク接続時のみ実行」が有効になっている場合、ネットワーク接続を確認
- 設定を変更する場合は、タスクのプロパティ -> 「条件」タブ
