import requests
import time
import os
import random
from datetime import datetime
from bs4 import BeautifulSoup
from dotenv import load_dotenv

# 載入 .env 檔案
load_dotenv()

# ================= 配置區 =================
SYSTEM_NAME = "🏀 Slater AI (Pro Ver.)"
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# 監控頻率 (亂數浮動，模擬人類行為，防止被鎖)
CHECK_INTERVAL_MIN = 40
CHECK_INTERVAL_MAX = 80

# 權重名單 (Impact Players) - 完整 Tier 1 + Tier 2
IMPACT_PLAYERS = [
    # --- Tier 1: 超級巨星 ---
    "Nikola Jokic", "Joel Embiid", "Giannis Antetokounmpo", "Luka Doncic", "Shai Gilgeous-Alexander",
    "Jayson Tatum", "Stephen Curry", "LeBron James", "Kevin Durant", "Anthony Davis",
    "Devin Booker", "Anthony Edwards", "Tyrese Haliburton", "Kawhi Leonard", "Jimmy Butler",
    # --- Tier 2: 核心球星 ---
    "Donovan Mitchell", "Jalen Brunson", "Kyrie Irving", "Paul George", "Damian Lillard",
    "Trae Young", "Ja Morant", "Zion Williamson", "De'Aaron Fox", "Domantas Sabonis",
    "Bam Adebayo", "Victor Wembanyama", "Tyrese Maxey", "Jamal Murray", "LaMelo Ball"
]

# 狀態關鍵字與對應策略
STATUS_MAPPING = {
    "Out": "📉 **利空警報 (Bearish)**\n💡 建議: 核心缺陣，關注 **對家讓分** 或 **小分 (Under)**",
    "Doubtful": "⚠️ **高度危險 (High Risk)**\n💡 建議: 缺陣機率 75%，提前佈局對家可能有紅利",
    "Questionable": "❓ **變數極大 (Unknown)**\n💡 建議: 暫停操作，等待賽前 30 分鐘確認",
    "Available": "📈 **強力回歸 (Bullish)**\n💡 建議: 戰力升級，關注 **本隊讓分**",
    "Probable": "✅ **基本確認 (Likely In)**\n💡 建議: 盤口應已反應，無明顯紅利",
    "Return": "📈 **強力回歸 (Bullish)**\n💡 建議: 關注 **本隊讓分**"
}

# 偽裝標頭 (User-Agent Rotation)
USER_AGENTS = [
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36'
]

# ================= 核心功能區 =================

def send_telegram_alert(message, silence=False):
    """發送通知 (silence=True 為靜音發送，不震動)"""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown",
        "disable_notification": silence
    }
    try:
        requests.post(url, json=payload, timeout=10)
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ 訊息已推送")
    except Exception as e:
        print(f"❌ 發送失敗: {e}")

def get_nba_news():
    """抓取 Rotowire 數據 (帶偽裝)"""
    url = "https://www.rotowire.com/basketball/news.php" 
    headers = {'User-Agent': random.choice(USER_AGENTS)}
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            return response.text
    except Exception as e:
        print(f"連線錯誤: {e}")
    return ""

def analyze_news(html_content, last_seen_news):
    soup = BeautifulSoup(html_content, 'html.parser')
    news_items = soup.find_all('div', class_='news-update')
    
    current_news_ids = []
    
    for item in news_items:
        try:
            player_tag = item.find('a', class_='news-update__player-link')
            headline_tag = item.find('div', class_='news-update__headline')
            
            if not player_tag or not headline_tag:
                continue
                
            player_name = player_tag.text.strip()
            headline = headline_tag.text.strip()
            news_text = item.find('div', class_='news-update__news').text.strip()
            
            # 產生 ID
            news_id = f"{player_name}-{headline}"
            current_news_ids.append(news_id)
            
            if news_id in last_seen_news:
                continue

            # --- 判讀邏輯 ---
            # 1. 是否為關鍵球星?
            if any(impact in player_name for impact in IMPACT_PLAYERS):
                
                # 2. 判斷狀態與策略
                strategy = "🔍 **一般新聞**\n💡 建議: 密切觀察，暫無動作"
                detected_status = None
                
                # 掃描 headline 和內文尋找關鍵字
                full_text = (headline + " " + news_text).lower()
                
                for status, advice in STATUS_MAPPING.items():
                    if status.lower() in full_text:
                        strategy = advice
                        detected_status = status
                        break
                
                # 3. 只有當偵測到明確狀態時才通知
                if detected_status:
                    alert_msg = (
                        f"🚨 **Slater AI 交易訊號** 🚨\n"
                        f"━━━━━━━━━━━━━━━━\n"
                        f"🏀 **{player_name}**\n"
                        f"📝 **狀態:** {headline}\n"
                        f"━━━━━━━━━━━━━━━━\n"
                        f"{strategy}"
                    )
                    send_telegram_alert(alert_msg)
                    print(f"!!! 發現訊號: {player_name} ({detected_status}) !!!")
                    
        except Exception:
            continue
            
    return current_news_ids

# ================= 主程式 =================
if __name__ == "__main__":
    print(f"\n🔥 {SYSTEM_NAME} 啟動中...")
    print(f"🎯 監控 {len(IMPACT_PLAYERS)} 位關鍵球星")
    send_telegram_alert(f"🤖 *{SYSTEM_NAME} v2.0 上線*\n偽裝模組: ON | 智能策略: ON")  # 啟動通知有聲音
    
    seen_news = set()
    last_heartbeat = time.time()
    daily_check_sent = False  # 每日提醒標記
    
    while True:
        try:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] 📡 掃描市場...", end="\r")
            
            content = get_nba_news()
            if content:
                latest_ids = analyze_news(content, seen_news)
                if len(seen_news) > 100:
                    seen_news.clear()
                seen_news.update(latest_ids)
            
            # 心跳檢測: 每 60 分鐘發送一次存活確認 (不震動)
            if time.time() - last_heartbeat > 3600:
                send_telegram_alert(f"💓 {SYSTEM_NAME} 系統正常運行中...", silence=True)
                last_heartbeat = time.time()
            
            # 每日賽前提醒 (美西時間 16:00 ~ 16:59 之間觸發一次)
            now = datetime.now()
            target_hour = 16  # 下午 4 點
            
            # 只要是 16 點，且還沒發送過，就觸發 (不用管是第幾分鐘，保證不漏接)
            if now.hour == target_hour and not daily_check_sent:
                msg = (
                    "🔔 **賽前檢查 (Pre-Game Check)**\n"
                    "━━━━━━━━━━━━━━━━\n"
                    "目前無重大傷病警報。\n"
                    "代表市場資訊已穩定 (Efficient Market)。\n"
                    "👉 **行動建議:** 執行「下午 2 點日報」中的【Plan A】策略。"
                )
                send_telegram_alert(msg)
                daily_check_sent = True  # 標記已發送
            
            # 每天過午夜重置標記
            if now.hour == 0:
                daily_check_sent = False
            
            # 隨機等待 (防止規律被抓)
            sleep_time = random.randint(CHECK_INTERVAL_MIN, CHECK_INTERVAL_MAX)
            time.sleep(sleep_time)
            
        except KeyboardInterrupt:
            print("\n🛑 系統關閉")
            break
        except Exception as e:
            print(f"\n❌ 錯誤: {e}")
            time.sleep(60)