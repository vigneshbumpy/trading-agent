# TradingAgents Fast Trading Graph
# Parallel async execution without LangGraph overhead
# Pre-fetches data, runs analysts in parallel, simplified decision flow

import asyncio
import os
import json
from pathlib import Path
from datetime import date
from typing import Dict, Any, List, Optional
import time

from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI

from tradingagents.default_config import DEFAULT_CONFIG
from tradingagents.dataflows.interface import route_to_vendor
from tradingagents.dataflows.config import set_config

from tradingagents.agents.fast_analysts import (
    run_market_analyst,
    run_fundamentals_analyst,
    run_news_analyst,
    run_social_analyst,
    run_research_summary,
    run_trader_decision,
    run_risk_assessment,
)


class FastTradingGraph:
    """Fast parallel execution engine for TradingAgents.
    
    Key differences from LangGraph version:
    1. Pre-fetches all data upfront (no iterative tool calls)
    2. Runs all 4 analysts in parallel using asyncio.gather()
    3. Single LLM call per analyst (no tool-use loops)
    4. Simplified research synthesis and decision flow
    
    Expected speedup: 3-4x faster than LangGraph version
    """

    def __init__(
        self,
        selected_analysts: List[str] = ["market", "social", "news", "fundamentals"],
        debug: bool = False,
        config: Dict[str, Any] = None,
    ):
        """Initialize the fast trading graph.

        Args:
            selected_analysts: List of analyst types to include
            debug: Whether to run in debug mode (prints timing info)
            config: Configuration dictionary. If None, uses default config
        """
        self.debug = debug
        self.config = config or DEFAULT_CONFIG.copy()
        self.selected_analysts = selected_analysts

        # Update the interface's config
        set_config(self.config)

        # Create necessary directories
        os.makedirs(
            os.path.join(self.config.get("project_dir", "."), "dataflows/data_cache"),
            exist_ok=True,
        )

        # Initialize LLM
        self.llm = self._create_llm()
        
        # State tracking
        self.last_result = None
        self.timing_info = {}

    def _create_llm(self):
        """Create LLM based on config."""
        provider = self.config.get("llm_provider", "openai").lower()
        model = self.config.get("quick_think_llm", "gpt-4o-mini")
        
        if provider in ["openai", "ollama", "openrouter"]:
            if provider == "openrouter":
                api_key = os.getenv("OPENROUTER_API_KEY")
            elif provider == "openai":
                api_key = os.getenv("OPENAI_API_KEY")
            else:  # ollama
                api_key = "ollama"

            return ChatOpenAI(
                model=model,
                base_url=self.config.get("backend_url", "https://api.openai.com/v1"),
                api_key=api_key
            )
        elif provider == "anthropic":
            api_key = os.getenv("ANTHROPIC_API_KEY")
            return ChatAnthropic(
                model=model,
                api_key=api_key
            )
        elif provider == "google":
            return ChatGoogleGenerativeAI(model=model)
        else:
            raise ValueError(f"Unsupported LLM provider: {provider}")

    def _log(self, message: str):
        """Log message if debug mode is enabled."""
        if self.debug:
            print(f"[FastTradingGraph] {message}")

    async def _fetch_all_data(self, ticker: str, trade_date: str) -> Dict[str, str]:
        """Pre-fetch all data required by analysts.
        
        Runs data fetching in parallel using asyncio.
        """
        self._log(f"Fetching all data for {ticker} on {trade_date}...")
        start_time = time.time()

        # Define data fetching functions
        async def fetch_stock_data():
            return route_to_vendor("get_stock_data", ticker, trade_date)

        async def fetch_indicators():
            return route_to_vendor("get_indicators", ticker, trade_date)

        async def fetch_balance_sheet():
            return route_to_vendor("get_balance_sheet", ticker)

        async def fetch_income_statement():
            return route_to_vendor("get_income_statement", ticker)

        async def fetch_cashflow():
            return route_to_vendor("get_cashflow", ticker)

        async def fetch_news():
            return route_to_vendor("get_news", ticker, trade_date)

        async def fetch_global_news():
            return route_to_vendor("get_global_news", trade_date)

        # Run all data fetches in parallel
        # Note: These use synchronous functions under the hood, 
        # so we wrap them with run_in_executor for true parallelism
        loop = asyncio.get_event_loop()
        
        results = await asyncio.gather(
            loop.run_in_executor(None, lambda: route_to_vendor("get_stock_data", ticker, trade_date)),
            loop.run_in_executor(None, lambda: route_to_vendor("get_indicators", ticker, trade_date)),
            loop.run_in_executor(None, lambda: route_to_vendor("get_balance_sheet", ticker)),
            loop.run_in_executor(None, lambda: route_to_vendor("get_income_statement", ticker)),
            loop.run_in_executor(None, lambda: route_to_vendor("get_cashflow", ticker)),
            loop.run_in_executor(None, lambda: route_to_vendor("get_news", ticker, trade_date)),
            loop.run_in_executor(None, lambda: route_to_vendor("get_global_news", trade_date)),
            return_exceptions=True
        )

        # Handle results, converting exceptions to error strings
        data = {
            "stock_data": str(results[0]) if not isinstance(results[0], Exception) else f"[Error fetching stock data: {results[0]}]",
            "indicators": str(results[1]) if not isinstance(results[1], Exception) else f"[Error fetching indicators: {results[1]}]",
            "balance_sheet": str(results[2]) if not isinstance(results[2], Exception) else f"[Error fetching balance sheet: {results[2]}]",
            "income_statement": str(results[3]) if not isinstance(results[3], Exception) else f"[Error fetching income statement: {results[3]}]",
            "cashflow": str(results[4]) if not isinstance(results[4], Exception) else f"[Error fetching cashflow: {results[4]}]",
            "news": str(results[5]) if not isinstance(results[5], Exception) else f"[Error fetching news: {results[5]}]",
            "global_news": str(results[6]) if not isinstance(results[6], Exception) else f"[Error fetching global news: {results[6]}]",
        }

        elapsed = time.time() - start_time
        self.timing_info["data_fetch"] = elapsed
        self._log(f"Data fetch completed in {elapsed:.2f}s")
        
        return data

    async def _run_analysts_parallel(
        self,
        ticker: str,
        trade_date: str,
        data: Dict[str, str]
    ) -> Dict[str, str]:
        """Run all selected analysts in parallel."""
        self._log("Running analysts in parallel...")
        start_time = time.time()

        # Build list of analyst coroutines based on selection
        tasks = []
        analyst_names = []

        if "market" in self.selected_analysts:
            tasks.append(run_market_analyst(
                self.llm, ticker, trade_date,
                data["stock_data"], data["indicators"]
            ))
            analyst_names.append("market")

        if "fundamentals" in self.selected_analysts:
            tasks.append(run_fundamentals_analyst(
                self.llm, ticker, trade_date,
                data["balance_sheet"], data["income_statement"], data["cashflow"]
            ))
            analyst_names.append("fundamentals")

        if "news" in self.selected_analysts:
            tasks.append(run_news_analyst(
                self.llm, ticker, trade_date,
                data["news"], data["global_news"]
            ))
            analyst_names.append("news")

        if "social" in self.selected_analysts:
            tasks.append(run_social_analyst(
                self.llm, ticker, trade_date,
                data["news"]  # Social uses same news data
            ))
            analyst_names.append("social")

        # Run all analysts in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        reports = {}
        for name, result in zip(analyst_names, results):
            if isinstance(result, Exception):
                self._log(f"Analyst {name} failed: {result}")
                reports[f"{name}_report"] = f"[Analyst error: {result}]"
            else:
                reports[f"{name}_report"] = result.get("report", "")
                self._log(f"Analyst {name} completed successfully")

        elapsed = time.time() - start_time
        self.timing_info["analysts"] = elapsed
        self._log(f"All analysts completed in {elapsed:.2f}s")

        return reports

    async def _run_decision_flow(
        self,
        ticker: str,
        trade_date: str,
        reports: Dict[str, str]
    ) -> Dict[str, str]:
        """Run research synthesis, trader decision, and risk assessment."""
        self._log("Running decision flow...")
        start_time = time.time()

        # Step 1: Research Summary
        research_summary = await run_research_summary(
            self.llm, ticker, trade_date,
            reports.get("market_report", "[No market report]"),
            reports.get("fundamentals_report", "[No fundamentals report]"),
            reports.get("news_report", "[No news report]"),
            reports.get("social_report", "[No social report]")
        )
        self._log("Research summary completed")

        # Step 2: Trader Decision
        trade_proposal = await run_trader_decision(
            self.llm, ticker, trade_date, research_summary
        )
        self._log("Trader decision completed")

        # Step 3: Risk Assessment (skip if configured)
        skip_risk = self.config.get("skip_risk_debate", False)
        if skip_risk:
            final_decision = trade_proposal
            risk_assessment = "[Risk assessment skipped]"
        else:
            risk_assessment = await run_risk_assessment(
                self.llm, ticker, trade_proposal, research_summary
            )
            final_decision = risk_assessment
            self._log("Risk assessment completed")

        elapsed = time.time() - start_time
        self.timing_info["decision_flow"] = elapsed
        self._log(f"Decision flow completed in {elapsed:.2f}s")

        return {
            "research_summary": research_summary,
            "trade_proposal": trade_proposal,
            "risk_assessment": risk_assessment,
            "final_decision": final_decision
        }

    async def propagate_async(self, company_name: str, trade_date: str) -> tuple:
        """Run the complete trading analysis pipeline asynchronously.
        
        Args:
            company_name: Stock ticker symbol
            trade_date: Date for analysis (YYYY-MM-DD format)
            
        Returns:
            Tuple of (full_state_dict, final_decision_string)
        """
        total_start = time.time()
        self._log(f"Starting analysis for {company_name} on {trade_date}")

        # Phase 1: Fetch all data in parallel
        data = await self._fetch_all_data(company_name, trade_date)

        # Phase 2: Run all analysts in parallel
        reports = await self._run_analysts_parallel(company_name, trade_date, data)

        # Phase 3: Run decision flow
        decisions = await self._run_decision_flow(company_name, trade_date, reports)

        # Build final state
        final_state = {
            "company_of_interest": company_name,
            "trade_date": trade_date,
            "market_report": reports.get("market_report", ""),
            "sentiment_report": reports.get("social_report", ""),
            "news_report": reports.get("news_report", ""),
            "fundamentals_report": reports.get("fundamentals_report", ""),
            "research_summary": decisions["research_summary"],
            "trader_investment_plan": decisions["trade_proposal"],
            "risk_assessment": decisions["risk_assessment"],
            "final_trade_decision": decisions["final_decision"],
        }

        self.last_result = final_state
        total_elapsed = time.time() - total_start
        self.timing_info["total"] = total_elapsed

        self._log(f"=== TIMING SUMMARY ===")
        self._log(f"  Data fetch:    {self.timing_info.get('data_fetch', 0):.2f}s")
        self._log(f"  Analysts:      {self.timing_info.get('analysts', 0):.2f}s")
        self._log(f"  Decision flow: {self.timing_info.get('decision_flow', 0):.2f}s")
        self._log(f"  TOTAL:         {total_elapsed:.2f}s")

        # Extract simple decision
        simple_decision = self._extract_decision(decisions["final_decision"])

        return final_state, simple_decision

    def propagate(self, company_name: str, trade_date: str) -> tuple:
        """Synchronous wrapper for propagate_async.
        
        This is the main entry point, matching the signature of TradingAgentsGraph.
        
        Args:
            company_name: Stock ticker symbol
            trade_date: Date for analysis (YYYY-MM-DD format)
            
        Returns:
            Tuple of (full_state_dict, final_decision_string)
        """
        return asyncio.run(self.propagate_async(company_name, trade_date))

    def _extract_decision(self, full_decision: str) -> str:
        """Extract BUY/HOLD/SELL from the full decision text."""
        full_decision_upper = full_decision.upper()
        
        # Look for explicit final decision markers
        if "APPROVE" in full_decision_upper and "BUY" in full_decision_upper:
            return "BUY"
        elif "APPROVE" in full_decision_upper and "SELL" in full_decision_upper:
            return "SELL"
        elif "REJECT" in full_decision_upper or "HOLD" in full_decision_upper:
            return "HOLD"
        
        # Fallback: look for action keywords
        if "BUY" in full_decision_upper:
            return "BUY"
        elif "SELL" in full_decision_upper:
            return "SELL"
        else:
            return "HOLD"

    def get_timing_info(self) -> Dict[str, float]:
        """Get timing information from last run."""
        return self.timing_info.copy()

    def log_state(self, trade_date: str, directory: str = None):
        """Log the current state to a JSON file."""
        if not self.last_result:
            raise ValueError("No result to log. Run propagate() first.")

        ticker = self.last_result.get("company_of_interest", "unknown")
        
        if directory is None:
            directory = Path(f"eval_results/{ticker}/FastTradingGraph_logs/")
        else:
            directory = Path(directory)
            
        directory.mkdir(parents=True, exist_ok=True)

        log_file = directory / f"fast_state_log_{trade_date}.json"
        with open(log_file, "w") as f:
            json.dump({
                str(trade_date): self.last_result,
                "timing": self.timing_info
            }, f, indent=4)
        
        self._log(f"State logged to {log_file}")
