# Polymarket 自動交易機器人 🤖

基於 Pinnacle 賠率的價值投注系統，使用 Kelly Criterion 進行資金管理。

## 快速開始 🚀

```bash
# 1. 安裝依賴
pip install -r requirements.txt

# 2. 設定環境變數
cp .env.example .env
# 編輯 .env 填入你的 API 金鑰

# 3. 執行主程式
python trade.py

# 4. 查看 Discord 獲取下注建議
```

## 項目結構 📁

```
polytrade/
├── trade.py                    # 主程式（每日執行）
├── backtest.py                 # 簡單回測
├── historical_backtest.py      # 完整歷史回測（一年數據）
│
├── data/                       # 數據文件
│   ├── polymarket_bets.csv     # 下注記錄
│   └── backtest_results_*.csv  # 回測結果
│
├── logs/                       # 日誌文件
│   └── polymarket_bot.log      # 運行日誌
│
├── utils/                      # 工具腳本
│   ├── google_sheets_sync.py   # Google Sheets 同步
│   ├── check_status.py         # 配置檢查
│   ├── merge_csv.py            # CSV 合併工具
│   └── fix_csv.py              # CSV 修復工具
│
├── docs/                       # 文檔
│   ├── README.md               # 完整說明
│   ├── QUICK_START.md          # 快速開始
│   ├── CHANGELOG.md            # 更新日誌
│   ├── SUMMARY.md              # 項目總結
│   └── setup_google_sheets.md  # Google Sheets 設定
│
└── backups/                    # 備份文件
```

## 核心功能 ✨

### 1. 每日交易建議
- 自動抓取 Pinnacle 與 Polymarket 賠率
- 識別高價值下注機會（勝率 >55%, EV >1.5%）
- Kelly Criterion 動態計算注額
- Discord 即時通知

### 2. 完整歷史回測
```bash
python historical_backtest.py
```
- 使用真實 Odds API 歷史數據
- 回測過去一年的 NBA 和 NHL 比賽
- 生成詳細報告和 HTML 圖表
- 計算 Sharpe Ratio、最大回撤、勝率等指標

### 3. Google Sheets 整合
```bash
python utils/google_sheets_sync.py
```
- 自動同步下注記錄到雲端
- 每日統計摘要
- 多裝置查看

## 策略參數 🎯

編輯 `trade.py` 調整策略：

```python
BANKROLL = 20.0           # 本金
MIN_WIN_PROB = 0.55       # 最低勝率 55%
MIN_EV = 0.015            # 最低期望值 1.5%
KELLY_FRACTION = 0.25     # Kelly 分數（保守）
MAX_BETS = 3              # 每日最多下注數
```

## 常用命令 ⚡

```bash
# 每日使用
python trade.py                          # 執行主程式
python utils/google_sheets_sync.py       # 同步到雲端

# 回測
python backtest.py                       # 簡單模擬回測
python historical_backtest.py            # 完整歷史回測

# 維護工具
python utils/check_status.py             # 檢查配置
python utils/merge_csv.py                # 修復 CSV
```

## 自動化執行 ⏰

### macOS / Linux (crontab)

```bash
# 每天早上 9 點執行
0 9 * * * cd /Users/jhinresh/Desktop/polytrade && python3 trade.py
```

## 環境變數設定 🔧

在 `.env` 中設定：

```bash
# 必填
ODDS_API_KEY=your_odds_api_key          # https://the-odds-api.com/
DISCORD_WEBHOOK_URL=your_webhook_url    # Discord Webhook

# 可選
GOOGLE_SHEET_ID=your_sheet_id           # Google Sheets 同步
```

## 核心優化 ⚡

| 功能 | 說明 |
|------|------|
| Kelly Criterion | 科學化資金管理，根據勝率動態調整注額 |
| 改進匹配算法 | 90% 門檻 + token_set_ratio，減少誤配 |
| 時效性驗證 | 自動跳過超過 15 分鐘的舊賠率 |
| 完整日誌 | 所有操作記錄到 `logs/polymarket_bot.log` |
| 歷史回測 | 使用真實 API 數據回測過去一年表現 |

## 文檔 📚

完整文檔請查看 `docs/` 文件夾：

- **[完整文檔](docs/README.md)** - 詳細功能說明
- **[快速開始](docs/QUICK_START.md)** - 常見問題與解決方案
- **[Google Sheets](docs/setup_google_sheets.md)** - 雲端同步設定
- **[更新日誌](docs/CHANGELOG.md)** - 版本更新記錄

## 重要提醒 ⚠️

1. **不是聖杯** - 無法保證獲利
2. **手動驗證** - 下注前務必確認比賽與賠率
3. **風險管理** - 不要投入超過你能承受的損失
4. **API 限制** - Odds API 免費方案每月 500 次請求
5. **歷史回測** - 使用模擬結果（基於真實勝率），非真實交易記錄

## 回測說明 📊

### historical_backtest.py

**特點：**
- ✅ 使用真實 Odds API 歷史數據
- ✅ 回測過去一年（最多 365 天）
- ✅ 生成 HTML 詳細報告
- ✅ 計算 Sharpe Ratio、最大回撤
- ⚠️ 比賽結果使用蒙特卡羅模擬（基於真實勝率）
- ⚠️ 免費 API 可能沒有完整歷史數據

**注意：** 每次回測會消耗大量 API 配額（每天 2 次請求 x 365 天 = ~730 次）

## 支援 💬

- 查看日誌：`tail -f logs/polymarket_bot.log`
- 檢查配置：`python utils/check_status.py`
- 閱讀文檔：[docs/README.md](docs/README.md)

---

**免責聲明**：此工具僅供教育目的。投資有風險，使用前請謹慎評估。

**授權**：MIT License
# Polymarket-NBA
