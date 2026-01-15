import requests
import time
import os
import random
from datetime import datetime
from urllib.parse import quote
from bs4 import BeautifulSoup
from dotenv import load_dotenv

# 載入 .env 環境變數
load_dotenv()

# ================= ⚙️ 系統配置區 =================
SYSTEM_NAME = "🦅 Slator Prime (Full Stack)"
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# 模擬人類瀏覽器的 User-Agent
USER_AGENTS = [
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36'
]

# 監控頻率 (秒)
CHECK_INTERVAL_MIN = 40
CHECK_INTERVAL_MAX = 80

# ================= 🏀 NBA 數據庫 =================
NBA_TARGETS = [
    "Nikola Jokic", "Joel Embiid", "Giannis Antetokounmpo", "Luka Doncic", "Shai Gilgeous-Alexander",
    "Jayson Tatum", "Stephen Curry", "LeBron James", "Kevin Durant", "Anthony Davis",
    "Devin Booker", "Anthony Edwards", "Tyrese Haliburton", "Kawhi Leonard", "Jimmy Butler",
    "Donovan Mitchell", "Jalen Brunson", "Kyrie Irving", "Paul George", "Damian Lillard",
    "Trae Young", "Ja Morant", "Zion Williamson", "Victor Wembanyama", "Jamal Murray"
]

PLAYER_TO_TEAM = {
    "Nikola Jokic": "Nuggets", "Joel Embiid": "76ers", "Giannis Antetokounmpo": "Bucks",
    "Luka Doncic": "Lakers", "Shai Gilgeous-Alexander": "Thunder", "Jayson Tatum": "Celtics",
    "Stephen Curry": "Warriors", "LeBron James": "Lakers", "Kevin Durant": "Rockets",
    "Anthony Davis": "Mavericks", "Devin Booker": "Suns", "Anthony Edwards": "Timberwolves",
    "Tyrese Haliburton": "Pacers", "Kawhi Leonard": "Clippers", "Jimmy Butler": "Warriors",
    "Donovan Mitchell": "Cavaliers", "Jalen Brunson": "Knicks", "Kyrie Irving": "Mavericks",
    "Paul George": "76ers", "Damian Lillard": "Bucks", "Trae Young": "Wizards",
    "Ja Morant": "Grizzlies", "Zion Williamson": "Pelicans", "Victor Wembanyama": "Spurs",
    "Jamal Murray": "Nuggets","James Harden": "Clippers","Jimmy Butler": "Warriors", "Alperen Şengün": "Rockets", 
}
# 模糊比對用的隊名清單
NBA_TEAMS_LIST = [
    "Celtics", "Nets", "Knicks", "76ers", "Raptors", "Bulls", "Cavaliers", "Pistons", "Pacers", "Bucks",
    "Hawks", "Hornets", "Heat", "Magic", "Wizards", "Nuggets", "Timberwolves", "Thunder", "Blazers", "Jazz",
    "Warriors", "Clippers", "Lakers", "Suns", "Kings", "Mavericks", "Rockets", "Grizzlies", "Pelicans", "Spurs"
]

NBA_STRATEGY = {
    "Out":          "📉 **利空 (Bearish)**\n🎯 **策略:** PolyMarket 買對手 Yes / 對家讓分",
    "Doubtful":     "⚠️ **高度危險**\n🎯 **策略:** 提前佈局對家",
    "Questionable": "❓ **變數極大**\n🎯 **策略:** 觀望 (Pass)",
    "Available":    "📈 **戰力回歸 (Bullish)**\n🎯 **策略:** PolyMarket 買本隊 Yes / 本隊讓分",
    "Game Time":    "⏳ **賽前決定 (GTD)**\n🎯 **策略:** 觀望"
}

# ================= 🎮 LoL 數據庫 (量化模型) =================
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

LOL_STRATEGY = {
    "Start": "✅ **首發確認 (Starting)**",
    "Bench": "📉 **板凳警報 (Benched)**",
    "Sub":   "⚠️ **替補上陣 (Sub)**"
}

# 全局變數：儲存今日賽程快取
TODAY_MATCHUPS = {} 

# ================= �️ 工具函數區 =================

def fetch_content(url):
    """通用爬蟲函數"""
    headers = {'User-Agent': random.choice(USER_AGENTS)}
    try:
        r = requests.get(url, headers=headers, timeout=10)
        return r.text if r.status_code == 200 else ""
    except: return ""

def send_telegram(message, silence=False):
    """發送 Telegram 訊息"""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID, 
        "text": message, 
        "parse_mode": "Markdown", 
        "disable_notification": silence, 
        "disable_web_page_preview": True
    }
    try: requests.post(url, json=payload, timeout=10)
    except: pass

def get_daily_schedule():
    """抓取 NBA 今日賽程與主客場資訊"""
    url = "https://www.cbssports.com/nba/schedule/"
    matchups = {}
    try:
        html = fetch_content(url)
        soup = BeautifulSoup(html, 'html.parser')
        rows = soup.find_all('tr', class_='TableBase-bodyTr')
        for row in rows:
            team_links = row.find_all('a', class_='TeamLogoNameLockup-link')
            if len(team_links) >= 2:
                team_a_full = team_links[0].text.strip() # 客隊 (Away)
                team_b_full = team_links[1].text.strip() # 主隊 (Home)
                
                # 模糊匹配標準隊名
                team_a = next((t for t in NBA_TEAMS_LIST if t in team_a_full), team_a_full)
                team_b = next((t for t in NBA_TEAMS_LIST if t in team_b_full), team_b_full)
                
                # 建立雙向查詢
                matchups[team_a] = {'opp': team_b, 'is_home': False}
                matchups[team_b] = {'opp': team_a, 'is_home': True}
        print(f"✅ 賽程更新完成: 監控 {len(matchups)//2} 場比賽")
        return matchups
    except Exception as e:
        print(f"Schedule Error: {e}")
        return {}

def get_team_stats(team_name):
    """抓取 NBA 球隊詳細戰績 (CBS)"""
    url = "https://www.cbssports.com/nba/standings/"
    try:
        html = fetch_content(url)
        soup = BeautifulSoup(html, 'html.parser')
        rows = soup.find_all('tr', class_='TableBase-bodyTr')
        for row in rows:
            name_tag = row.find('span', class_='TeamLogoNameLockup-name')
            if name_tag and team_name in name_tag.text:
                cols = row.find_all('td')
                return {
                    "record": f"{cols[1].text.strip()}-{cols[2].text.strip()}", # 勝-負
                    "l10": cols[13].text.strip(),   # 近10場
                    "streak": cols[12].text.strip() # 連勝敗
                }
    except: pass
    return {"record": "N/A", "l10": "-", "streak": "-"}

def get_polymarket_data(team_name, sport="NBA"):
    """查詢 PolyMarket 即時價格"""
    base_url = "https://gamma-api.polymarket.com/events"
    if not team_name: return None
    try:
        query = quote(team_name)
        r = requests.get(base_url, params={"limit": 5, "active": "true", "closed": "false", "keyword": query}, timeout=5)
        if r.status_code == 200:
            for e in r.json():
                title = e.get("title", "").upper()
                # 簡單過濾運動類型
                if sport == "NBA" and "NBA" not in title and "BASKETBALL" not in title: continue
                
                for m in e.get("markets", []):
                    try:
                        prices = eval(m.get("outcomePrices", "[]"))
                        if prices and len(prices) >= 2:
                            return {
                                "event": e['title'], 
                                "price": f"Yes: {prices[0]} | No: {prices[1]}", 
                                "url": f"https://polymarket.com/event/{e['slug']}"
                            }
                    except: continue
    except: pass
    return None

def calculate_lol_scenarios(team_code, status_key):
    """LoL 量化評分引擎"""
    if team_code not in LOL_TEAM_DB: return None, None
    data = LOL_TEAM_DB[team_code]
    
    base = 0
    if "Start" in status_key: base += 50
    elif "Bench" in status_key or "Sub" in status_key: return 0, 0
    else: base += 20
    
    if data["tier"] == "S": base += 30
    elif data["tier"] == "A+": base += 20
    else: base += 10
    
    if data["game1_wr_high"]: base += 20
    
    # 滿分 100
    blue_score = min(base + 10, 100)
    red_score = max(base - 10, 0)
    return blue_score, red_score

# ================= 🧠 核心處理邏輯 =================

def process_nba(seen_ids):
    global TODAY_MATCHUPS
    html = fetch_content("https://www.rotowire.com/basketball/news.php")
    soup = BeautifulSoup(html, 'html.parser')
    new_ids = []
    
    for item in soup.find_all('div', class_='news-update'):
        try:
            name = item.find('a', class_='news-update__player-link').text.strip()
            headline = item.find('div', class_='news-update__headline').text.strip()
            news_id = f"NBA-{name}-{headline}"
            
            if news_id in seen_ids: continue
            new_ids.append(news_id)

            if any(t in name for t in NBA_TARGETS):
                # 1. 取得基礎策略
                advice = "🔍 密切觀察"
                full_txt = headline + " " + item.find('div', class_='news-update__news').text.strip()
                for k, v in NBA_STRATEGY.items():
                    if k in full_txt: advice = v; break
                
                team_name = PLAYER_TO_TEAM.get(name, name.split()[-1])
                
                # 2. 對戰情境分析 (Matchup Context)
                context_msg = ""
                matchup = TODAY_MATCHUPS.get(team_name)
                
                if matchup:
                    opp_name = matchup['opp']
                    is_home = matchup['is_home']
                    venue = "🏠 主場" if is_home else "✈️ 客場"
                    
                    # 抓雙方戰績
                    team_stats = get_team_stats(team_name)
                    opp_stats = get_team_stats(opp_name)
                    
                    context_msg = (
                        f"\n⚔️ **對戰情境 (Context)**\n"
                        f"🏟️ {venue} vs {opp_name}\n"
                        f"� 本隊: {team_stats['record']} (L10: {team_stats['l10']})\n"
                        f"🛡️ 對手: {opp_stats['record']} (L10: {opp_stats['l10']})\n"
                    )
                else:
                    context_msg = "\n⚠️ 無今日賽程 (或為明日賽事)"

                # 3. PolyMarket 價格
                poly_data = get_polymarket_data(team_name, "NBA")
                poly_msg = f"\n🔮 **PolyMarket:** 暫無盤口"
                if poly_data:
                    poly_msg = (
                        f"\n🔮 **PolyMarket Live**\n"
                        f"💰 {poly_data['price']}\n"
                        f"👉 [點擊下注]({poly_data['url']})"
                    )

                send_telegram(
                    f"🏀 **NBA Signal: {name}**\n"
                    f"📝 {headline}\n"
                    f"━━━━━━━━━━━━━━━━\n"
                    f"{advice}"
                    f"{context_msg}"
                    f"{poly_msg}"
                )
                print(f"⚡ NBA: {name} | Matchup: {matchup.get('opp') if matchup else 'N/A'}")
        except: continue
    return new_ids

def process_lol(seen_ids):
    html = fetch_content("https://www.rotowire.com/esports/lol/news.php")
    soup = BeautifulSoup(html, 'html.parser')
    new_ids = []
    
    for item in soup.find_all('div', class_='news-update'):
        try:
            name = item.find('a', class_='news-update__player-link').text.strip()
            headline = item.find('div', class_='news-update__headline').text.strip()
            news_id = f"LOL-{name}-{headline}"
            
            if news_id in seen_ids: continue
            new_ids.append(news_id)

            team_code = PLAYER_MAP.get(name) or (name if name in LOL_TEAM_DB else None)
            
            if team_code:
                status_key = "Info"
                advice = "🔍 情報更新"
                full_txt = headline + " " + item.find('div', class_='news-update__news').text.strip()
                for k, v in LOL_STRATEGY.items():
                    if k in full_txt: advice = v; status_key = k; break
                
                blue, red = calculate_lol_scenarios(team_code, status_key)
                
                quant_msg = ""
                if blue > 0:
                    quant_msg = (
                        f"\n🎯 **Game 1 獨贏推薦**\n"
                        f"🔵 **若為藍方:** Score {blue} ➔ 🔥 重注\n"
                        f"🔴 **若為紅方:** Score {red} ➔ ⚠️ 輕注"
                    )
                elif blue == 0:
                    quant_msg = "\n🛑 **風險警報:** 建議放棄 (Pass)"

                # LoL 的 PolyMarket 通常是按隊名開盤，嘗試搜尋
                poly_data = get_polymarket_data(team_code, "LOL") # 注意這裡可能不一定有盤
                poly_msg = ""
                if poly_data:
                     poly_msg = f"\n🔮 **PolyMarket:** {poly_data['price']}\n🔗 [下注連結]({poly_data['url']})"

                send_telegram(
                    f"🎮 **LoL Signal: {team_code} ({name})**\n"
                    f"📝 {headline}\n"
                    f"━━━━━━━━━━━━━━━━\n"
                    f"{advice}"
                    f"{quant_msg}"
                    f"{poly_msg}"
                )
                print(f"⚡ LoL: {team_code}")
        except: continue
    return new_ids

# ================= 🚀 主程式 =================
if __name__ == "__main__":
    print("\n" + "="*50)
    print(f"   🦅 {SYSTEM_NAME}")
    print("   Modules: News + Stats + Schedule + PolyMarket")
    print("="*50 + "\n")
    
    # 1. 初始賽程更新
    print("📅 正在同步今日賽程與對戰資訊...")
    TODAY_MATCHUPS = get_daily_schedule()
    
    send_telegram(f"🤖 *Slator Prime v9.0 啟動*\n監控場次: {len(TODAY_MATCHUPS)//2} 場\nPolyMarket: 連線中", silence=True)
    
    seen_news = set()
    last_heartbeat = time.time()
    last_schedule_update = time.time()
    
    while True:
        try:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] 📡 掃描全域市場...", end="\r")
            
            # 執行雙核掃描
            seen_news.update(process_nba(seen_news))
            seen_news.update(process_lol(seen_news))
            
            # 記憶體清理
            if len(seen_news) > 500: seen_news.clear()
            
            # 每 6 小時更新一次賽程 (應對延賽或開盤變動)
            if time.time() - last_schedule_update > 21600:
                print("\n📅 更新賽程表...")
                TODAY_MATCHUPS = get_daily_schedule()
                last_schedule_update = time.time()
            
            # 心跳檢查
            if time.time() - last_heartbeat > 3600:
                send_telegram("💓 Slator 運行中...", silence=True)
                last_heartbeat = time.time()
                
            time.sleep(random.randint(CHECK_INTERVAL_MIN, CHECK_INTERVAL_MAX))
            
        except KeyboardInterrupt:
            print("\n🛑 系統已手動停止")
            break
        except Exception as e:
            print(f"\n❌ 錯誤: {e}")
            time.sleep(60)