"""
設定読み込みユーティリティ
設定ファイルを統一的に読み込む関数を提供
"""
import json
import os
from typing import Dict, Optional
from pathlib import Path


def load_app_config(config_dir: Optional[str] = None) -> Dict:
    """アプリケーション設定を読み込む
    
    Args:
        config_dir: 設定ディレクトリのパス（デフォルト: プロジェクトルートのconfig/）
    
    Returns:
        アプリケーション設定の辞書
    """
    if config_dir is None:
        # プロジェクトルートのconfig/ディレクトリを探す
        current_dir = Path(__file__).parent
        config_dir = str(current_dir)
    
    config_path = os.path.join(config_dir, 'app_config.json')
    
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"警告: app_config.jsonの読み込みエラー: {e}")
    
    # デフォルト値
    return {
        "symbols": [],
        "check_interval": 86400,
        "llm_model": "gpt-4o-mini",
        "llm_temperature": 0.3
    }


def load_notifications_config(config_dir: Optional[str] = None) -> Dict:
    """通知設定を読み込む
    
    Args:
        config_dir: 設定ディレクトリのパス（デフォルト: プロジェクトルートのconfig/）
    
    Returns:
        通知設定の辞書
    """
    if config_dir is None:
        current_dir = Path(__file__).parent
        config_dir = str(current_dir)
    
    config_path = os.path.join(config_dir, 'notifications_config.json')
    
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"警告: notifications_config.jsonの読み込みエラー: {e}")
    
    # デフォルト値
    return {
        "webhook": "",
        "line_token": "",
        "slack_webhook": "",
        "gmail_user": "",
        "gmail_password": "",
        "gmail_to": ""
    }


def load_legacy_config(config_path: str = "config.json") -> Optional[Dict]:
    """後方互換性のため、既存のconfig.jsonを読み込む
    
    Args:
        config_path: 設定ファイルのパス
    
    Returns:
        設定の辞書、またはNone
    """
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                print("警告: 古いconfig.json形式を使用しています。config/ディレクトリへの移行を推奨します。")
                return config
        except Exception as e:
            print(f"警告: config.jsonの読み込みエラー: {e}")
    
    return None


def load_all_config(config_dir: Optional[str] = None, legacy_config_path: str = "config.json") -> Dict:
    """すべての設定を統合して読み込む
    
    優先順位:
    1. 新しい設定ファイル（config/app_config.json, config/notifications_config.json）
    2. 環境変数（LLM_API_KEY等）
    3. 既存のconfig.json（後方互換性）
    4. デフォルト値
    
    Args:
        config_dir: 設定ディレクトリのパス（デフォルト: プロジェクトルートのconfig/）
        legacy_config_path: 既存のconfig.jsonのパス
    
    Returns:
        統合された設定の辞書
    """
    config = {}
    
    # 1. 新しい設定ファイルを読み込む
    app_config = load_app_config(config_dir)
    notifications_config = load_notifications_config(config_dir)
    
    # 統合
    config.update(app_config)
    config.update(notifications_config)
    
    # 2. 環境変数から機密情報を読み込む
    llm_api_key = os.getenv('LLM_API_KEY')
    if llm_api_key:
        config['llm_api_key'] = llm_api_key
    
    gmail_password = os.getenv('GMAIL_PASSWORD')
    if gmail_password:
        config['gmail_password'] = gmail_password
    
    # 3. 既存のconfig.jsonから不足している値を補完（後方互換性）
    legacy_config = load_legacy_config(legacy_config_path)
    if legacy_config:
        # 新しい設定ファイルにない値のみ補完
        for key, value in legacy_config.items():
            if key not in config or not config[key]:
                config[key] = value
    
    return config


def load_config_for_streamlit(config_dir: Optional[str] = None, legacy_config_path: str = "config.json") -> Dict:
    """Streamlit用の設定読み込み（Streamlit Secrets対応）
    
    優先順位:
    1. Streamlit Secrets（Streamlit Cloud用）
    2. 新しい設定ファイル（config/app_config.json, config/notifications_config.json）
    3. 環境変数
    4. 既存のconfig.json（後方互換性）
    5. デフォルト値
    
    Args:
        config_dir: 設定ディレクトリのパス
        legacy_config_path: 既存のconfig.jsonのパス
    
    Returns:
        統合された設定の辞書
    """
    # Streamlitが利用可能な場合、Secretsを試す
    try:
        import streamlit as st
        if hasattr(st, 'secrets') and len(st.secrets) > 0:
            config = dict(st.secrets)
            # Streamlit Secretsから読み込んだ場合は、そのまま返す
            return config
    except ImportError:
        # Streamlitが利用できない場合は通常の読み込み
        pass
    except Exception:
        # Streamlit Secretsの読み込みに失敗した場合は通常の読み込み
        pass
    
    # Streamlit Secretsが利用できない場合は通常の読み込み
    return load_all_config(config_dir, legacy_config_path)
