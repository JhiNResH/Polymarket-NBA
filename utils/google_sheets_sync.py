import os
import pandas as pd
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import logging
from datetime import datetime
from dotenv import load_dotenv

# 載入環境變數
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Google Sheets API 設定
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
SERVICE_ACCOUNT_FILE = 'google_credentials.json'  # 你的服務帳號 JSON 檔案
SPREADSHEET_ID = os.getenv('GOOGLE_SHEET_ID')  # 在 .env 中設定

def get_sheets_service():
    """建立 Google Sheets API 服務"""
    try:
        creds = Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE, scopes=SCOPES
        )
        service = build('sheets', 'v4', credentials=creds)
        return service
    except Exception as e:
        logger.error(f"❌ 無法連接 Google Sheets API: {e}")
        return None

def create_or_update_sheet(service, spreadsheet_id, sheet_name, data):
    """創建或更新工作表"""
    try:
        # 檢查工作表是否存在
        spreadsheet = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
        sheets = spreadsheet.get('sheets', [])
        sheet_exists = any(sheet['properties']['title'] == sheet_name for sheet in sheets)

        if not sheet_exists:
            # 創建新工作表
            request_body = {
                'requests': [{
                    'addSheet': {
                        'properties': {
                            'title': sheet_name
                        }
                    }
                }]
            }
            service.spreadsheets().batchUpdate(
                spreadsheetId=spreadsheet_id,
                body=request_body
            ).execute()
            logger.info(f"✅ 已創建工作表: {sheet_name}")

        # 準備數據（處理 NaN 和特殊類型）
        # 將 DataFrame 轉換為字符串，避免 JSON 序列化問題
        data_clean = data.copy()

        # 將所有欄位轉換為字符串，處理 NaN
        for col in data_clean.columns:
            data_clean[col] = data_clean[col].apply(
                lambda x: '' if pd.isna(x) else str(x)
            )

        values = [data_clean.columns.tolist()] + data_clean.values.tolist()

        # 更新數據
        range_name = f"{sheet_name}!A1"
        body = {'values': values}

        result = service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range=range_name,
            valueInputOption='RAW',
            body=body
        ).execute()

        logger.info(f"✅ 已更新 {result.get('updatedCells')} 個儲存格")
        return True

    except HttpError as error:
        logger.error(f"❌ Google Sheets API 錯誤: {error}")
        return False

def append_to_sheet(service, spreadsheet_id, sheet_name, data):
    """追加數據到工作表（不覆蓋舊數據）"""
    try:
        values = data.values.tolist()
        range_name = f"{sheet_name}!A:Z"

        body = {'values': values}

        result = service.spreadsheets().values().append(
            spreadsheetId=spreadsheet_id,
            range=range_name,
            valueInputOption='RAW',
            insertDataOption='INSERT_ROWS',
            body=body
        ).execute()

        logger.info(f"✅ 已追加 {result.get('updates').get('updatedRows')} 行數據")
        return True

    except HttpError as error:
        logger.error(f"❌ Google Sheets API 錯誤: {error}")
        return False

def sync_bets_to_sheets():
    """同步下注記錄到 Google Sheets"""
    try:
        # 讀取 CSV 檔案
        csv_file = 'data/polymarket_bets.csv'
        if not os.path.exists(csv_file):
            logger.warning("⚠️ 找不到 polymarket_bets.csv")
            return

        # 嘗試讀取 CSV，處理格式錯誤
        try:
            df = pd.read_csv(csv_file)
        except pd.errors.ParserError as e:
            logger.warning(f"⚠️ CSV 格式錯誤，嘗試修復: {e}")
            # 使用 error_bad_lines=False 跳過錯誤行（舊版 pandas）
            # 或使用 on_bad_lines='skip'（新版 pandas）
            try:
                df = pd.read_csv(csv_file, on_bad_lines='skip')
            except TypeError:
                # 如果是舊版 pandas
                df = pd.read_csv(csv_file, error_bad_lines=False, warn_bad_lines=True)

            logger.warning(f"⚠️ 已跳過 {len(df)} 行錯誤數據")

        # 檢查是否有數據
        if df.empty:
            logger.warning("⚠️ CSV 檔案為空")
            return

        # 連接 Google Sheets
        service = get_sheets_service()
        if not service:
            return

        if not SPREADSHEET_ID:
            logger.warning("⚠️  未設定 GOOGLE_SHEET_ID，跳過 Google Sheets 同步")
            logger.info("💡 如需啟用 Google Sheets 同步，請參考 setup_google_sheets.md")
            return

        # 同步到 "Bets" 工作表
        success = create_or_update_sheet(service, SPREADSHEET_ID, 'Bets', df)

        if success:
            logger.info("✅ 數據已成功同步到 Google Sheets")
            logger.info(f"📊 查看: https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}")
        else:
            logger.error("❌ 同步失敗")

    except Exception as e:
        logger.error(f"❌ 同步錯誤: {e}", exc_info=True)

def sync_daily_summary():
    """同步每日摘要到 Google Sheets"""
    try:
        csv_file = 'data/polymarket_bets.csv'
        if not os.path.exists(csv_file):
            return

        # 嘗試讀取 CSV
        try:
            df = pd.read_csv(csv_file)
        except pd.errors.ParserError:
            try:
                df = pd.read_csv(csv_file, on_bad_lines='skip')
            except TypeError:
                df = pd.read_csv(csv_file, error_bad_lines=False, warn_bad_lines=True)

        if df.empty:
            return

        # 檢查必要欄位是否存在
        required_columns = ['Date', 'Pick']
        if not all(col in df.columns for col in required_columns):
            logger.warning(f"⚠️ CSV 缺少必要欄位，目前欄位: {df.columns.tolist()}")
            return

        # 計算每日統計（根據實際存在的欄位）
        df['Date'] = pd.to_datetime(df['Date'], errors='coerce').dt.date

        agg_dict = {'Pick': 'count'}

        if 'Kelly_Stake' in df.columns:
            agg_dict['Kelly_Stake'] = 'sum'
        elif 'Stake' in df.columns:
            agg_dict['Stake'] = 'sum'

        if 'Expected_Profit' in df.columns:
            agg_dict['Expected_Profit'] = 'sum'

        if 'Actual_Profit' in df.columns:
            agg_dict['Actual_Profit'] = lambda x: pd.to_numeric(x, errors='coerce').sum()

        daily_summary = df.groupby('Date').agg(agg_dict).reset_index()

        # 同步到 "Daily Summary" 工作表
        service = get_sheets_service()
        if service and SPREADSHEET_ID:
            create_or_update_sheet(service, SPREADSHEET_ID, 'Daily Summary', daily_summary)
            logger.info("✅ 每日摘要已同步")

    except Exception as e:
        logger.error(f"❌ 同步每日摘要錯誤: {e}", exc_info=True)

def format_sheet(service, spreadsheet_id, sheet_name):
    """格式化工作表（標題加粗、凍結首行等）"""
    try:
        # 獲取工作表 ID
        spreadsheet = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
        sheets = spreadsheet.get('sheets', [])
        sheet_id = None

        for sheet in sheets:
            if sheet['properties']['title'] == sheet_name:
                sheet_id = sheet['properties']['sheetId']
                break

        if sheet_id is None:
            return

        requests = [
            # 凍結首行
            {
                'updateSheetProperties': {
                    'properties': {
                        'sheetId': sheet_id,
                        'gridProperties': {
                            'frozenRowCount': 1
                        }
                    },
                    'fields': 'gridProperties.frozenRowCount'
                }
            },
            # 標題行加粗
            {
                'repeatCell': {
                    'range': {
                        'sheetId': sheet_id,
                        'startRowIndex': 0,
                        'endRowIndex': 1
                    },
                    'cell': {
                        'userEnteredFormat': {
                            'textFormat': {
                                'bold': True
                            }
                        }
                    },
                    'fields': 'userEnteredFormat.textFormat.bold'
                }
            }
        ]

        body = {'requests': requests}
        service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body=body
        ).execute()

        logger.info(f"✅ 已格式化工作表: {sheet_name}")

    except Exception as e:
        logger.error(f"❌ 格式化錯誤: {e}")

if __name__ == "__main__":
    logger.info("🚀 開始同步數據到 Google Sheets...")
    sync_bets_to_sheets()
    sync_daily_summary()

    # 格式化工作表
    service = get_sheets_service()
    if service and SPREADSHEET_ID:
        format_sheet(service, SPREADSHEET_ID, 'Bets')
        format_sheet(service, SPREADSHEET_ID, 'Daily Summary')

    logger.info("✅ 同步完成！")
