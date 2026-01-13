import pandas as pd
import os
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def merge_and_convert():
    """合併舊格式和新格式的 CSV 數據"""

    backup_file = 'polymarket_bets_backup_20260113_143232.csv'

    if not os.path.exists(backup_file):
        logger.error("❌ 找不到備份檔案")
        return

    # 手動解析混合格式的檔案
    old_format_data = []
    new_format_data = []

    with open(backup_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    # 跳過標題和空行
    for line in lines[2:]:
        line = line.strip()
        if not line:
            continue

        fields = [f.strip() for f in line.split(',')]

        # 判斷是舊格式 (8 欄) 還是新格式 (14 欄)
        if len(fields) == 8:
            # 舊格式: Date, Match, Pick, Price, Prob, Stake, Result, Profit
            try:
                old_format_data.append({
                    'Date': fields[0],
                    'Match': fields[1],
                    'Pick': fields[2],
                    'Price': float(fields[3]) if fields[3] else 0,
                    'Prob': float(fields[4]) if fields[4] else 0,
                    'Stake': float(fields[5]) if fields[5] else 0,
                    'Result': fields[6],
                    'Profit': fields[7]
                })
            except ValueError:
                continue

        elif len(fields) >= 14:
            # 新格式: Date, Sport, Match, Pick, Poly_Price, Implied_Odds, True_Prob, EV, Kelly_Stake, Expected_Profit, Match_Score, Link, Result, Actual_Profit
            try:
                new_format_data.append({
                    'Date': fields[0],
                    'Sport': fields[1],
                    'Match': fields[2],
                    'Pick': fields[3],
                    'Poly_Price': float(fields[4]) if fields[4] else 0,
                    'Implied_Odds': float(fields[5]) if fields[5] else 0,
                    'True_Prob': float(fields[6]) if fields[6] else 0,
                    'EV': float(fields[7]) if fields[7] else 0,
                    'Kelly_Stake': float(fields[8]) if fields[8] else 0,
                    'Expected_Profit': float(fields[9]) if fields[9] else 0,
                    'Match_Score': float(fields[10]) if fields[10] else 0,
                    'Link': fields[11],
                    'Result': fields[12] if len(fields) > 12 else '',
                    'Actual_Profit': fields[13] if len(fields) > 13 else ''
                })
            except ValueError:
                continue

    logger.info(f"📊 找到 {len(old_format_data)} 筆舊格式數據")
    logger.info(f"📊 找到 {len(new_format_data)} 筆新格式數據")

    # 轉換舊格式到新格式
    converted_data = []
    for old in old_format_data:
        converted_data.append({
            'Date': old['Date'],
            'Sport': 'Unknown',
            'Match': old['Match'],
            'Pick': old['Pick'],
            'Poly_Price': old['Price'],
            'Implied_Odds': round(1 / old['Price'], 2) if old['Price'] > 0 else 0,
            'True_Prob': old['Prob'],
            'EV': round((old['Prob'] - old['Price']) / old['Price'], 4) if old['Price'] > 0 else 0,
            'Kelly_Stake': old['Stake'],
            'Expected_Profit': 0.0,
            'Match_Score': 100.0,
            'Link': '',
            'Result': old['Result'],
            'Actual_Profit': old['Profit']
        })

    # 合併所有數據
    all_data = converted_data + new_format_data

    # 創建 DataFrame
    df = pd.DataFrame(all_data)

    # 移除重複項（基於 Date, Match, Pick）
    df_unique = df.drop_duplicates(subset=['Date', 'Match', 'Pick'], keep='last')

    logger.info(f"📊 合併後共 {len(df_unique)} 筆唯一數據")

    # 儲存為新格式 CSV
    output_file = 'polymarket_bets.csv'
    df_unique.to_csv(output_file, index=False)

    logger.info(f"✅ 已儲存至 {output_file}")

    # 顯示前幾筆
    logger.info("\n📋 前 3 筆數據:")
    print(df_unique.head(3).to_string(index=False))

    logger.info(f"\n📋 欄位列表:")
    logger.info(f"   {df_unique.columns.tolist()}")

if __name__ == "__main__":
    logger.info("🔄 開始合併 CSV 數據...\n")
    merge_and_convert()
    logger.info("\n✅ 完成！現在可以執行 google_sheets_sync.py")
