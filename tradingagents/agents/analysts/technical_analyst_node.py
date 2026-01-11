"""
Technical Analyst Node - TradingView-style Chart Analysis Integration
Wraps the TechnicalAnalyst class for use in the TradingAgents graph
"""

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from tradingagents.agents.technical_analyst import TechnicalAnalyst
from tradingagents.dataflows.config import get_config


def create_technical_analyst(llm):
    """
    Create technical analyst node for the trading graph

    This node performs TradingView-style technical analysis including:
    - Moving averages (MA, EMA)
    - Momentum indicators (RSI, MACD, Stochastic)
    - Volatility indicators (Bollinger Bands, ATR)
    - Support/Resistance levels
    - Chart patterns
    - TradingView-style ratings

    Args:
        llm: Language model for generating analysis

    Returns:
        Function that can be used as a node in the trading graph
    """

    def technical_analyst_node(state):
        """Node function for technical analysis"""
        current_date = state["trade_date"]
        ticker = state["company_of_interest"]
        config = get_config()

        # Create technical analyst instance
        analyst = TechnicalAnalyst(llm=llm, config=config)

        # Perform analysis
        report = analyst.analyze(ticker=ticker, analysis_date=current_date)

        # Create message for the system
        system_message = f"""
Technical Analysis Complete for {ticker}

This analysis uses TradingView methodology including:
- Moving Averages (10, 20, 50, 100, 200 SMA/EMA)
- RSI (Relative Strength Index)
- MACD (Moving Average Convergence Divergence)
- Stochastic Oscillator
- Bollinger Bands
- Support/Resistance levels
- Chart patterns
- Volume analysis

The analysis provides a comprehensive technical view to complement fundamental analysis.
"""

        # Create prompt template
        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You are a technical analyst specializing in TradingView-style chart analysis."
                    " You have completed comprehensive technical analysis for {ticker}."
                    " The current date is {current_date}."
                    "\n{system_message}"
                ),
                MessagesPlaceholder(variable_name="messages"),
            ]
        )

        prompt = prompt.partial(system_message=system_message)
        prompt = prompt.partial(current_date=current_date)
        prompt = prompt.partial(ticker=ticker)

        # Create completion message
        chain = prompt | llm

        # Invoke with the report
        # Invoke with the report
        completion_message = {
            "role": "assistant",
            "content": f"Technical analysis complete. Report:\n\n{report}"
        }
        
        # LLM Cache Integration
        from tradingagents.services.llm_cache import llm_cache
        from langchain_core.messages import messages_to_dict, messages_from_dict
        import json

        messages_input = state["messages"] + [completion_message]
        
        cache_context = {
            "messages": [str(m) for m in messages_input],
            "ticker": ticker,
            "date": str(current_date),
            "analyst": "technical_node"
        }
        cache_key = json.dumps(cache_context, sort_keys=True)
        
        cached_response = llm_cache.get(cache_key, "technical_analyst_node")
        
        if cached_response:
            try:
                result = messages_from_dict([json.loads(cached_response)])[0]
            except Exception:
                result = chain.invoke(messages_input)
        else:
            result = chain.invoke(messages_input)
            try:
                serialized = messages_to_dict([result])[0]
                llm_cache.set(cache_key, "technical_analyst_node", json.dumps(serialized))
            except Exception:
                pass

        return {
            "messages": [result],
            "technical_report": report,
        }

    return technical_analyst_node
