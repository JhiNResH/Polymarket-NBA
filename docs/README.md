# Polymarket 自動交易機器人 🤖

基於 Pinnacle 賠率的價值投注系統，使用 Kelly Criterion 進行資金管理。

## 功能特色 ✨

- ✅ **智能匹配**：自動比對 Pinnacle 與 Polymarket 賠率
- ✅ **Kelly Criterion**：科學化資金管理
- ✅ **高勝率過濾**：只選擇勝率 >55% 且 EV >1.5% 的機會
- ✅ **Discord 通知**：即時推送下注建議
- ✅ **Google Sheets 同步**：自動記錄到雲端試算表
- ✅ **歷史回測**：測試策略過去表現
- ✅ **完整日誌**：記錄所有操作與錯誤

## 快速開始 🚀

### 1. 安裝依賴

```bash
pip install -r requirements.txt
```

### 2. 設定環境變數

創建 `.env` 檔案：

```bash
ODDS_API_KEY=你的OddsAPI金鑰
DISCORD_WEBHOOK_URL=你的Discord Webhook網址
GOOGLE_SHEET_ID=你的Google試算表ID（可選）
```

### 3. 調整參數

編輯 [trade.py](trade.py) 中的參數：

```python
BANKROLL = 20.0          # 本金
DAILY_RISK_PCT = 0.50    # 每日風險比例
MAX_BETS = 3             # 每日最多下注數
MIN_WIN_PROB = 0.55      # 最低勝率門檻
MIN_EV = 0.015           # 最低期望值門檻
KELLY_FRACTION = 0.25    # Kelly 分數（保守）
```

### 4. 執行程式

```bash
python trade.py
```

## 檔案說明 📁

- [trade.py](trade.py) - 主程式（每日執行）
- [backtest.py](backtest.py) - 回測腳本（測試歷史表現）
- [google_sheets_sync.py](google_sheets_sync.py) - Google Sheets 同步
- [fix_csv.py](fix_csv.py) - CSV 格式修復工具
- [merge_csv.py](merge_csv.py) - CSV 格式合併工具（推薦）
- [setup_google_sheets.md](setup_google_sheets.md) - Google Sheets 設定教學
- [QUICK_START.md](QUICK_START.md) - 快速開始指南

## 使用流程 📊

1. **每日執行** `python trade.py`
2. **查看 Discord** 獲取下注建議
3. **手動下注** 到 Polymarket
4. **更新結果** 在 Google Sheets 或 CSV 中記錄結果
5. **（可選）同步** `python google_sheets_sync.py`

## 故障排除 🔧

### CSV 格式錯誤
如果遇到 `Error tokenizing data` 錯誤：

```bash
# 自動合併舊格式和新格式（推薦）
python merge_csv.py

# 或手動修復
python fix_csv.py
```

詳細說明請參考 [QUICK_START.md](QUICK_START.md)

## 優化項目 ⚡

相比原版，已優化：

### 1. 資金管理
- ❌ 固定注額 → ✅ Kelly Criterion 動態計算
- ❌ 平均分配 → ✅ 根據勝率與賠率調整

### 2. 匹配準確度
- ❌ 85% 門檻 + partial_ratio → ✅ 90% 門檻 + token_set_ratio
- ❌ 可能誤配 → ✅ 更精確的隊名匹配

### 3. 數據時效性
- ❌ 無時間戳驗證 → ✅ 賠率超過 15 分鐘自動跳過
- ❌ 不知道數據是否過時 → ✅ 記錄抓取時間

### 4. 錯誤處理
- ❌ 簡單 try-except → ✅ 完整 logging + 超時處理
- ❌ 靜默失敗 → ✅ 詳細錯誤訊息

### 5. 數據追蹤
- ❌ 空的 Result/Profit 欄位 → ✅ 完整 CSV + Google Sheets 整合
- ❌ 無法計算實際 ROI → ✅ 自動計算期望獲利與實際表現

### 6. 回測功能
- ❌ 無法驗證策略 → ✅ 回測過去一年的表現
- ❌ 不知道最大回撤 → ✅ 計算 Sharpe Ratio 與最大回撤

## 回測使用 📈

```bash
python backtest.py
```

這會模擬過去一年的交易，輸出：
- 總獲利 / ROI
- 勝率
- Sharpe Ratio
- 最大回撤

**注意**：回測使用蒙特卡羅模擬，結果僅供參考。

## Google Sheets 同步 ☁️

詳細設定請參考 [setup_google_sheets.md](setup_google_sheets.md)

好處：
- 📱 手機隨時查看
- 📊 自動生成圖表
- 🔔 設定條件式警示
- 🤝 與團隊共享數據

## 自動化執行 ⏰

### macOS / Linux (crontab)

每天早上 9 點執行：

```bash
crontab -e
```

加入：

```bash
0 9 * * * cd /Users/jhinresh/Desktop/polytrade && /usr/bin/python3 trade.py
```

### Windows (工作排程器)

1. 開啟工作排程器
2. 建立基本工作
3. 觸發：每天 09:00
4. 動作：執行 `python trade.py`

## 重要提醒 ⚠️

1. **不是聖杯**：這只是輔助工具，無法保證獲利
2. **風險管理**：不要投入超過你能承受的損失
3. **手動驗證**：下注前務必確認比賽與賠率正確
4. **API 限制**：Odds API 有每月請求限制
5. **流動性**：Polymarket 大額下注會有滑價
6. **時效性**：機會稍縱即逝，建議設定自動通知

## 已知限制 🚧

- ❌ 無法檢查 Polymarket 實際流動性
- ❌ 未整合自動下單（需手動）
- ❌ 回測使用模擬數據（非真實歷史價格）
- ❌ 未考慮交易手續費

## 未來改進 🔮

- [ ] 整合 Polymarket CLOB API 查詢訂單簿
- [ ] 自動比對比賽結果並更新 P&L
- [ ] 加入更多運動（NFL, MLB, 足球等）
- [ ] 機器學習優化 EV 門檻
- [ ] 網頁儀表板

## 授權 📄

MIT License - 自由使用，風險自負

## 支援 💬

有問題請開 Issue 或聯繫作者。

---

**免責聲明**：此工具僅供教育目的。投資有風險，使用前請謹慎評估。
