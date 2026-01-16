"""
EV Calculator using Gemini AI - Async implementation
"""
import re
import json
import logging
from typing import List, Optional, Dict
from google import genai

from ..config import config
from ..models import GameData, EVResult, OddsData

logger = logging.getLogger("nba_scanner.calculators.ev")

# System prompt for Gemini
SYSTEM_PROMPT = """你是「Slator Prime」——頂級量化體育投注分析師 AI。

## 你的身份
- 前華爾街量化交易員，專精運動博彩套利
- 10 年 NBA 傷病分析與盤口預測經驗
- 精通 Expected Value (EV) 計算與凱利公式

## 分析方法論
1. 核心球員缺陣 = 勝率下降 5-15%
2. 主場優勢 +3.5 分，約 +2% 勝率
3. 陣容完整度: 5 首發齊 = 100%，缺 1 人 = -10%

## EV 公式
EV = (勝率 × 獲利) - (敗率 × 投注額)
+EV > 5% = 推薦下注

## 輸出風格
- 簡潔、數據驅動
- 必須給出 BET 或 PASS 建議
- 必須估算具體 EV 百分比
- 用繁體中文回答"""


class EVCalculator:
    """Calculates Expected Value using Gemini AI"""
    
    def __init__(self):
        self.client: Optional[genai.Client] = None
        self._init_client()
    
    def _init_client(self) -> None:
        """Initialize Gemini client"""
        if not config.gemini_configured:
            logger.warning("Gemini API key not configured")
            return
        
        try:
            self.client = genai.Client(api_key=config.google_api_key)
            logger.info(f"Gemini client initialized (model: {config.gemini_model})")
        except Exception as e:
            logger.error(f"Failed to initialize Gemini: {e}")
    
    async def analyze_game(
        self, 
        game: GameData, 
        odds: Optional[Dict[str, OddsData]] = None
    ) -> EVResult:
        """Analyze a single game and calculate EV"""
        if not self.client:
            return self._create_fallback_result(game)
        
        prompt = self._build_prompt(game, odds)
        
        try:
            response = self.client.models.generate_content(
                model=config.gemini_model,
                contents=prompt,
                config={
                    "system_instruction": SYSTEM_PROMPT,
                    "temperature": 0.2,
                }
            )
            return self._parse_response(game, response.text, odds)
        except Exception as e:
            logger.error(f"Gemini analysis failed for {game.matchup}: {e}")
            return self._create_fallback_result(game)
    
    async def analyze_batch(
        self, 
        games: List[GameData], 
        odds: Dict[str, OddsData]
    ) -> List[EVResult]:
        """Analyze multiple games"""
        results = []
        for game in games:
            # 檢查是否有異常賠率（比賽已結束或即將結束）
            away_odds = odds.get(game.away_team.abbreviation)
            home_odds = odds.get(game.home_team.abbreviation)
            
            skip_game = False
            for team_odds in [away_odds, home_odds]:
                if team_odds and team_odds.moneyline_prob is not None:
                    if team_odds.moneyline_prob >= 0.95 or team_odds.moneyline_prob <= 0.05:
                        logger.warning(f"跳過 {game.matchup}: 賠率異常 ({team_odds.moneyline_prob*100:.0f}%) - 比賽可能已結束")
                        skip_game = True
                        break
            
            if skip_game:
                results.append(self._create_fallback_result(game))
                continue
            
            result = await self.analyze_game(game, odds)
            results.append(result)
            logger.debug(f"{game.matchup}: EV={result.ev_percent}, Bet={result.best_bet}")
        return results
    
    def _build_prompt(self, game: GameData, odds: Optional[Dict[str, OddsData]]) -> str:
        """Build analysis prompt"""
        away = game.away_team
        home = game.home_team
        
        # Format injuries
        away_injuries = ", ".join([f"{p.name}({p.status})" for p in away.injuries]) or "無"
        home_injuries = ", ".join([f"{p.name}({p.status})" for p in home.injuries]) or "無"
        
        # Get odds if available
        away_odds = odds.get(away.abbreviation) if odds else None
        home_odds = odds.get(home.abbreviation) if odds else None
        
        odds_text = ""
        if away_odds or home_odds:
            odds_text = "\n## Polymarket 賠率\n"
            if away_odds:
                odds_text += f"- {away.name}: {away_odds.moneyline_prob*100:.1f}% ({away_odds.moneyline_american})\n"
            if home_odds:
                odds_text += f"- {home.name}: {home_odds.moneyline_prob*100:.1f}% ({home_odds.moneyline_american})\n"
        
        return f"""分析這場 NBA 比賽:

## 比賽: {game.matchup}
⏰ {game.game_time}

## 客隊 {away.name}
- 首發: {', '.join([p.name for p in away.players[:5]])}
- 傷病: {away_injuries}

## 主隊 {home.name}  
- 首發: {', '.join([p.name for p in home.players[:5]])}
- 傷病: {home_injuries}
{odds_text}
## JSON 格式輸出:
```json
{{
  "away_win_prob": 0.XX,
  "home_win_prob": 0.XX,
  "best_bet": "AWAY_ML" | "HOME_ML" | "AWAY_SPREAD" | "HOME_SPREAD" | "PASS",
  "ev_percent": X.X,
  "confidence": "HIGH" | "MEDIUM" | "LOW",
  "reason": "簡短理由"
}}
```"""
    
    def _parse_response(
        self, 
        game: GameData, 
        response_text: str, 
        odds: Optional[Dict[str, OddsData]]
    ) -> EVResult:
        """Parse Gemini response into EVResult"""
        ev_value = 0.0
        best_bet = "PASS"
        confidence = "LOW"
        reason = ""
        
        # Extract JSON
        json_match = re.search(r'\{[^{}]*"away_win_prob"[^{}]*\}', response_text, re.DOTALL)
        if json_match:
            try:
                data = json.loads(json_match.group())
                ev_value = float(data.get('ev_percent', 0)) / 100
                best_bet = data.get('best_bet', 'PASS')
                confidence = data.get('confidence', 'LOW')
                reason = data.get('reason', '')
            except json.JSONDecodeError:
                pass
        
        # Fallback parsing
        if ev_value == 0:
            if "+EV" in response_text.upper() or "正期望" in response_text:
                ev_value = 0.06
            elif "-EV" in response_text.upper():
                ev_value = -0.03
        
        # Convert best_bet to team name
        bet_display = self._convert_bet_display(game, best_bet)
        
        return EVResult(
            game=game,
            ev=ev_value,
            best_bet=bet_display,
            best_bet_raw=best_bet,
            confidence=confidence,
            analysis=response_text[:1500],
            has_signal=ev_value >= config.ev_threshold and best_bet != "PASS"
        )
    
    def _convert_bet_display(self, game: GameData, bet_raw: str) -> str:
        """Convert bet code to display name"""
        if bet_raw == "AWAY_ML":
            return f"{game.away_team.name} ML"
        elif bet_raw == "HOME_ML":
            return f"{game.home_team.name} ML"
        elif bet_raw == "AWAY_SPREAD":
            return f"{game.away_team.name} SPREAD"
        elif bet_raw == "HOME_SPREAD":
            return f"{game.home_team.name} SPREAD"
        return bet_raw
    
    def _create_fallback_result(self, game: GameData) -> EVResult:
        """Create fallback result when analysis fails"""
        return EVResult(
            game=game,
            ev=0,
            best_bet="PASS",
            best_bet_raw="PASS",
            confidence="LOW",
            analysis="分析不可用",
            has_signal=False
        )
