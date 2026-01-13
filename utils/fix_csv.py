import pandas as pd
import os
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fix_csv():
    """修復 CSV 檔案格式問題"""
    csv_file = 'polymarket_bets.csv'

    if not os.path.exists(csv_file):
        logger.info("✅ CSV 檔案不存在，無需修復")
        return

    # 備份原始檔案
    backup_file = f'polymarket_bets_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
    os.rename(csv_file, backup_file)
    logger.info(f"📦 已備份原始檔案至: {backup_file}")

    # 嘗試讀取並修復
    try:
        # 先嘗試逐行讀取，找出問題行
        with open(backup_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        logger.info(f"📄 原始檔案共 {len(lines)} 行")

        # 分析標題行
        if lines:
            header = lines[0].strip().split(',')
            logger.info(f"📋 標題欄位 ({len(header)} 個): {header}")

        # 檢查每一行
        valid_lines = [lines[0]]  # 保留標題行
        problematic_lines = []

        for i, line in enumerate(lines[1:], start=2):
            fields = line.strip().split(',')
            if len(fields) == len(header):
                valid_lines.append(line)
            else:
                problematic_lines.append((i, len(fields), line))
                logger.warning(f"⚠️ 第 {i} 行欄位數不符: 預期 {len(header)}，實際 {len(fields)}")

        # 寫入修復後的檔案
        with open(csv_file, 'w', encoding='utf-8') as f:
            f.writelines(valid_lines)

        logger.info(f"✅ 修復完成！")
        logger.info(f"   - 保留有效行: {len(valid_lines) - 1}")
        logger.info(f"   - 移除問題行: {len(problematic_lines)}")

        if problematic_lines:
            logger.info(f"\n❌ 問題行詳情:")
            for line_num, field_count, content in problematic_lines[:5]:  # 只顯示前 5 行
                logger.info(f"   第 {line_num} 行 ({field_count} 個欄位): {content[:100]}...")

        # 驗證修復結果
        df = pd.read_csv(csv_file)
        logger.info(f"\n📊 修復後的 CSV:")
        logger.info(f"   - 欄位: {df.columns.tolist()}")
        logger.info(f"   - 資料筆數: {len(df)}")

        # 顯示前幾筆資料
        if not df.empty:
            logger.info(f"\n📋 前 3 筆資料:")
            print(df.head(3).to_string())

    except Exception as e:
        logger.error(f"❌ 修復失敗: {e}")
        # 還原備份
        if os.path.exists(backup_file):
            os.rename(backup_file, csv_file)
            logger.info("↩️  已還原原始檔案")

def migrate_old_csv():
    """將舊格式 CSV 遷移到新格式"""
    csv_file = 'polymarket_bets.csv'

    if not os.path.exists(csv_file):
        logger.info("✅ CSV 檔案不存在，無需遷移")
        return

    try:
        # 嘗試讀取舊格式
        df = pd.read_csv(csv_file, on_bad_lines='skip')

        # 檢查是否為舊格式（8 個欄位）
        old_columns = ['Date', 'Match', 'Pick', 'Price', 'Prob', 'Stake', 'Result', 'Profit']

        if list(df.columns) == old_columns:
            logger.info("🔄 偵測到舊格式 CSV，正在遷移...")

            # 創建新格式
            new_df = pd.DataFrame({
                'Date': df['Date'],
                'Sport': 'Unknown',  # 舊格式沒有此欄位
                'Match': df['Match'],
                'Pick': df['Pick'],
                'Poly_Price': df['Price'],
                'Implied_Odds': 1 / df['Price'],  # 計算隱含賠率
                'True_Prob': df['Prob'],
                'EV': 0.0,  # 舊格式沒有此欄位
                'Kelly_Stake': df['Stake'],
                'Expected_Profit': 0.0,  # 舊格式沒有此欄位
                'Match_Score': 100.0,  # 假設舊數據匹配分數為 100
                'Link': '',  # 舊格式沒有此欄位
                'Result': df['Result'],
                'Actual_Profit': df['Profit']
            })

            # 備份並寫入
            backup_file = f'polymarket_bets_old_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
            os.rename(csv_file, backup_file)
            logger.info(f"📦 已備份舊檔案至: {backup_file}")

            new_df.to_csv(csv_file, index=False)
            logger.info(f"✅ 遷移完成！已更新為新格式")

        else:
            logger.info("✅ 已是新格式，無需遷移")

    except Exception as e:
        logger.error(f"❌ 遷移失敗: {e}")

if __name__ == "__main__":
    logger.info("🔧 開始修復 CSV 檔案...\n")

    # 步驟 1: 嘗試遷移舊格式
    migrate_old_csv()

    # 步驟 2: 修復格式問題
    fix_csv()

    logger.info("\n✅ 所有修復完成！現在可以執行 google_sheets_sync.py")
