#!/usr/bin/env python3
"""
NBA Lineup Scanner v2.0 - Production Grade Async Architecture
==============================================================
Main entry point with async orchestration

Usage:
    python -m lineup_scanner_v2.main --test     # Single scan
    python -m lineup_scanner_v2.main            # Scheduled scan
"""
import asyncio
import argparse
import logging
import time
from datetime import datetime
from typing import Optional
import httpx

from .config import config
from .models import GameData, ScanReport, EVResult
from .scrapers.rotowire import LineupScraper
from .scrapers.polymarket import PolymarketScraper
from .calculators.ev_calculator import EVCalculator
from .notifiers.telegram import TelegramNotifier

# Configure logging
logging.basicConfig(
    level=getattr(logging, config.log_level),
    format='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("nba_scanner")


class NBAScanner:
    """Main scanner orchestrator"""
    
    def __init__(self, use_ml: bool = True):
        self.lineup_scraper = LineupScraper()
        self.odds_scraper = PolymarketScraper()
        self.use_ml = use_ml
        
        if use_ml:
            from .ml.hybrid import HybridCalculator
            self.ev_calculator = HybridCalculator()
            logger.info("🤖 Using ML Model (XGBoost)")
        else:
            self.ev_calculator = EVCalculator()
            logger.info("🤖 Using Gemini AI")
        
        self.notifier = TelegramNotifier()
    
    async def run_scan(self, date: Optional[str] = None) -> Optional[ScanReport]:
        """Execute a full scan with parallel data fetching"""
        scan_start = time.time()
        logger.info("="*50)
        logger.info("🏀 NBA Lineup Scanner v2.0")
        logger.info(f"   Scan Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("="*50)
        
        async with httpx.AsyncClient() as client:
            # Parallel fetch: lineups + odds
            logger.info("Fetching data (parallel)...")
            games, odds = await asyncio.gather(
                self.lineup_scraper.scrape(client, date=date),
                self.odds_scraper.scrape(client)
            )
            
            if not games and date:
                logger.warning(f"No games found from RotoWire for {date}. Trying fallback to Polymarket schedule...")
                games = await self.odds_scraper.scrape_games(client, date=date)
            
            if not games:
                logger.error("No games found, aborting scan")
                return None
            
            logger.info(f"Found {len(games)} games, {len(odds)} odds entries")
            
            # Analyze all games
            logger.info("Running EV analysis...")
            results = await self.ev_calculator.analyze_batch(games, odds)
            
            # Create report
            report = ScanReport(
                scan_time=datetime.now(),
                games=games,
                results=results
            )
            
            # Log results
            for result in report.sorted_by_ev:
                ev_pct = result.ev * 100
                status = "✅" if result.has_signal else "⏭️"
                logger.info(f"{status} {result.game.matchup}: EV={ev_pct:+.1f}% | {result.best_bet}")
            
            # Send to Telegram
            if self.notifier.is_configured:
                success = await self.notifier.send_report(client, report)
                if success:
                    logger.info("✅ Report sent to Telegram")
                else:
                    logger.warning("⚠️ Failed to send Telegram report")
            
            # Performance stats
            elapsed = time.time() - scan_start
            valuable = len([r for r in results if r.has_signal])
            logger.info(f"📊 Scan complete | Games: {len(games)} | Signals: {valuable} | Time: {elapsed:.1f}s")
            
            return report
    
    async def run_scheduled(self):
        """Run scheduled scans"""
        logger.info(f"🚀 Starting scheduled scan (every {config.scan_interval_minutes} min)")
        logger.info("Press Ctrl+C to stop\n")
        
        # Send startup notification
        async with httpx.AsyncClient() as client:
            await self.notifier.send_message(
                client,
                f"🤖 *Slator Prime v2.0 啟動*\n掃描頻率: 每 {config.scan_interval_minutes} 分鐘\nEV 閾值: {config.ev_threshold*100}%"
            )
        
        while True:
            try:
                await self.run_scan()
                logger.info(f"⏰ Next scan in {config.scan_interval_minutes} minutes")
                await asyncio.sleep(config.scan_interval_minutes * 60)
            except KeyboardInterrupt:
                logger.info("🛑 Scanner stopped by user")
                break
            except Exception as e:
                logger.error(f"Scan error: {e}")
                await asyncio.sleep(60)  # Wait 1 min before retry


async def main_async(test_mode: bool = False, use_ml: bool = False, date: Optional[str] = None):
    """Async main entry point"""
    scanner = NBAScanner(use_ml=use_ml)
    
    if test_mode:
        await scanner.run_scan(date=date)
        logger.info("🧪 Test mode complete")
    else:
        await scanner.run_scheduled()


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='NBA Lineup Scanner v2.0')
    parser.add_argument('--test', action='store_true', help='Single test scan')
    parser.add_argument('--gemini', action='store_true', help='Use Gemini AI instead of XGBoost ML')
    parser.add_argument('--date', type=str, help='Target date (YYYY-MM-DD)')
    args = parser.parse_args()
    
    # helper for use_ml: if gemini is set, use_ml is False. Default use_ml is True.
    asyncio.run(main_async(test_mode=args.test, use_ml=not args.gemini, date=args.date))


if __name__ == "__main__":
    main()
