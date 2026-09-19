from .nodes import yield_node, weather_node, aggregator_node, market_node, supply_chain_node
from .state import HarvestState
from langgraph.graph import StateGraph, START, END

def build_graph():
    graph = StateGraph(HarvestState)
 
    graph.add_node("yield_node", yield_node)
    graph.add_node("weather_node", weather_node)
    graph.add_node("aggregator", aggregator_node)
    graph.add_node("market_node", market_node)
    graph.add_node("supply_chain_node", supply_chain_node)
 
    # parallel fan-out
    graph.add_edge(START, "yield_node")
    graph.add_edge(START, "weather_node")
 
    # fan-in: aggregator waits for both
    graph.add_edge("yield_node", "aggregator")
    graph.add_edge("weather_node", "aggregator")
 
    # sequential tail
    graph.add_edge("aggregator", "market_node")
    graph.add_edge("market_node", "supply_chain_node")
    graph.add_edge("supply_chain_node", END)
 
    return graph.compile()







    