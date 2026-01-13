# 快速開始指南 🚀

## 問題：CSV 格式錯誤怎麼辦？

如果遇到以下錯誤：
```
Error tokenizing data. C error: Expected 8 fields in line 9, saw 14
```

**解決方法：**

### 選項 1: 自動修復（推薦）
```bash
python merge_csv.py
```
這會自動合併舊格式和新格式的數據。

### 選項 2: 手動修復
```bash
python fix_csv.py
```
這會移除格式錯誤的行。

### 選項 3: 重新開始
```bash
# 備份舊檔案
mv polymarket_bets.csv polymarket_bets_old.csv

# 重新執行程式
python trade.py
```

---

## 每日使用流程 📅

### 1. 執行主程式
```bash
python trade.py
```

**這會：**
- 抓取最新賠率
- 找出高價值下注機會
- 發送 Discord 通知
- 儲存到 CSV

### 2. 查看 Discord
- 檢查推薦的下注
- 點擊連結前往 Polymarket

### 3. 手動下注
- 在 Polymarket 上下注
- 記錄實際下注金額

### 4. 更新結果（可選）
在 Google Sheets 或 CSV 中更新：
- `Result` 欄位：填入 `Win` 或 `Loss`
- `Actual_Profit` 欄位：填入實際盈虧

---

## 常用命令 🔧

```bash
# 每日執行主程式
python trade.py

# 回測歷史表現
python backtest.py

# 同步到 Google Sheets
python google_sheets_sync.py

# 修復 CSV 格式
python merge_csv.py

# 修復 CSV 錯誤（移除問題行）
python fix_csv.py
```

---

## 自動化設定 ⏰

### macOS / Linux

```bash
# 編輯 crontab
crontab -e

# 加入以下行（每天早上 9 點執行）
0 9 * * * cd /Users/jhinresh/Desktop/polytrade && /usr/bin/python3 trade.py >> /tmp/polytrade.log 2>&1
```

### 驗證 crontab
```bash
crontab -l
```

### 查看執行日誌
```bash
tail -f /tmp/polytrade.log
# 或
tail -f /Users/jhinresh/Desktop/polytrade/polymarket_bot.log
```

---

## 調整策略參數 🎯

編輯 [trade.py](trade.py) 的參數：

```python
# 資金管理
BANKROLL = 20.0           # 本金（每天更新）
MIN_BET_SIZE = 1.0        # 最小下注額
MAX_BETS = 3              # 每日最多下注數

# 策略過濾
MIN_WIN_PROB = 0.55       # 最低勝率 55%
MIN_EV = 0.015            # 最低期望值 1.5%
KELLY_FRACTION = 0.25     # Kelly 分數（0.25 = 保守）

# 匹配設定
MIN_FUZZY_SCORE = 90      # 隊名匹配門檻
MAX_ODDS_AGE_MINUTES = 15 # 賠率最大延遲
```

**建議設定：**
- **保守型**：`MIN_WIN_PROB=0.60`, `MIN_EV=0.02`, `KELLY_FRACTION=0.2`
- **平衡型**：`MIN_WIN_PROB=0.55`, `MIN_EV=0.015`, `KELLY_FRACTION=0.25`（預設）
- **激進型**：`MIN_WIN_PROB=0.52`, `MIN_EV=0.01`, `KELLY_FRACTION=0.3`

---

## Google Sheets 設定 ☁️

詳細步驟請參考 [setup_google_sheets.md](setup_google_sheets.md)

**快速步驟：**

1. 創建 Google Cloud 專案
2. 啟用 Google Sheets API
3. 建立服務帳號並下載 JSON 金鑰
4. 重新命名為 `google_credentials.json`
5. 在 `.env` 加入：
   ```
   GOOGLE_SHEET_ID=你的試算表ID
   ```
6. 測試同步：
   ```bash
   python google_sheets_sync.py
   ```

---

## 常見問題 ❓

### Q: 為什麼沒有找到任何下注機會？
**A:** 可能原因：
1. 當天沒有符合高勝率標準的比賽（這是正常的）
2. Pinnacle 或 Polymarket API 無回應
3. 參數設定太嚴格

**解決方法：**
- 調低 `MIN_WIN_PROB` 或 `MIN_EV`
- 檢查 API 金鑰是否有效
- 查看 `polymarket_bot.log` 錯誤訊息

### Q: Discord 通知沒收到？
**A:** 檢查：
1. `.env` 中的 `DISCORD_WEBHOOK_URL` 是否正確
2. Webhook 是否仍然有效
3. 查看終端機錯誤訊息

### Q: Google Sheets 同步失敗？
**A:** 確認：
1. `google_credentials.json` 在正確位置
2. 服務帳號已加入試算表並設為編輯者
3. `GOOGLE_SHEET_ID` 正確
4. 已安裝 Google API 套件：
   ```bash
   pip install google-api-python-client google-auth
   ```

### Q: CSV 格式錯誤？
**A:** 執行：
```bash
python merge_csv.py
```

### Q: 如何更新本金？
**A:** 每天執行前，手動編輯 [trade.py](trade.py)：
```python
BANKROLL = 25.0  # 更新為實際餘額
```

或使用環境變數（在 `.env` 中）：
```bash
BANKROLL=25.0
```

然後在程式中讀取：
```python
BANKROLL = float(os.getenv('BANKROLL', 20.0))
```

### Q: 回測結果可信嗎？
**A:**
- 回測使用蒙特卡羅模擬，**不是真實歷史價格**
- 僅供參考，不保證未來表現
- 實際結果會受流動性、滑價、時效性影響

---

## 檔案結構 📁

```
polytrade/
├── .env                          # 環境變數（API 金鑰）
├── trade.py                      # 主程式
├── backtest.py                   # 回測腳本
├── google_sheets_sync.py         # Google Sheets 同步
├── fix_csv.py                    # CSV 修復工具
├── merge_csv.py                  # CSV 合併工具
├── requirements.txt              # 依賴套件
├── README.md                     # 完整文檔
├── setup_google_sheets.md        # Google Sheets 設定
├── QUICK_START.md                # 本檔案
├── polymarket_bets.csv           # 下注記錄
├── polymarket_bot.log            # 執行日誌
└── google_credentials.json       # Google API 金鑰（需自行創建）
```

---

## 重要提醒 ⚠️

1. **不是聖杯**：無法保證獲利
2. **手動驗證**：下注前務必確認比賽與賠率
3. **資金管理**：不要投入超過你能承受的損失
4. **API 限制**：Odds API 有每月請求限制
5. **時效性**：價值機會稍縱即逝
6. **流動性**：Polymarket 大額下注會有滑價

---

## 支援 💬

遇到問題？
1. 查看 `polymarket_bot.log`
2. 閱讀完整文檔 [README.md](README.md)
3. 開 Issue 或聯繫作者

---

**祝你好運！🍀**
