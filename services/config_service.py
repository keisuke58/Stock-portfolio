"""
設定取得サービス（Streamlit用）
Streamlitアプリケーション用の設定取得サービス
"""
from typing import Dict
from config.config_loader import load_config_for_streamlit


def load_config(config_path: str = "config.json") -> Dict:
    """設定ファイルを読み込む（Streamlit Cloud Secrets対応）
    
    Args:
        config_path: 既存のconfig.jsonのパス（後方互換性のため）
    
    Returns:
        設定の辞書
    """
    return load_config_for_streamlit(legacy_config_path=config_path)
