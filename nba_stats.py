import pandas as pd
import time

# 目標網址
url = "https://www.basketball-reference.com/leagues/NBA_2026_totals.html"

try:
    print(f"正在從 {url} 讀取數據...")
    
    # 使用 pandas 的 read_html 直接抓取表格
    # Basketball Reference 的表格通常是頁面中的第一個表格
    dfs = pd.read_html(url)
    
    if len(dfs) > 0:
        df = dfs[0]
        
        # 清理數據：
        # 1. 移除重複的標頭列（每隔一段距離表格會重複標頭）
        df = df[df['Rk'] != 'Rk']
        
        # 2. 處理球員轉隊情況（Total 行通常是我們需要的，但也保留各隊數據）
        # 如果只需要每位球員的總計，可以篩選 Tm == 'TOT'，但這裡我們先保留全部
        
        # 3. 輸出成 CSV
        filename = "nba_2026_totals.csv"
        df.to_csv(filename, index=False, encoding='utf-8-sig')
        
        print(f"成功！已將 {len(df)} 筆球員數據儲存為 '{filename}'")
        print("所有數據預覽：")
        print(df)
        
    else:
        print("錯誤：在頁面上找不到表格。")

except Exception as e:
    print(f"發生錯誤：{e}")
    print("提示：如果遇到 429 Too Many Requests 錯誤，請稍後再試，或嘗試在請求中加入 User-Agent header。")