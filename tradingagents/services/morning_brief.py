"""
Morning Brief Service
Generates pre-market analysis reports ("Morning Briefs") for the watchlist.
"""
import os
from datetime import datetime
from typing import List, Dict
import logging
from pathlib import Path

from tradingagents.services.market_filter import market_filter

class MorningBriefService:
    def __init__(self, output_dir: str = "dashboard/data/morning_briefs"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger(__name__)

    def generate_brief(self, watchlist: List[str]) -> str:
        """
        Generate a morning brief for the watchlist.
        Returns the path to the generated report or content.
        """
        self.logger.info("Generating Morning Brief...")
        
        date_str = datetime.now().strftime("%Y-%m-%d")
        report_lines = [f"# 🌅 Morning Brief - {date_str}", ""]
        
        report_lines.append("## Watchlist Momentum Check")
        report_lines.append("| Ticker | Status | Reason |")
        report_lines.append("|---|---|---|")
        
        passed_symbols = []
        
        for symbol in watchlist:
            passed, reason = market_filter.check_momentum(symbol)
            status_icon = "✅" if passed else "⏭️"
            report_lines.append(f"| {symbol} | {status_icon} | {reason} |")
            
            if passed:
                passed_symbols.append(symbol)
        
        report_lines.append("")
        report_lines.append("## Potential Plays")
        if passed_symbols:
            report_lines.append(f"Focus today on: **{', '.join(passed_symbols)}**")
        else:
            report_lines.append("No high-momentum setups detected in watchlist.")
            
        # Save report
        filename = f"morning_brief_{date_str}.md"
        filepath = self.output_dir / filename
        
        content = "\n".join(report_lines)
        
        with open(filepath, "w") as f:
            f.write(content)
            
        self.logger.info(f"Morning Brief saved to {filepath}")
        return content

morning_brief_service = MorningBriefService()
