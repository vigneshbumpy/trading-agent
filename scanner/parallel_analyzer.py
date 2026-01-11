"""
Parallel AI Analyzer (Stage 3)

Runs deep AI analysis on top candidates using parallel Ollama instances.
"""

import time
from typing import List, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime

from openai import OpenAI

from .config import ScannerConfig
from .screener import ScreenedStock
from .news_aggregator import StockNews


@dataclass
class AnalysisResult:
    """Result from AI analysis"""
    symbol: str
    signal: str  # BUY, HOLD, SELL, AVOID
    confidence: float  # 0-100
    score: float  # Combined score
    summary: str
    value_analysis: str
    news_analysis: str
    risk_assessment: str
    action_recommendation: str
    timestamp: datetime = field(default_factory=datetime.now)


class ParallelAnalyzer:
    """Parallel AI analyzer using Ollama"""

    def __init__(self, config: ScannerConfig):
        self.config = config
        self.analysis_config = config.analysis
        self.client = OpenAI(
            base_url=self.analysis_config.ollama_base_url,
            api_key="ollama"
        )

    def build_prompt(self, stock: ScreenedStock, news: StockNews) -> str:
        """Build analysis prompt"""
        news_text = "\n".join([f"- {n.title}" for n in news.news_items[:5]]) or "No recent news."

        return f"""Analyze this stock. Be concise.

STOCK: {stock.symbol} | Sector: {stock.sector or 'N/A'}

METRICS:
- P/E: {stock.pe_ratio or 'N/A'} | P/B: {stock.pb_ratio or 'N/A'}
- D/E: {stock.debt_equity or 'N/A'} | ROE: {f'{stock.roe*100:.1f}%' if stock.roe else 'N/A'}
- Market Cap: {f'${stock.market_cap/1e9:.1f}B' if stock.market_cap else 'N/A'}

NEWS (Score: {news.news_score}, +{news.positive_count}/-{news.negative_count}):
{news_text}

Reply in EXACT format:
SIGNAL: [BUY/HOLD/SELL/AVOID]
CONFIDENCE: [0-100]%
VALUE: [1 sentence]
NEWS: [1 sentence]
RISK: [1 sentence]
ACTION: [1 sentence]"""

    def parse_response(self, text: str, stock: ScreenedStock, news: StockNews) -> AnalysisResult:
        """Parse LLM response"""
        signal, confidence = "HOLD", 50.0
        value_analysis = news_analysis = risk_assessment = action = ""

        for line in text.strip().split('\n'):
            line = line.strip()
            if line.startswith('SIGNAL:'):
                sig = line.split(':', 1)[1].strip().upper()
                if sig in ['BUY', 'HOLD', 'SELL', 'AVOID']:
                    signal = sig
            elif line.startswith('CONFIDENCE:'):
                try:
                    confidence = float(line.split(':', 1)[1].replace('%', '').strip())
                except:
                    pass
            elif line.startswith('VALUE:'):
                value_analysis = line.split(':', 1)[1].strip()
            elif line.startswith('NEWS:'):
                news_analysis = line.split(':', 1)[1].strip()
            elif line.startswith('RISK:'):
                risk_assessment = line.split(':', 1)[1].strip()
            elif line.startswith('ACTION:'):
                action = line.split(':', 1)[1].strip()

        signal_scores = {'BUY': 30, 'HOLD': 15, 'SELL': -15, 'AVOID': -30}
        combined_score = stock.score + news.news_score + signal_scores.get(signal, 0) + (confidence / 5)

        return AnalysisResult(
            symbol=stock.symbol, signal=signal, confidence=confidence,
            score=combined_score, summary=f"{signal} ({confidence:.0f}%)",
            value_analysis=value_analysis, news_analysis=news_analysis,
            risk_assessment=risk_assessment, action_recommendation=action
        )

    def analyze_stock(self, stock: ScreenedStock, news: StockNews) -> AnalysisResult:
        """Analyze single stock"""
        try:
            response = self.client.chat.completions.create(
                model=self.analysis_config.ollama_model,
                messages=[
                    {"role": "system", "content": "You are a concise stock analyst."},
                    {"role": "user", "content": self.build_prompt(stock, news)}
                ],
                temperature=0.3, max_tokens=300,
            )
            return self.parse_response(response.choices[0].message.content, stock, news)
        except Exception as e:
            return AnalysisResult(
                symbol=stock.symbol, signal="HOLD", confidence=0, score=stock.score,
                summary=f"Error: {str(e)[:30]}", value_analysis="", news_analysis="",
                risk_assessment="Analysis failed", action_recommendation="Skip"
            )

    def analyze_batch(self, candidates: List[Tuple[ScreenedStock, StockNews]]) -> List[AnalysisResult]:
        """Analyze stocks in parallel"""
        max_workers = self.analysis_config.parallel_instances

        print(f"\n{'='*60}")
        print(f"STAGE 3: AI ANALYSIS ({len(candidates)} stocks, {max_workers} parallel)")
        print(f"{'='*60}")

        start = time.time()
        results = []

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(self.analyze_stock, s, n): s.symbol for s, n in candidates}
            for i, future in enumerate(as_completed(futures), 1):
                print(f"[{i}/{len(candidates)}] {futures[future]}")
                try:
                    results.append(future.result())
                except Exception as e:
                    print(f"  Error: {e}")

        results.sort(key=lambda x: x.score, reverse=True)
        buys = sum(1 for r in results if r.signal == 'BUY')
        print(f"\nDone in {time.time()-start:.1f}s | BUY signals: {buys}")
        return results

    def format_results(self, results: List[AnalysisResult]) -> str:
        """Format results for display"""
        output = f"\n{'='*60}\nSCAN RESULTS - {datetime.now().strftime('%Y-%m-%d %H:%M')}\n{'='*60}\n\n"

        for signal_type in ['BUY', 'HOLD', 'SELL', 'AVOID']:
            items = [r for r in results if r.signal == signal_type]
            if items:
                output += f"{signal_type} ({len(items)}):\n"
                for r in items[:10]:
                    output += f"  {r.symbol}: {r.confidence:.0f}% - {r.action_recommendation}\n"
                output += "\n"

        return output
