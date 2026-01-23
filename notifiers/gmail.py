"""
Gmail通知モジュール
状態変化 or Daily pick をメールで通知
"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
from datetime import datetime


class GmailNotifier:
    """Gmail SMTPに通知を送信するクラス"""
    
    def __init__(self, smtp_user: str, smtp_password: str, to_email: str):
        """
        Args:
            smtp_user: Gmailアドレス（送信元）
            smtp_password: Gmailアプリパスワード（2段階認証を有効にした場合）
            to_email: 送信先メールアドレス
        """
        self.smtp_user = smtp_user
        self.smtp_password = smtp_password
        self.to_email = to_email
        self.smtp_server = 'smtp.gmail.com'
        self.smtp_port = 587
    
    def send(self, subject: str, message: str) -> bool:
        """メールを送信"""
        try:
            # メール作成
            msg = MIMEMultipart()
            msg['From'] = self.smtp_user
            msg['To'] = self.to_email
            msg['Subject'] = subject
            
            # 本文を追加（HTML形式で送信）
            msg.attach(MIMEText(message, 'html', 'utf-8'))
            
            # SMTPサーバーに接続して送信
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.smtp_user, self.smtp_password)
            server.send_message(msg)
            server.quit()
            
            print(f"✓ Gmail通知送信成功: {subject}")
            return True
        except Exception as e:
            print(f"✗ Gmail通知エラー: {e}")
            return False
    
    def format_state_change_message(
        self,
        symbol: str,
        old_state: str,
        new_state: str,
        price: float
    ) -> str:
        """状態変化時のメッセージを生成（HTML形式）"""
        emoji_map = {
            'WATCH': '⚠️',
            'BASE': '📊',
            'BUY': '🚀',
            'NORMAL': '📈'
        }
        
        state_names = {
            'WATCH': '急落検知（WATCH入り）',
            'BASE': '低迷継続（BASE入り）',
            'BUY': '反転シグナル（BUY候補）',
            'NORMAL': '通常状態'
        }
        
        emoji = emoji_map.get(new_state, '📌')
        state_name = state_names.get(new_state, new_state)
        
        timestamp = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
        
        # HTML形式でメッセージを作成
        html = f"""
        <html>
        <body>
            <h2>{emoji} {symbol} 状態変化通知</h2>
            <p><strong>状態:</strong> {old_state or 'NONE'} → {new_state}</p>
            <p><strong>{state_name}</strong></p>
            <hr>
            <p><strong>現在価格:</strong> ${price:,.2f}</p>
            <p><strong>時刻:</strong> {timestamp}</p>
        """
        
        # 仮想通貨か米国株かでURLを変更
        import sys
        import os
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from signals import is_crypto_symbol
        if is_crypto_symbol(symbol):
            url = f"https://www.coingecko.com/en/coins/{symbol.lower()}"
        else:
            url = f"https://finance.yahoo.com/quote/{symbol.upper()}"
        
        html += f'<p><a href="{url}">詳細を見る</a></p>'
        html += """
        </body>
        </html>
        """
        
        return html
    
    def format_daily_pick_message(self, daily_pick: dict) -> str:
        """Daily pickのメッセージを生成（HTML形式）"""
        symbol = daily_pick['symbol']
        category = daily_pick.get('asset_category', 'その他')
        state = daily_pick.get('current_state', 'NORMAL')
        total_score = daily_pick.get('total_score', 0)
        confidence = daily_pick.get('confidence', 'Spec')
        
        value_score = daily_pick.get('value_score', 0)
        momentum_score = daily_pick.get('momentum_score', 0)
        stability_score = daily_pick.get('stability_score', 0)
        
        current_price = daily_pick.get('current_price', 0)
        ath_ratio = daily_pick.get('ath_ratio')
        return_30d = daily_pick.get('return_30d')
        
        timestamp = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
        
        # 信頼度の絵文字
        confidence_emoji = {
            'High': '🟢',
            'Mid': '🟡',
            'Spec': '🟠'
        }
        
        emoji = confidence_emoji.get(confidence, '⚪')
        
        html = f"""
        <html>
        <body>
            <h2>{emoji} 【今日の1個】{symbol}</h2>
            <p><strong>信頼度:</strong> {confidence} | <strong>状態:</strong> {state} | <strong>カテゴリ:</strong> {category}</p>
            <hr>
            <h3>投資スコア: {total_score:.1f}/100点</h3>
            <ul>
                <li>Value（割安度）: {value_score:.1f}/100</li>
                <li>Momentum（反転）: {momentum_score:.1f}/100</li>
                <li>Stability（安定性）: {stability_score:.1f}/100</li>
            </ul>
            <hr>
            <h3>基本情報</h3>
            <p><strong>現在価格:</strong> ${current_price:,.2f}</p>
        """
        
        if ath_ratio:
            html += f"<p><strong>ATH比:</strong> {ath_ratio:.1%} (ATHから{(1-ath_ratio)*100:.1f}%下落)</p>"
        
        if return_30d:
            html += f"<p><strong>30日リターン:</strong> {return_30d:+.1f}%</p>"
        
        html += f"<p><strong>時刻:</strong> {timestamp}</p>"
        
        # URL
        import sys
        import os
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from signals import is_crypto_symbol
        if is_crypto_symbol(symbol):
            url = f"https://www.coingecko.com/en/coins/{symbol.lower()}"
        else:
            url = f"https://finance.yahoo.com/quote/{symbol.upper()}"
        
        html += f'<p><a href="{url}">詳細を見る</a></p>'
        html += """
        </body>
        </html>
        """
        
        return html
    
    def notify_state_change(
        self,
        symbol: str,
        old_state: str,
        new_state: str,
        price: float
    ) -> bool:
        """状態変化を通知"""
        subject = f"【{symbol}】状態変化: {old_state or 'NONE'} → {new_state}"
        message = self.format_state_change_message(symbol, old_state, new_state, price)
        return self.send(subject, message)
    
    def notify_daily_pick(self, daily_pick: dict) -> bool:
        """Daily pickを通知"""
        symbol = daily_pick['symbol']
        subject = f"【今日の1個】{symbol} - 投資スコア: {daily_pick.get('total_score', 0):.1f}/100"
        message = self.format_daily_pick_message(daily_pick)
        return self.send(subject, message)
