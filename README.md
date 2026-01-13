# Polymarket 自動交易機器人

> 基於 Pinnacle 賠率的價值投注系統，採用 Kelly Criterion 進行科學化資金管理

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)

## 專案簡介

本專案是一個自動化體育博彩分析系統，透過比對 Pinnacle（賠率基準）與 Polymarket 的賠率差異，識別高價值投注機會。系統整合了 Kelly Criterion 資金管理、歷史回測分析、以及 Discord 即時通知功能。

### 主要特色

- **智能賠率比對** - 自動抓取並分析 Pinnacle 與 Polymarket 賠率
- **價值投注識別** - 篩選勝率 >55%、期望值 >1.5% 的高價值機會
- **科學化資金管理** - 採用 Kelly Criterion 動態計算最佳注額
- **歷史數據回測** - 使用真實 Odds API 數據進行一年期績效驗證
- **即時通知系統** - Discord Webhook 推送交易建議
- **雲端資料同步** - Google Sheets 整合，多裝置存取

---

## 快速開始

### 環境需求

- Python 3.8 或以上版本
- pip 套件管理器
- API 金鑰：[The Odds API](https://the-odds-api.com/)
- Discord Webhook URL（用於接收通知）

### 安裝步驟

```bash
# 1. 克隆專案
git clone <repository-url>
cd polytrade

# 2. 安裝相依套件
pip install -r requirements.txt

# 3. 設定環境變數
cp .env.example .env
# 編輯 .env 檔案，填入以下資訊：
# - ODDS_API_KEY (必填)
# - DISCORD_WEBHOOK_URL (必填)
# - GOOGLE_SHEET_ID (選填)

# 4. 執行主程式
python trade.py
```

### 驗證安裝

```bash
# 檢查系統配置與 API 連線狀態
python utils/check_status.py
```

---

## 專案架構

```
polytrade/
├── trade.py                    # 主程式入口（每日交易執行）
├── backtest.py                 # 簡易回測模擬
├── historical_backtest.py      # 完整歷史回測（一年數據）
│
├── data/                       # 數據儲存目錄
│   ├── polymarket_bets.csv     # 投注記錄資料庫
│   └── backtest_results_*.csv  # 回測結果檔案
│
├── logs/                       # 系統日誌
│   └── polymarket_bot.log      # 運行紀錄與錯誤追蹤
│
├── utils/                      # 工具腳本集
│   ├── google_sheets_sync.py   # Google Sheets 雲端同步
│   ├── check_status.py         # 系統狀態檢查
│   ├── merge_csv.py            # CSV 資料合併工具
│   └── fix_csv.py              # CSV 資料修復工具
│
├── docs/                       # 完整文檔
│   ├── README.md               # 詳細使用說明
│   ├── QUICK_START.md          # 快速入門指南
│   ├── CHANGELOG.md            # 版本更新紀錄
│   ├── SUMMARY.md              # 專案總覽
│   └── setup_google_sheets.md  # Google Sheets 設定教學
│
└── backups/                    # 資料備份目錄
```

---

## 核心功能

### 1. 每日交易分析

執行主程式進行即時賽事分析：

```bash
python trade.py
```

**運作流程：**

1. 抓取 Pinnacle 與 Polymarket 最新賠率
2. 計算真實勝率與期望值（EV）
3. 篩選符合門檻的投注機會
4. 使用 Kelly Criterion 計算建議注額
5. 發送 Discord 通知並記錄到 CSV

**篩選條件：**

- 勝率（Win Probability）≥ 55%
- 期望值（Expected Value）≥ 1.5%
- 賠率更新時間 ≤ 15 分鐘（確保時效性）

### 2. 歷史回測分析

使用真實歷史數據驗證策略績效：

```bash
python historical_backtest.py
```

**功能特點：**

- 透過 Odds API 取得過去一年 NBA/NHL 賽事數據
- 模擬每日交易決策與資金變化
- 生成 HTML 視覺化報告（包含資金曲線、勝率分析）
- 計算關鍵指標：
  - Sharpe Ratio（風險調整後報酬）
  - Maximum Drawdown（最大回撤）
  - Win Rate（勝率）
  - Total Return（總報酬率）

**注意事項：**

- 每次回測約消耗 730 次 API 請求（365 天 × 2 次/天）
- 比賽結果使用蒙特卡羅模擬（基於真實勝率概率）
- 免費 API 方案可能缺少部分歷史數據

### 3. Google Sheets 整合

同步投注記錄至雲端試算表：

```bash
python utils/google_sheets_sync.py
```

**功能：**

- 自動上傳 `polymarket_bets.csv` 至 Google Sheets
- 生成每日統計摘要（勝率、報酬率、總投注數）
- 多裝置即時查看交易紀錄

**設定方式：**
請參閱 [docs/setup_google_sheets.md](docs/setup_google_sheets.md)

---

## 策略參數調整

編輯 [trade.py](trade.py) 檔案中的參數：

```python
# 資金管理
BANKROLL = 20.0              # 初始本金（美元）
KELLY_FRACTION = 0.25        # Kelly 分數（0.25 = 保守型，降低波動）

# 篩選條件
MIN_WIN_PROB = 0.55          # 最低勝率 55%
MIN_EV = 0.015               # 最低期望值 1.5%

# 風險控管
MAX_BETS = 3                 # 每日最大投注數量
```

**Kelly Fraction 說明：**

- `1.0` = 完整 Kelly（激進，高波動）
- `0.5` = 半 Kelly（平衡）
- `0.25` = 四分之一 Kelly（保守，建議值）

---

## 常用指令

### 日常操作

```bash
# 執行每日交易分析
python trade.py

# 同步數據到 Google Sheets
python utils/google_sheets_sync.py

# 查看系統配置狀態
python utils/check_status.py
```

### 回測分析

```bash
# 簡易模擬回測
python backtest.py

# 完整歷史數據回測（一年）
python historical_backtest.py
```

### 資料維護

```bash
# 檢查並修復 CSV 檔案格式
python utils/merge_csv.py

# 查看即時日誌
tail -f logs/polymarket_bot.log
```

---

## 自動化排程

### macOS / Linux（使用 crontab）

```bash
# 編輯 crontab
crontab -e

# 新增每日早上 9:00 執行
0 9 * * * cd /Users/jhinresh/Desktop/polytrade && /usr/bin/python3 trade.py

# 新增每日晚上 21:00 同步到 Google Sheets
0 21 * * * cd /Users/jhinresh/Desktop/polytrade && /usr/bin/python3 utils/google_sheets_sync.py
```

### Windows（使用工作排程器）

1. 開啟「工作排程器」（Task Scheduler）
2. 建立基本工作
3. 觸發程序：每日 09:00
4. 動作：啟動程式 `python.exe`
5. 引數：`C:\path\to\polytrade\trade.py`

---

## 環境變數設定

在專案根目錄建立 `.env` 檔案：

```bash
# === 必填項目 ===
# Odds API 金鑰（取得網址：https://the-odds-api.com/）
ODDS_API_KEY=your_odds_api_key_here

# Discord Webhook URL（用於接收投注通知）
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...

# === 選填項目 ===
# Google Sheets 試算表 ID（啟用雲端同步時需要）
GOOGLE_SHEET_ID=your_google_sheet_id_here
```

**取得方式：**

- Odds API Key：註冊 [The Odds API](https://the-odds-api.com/) 取得免費方案（每月 500 次請求）
- Discord Webhook：伺服器設定 → 整合 → Webhook → 新增 Webhook
- Google Sheet ID：試算表 URL 中的長字串（docs.google.com/spreadsheets/d/**{SHEET_ID}**/edit）

---

## 技術亮點

| 模組                | 說明                         | 優勢                                             |
| ------------------- | ---------------------------- | ------------------------------------------------ |
| **Kelly Criterion** | 數學化資金管理模型           | 根據勝率與賠率動態調整投注比例，最大化長期增長率 |
| **模糊匹配演算法**  | token_set_ratio + 90% 門檻   | 準確匹配不同平台的隊伍名稱（處理縮寫與拼寫差異） |
| **時效性驗證**      | 15 分鐘賠率新鮮度檢查        | 避免使用過時賠率導致錯誤決策                     |
| **完整日誌系統**    | 所有操作記錄至 `logs/`       | 便於除錯與績效追蹤                               |
| **歷史回測引擎**    | 真實 API 數據 + 蒙特卡羅模擬 | 驗證策略長期穩定性與風險指標                     |

---

## 完整文檔

詳細資訊請參閱 `docs/` 目錄：

- **[完整使用說明](docs/README.md)** - 深入功能介紹與進階配置
- **[快速入門指南](docs/QUICK_START.md)** - 常見問題與故障排除
- **[Google Sheets 設定](docs/setup_google_sheets.md)** - 雲端同步詳細步驟
- **[更新日誌](docs/CHANGELOG.md)** - 版本歷史與新功能紀錄

---

## 風險提醒

⚠️ **使用前必讀**

1. **非獲利保證工具** - 本系統僅為輔助分析工具，無法保證投資報酬
2. **需人工驗證** - 所有投注建議需手動確認賽事資訊與賠率正確性
3. **嚴格風控** - 切勿投入無法承受損失的資金
4. **API 配額限制** - 免費方案每月 500 次請求（歷史回測會快速消耗）
5. **回測非實盤** - 歷史績效使用模擬結果，實際交易可能因滑價、限額等因素產生差異
6. **法規遵循** - 請確認當地法律是否允許體育博彩與預測市場交易

---

## 疑難排解

### 查看系統日誌

```bash
# 即時監控日誌（Linux/macOS）
tail -f logs/polymarket_bot.log

# 查看最後 50 行（Windows）
type logs\polymarket_bot.log | more
```

### 常見問題

**Q: API 請求失敗**
A: 檢查 `.env` 中的 `ODDS_API_KEY` 是否正確，並確認配額未用盡

**Q: Discord 通知未收到**
A: 驗證 `DISCORD_WEBHOOK_URL` 格式正確，並測試 Webhook 是否啟用

**Q: CSV 檔案損壞**
A: 執行 `python utils/merge_csv.py` 自動修復

**Q: 找不到投注機會**
A: 調低 `MIN_WIN_PROB` 或 `MIN_EV` 參數，或確認當日有足夠賽事

---

## 授權與免責聲明

**授權條款：** MIT License

**免責聲明：**
本專案僅供教育與研究用途。使用者需自行承擔所有投資風險，開發者不對任何財務損失負責。投資前請審慎評估個人財務狀況與風險承受能力。

---

**專案維護：** JhiNResH
**最後更新：** 2026-01-13
