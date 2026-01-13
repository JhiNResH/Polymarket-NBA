# 更新日誌

## 2026-01-13 - 主要優化版本

### ✨ 新增功能

1. **Kelly Criterion 資金管理**
   - 動態計算下注額，取代固定分配
   - 根據勝率和賠率優化注額
   - 單筆最多 10% 資金保護

2. **Google Sheets 整合**
   - 自動同步下注記錄到雲端
   - 每日統計摘要
   - 支援多裝置查看
   - 檔案：`google_sheets_sync.py`

3. **歷史回測功能**
   - 測試策略過去一年表現
   - 計算 Sharpe Ratio、最大回撤
   - 蒙特卡羅模擬結果
   - 檔案：`backtest.py`

4. **CSV 修復工具**
   - 自動合併舊格式和新格式
   - 修復格式錯誤
   - 檔案：`merge_csv.py`, `fix_csv.py`

5. **完整日誌系統**
   - 記錄所有操作到 `polymarket_bot.log`
   - 詳細錯誤追蹤
   - 時間戳記錄

### 🚀 核心優化

1. **改進模糊匹配算法**
   - 從 85% 提升到 90% 門檻
   - 使用 `token_set_ratio` 替代 `partial_ratio`
   - 減少隊名誤配

2. **賠率時效驗證**
   - 自動跳過超過 15 分鐘的舊賠率
   - 記錄抓取時間戳
   - 確保數據新鮮度

3. **增強錯誤處理**
   - 所有 API 請求加入超時處理
   - 詳細錯誤日誌
   - 優雅降級

4. **CSV 格式升級**
   - 新增欄位：
     - `Sport` - 運動類型
     - `Implied_Odds` - 隱含賠率
     - `EV` - 期望值
     - `Expected_Profit` - 期望獲利
     - `Match_Score` - 匹配分數
     - `Link` - Polymarket 連結

### 📊 數據追蹤改進

| 項目 | 舊版 | 新版 |
|------|------|------|
| CSV 欄位 | 8 個 | 14 個 |
| 期望獲利 | ❌ | ✅ |
| 匹配信心度 | ❌ | ✅ |
| 下注連結 | ❌ | ✅ |
| 雲端同步 | ❌ | ✅ Google Sheets |

### 🔧 技術改進

1. **依賴管理**
   - 新增 `requirements.txt`
   - 明確版本需求

2. **文檔完善**
   - `README.md` - 完整說明
   - `QUICK_START.md` - 快速開始
   - `setup_google_sheets.md` - Google Sheets 設定
   - `CHANGELOG.md` - 本檔案

3. **代碼質量**
   - 完整類型提示（部分）
   - 詳細註解
   - 模組化設計

### 🐛 修復問題

1. **CSV 格式混亂**
   - 修復舊格式和新格式混合問題
   - 提供自動合併工具

2. **API 錯誤處理**
   - 加入超時機制
   - 避免無限等待

3. **Discord 通知失敗**
   - 改善錯誤訊息
   - 加入日誌記錄

### 📈 性能提升

- API 請求加入超時（10 秒）
- 減少不必要的重複計算
- 優化模糊匹配效能

### ⚠️ 破壞性變更

1. **CSV 格式變更**
   - 舊格式 8 欄 → 新格式 14 欄
   - 需執行 `merge_csv.py` 遷移舊數據

2. **環境變數檢查**
   - 啟動時強制檢查 `ODDS_API_KEY` 和 `DISCORD_WEBHOOK_URL`
   - 缺少時會立即退出

### 🔜 未來計劃

- [ ] 整合 Polymarket CLOB API 查詢流動性
- [ ] 自動更新比賽結果
- [ ] 加入更多運動（NFL, MLB, 足球）
- [ ] 機器學習優化參數
- [ ] 網頁儀表板
- [ ] 自動下單功能

---

## 使用建議

### 升級步驟

1. **備份舊數據**
   ```bash
   cp polymarket_bets.csv polymarket_bets_old_backup.csv
   ```

2. **更新代碼**
   ```bash
   git pull  # 或下載最新版本
   ```

3. **安裝依賴**
   ```bash
   pip install -r requirements.txt
   ```

4. **合併 CSV 格式**
   ```bash
   python merge_csv.py
   ```

5. **測試運行**
   ```bash
   python trade.py
   ```

### 新用戶快速開始

直接閱讀 [QUICK_START.md](QUICK_START.md)

---

## 版本對比

### 資金管理
- **舊版**：固定 50% 平分 3 注
- **新版**：Kelly Criterion 動態計算

### 數據追蹤
- **舊版**：基本 CSV（8 欄）
- **新版**：詳細 CSV（14 欄）+ Google Sheets 雲端同步

### 匹配準確度
- **舊版**：85% 門檻 + partial_ratio
- **新版**：90% 門檻 + token_set_ratio

### 錯誤處理
- **舊版**：簡單 try-except
- **新版**：完整 logging + 超時 + 優雅降級

### 回測功能
- **舊版**：無
- **新版**：完整回測系統（Sharpe Ratio、最大回撤）

---

## 致謝

感謝所有使用者的反饋和建議！

---

**免責聲明**：此工具僅供教育目的。投資有風險，使用前請謹慎評估。
