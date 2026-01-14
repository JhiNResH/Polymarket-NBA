import requests
import time
import os
import random
from datetime import datetime
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()

# ================= ⚙️ 系統配置區 =================
SYSTEM_NAME = "🦅 Slator Prime (Market Expert)"
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

CHECK_INTERVAL_MIN = 40
CHECK_INTERVAL_MAX = 80

USER_AGENTS = [
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36'
]

# ================= 🏀 NBA 配置 (主攻 Spread) =================
NBA_TARGETS = [
    "Nikola Jokic", "Joel Embiid", "Giannis Antetokounmpo", "Luka Doncic", "Shai Gilgeous-Alexander",
    "Jayson Tatum", "Stephen Curry", "LeBron James", "Kevin Durant", "Anthony Davis",
    "Devin Booker", "Anthony Edwards", "Tyrese Haliburton", "Kawhi Leonard", "Jimmy Butler",
    "Donovan Mitchell", "Jalen Brunson", "Kyrie Irving", "Paul George", "Damian Lillard",
    "Trae Young", "Ja Morant", "Zion Williamson", "Victor Wembanyama", "Jamal Murray"
]

# NBA 針對盤口的精細化建議
NBA_STRATEGY = {
    "Out":          "📉 **利空 (Bearish)**\n🎯 **推薦盤口:** 對家讓分 (Spread)\n💡 邏輯: 趁莊家沒改盤，買受讓最穩。",
    "Doubtful":     "⚠️ **高度危險**\n🎯 **推薦盤口:** 對家讓分 (Spread)\n💡 邏輯: 缺陣機率高，提前卡位。",
    "Questionable": "❓ **變數極大**\n🎯 **推薦盤口:** 暫停操作 (Pass)\n💡 邏輯: 等待賽前 GTD 確認。",
    "Available":    "📈 **戰力回歸 (Bullish)**\n🎯 **推薦盤口:** 本隊讓分 (Spread)\n💡 邏輯: 巨星回歸，看好大勝。",
    "Game Time":    "⏳ **賽前決定 (GTD)**\n🎯 **推薦盤口:** 觀望\n💡 邏輯: 風險過高。"
}

# ================= 🎮 LoL 配置 (主攻 Game 1) =================
LOL_TEAM_DB = {
    "GEN": {"name": "Gen.G", "game1_wr_high": True,  "tier": "S"},
    "T1":  {"name": "T1",    "game1_wr_high": True,  "tier": "S"},
    "HLE": {"name": "HLE",   "game1_wr_high": True,  "tier": "A+"},
    "DK":  {"name": "Dplus", "game1_wr_high": False, "tier": "A"},
    "KT":  {"name": "KT",    "game1_wr_high": False, "tier": "B"},
    "BLG": {"name": "BLG",   "game1_wr_high": True,  "tier": "S"},
    "JDG": {"name": "JDG",   "game1_wr_high": True,  "tier": "S"},
    "TES": {"name": "TES",   "game1_wr_high": True,  "tier": "A+"},
    "WBG": {"name": "WBG",   "game1_wr_high": False, "tier": "A"},
}

PLAYER_MAP = {
    "Faker": "T1", "Zeus": "T1", "Oner": "T1", "Gumayusi": "T1", "Keria": "T1",
    "Chovy": "GEN", "Canyon": "GEN", "Ruler": "GEN", "Kiin": "GEN", "Peyz": "GEN",
    "Viper": "HLE", "Zeka": "HLE", "Peanut": "HLE", "Doran": "HLE", "Delight": "HLE",
    "ShowMaker": "DK", "Aiming": "DK", "Lucid": "DK",
    "Knight": "BLG", "Bin": "BLG", "Elk": "BLG", "Xun": "BLG", "ON": "BLG",
    "Kanavi": "JDG", "Yagao": "JDG", "Missing": "JDG",
    "JackeyLove": "TES", "Tian": "TES", "Creme": "TES", "Meiko": "TES",
    "TheShy": "WBG", "Xiaohu": "WBG", "Light": "WBG"
}

# LoL 策略 (全部導向 Game 1)
LOL_STRATEGY = {
    "Start": "✅ **首發確認 (Starting)**",
    "Bench": "📉 **板凳警報 (Benched)**",
    "Sub":   "⚠️ **替補上陣 (Sub)**"
}

# ================= 核心邏輯 =================

def send_telegram(message, silence=False):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown", "disable_notification": silence
    }
    try: requests.post(url, json=payload, timeout=10)
    except: pass

def fetch_news(url):
    headers = {'User-Agent': random.choice(USER_AGENTS)}
    try:
        r = requests.get(url, headers=headers, timeout=10)
        return r.text if r.status_code == 200 else ""
    except: return ""

def calculate_scenarios(team_code, status_key):
    if team_code not in LOL_TEAM_DB: return None, None
    data = LOL_TEAM_DB[team_code]
    
    base_score = 0
    if "Start" in status_key: base_score += 50
    elif "Bench" in status_key or "Sub" in status_key: return 0, 0
    else: base_score += 20
    
    if data["tier"] == "S": base_score += 30
    elif data["tier"] == "A+": base_score += 20
    else: base_score += 10
    
    if data["game1_wr_high"]: base_score += 20

    blue_score = min(base_score + 10, 100)
    red_score = max(base_score - 10, 0)
    return blue_score, red_score

def process_nba(seen_ids):
    html = fetch_news("https://www.rotowire.com/basketball/news.php")
    if not html: return []
    soup = BeautifulSoup(html, 'html.parser')
    new_ids = []
    
    for item in soup.find_all('div', class_='news-update'):
        try:
            name = item.find('a', class_='news-update__player-link').text.strip()
            headline = item.find('div', class_='news-update__headline').text.strip()
            news_text = item.find('div', class_='news-update__news').text.strip()
            news_id = f"NBA-{name}-{headline}"
            
            if news_id in seen_ids: continue
            new_ids.append(news_id)

            if any(t in name for t in NBA_TARGETS):
                advice = "🔍 密切觀察"
                # 這裡會抓取我們設定好的「推薦盤口」
                full = headline + " " + news_text
                for k, v in NBA_STRATEGY.items():
                    if k in full: advice = v; break
                
                send_telegram(f"🏀 **NBA Signal: {name}**\n📝 {headline}\n━━━━━━━━\n{advice}")
                print(f"⚡ NBA: {name}")
        except: continue
    return new_ids

def process_lol(seen_ids):
    html = fetch_news("https://www.rotowire.com/esports/lol/news.php")
    if not html: return []
    soup = BeautifulSoup(html, 'html.parser')
    new_ids = []
    
    for item in soup.find_all('div', class_='news-update'):
        try:
            name = item.find('a', class_='news-update__player-link').text.strip()
            headline = item.find('div', class_='news-update__headline').text.strip()
            news_text = item.find('div', class_='news-update__news').text.strip()
            news_id = f"LOL-{name}-{headline}"
            
            if news_id in seen_ids: continue
            new_ids.append(news_id)

            # 先查 PLAYER_MAP (選手→戰隊)，再檢查是否本身就是戰隊碼
            team_code = PLAYER_MAP.get(name) or (name if name in LOL_TEAM_DB else None)
            
            if team_code:
                status_key = "Info"
                advice = "🔍 情報更新"
                full = headline + " " + news_text
                for k, v in LOL_STRATEGY.items():
                    if k in full: advice = v; status_key = k; break
                
                blue_score, red_score = calculate_scenarios(team_code, status_key)
                
                scenario_msg = ""
                if blue_score > 0:
                    # 強制推薦 Game 1 Winner
                    scenario_msg = (
                        f"\n🎯 **推薦盤口: Game 1 Winner (第一局獨贏)**\n"
                        f"🔵 **若為藍方:** Score {blue_score} ➔ 🔥 重注\n"
                        f"🔴 **若為紅方:** Score {red_score} ➔ ⚠️ 輕注"
                    )
                elif blue_score == 0:
                    scenario_msg = "\n🛑 **風險警報: 放棄所有盤口 (Pass)**"

                send_telegram(
                    f"🎮 **LoL Signal: {team_code} ({name})**\n"
                    f"📝 {headline}\n"
                    f"━━━━━━━━━━━━━━━━\n"
                    f"{advice}"
                    f"{scenario_msg}"
                )
                print(f"⚡ LoL: {team_code}")
        except: continue
    return new_ids

if __name__ == "__main__":
    print(f"\n🦅 {SYSTEM_NAME} ONLINE")
    send_telegram(f"🤖 *Slator v6.0 (Market Expert) 上線*", silence=True)
    
    seen_news = set()
    last_heartbeat = time.time()
    
    while True:
        try:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] 掃描中...", end="\r")
            seen_news.update(process_nba(seen_news))
            seen_news.update(process_lol(seen_news))
            if len(seen_news) > 500: seen_news.clear()
            
            if time.time() - last_heartbeat > 3600:
                send_telegram("💓 Slator 運行中...", silence=True)
                last_heartbeat = time.time()
                
            time.sleep(random.randint(CHECK_INTERVAL_MIN, CHECK_INTERVAL_MAX))
        except KeyboardInterrupt: break
        except Exception as e: time.sleep(60)