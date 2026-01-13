#!/usr/bin/env python3
"""檢查 Polymarket Bot 配置狀態"""

import os
from dotenv import load_dotenv

load_dotenv()

def check_status():
    print("🔍 Polymarket Trading Bot - 狀態檢查")
    print("=" * 50)
    print()

    # 檢查環境變數
    print("📋 環境變數檢查:")
    print("-" * 50)

    odds_api_key = os.getenv("ODDS_API_KEY")
    discord_webhook = os.getenv("DISCORD_WEBHOOK_URL")
    google_sheet_id = os.getenv("GOOGLE_SHEET_ID")
    bankroll = os.getenv("BANKROLL")

    # ODDS_API_KEY
    if odds_api_key and odds_api_key != "your_odds_api_key_here":
        print("✅ ODDS_API_KEY: 已設定")
    else:
        print("❌ ODDS_API_KEY: 未設定")
        print("   請前往 https://the-odds-api.com/ 申請")

    # DISCORD_WEBHOOK_URL
    if discord_webhook and discord_webhook != "your_discord_webhook_url_here":
        print("✅ DISCORD_WEBHOOK_URL: 已設定")
    else:
        print("❌ DISCORD_WEBHOOK_URL: 未設定")
        print("   請在 Discord 中創建 Webhook")

    # GOOGLE_SHEET_ID (可選)
    if google_sheet_id and google_sheet_id != "your_google_sheet_id_here":
        print("✅ GOOGLE_SHEET_ID: 已設定（可選）")
    else:
        print("⚪ GOOGLE_SHEET_ID: 未設定（可選）")
        print("   如需同步到 Google Sheets，請參考 setup_google_sheets.md")

    # BANKROLL (可選)
    if bankroll:
        print(f"✅ BANKROLL: ${bankroll}（從環境變數）")
    else:
        print("⚪ BANKROLL: 使用預設值 $20（從 trade.py）")

    print()

    # 檢查檔案
    print("📁 檔案檢查:")
    print("-" * 50)

    files_to_check = {
        'trade.py': '主程式',
        'backtest.py': '回測腳本',
        'google_sheets_sync.py': 'Google Sheets 同步',
        'requirements.txt': '依賴清單',
        '.env': '環境變數配置',
        'google_credentials.json': 'Google API 金鑰（可選）',
        'polymarket_bets.csv': '下注記錄'
    }

    for filename, description in files_to_check.items():
        if os.path.exists(filename):
            print(f"✅ {filename}: 存在 ({description})")
        else:
            if filename in ['google_credentials.json', 'polymarket_bets.csv']:
                print(f"⚪ {filename}: 不存在 ({description})")
            else:
                print(f"❌ {filename}: 不存在 ({description})")

    print()

    # 檢查 Python 套件
    print("📦 Python 套件檢查:")
    print("-" * 50)

    packages = {
        'requests': '必需',
        'pandas': '必需',
        'dotenv': '必需（python-dotenv）',
        'discord_webhook': '必需',
        'thefuzz': '必需',
        'google.oauth2': '可選（Google Sheets）'
    }

    for package, status in packages.items():
        try:
            if package == 'dotenv':
                __import__('dotenv')
            elif package == 'google.oauth2':
                __import__('google.oauth2.service_account')
            else:
                __import__(package)
            print(f"✅ {package}: 已安裝 ({status})")
        except ImportError:
            if status == '可選（Google Sheets）':
                print(f"⚪ {package}: 未安裝 ({status})")
            else:
                print(f"❌ {package}: 未安裝 ({status})")
                print(f"   執行: pip install -r requirements.txt")

    print()

    # 總結
    print("📊 總結:")
    print("-" * 50)

    required_ok = (
        odds_api_key and odds_api_key != "your_odds_api_key_here" and
        discord_webhook and discord_webhook != "your_discord_webhook_url_here" and
        os.path.exists('trade.py') and
        os.path.exists('.env')
    )

    if required_ok:
        print("✅ 所有必需配置已完成，可以執行 python trade.py")
    else:
        print("❌ 尚有必需配置未完成")
        print()
        print("下一步:")
        if not odds_api_key or odds_api_key == "your_odds_api_key_here":
            print("1. 申請 Odds API Key: https://the-odds-api.com/")
        if not discord_webhook or discord_webhook == "your_discord_webhook_url_here":
            print("2. 在 Discord 中創建 Webhook")
        if not os.path.exists('.env'):
            print("3. 複製 .env.example 為 .env 並填入配置")

    print()

    # Google Sheets 狀態
    google_sheets_ok = (
        google_sheet_id and
        google_sheet_id != "your_google_sheet_id_here" and
        os.path.exists('google_credentials.json')
    )

    if google_sheets_ok:
        print("✅ Google Sheets 同步已配置")
    else:
        print("⚪ Google Sheets 同步未配置（可選）")
        print("   如需啟用，請參考 setup_google_sheets.md")

    print()
    print("=" * 50)
    print()

    # 顯示當前策略參數
    if os.path.exists('trade.py'):
        print("🎯 當前策略參數:")
        print("-" * 50)
        try:
            with open('trade.py', 'r') as f:
                lines = f.readlines()
                for line in lines:
                    if any(param in line for param in ['BANKROLL =', 'MIN_WIN_PROB =', 'MIN_EV =', 'KELLY_FRACTION =', 'MAX_BETS =']):
                        print(f"   {line.strip()}")
        except:
            pass
        print()

if __name__ == "__main__":
    check_status()
