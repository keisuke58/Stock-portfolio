"""
HTMLレポート生成モジュール
価格チャート、スコア内訳、比較グラフなどを含む可視化レポートを生成
"""
import os
import base64
from io import BytesIO
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import matplotlib
matplotlib.use('Agg')  # GUI不要のバックエンド
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.figure import Figure
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.offline as pyo


class ReportGenerator:
    """可視化レポート生成クラス"""
    
    def __init__(self, output_dir: str = 'reports'):
        """出力ディレクトリを初期化"""
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
    
    def generate_html_report(
        self,
        top_picks: List[Dict],
        candidates: List[Dict],
        date_str: Optional[str] = None
    ) -> str:
        """
        HTMLレポートを生成して保存
        
        Args:
            top_picks: 上位3個のピック
            candidates: 全候補リスト
            date_str: 日付文字列（YYYY-MM-DD形式、Noneの場合は今日）
        
        Returns:
            保存されたファイルパス
        """
        if date_str is None:
            date_str = datetime.utcnow().strftime('%Y-%m-%d')
        
        # HTMLコンテンツを生成
        html_content = self._generate_html_content(top_picks, candidates, date_str)
        
        # ファイルに保存
        filename = f"{date_str}_report.html"
        filepath = os.path.join(self.output_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        return filepath
    
    def _generate_html_content(
        self,
        top_picks: List[Dict],
        candidates: List[Dict],
        date_str: str
    ) -> str:
        """HTMLコンテンツを生成"""
        html_parts = []
        
        # HTMLヘッダー
        html_parts.append("""<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>投資分析レポート - """ + date_str + """</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .container {
            max-width: 1400px;
            margin: 0 auto;
            background-color: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        h1 {
            color: #2c3e50;
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
        }
        h2 {
            color: #34495e;
            margin-top: 30px;
            border-left: 4px solid #3498db;
            padding-left: 10px;
        }
        .pick-card {
            border: 2px solid #e0e0e0;
            border-radius: 8px;
            padding: 20px;
            margin: 20px 0;
            background-color: #fafafa;
        }
        .pick-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
        }
        .symbol {
            font-size: 24px;
            font-weight: bold;
            color: #2c3e50;
        }
        .score {
            font-size: 32px;
            font-weight: bold;
            color: #27ae60;
        }
        .score-detail {
            display: flex;
            gap: 20px;
            margin: 15px 0;
        }
        .score-item {
            flex: 1;
            padding: 10px;
            background-color: white;
            border-radius: 5px;
            text-align: center;
        }
        .score-label {
            font-size: 12px;
            color: #7f8c8d;
            margin-bottom: 5px;
        }
        .score-value {
            font-size: 20px;
            font-weight: bold;
            color: #2c3e50;
        }
        .info-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin: 15px 0;
        }
        .info-item {
            padding: 10px;
            background-color: white;
            border-radius: 5px;
        }
        .info-label {
            font-size: 12px;
            color: #7f8c8d;
            margin-bottom: 5px;
        }
        .info-value {
            font-size: 16px;
            font-weight: bold;
            color: #2c3e50;
        }
        .chart-container {
            margin: 20px 0;
            text-align: center;
        }
        .chart-container img {
            max-width: 100%;
            height: auto;
            border: 1px solid #e0e0e0;
            border-radius: 5px;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }
        th, td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #e0e0e0;
        }
        th {
            background-color: #3498db;
            color: white;
            font-weight: bold;
        }
        tr:hover {
            background-color: #f5f5f5;
        }
        .confidence-high { color: #27ae60; font-weight: bold; }
        .confidence-mid { color: #f39c12; font-weight: bold; }
        .confidence-spec { color: #e74c3c; font-weight: bold; }
        .state-buy { color: #27ae60; font-weight: bold; }
        .state-base { color: #f39c12; font-weight: bold; }
        .state-normal { color: #95a5a6; }
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 投資分析レポート - """ + date_str + """</h1>
        <p>生成時刻: """ + datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC') + """</p>
""")
        
        # 上位3個の詳細セクション
        html_parts.append('<h2>🏆 スコア上位3個</h2>')
        for idx, pick in enumerate(top_picks, 1):
            html_parts.append(self._generate_pick_section(pick, idx))
        
        # 価格チャート比較
        html_parts.append('<h2>📈 価格チャート比較</h2>')
        price_chart_html = self._generate_price_comparison_chart(top_picks)
        html_parts.append(price_chart_html)
        
        # スコア比較チャート
        html_parts.append('<h2>📊 スコア内訳比較</h2>')
        score_chart_html = self._generate_score_comparison_chart(top_picks)
        html_parts.append(score_chart_html)
        
        # レーダーチャート
        html_parts.append('<h2>🎯 総合評価レーダーチャート</h2>')
        radar_chart_html = self._generate_radar_chart(top_picks)
        html_parts.append(radar_chart_html)
        
        # 候補リスト（Top 20）
        html_parts.append('<h2>📋 候補リスト（Top 20）</h2>')
        candidates_sorted = sorted(candidates, key=lambda x: x.get('total_score', 0), reverse=True)
        html_parts.append(self._generate_candidates_table(candidates_sorted[:20]))
        
        # HTMLフッター
        html_parts.append("""
    </div>
</body>
</html>
""")
        
        return '\n'.join(html_parts)
    
    def _generate_pick_section(self, pick: Dict, rank: int) -> str:
        """個別ピックのセクションを生成"""
        symbol = pick.get('symbol', 'N/A')
        total_score = pick.get('total_score', 0)
        value_score = pick.get('value_score', 0)
        momentum_score = pick.get('momentum_score', 0)
        stability_score = pick.get('stability_score', 0)
        confidence = pick.get('confidence', 'Spec')
        state = pick.get('current_state', 'NORMAL')
        category = pick.get('asset_category', 'その他')
        current_price = pick.get('current_price', 0)
        ath_ratio = pick.get('ath_ratio')
        return_30d = pick.get('return_30d')
        
        # 価格チャート
        price_chart_img = self._generate_price_chart(pick)
        
        html = f"""
        <div class="pick-card">
            <div class="pick-header">
                <div>
                    <span class="symbol">#{rank} {symbol}</span>
                    <span class="confidence-{confidence.lower()}">[{confidence}]</span>
                </div>
                <div class="score">{total_score:.1f}</div>
            </div>
            
            <div class="score-detail">
                <div class="score-item">
                    <div class="score-label">Value（割安度）</div>
                    <div class="score-value">{value_score:.1f}</div>
                </div>
                <div class="score-item">
                    <div class="score-label">Momentum（反転）</div>
                    <div class="score-value">{momentum_score:.1f}</div>
                </div>
                <div class="score-item">
                    <div class="score-label">Stability（安定性）</div>
                    <div class="score-value">{stability_score:.1f}</div>
                </div>
            </div>
            
            <div class="info-grid">
                <div class="info-item">
                    <div class="info-label">状態</div>
                    <div class="info-value state-{state.lower()}">{state}</div>
                </div>
                <div class="info-item">
                    <div class="info-label">カテゴリ</div>
                    <div class="info-value">{category}</div>
                </div>
                <div class="info-item">
                    <div class="info-label">現在価格</div>
                    <div class="info-value">${current_price:,.2f}</div>
                </div>
"""
        
        if ath_ratio is not None:
            html += f"""
                <div class="info-item">
                    <div class="info-label">ATH比</div>
                    <div class="info-value">{ath_ratio:.1%}</div>
                </div>
"""
        
        if return_30d is not None:
            color = '#27ae60' if return_30d >= 0 else '#e74c3c'
            html += f"""
                <div class="info-item">
                    <div class="info-label">30日リターン</div>
                    <div class="info-value" style="color: {color}">{return_30d:+.1f}%</div>
                </div>
"""
        
        html += """
            </div>
            
            <div class="chart-container">
""" + price_chart_img + """
            </div>
        </div>
"""
        
        return html
    
    def _generate_price_chart(self, pick: Dict) -> str:
        """個別の価格チャートを生成（matplotlib）"""
        symbol = pick.get('symbol', 'N/A')
        prices = pick.get('historical_prices')
        
        # 履歴価格データがある場合は使用
        if prices:
            return self._generate_price_chart_with_data(symbol, prices)
        
        # データがない場合
        try:
            fig, ax = plt.subplots(figsize=(10, 4))
            ax.text(0.5, 0.5, f'{symbol}の価格データがありません', 
                   ha='center', va='center', transform=ax.transAxes)
            ax.set_title(f'{symbol} - 過去30日の価格推移', fontsize=12, fontweight='bold')
            ax.axis('off')
            
            # 画像をBase64エンコード
            img_buffer = BytesIO()
            fig.savefig(img_buffer, format='png', bbox_inches='tight', dpi=100)
            img_buffer.seek(0)
            img_base64 = base64.b64encode(img_buffer.read()).decode('utf-8')
            plt.close(fig)
            
            return f'<img src="data:image/png;base64,{img_base64}" alt="{symbol} Price Chart">'
        except Exception as e:
            return f'<p>チャート生成エラー: {e}</p>'
    
    def _generate_price_chart_with_data(self, symbol: str, prices: List[Tuple[datetime, float]]) -> str:
        """履歴価格データを使用して価格チャートを生成"""
        if not prices:
            return f'<p>{symbol}: 価格データがありません</p>'
        
        try:
            dates = [p[0] for p in prices]
            price_values = [p[1] for p in prices]
            
            fig, ax = plt.subplots(figsize=(10, 4))
            ax.plot(dates, price_values, linewidth=2, color='#3498db')
            ax.fill_between(dates, price_values, alpha=0.3, color='#3498db')
            ax.set_title(f'{symbol} - 過去30日の価格推移', fontsize=12, fontweight='bold')
            ax.set_xlabel('日付')
            ax.set_ylabel('価格 (USD)')
            ax.grid(True, alpha=0.3)
            
            # 日付フォーマット
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
            ax.xaxis.set_major_locator(mdates.DayLocator(interval=5))
            plt.xticks(rotation=45)
            
            # 画像をBase64エンコード
            img_buffer = BytesIO()
            fig.savefig(img_buffer, format='png', bbox_inches='tight', dpi=100)
            img_buffer.seek(0)
            img_base64 = base64.b64encode(img_buffer.read()).decode('utf-8')
            plt.close(fig)
            
            return f'<img src="data:image/png;base64,{img_base64}" alt="{symbol} Price Chart">'
        except Exception as e:
            return f'<p>チャート生成エラー: {e}</p>'
    
    def _generate_price_comparison_chart(self, top_picks: List[Dict]) -> str:
        """上位3個の価格チャート比較（matplotlib）"""
        if not top_picks:
            return '<p>データがありません</p>'
        
        try:
            fig, axes = plt.subplots(len(top_picks), 1, figsize=(12, 4 * len(top_picks)))
            if len(top_picks) == 1:
                axes = [axes]
            
            for idx, (pick, ax) in enumerate(zip(top_picks, axes)):
                symbol = pick.get('symbol', 'N/A')
                prices = pick.get('historical_prices')
                
                if prices:
                    dates = [p[0] for p in prices]
                    price_values = [p[1] for p in prices]
                    
                    ax.plot(dates, price_values, linewidth=2, color='#3498db')
                    ax.fill_between(dates, price_values, alpha=0.3, color='#3498db')
                    ax.set_title(f'{symbol} - 過去30日の価格推移', fontsize=12, fontweight='bold')
                    ax.set_ylabel('価格 (USD)')
                    ax.grid(True, alpha=0.3)
                    
                    # 日付フォーマット
                    ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
                    ax.xaxis.set_major_locator(mdates.DayLocator(interval=5))
                    plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)
                else:
                    ax.text(0.5, 0.5, f'{symbol}: 価格データがありません', 
                           ha='center', va='center', transform=ax.transAxes)
                    ax.axis('off')
            
            # 最後のサブプロットにxlabelを設定
            axes[-1].set_xlabel('日付')
            
            plt.tight_layout()
            
            # 画像をBase64エンコード
            img_buffer = BytesIO()
            fig.savefig(img_buffer, format='png', bbox_inches='tight', dpi=100)
            img_buffer.seek(0)
            img_base64 = base64.b64encode(img_buffer.read()).decode('utf-8')
            plt.close(fig)
            
            return f'<div class="chart-container"><img src="data:image/png;base64,{img_base64}" alt="Price Comparison"></div>'
        except Exception as e:
            return f'<p>チャート生成エラー: {e}</p>'
    
    def _generate_score_comparison_chart(self, top_picks: List[Dict]) -> str:
        """スコア内訳比較チャートを生成"""
        if not top_picks:
            return '<p>データがありません</p>'
        
        try:
            symbols = [p.get('symbol', 'N/A') for p in top_picks]
            value_scores = [p.get('value_score', 0) for p in top_picks]
            momentum_scores = [p.get('momentum_score', 0) for p in top_picks]
            stability_scores = [p.get('stability_score', 0) for p in top_picks]
            
            fig, ax = plt.subplots(figsize=(12, 6))
            x = range(len(symbols))
            width = 0.25
            
            ax.bar([i - width for i in x], value_scores, width, label='Value', color='#3498db')
            ax.bar(x, momentum_scores, width, label='Momentum', color='#27ae60')
            ax.bar([i + width for i in x], stability_scores, width, label='Stability', color='#e74c3c')
            
            ax.set_xlabel('シンボル')
            ax.set_ylabel('スコア')
            ax.set_title('スコア内訳比較', fontsize=14, fontweight='bold')
            ax.set_xticks(x)
            ax.set_xticklabels(symbols)
            ax.legend()
            ax.grid(True, alpha=0.3, axis='y')
            ax.set_ylim([0, 100])
            
            # 画像をBase64エンコード
            img_buffer = BytesIO()
            fig.savefig(img_buffer, format='png', bbox_inches='tight', dpi=100)
            img_buffer.seek(0)
            img_base64 = base64.b64encode(img_buffer.read()).decode('utf-8')
            plt.close(fig)
            
            return f'<div class="chart-container"><img src="data:image/png;base64,{img_base64}" alt="Score Comparison"></div>'
        except Exception as e:
            return f'<p>チャート生成エラー: {e}</p>'
    
    def _generate_radar_chart(self, top_picks: List[Dict]) -> str:
        """レーダーチャートを生成"""
        if not top_picks:
            return '<p>データがありません</p>'
        
        try:
            import numpy as np
            
            categories = ['Value', 'Momentum', 'Stability']
            num_vars = len(categories)
            
            # 角度を計算
            angles = np.linspace(0, 2 * np.pi, num_vars, endpoint=False).tolist()
            angles += angles[:1]  # 閉じる
            
            fig, ax = plt.subplots(figsize=(10, 10), subplot_kw=dict(projection='polar'))
            
            colors = ['#3498db', '#27ae60', '#e74c3c']
            for idx, pick in enumerate(top_picks):
                symbol = pick.get('symbol', 'N/A')
                values = [
                    pick.get('value_score', 0),
                    pick.get('momentum_score', 0),
                    pick.get('stability_score', 0)
                ]
                values += values[:1]  # 閉じる
                
                ax.plot(angles, values, 'o-', linewidth=2, label=symbol, color=colors[idx % len(colors)])
                ax.fill(angles, values, alpha=0.15, color=colors[idx % len(colors)])
            
            ax.set_xticks(angles[:-1])
            ax.set_xticklabels(categories)
            ax.set_ylim(0, 100)
            ax.set_yticks([20, 40, 60, 80, 100])
            ax.set_yticklabels(['20', '40', '60', '80', '100'])
            ax.grid(True)
            ax.legend(loc='upper right', bbox_to_anchor=(1.3, 1.1))
            ax.set_title('総合評価レーダーチャート', fontsize=14, fontweight='bold', pad=20)
            
            # 画像をBase64エンコード
            img_buffer = BytesIO()
            fig.savefig(img_buffer, format='png', bbox_inches='tight', dpi=100)
            img_buffer.seek(0)
            img_base64 = base64.b64encode(img_buffer.read()).decode('utf-8')
            plt.close(fig)
            
            return f'<div class="chart-container"><img src="data:image/png;base64,{img_base64}" alt="Radar Chart"></div>'
        except Exception as e:
            return f'<p>チャート生成エラー: {e}</p>'
    
    def _generate_candidates_table(self, candidates: List[Dict]) -> str:
        """候補リストのテーブルを生成"""
        html = '<table><thead><tr>'
        html += '<th>順位</th>'
        html += '<th>シンボル</th>'
        html += '<th>スコア</th>'
        html += '<th>状態</th>'
        html += '<th>信頼度</th>'
        html += '<th>カテゴリ</th>'
        html += '<th>価格</th>'
        html += '</tr></thead><tbody>'
        
        for idx, candidate in enumerate(candidates, 1):
            symbol = candidate.get('symbol', 'N/A')
            score = candidate.get('total_score', 0)
            state = candidate.get('current_state', 'NORMAL')
            confidence = candidate.get('confidence', 'Spec')
            category = candidate.get('asset_category', 'その他')
            price = candidate.get('current_price', 0)
            
            html += '<tr>'
            html += f'<td>{idx}</td>'
            html += f'<td><strong>{symbol}</strong></td>'
            html += f'<td>{score:.1f}</td>'
            html += f'<td class="state-{state.lower()}">{state}</td>'
            html += f'<td class="confidence-{confidence.lower()}">{confidence}</td>'
            html += f'<td>{category}</td>'
            html += f'<td>${price:,.2f}</td>'
            html += '</tr>'
        
        html += '</tbody></table>'
        return html
