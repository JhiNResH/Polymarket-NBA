"""
Polymarket 價值投注機器人
使用 Pinnacle 賠率作為真實勝率基準，尋找 Polymarket 上的正 EV 機會
"""

import os
import logging
import requests
import pandas as pd
from datetime import datetime, timedelta
from discord_webhook import DiscordWebhook, DiscordEmbed
from thefuzz import process, fuzz
from dotenv import load_dotenv

# ==================== 初始化 ====================
load_dotenv()

os.makedirs('logs', exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/polymarket_bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ==================== 配置參數 ====================
ODDS_API_KEY = os.getenv("ODDS_API_KEY")
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

if not ODDS_API_KEY or not DISCORD_WEBHOOK_URL:
    logger.error("❌ 缺少環境變數 ODDS_API_KEY 或 DISCORD_WEBHOOK_URL")
    exit(1)

# 資金管理
BANKROLL = 20.0
DAILY_TOTAL_STAKE = 20.0
MAX_BETS = 3
MIN_BET_SIZE = 0.50
USE_EV_WEIGHTED = True

# 篩選條件
MIN_WIN_PROB = 0.55
MIN_EV = 0.02
MIN_IMPLIED_ODDS = 1.55
MIN_FUZZY_SCORE = 90
MAX_ODDS_AGE_MINUTES = 15

# 運動賽事配置
SPORTS = [
    {'name': 'NBA', 'key': 'basketball_nba', 'series_id': '10345'},
]

# ==================== API 函數 ====================

def get_sharp_odds(sport_key):
    """從 The Odds API 獲取 Pinnacle 賠率"""
    try:
        url = f"https://api.the-odds-api.com/v4/sports/{sport_key}/odds"
        params = {
            'apiKey': ODDS_API_KEY,
            'regions': 'eu',
            'markets': 'h2h',
            'oddsFormat': 'decimal',
            'bookmakers': 'pinnacle'
        }
        res = requests.get(url, params=params, timeout=10)
        if res.status_code != 200:
            logger.warning(f"⚠️ 無法獲取 {sport_key} 賠率: {res.status_code}")
            return None

        data = res.json()
        fetch_time = datetime.now()
        for match in data:
            match['fetch_time'] = fetch_time

        logger.info(f"✅ 成功獲取 {sport_key} 的 {len(data)} 場比賽")
        return data
    except requests.exceptions.Timeout:
        logger.error(f"❌ API 請求超時: {sport_key}")
        return None
    except Exception as e:
        logger.error(f"❌ API 連線錯誤: {e}")
        return None


def get_polymarket_events(series_id):
    """從 Polymarket Gamma API 獲取賽事"""
    try:
        url = "https://gamma-api.polymarket.com/events"
        params = {
            'limit': 50,
            'active': 'true',
            'closed': 'false',
            'series_id': series_id,
            'order': 'startTime',
            'ascending': 'true'
        }
        res = requests.get(url, params=params, timeout=10)
        if res.status_code != 200:
            logger.warning(f"⚠️ Polymarket API 返回 {res.status_code}")
            return None
        return res.json()
    except requests.exceptions.Timeout:
        logger.error("❌ Polymarket API 超時")
        return None
    except Exception as e:
        logger.error(f"❌ Polymarket API 錯誤: {e}")
        return None


# ==================== 計算函數 ====================

def calculate_true_prob(odds_a, odds_b):
    """乘法去水法計算真實勝率"""
    p_a, p_b = 1 / odds_a, 1 / odds_b
    overround = p_a + p_b
    return p_a / overround, p_b / overround


def get_ev_rating(ev):
    """根據 EV 返回星級評分"""
    if ev >= 0.50:
        return "⭐⭐⭐"
    elif ev >= 0.30:
        return "⭐⭐"
    return "⭐"


# ==================== 主程式 ====================

def run_analysis():
    logger.info(f"🚀 啟動 ${BANKROLL} 挑戰狙擊程式...")
    candidates = []

    for sport in SPORTS:
        logger.info(f"正在掃描 {sport['name']}...")
        sharp_data = get_sharp_odds(sport['key'])
        poly_data = get_polymarket_events(sport['series_id'])

        if not sharp_data or not poly_data:
            logger.warning(f"  ⚠️ {sport['name']} 數據不完整，跳過")
            continue

        # 解析 Pinnacle 數據
        sharp_matches = []
        for match in sharp_data:
            fetch_time = match.get('fetch_time', datetime.now())
            if datetime.now() - fetch_time > timedelta(minutes=MAX_ODDS_AGE_MINUTES):
                continue

            if 'bookmakers' not in match or not match['bookmakers']:
                continue
            bookmaker = match['bookmakers'][0]
            if 'markets' not in bookmaker or not bookmaker['markets']:
                continue
            market = bookmaker['markets'][0]
            outcomes = market.get('outcomes', [])
            if len(outcomes) != 2:
                continue

            team1, price1 = outcomes[0]['name'], outcomes[0]['price']
            team2, price2 = outcomes[1]['name'], outcomes[1]['price']
            tp1, tp2 = calculate_true_prob(price1, price2)

            sharp_matches.append({
                'teams': [team1, team2],
                'probs': {team1: tp1, team2: tp2},
            })

        if not sharp_matches:
            logger.warning(f"  ⚠️ 無有效 Pinnacle 賠率數據")
            continue

        logger.info(f"  🔍 找到 {len(sharp_matches)} 場有效比賽")

        # 匹配 Polymarket 賽事
        for event in poly_data:
            try:
                mkts = event.get('markets', [])
                if not mkts:
                    continue

                best_pair = None
                for mkt in mkts:
                    outcomes = eval(mkt.get('outcomes', '[]'))
                    prices = eval(mkt.get('outcomePrices', '[]'))
                    if len(outcomes) != 2 or len(prices) != 2:
                        continue

                    poly_team1, poly_team2 = outcomes[0], outcomes[1]
                    if poly_team1 in ['Over', 'Under', 'Yes', 'No']:
                        continue

                    for sharp in sharp_matches:
                        s_t1, s_t2 = sharp['teams']
                        score1 = (fuzz.token_set_ratio(poly_team1, s_t1) + 
                                  fuzz.token_set_ratio(poly_team2, s_t2)) / 2
                        score2 = (fuzz.token_set_ratio(poly_team1, s_t2) + 
                                  fuzz.token_set_ratio(poly_team2, s_t1)) / 2
                        score = max(score1, score2)

                        if score >= MIN_FUZZY_SCORE:
                            if not best_pair or score > best_pair[3]:
                                best_pair = (sharp, outcomes, prices, score)

                if not best_pair:
                    continue

                sharp_match, outcomes, prices, match_score = best_pair
                logger.info(f"  ✅ 匹配成功 ({match_score:.0f}%): {event['title']}")

                for i, team_name in enumerate(outcomes):
                    match_name, score = process.extractOne(team_name, sharp_match['probs'].keys())
                    if score < MIN_FUZZY_SCORE:
                        continue

                    true_prob = sharp_match['probs'][match_name]
                    poly_price = float(prices[i])
                    if poly_price <= 0 or poly_price >= 1:
                        continue

                    ev = (true_prob - poly_price) / poly_price
                    implied_odds = 1 / poly_price

                    if true_prob >= MIN_WIN_PROB and ev >= MIN_EV and implied_odds >= MIN_IMPLIED_ODDS:
                        candidates.append({
                            'sport': sport['name'],
                            'match': event['title'],
                            'pick': team_name,
                            'price': poly_price,
                            'implied_odds': implied_odds,
                            'prob': true_prob,
                            'ev': ev,
                            'link': f"https://polymarket.com/event/{event['slug']}",
                            'match_score': match_score
                        })

            except Exception as e:
                logger.error(f"❌ 處理比賽時出錯: {e}")
                continue

    # 排序與分配
    candidates.sort(key=lambda x: x['ev'], reverse=True)
    top_picks = candidates[:MAX_BETS]

    if not top_picks:
        logger.info("😴 今日無符合標準的比賽，建議休息。")
        DiscordWebhook(url=DISCORD_WEBHOOK_URL, content="😴 今日無高勝率機會，機器人建議：休息。").execute()
        return

    # 計算注額
    if USE_EV_WEIGHTED:
        total_ev = sum(p['ev'] for p in top_picks)
        for p in top_picks:
            p['stake'] = max(MIN_BET_SIZE, DAILY_TOTAL_STAKE * (p['ev'] / total_ev))
    else:
        for p in top_picks:
            p['stake'] = max(MIN_BET_SIZE, DAILY_TOTAL_STAKE / len(top_picks))

    total_stake = sum(p['stake'] for p in top_picks)

    # 輸出結果
    logger.info("\n" + "=" * 50)
    logger.info(f"💰 評分下注系統 - 總投入: ${total_stake:.2f}")
    logger.info("=" * 50)

    csv_data = []
    for i, p in enumerate(top_picks):
        stake = p['stake']
        expected_profit = stake * (p['implied_odds'] - 1) * p['prob'] - stake * (1 - p['prob'])
        rating = get_ev_rating(p['ev'])

        logger.info(f"推薦 {i+1} {rating}: {p['pick']} (勝率 {p['prob']*100:.1f}%)")
        logger.info(f"  價格: {p['price']:.3f} | 隱含賠率: {p['implied_odds']:.2f}")
        logger.info(f"  EV: +{p['ev']*100:.2f}% | 注額: ${stake:.2f}")
        logger.info(f"  期望獲利: ${expected_profit:.2f}")
        logger.info("-" * 50)

        csv_data.append({
            'Date': datetime.now().strftime("%Y-%m-%d %H:%M"),
            'Sport': p['sport'],
            'Match': p['match'],
            'Pick': p['pick'],
            'Poly_Price': round(p['price'], 4),
            'Implied_Odds': round(p['implied_odds'], 2),
            'True_Prob': round(p['prob'], 4),
            'EV': round(p['ev'], 4),
            'Stake': round(stake, 2),
            'Expected_Profit': round(expected_profit, 2),
            'Link': p['link'],
            'Result': '',
            'Actual_Profit': ''
        })

    # Discord 通知
    webhook = DiscordWebhook(url=DISCORD_WEBHOOK_URL)
    embed = DiscordEmbed(title=f"🎯 ${BANKROLL:.0f} 挑戰：今日 Top {len(top_picks)} 狙擊", color='00ff00')
    embed.set_footer(text=f"本金: ${BANKROLL:.2f} | 總投入: ${total_stake:.2f} ({total_stake/BANKROLL*100:.1f}%)")

    for i, p in enumerate(top_picks):
        embed.add_embed_field(
            name=f"#{i+1} {p['sport']} - {p['pick']}",
            value=(f"勝率: **{p['prob']*100:.1f}%** | 價格: **{p['price']:.3f}**\n"
                   f"EV: **+{p['ev']*100:.2f}%** | 注額: **${p['stake']:.2f}**\n"
                   f"[👉 點擊下注]({p['link']})"),
            inline=False
        )

    webhook.add_embed(embed)
    webhook.execute()
    logger.info("✅ Discord 通知已發送！")

    # 儲存 CSV
    os.makedirs('data', exist_ok=True)
    file_name = 'data/polymarket_bets.csv'
    df = pd.DataFrame(csv_data)
    df.to_csv(file_name, mode='a', header=not os.path.exists(file_name), index=False)
    logger.info(f"📝 紀錄已儲存至 {file_name}")


if __name__ == "__main__":
    try:
        run_analysis()

        if os.getenv('GOOGLE_SHEET_ID'):
            try:
                import sys
                sys.path.insert(0, 'utils')
                from google_sheets_sync import sync_bets_to_sheets, sync_daily_summary
                logger.info("📊 正在同步到 Google Sheets...")
                sync_bets_to_sheets()
                sync_daily_summary()
            except ImportError:
                logger.warning("⚠️ 請先安裝 Google API 套件")
            except Exception as e:
                logger.error(f"❌ Google Sheets 同步失敗: {e}")

    except KeyboardInterrupt:
        logger.info("\n👋 程式已手動停止")
    except Exception as e:
        logger.error(f"❌ 程式執行錯誤: {e}", exc_info=True)