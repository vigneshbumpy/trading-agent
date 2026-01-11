from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from tradingagents.agents.utils.agent_utils import get_stock_data, get_news
import json

def create_sector_analyst(llm):
    def sector_analyst_node(state):
        current_date = state["trade_date"]
        # Sector ETFs: Tech, Finance, Energy, Healthcare, Consumer Discretionary, Staples, Utilities, Real Estate, Materials, Industrials, Comms
        sectors = ["XLK", "XLF", "XLE", "XLV", "XLY", "XLP", "XLU", "XLRE", "XLB", "XLI", "XLC"]
        
        tools = [get_stock_data, get_news]
        
        system_message = (
            f"""You are a Sector Rotation Analyst. Your job is to analyze the performance of major S&P 500 sector ETFs to identify which sectors are leading (bullish) and lagging (bearish). 
            
            Sectors to Analyze: {', '.join(sectors)}
            
            Tasks:
            1. Use `get_stock_data` to check the recent performance (1 week, 1 month) of key sectors.
            2. Use `get_news` to find broad market themes driving these sectors.
            3. Identify the current market cycle (e.g., Expansion, Contraction, Rotation into defensive).
            4. Recommend which sectors to OVERWEIGHT (Buy) and UNDERWEIGHT (Avoid).
            
            Write a concise report titled "Sector Rotation Analysis".
            Include a table showing Relative Strength of each sector."""
        )

        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You are a helpful AI assistant. Use tools to analyze sector performance.\n{system_message}\n"
                    "Current Date: {current_date}"
                ),
                MessagesPlaceholder(variable_name="messages"),
            ]
        )

        prompt = prompt.partial(system_message=system_message)
        prompt = prompt.partial(current_date=current_date)

        # Integration with LLM Cache
        chain = prompt | llm.bind_tools(tools)
        
        from tradingagents.services.llm_cache import llm_cache
        from langchain_core.messages import messages_to_dict, messages_from_dict
        
        # We generally run this once per day per "market" context, but here it's tied to the specific stock analysis graph.
        # Ideally this should be run once globally, but for now we run it per cycle.
        cache_context = {
            "date": str(current_date),
            "analyst": "sector"
        }
        cache_key = json.dumps(cache_context, sort_keys=True)
        
        cached_response = llm_cache.get(cache_key, "sector_analyst")
        
        if cached_response:
            try:
                result = messages_from_dict([json.loads(cached_response)])[0]
            except Exception:
                result = chain.invoke(state["messages"])
        else:
            result = chain.invoke(state["messages"])
            try:
                serialized = messages_to_dict([result])[0]
                llm_cache.set(cache_key, "sector_analyst", json.dumps(serialized))
            except Exception:
                pass

        report = ""
        if len(result.tool_calls) == 0:
            report = result.content
            
        return {
            "messages": [result],
            "sector_report": report
        }

    return sector_analyst_node
