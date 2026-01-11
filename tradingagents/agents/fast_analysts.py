# TradingAgents Fast Analysts
# Single-pass analyst functions that work with pre-fetched data
# No iterative tool-use loops - 1 LLM call per analyst

import asyncio
from typing import Dict, Any, Optional
from langchain_core.messages import HumanMessage


# ============================================================================
# ANALYST PROMPTS (Simplified single-pass versions)
# ============================================================================

MARKET_ANALYST_PROMPT = """You are a Market Analyst. Analyze the following stock data and technical indicators for {ticker} as of {date}.

## Stock Price Data
{stock_data}

## Technical Indicators
{indicators}

Based on this data, provide a detailed market analysis report including:
1. **Price Trend Assessment**: Current trend direction and strength
2. **Technical Signal Summary**: Key signals from the indicators
3. **Support/Resistance Levels**: Key price levels identified
4. **Momentum Analysis**: Current momentum state
5. **Volume Analysis**: Any notable volume patterns

End with a clear **Market Outlook**: Bullish / Bearish / Neutral with confidence level.

Format your analysis with clear headers and include a summary table at the end."""

FUNDAMENTALS_ANALYST_PROMPT = """You are a Fundamentals Analyst. Analyze the following financial data for {ticker} as of {date}.

## Balance Sheet
{balance_sheet}

## Income Statement
{income_statement}

## Cash Flow Statement
{cashflow}

Based on this data, provide a comprehensive fundamental analysis including:
1. **Financial Health**: Debt levels, liquidity ratios, working capital
2. **Profitability Analysis**: Margins, ROE, ROA trends
3. **Cash Flow Quality**: Operating cash flow, free cash flow trends
4. **Growth Assessment**: Revenue and earnings growth patterns
5. **Valuation Considerations**: Key metrics and comparisons

End with a clear **Fundamental Outlook**: Strong / Moderate / Weak with key supporting factors.

Format your analysis with clear headers and include a summary table at the end."""

NEWS_ANALYST_PROMPT = """You are a News Analyst. Analyze the following news for {ticker} as of {date}.

## Company-Specific News
{news}

## Global Market News
{global_news}

Based on this information, provide a news sentiment analysis including:
1. **Key Headlines Summary**: Most impactful news items
2. **Sentiment Assessment**: Overall positive/negative/neutral tone
3. **Market Impact Analysis**: How news might affect stock price
4. **Catalyst Identification**: Upcoming events or developments
5. **Risk Factors**: Any concerning news or developments

End with a clear **News Sentiment**: Positive / Negative / Neutral with confidence level.

Format your analysis with clear headers and include a summary table at the end."""

SOCIAL_ANALYST_PROMPT = """You are a Social Media Sentiment Analyst. Analyze the following social sentiment data for {ticker} as of {date}.

## Social Media & Discussion Activity
{news}

Based on this information, provide a sentiment analysis including:
1. **Discussion Volume**: Level of social activity around the stock
2. **Sentiment Breakdown**: Positive vs negative sentiment ratio
3. **Key Topics**: Main themes being discussed
4. **Influencer Activity**: Any notable analyst or influencer mentions
5. **Crowd Psychology**: Signs of FOMO, fear, or rational discussion

End with a clear **Social Sentiment**: Bullish / Bearish / Neutral with confidence level.

Format your analysis with clear headers and include a summary table at the end."""


# ============================================================================
# FAST ANALYST FUNCTIONS
# ============================================================================

async def run_market_analyst(
    llm,
    ticker: str,
    date: str,
    stock_data: str,
    indicators: str
) -> Dict[str, Any]:
    """Run market analyst with pre-fetched data. Single LLM call."""
    prompt = MARKET_ANALYST_PROMPT.format(
        ticker=ticker,
        date=date,
        stock_data=stock_data,
        indicators=indicators
    )
    
    result = await llm.ainvoke([HumanMessage(content=prompt)])
    
    return {
        "analyst": "market",
        "report": result.content,
        "success": True
    }


async def run_fundamentals_analyst(
    llm,
    ticker: str,
    date: str,
    balance_sheet: str,
    income_statement: str,
    cashflow: str
) -> Dict[str, Any]:
    """Run fundamentals analyst with pre-fetched data. Single LLM call."""
    prompt = FUNDAMENTALS_ANALYST_PROMPT.format(
        ticker=ticker,
        date=date,
        balance_sheet=balance_sheet,
        income_statement=income_statement,
        cashflow=cashflow
    )
    
    result = await llm.ainvoke([HumanMessage(content=prompt)])
    
    return {
        "analyst": "fundamentals",
        "report": result.content,
        "success": True
    }


async def run_news_analyst(
    llm,
    ticker: str,
    date: str,
    news: str,
    global_news: str
) -> Dict[str, Any]:
    """Run news analyst with pre-fetched data. Single LLM call."""
    prompt = NEWS_ANALYST_PROMPT.format(
        ticker=ticker,
        date=date,
        news=news,
        global_news=global_news
    )
    
    result = await llm.ainvoke([HumanMessage(content=prompt)])
    
    return {
        "analyst": "news",
        "report": result.content,
        "success": True
    }


async def run_social_analyst(
    llm,
    ticker: str,
    date: str,
    news: str
) -> Dict[str, Any]:
    """Run social media analyst with pre-fetched data. Single LLM call."""
    prompt = SOCIAL_ANALYST_PROMPT.format(
        ticker=ticker,
        date=date,
        news=news
    )
    
    result = await llm.ainvoke([HumanMessage(content=prompt)])
    
    return {
        "analyst": "social",
        "report": result.content,
        "success": True
    }


# ============================================================================
# RESEARCH & DECISION PROMPTS
# ============================================================================

RESEARCH_SUMMARY_PROMPT = """You are a Research Manager synthesizing analyst reports for {ticker} as of {date}.

## Market Analysis Report
{market_report}

## Fundamentals Analysis Report
{fundamentals_report}

## News Analysis Report
{news_report}

## Social Sentiment Report
{social_report}

Synthesize these reports into a coherent investment thesis:

1. **Consensus View**: Where do analysts agree?
2. **Key Disagreements**: Where do analysts differ?
3. **Bull Case**: Best case scenario and supporting evidence
4. **Bear Case**: Worst case scenario and risks
5. **Weighted Assessment**: Overall investment attractiveness

Provide a final **Research Verdict**: Strong Buy / Buy / Hold / Sell / Strong Sell"""


TRADER_DECISION_PROMPT = """You are a Trader making a final decision for {ticker} as of {date}.

## Research Summary
{research_summary}

## Current Portfolio Context
- Available capital for trading
- Risk tolerance: Moderate

Based on the research, make a trading decision:

1. **Action**: BUY / HOLD / SELL
2. **Confidence**: High / Medium / Low
3. **Position Size Recommendation**: Percentage of available capital (if BUY)
4. **Entry/Exit Rationale**: Why this action now?
5. **Risk Management**: Stop-loss level or exit conditions

**FINAL TRANSACTION PROPOSAL**: [BUY/HOLD/SELL] - [Brief 1-line rationale]"""


RISK_ASSESSMENT_PROMPT = """You are a Risk Manager assessing the proposed trade for {ticker}.

## Proposed Trade
{trade_proposal}

## Research Summary
{research_summary}

Evaluate the risk of this trade:

1. **Market Risk**: Volatility and market condition risks
2. **Fundamental Risk**: Company-specific financial risks
3. **Timing Risk**: Is the entry point appropriate?
4. **Position Size Risk**: Is the proposed size appropriate?
5. **Downside Scenario**: Maximum expected loss

**RISK VERDICT**: APPROVE / MODIFY / REJECT

If MODIFY or REJECT, explain required changes or concerns.

**FINAL DECISION**: [APPROVE/MODIFY/REJECT] - [Action: BUY/HOLD/SELL] - [Final Rationale]"""


# ============================================================================
# RESEARCH & DECISION FUNCTIONS
# ============================================================================

async def run_research_summary(
    llm,
    ticker: str,
    date: str,
    market_report: str,
    fundamentals_report: str,
    news_report: str,
    social_report: str
) -> str:
    """Synthesize all analyst reports into a research summary."""
    prompt = RESEARCH_SUMMARY_PROMPT.format(
        ticker=ticker,
        date=date,
        market_report=market_report,
        fundamentals_report=fundamentals_report,
        news_report=news_report,
        social_report=social_report
    )
    
    result = await llm.ainvoke([HumanMessage(content=prompt)])
    return result.content


async def run_trader_decision(
    llm,
    ticker: str,
    date: str,
    research_summary: str
) -> str:
    """Make trading decision based on research summary."""
    prompt = TRADER_DECISION_PROMPT.format(
        ticker=ticker,
        date=date,
        research_summary=research_summary
    )
    
    result = await llm.ainvoke([HumanMessage(content=prompt)])
    return result.content


async def run_risk_assessment(
    llm,
    ticker: str,
    trade_proposal: str,
    research_summary: str
) -> str:
    """Assess risk of proposed trade."""
    prompt = RISK_ASSESSMENT_PROMPT.format(
        ticker=ticker,
        trade_proposal=trade_proposal,
        research_summary=research_summary
    )
    
    result = await llm.ainvoke([HumanMessage(content=prompt)])
    return result.content
