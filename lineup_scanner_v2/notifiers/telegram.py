"""
Telegram Notifier - Async implementation
"""
import logging
from typing import List
from datetime import datetime
import httpx

from ..config import config
from ..models import EVResult, ScanReport

logger = logging.getLogger("nba_scanner.notifiers.telegram")


class TelegramNotifier:
    """Sends notifications to Telegram"""
    
    def __init__(self):
        self.bot_token = config.telegram_bot_token
        self.chat_id = config.telegram_chat_id
        self.api_url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
    
    @property
    def is_configured(self) -> bool:
        return config.telegram_configured
    
    async def send_message(self, client: httpx.AsyncClient, message: str) -> bool:
        """Send a message to Telegram"""
        if not self.is_configured:
            logger.warning("Telegram not configured")
            return False
        
        try:
            payload = {
                "chat_id": self.chat_id,
                "text": message,
                "parse_mode": "Markdown",
                "disable_notification": False
            }
            response = await client.post(self.api_url, json=payload, timeout=10.0)
            
            if response.status_code == 200:
                logger.info("Telegram message sent successfully")
                return True
            else:
                logger.error(f"Telegram API error: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"Failed to send Telegram message: {e}")
            return False
    
    async def send_report(self, client: httpx.AsyncClient, report: ScanReport) -> bool:
        """Send formatted scan report"""
        message = self._format_report(report)
        return await self.send_message(client, message)
    
    def _format_report(self, report: ScanReport) -> str:
        """Format scan report for Telegram"""
        lines = [
            "🏀 *NBA 每日投注分析報告*",
            "━━━━━━━━━━━━━━━━━━━━",
            f"📅 {report.scan_time.strftime('%Y-%m-%d %H:%M')}",
            f"📊 分析 {len(report.games)} 場比賽",
            "",
            "*📋 今日全部比賽:*"
        ]
        
        # All games summary
        for result in report.results:
            game = result.game
            ev_pct = result.ev * 100
            
            # Injury count
            inj_count = len(game.away_team.injuries) + len(game.home_team.injuries)
            inj_note = f" ⚠️{inj_count}傷" if inj_count > 0 else ""
            
            # EV indicator
            if ev_pct >= 5:
                ev_mark = f"✅ +{ev_pct:.0f}%"
            elif ev_pct >= 0:
                ev_mark = f"⚪ {ev_pct:+.0f}%"
            else:
                ev_mark = f"❌ {ev_pct:.0f}%"
            
            lines.append(f"• {game.matchup} {game.game_time}{inj_note} → {ev_mark}")
        
        lines.append("")
        lines.append("━━━━━━━━━━━━━━━━━━━━")
        lines.append("*🎯 TOP 3 最值得下注:*")
        lines.append("")
        
        # Top 3 picks
        for i, result in enumerate(report.top_recommendations, 1):
            game = result.game
            
            # Confidence emoji
            conf_emoji = {"HIGH": "🔥", "MEDIUM": "⚡", "LOW": "💡"}.get(result.confidence, "💡")
            
            # Injuries
            away_inj = ", ".join([f"{p.name}({p.status})" for p in game.away_team.injuries]) or "無"
            home_inj = ", ".join([f"{p.name}({p.status})" for p in game.home_team.injuries]) or "無"
            
            lines.extend([
                f"*#{i} {game.matchup}* {conf_emoji}",
                f"⏰ {game.game_time}",
                f"📊 EV: *{result.ev_percent}*",
                f"🎯 建議: *{result.best_bet}*",
                "",
                "傷病:",
                f"• {game.away_team.name}: {away_inj}",
                f"• {game.home_team.name}: {home_inj}",
                "",
                "💡 分析:",
                f"{result.analysis[:400]}...",
                ""
            ])
        
        lines.extend([
            "━━━━━━━━━━━━━━━━━━━━",
            "_Slator Prime v2.0 | 投注請理性_"
        ])
        
        return "\n".join(lines)
