from typing import Annotated, Literal, TypedDict

from langchain_openai import AzureChatOpenAI
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

from app.agent.tools import (
    get_daily_traffic,
    get_daily_traffic_for_country,
    get_daily_traffic_for_page,
    get_overall_traffic,
    get_traffic_by_countries,
    get_traffic_by_pages,
)
from app.config import get_settings


class ChatState(TypedDict):
    messages: Annotated[list, add_messages]


def get_graph():
    settings = get_settings()
    llm = AzureChatOpenAI(
        azure_endpoint=str(settings.azure_openai_endpoint),
        api_key=settings.azure_openai_api_key,
        azure_deployment=settings.azure_openai_deployment,
        api_version=settings.azure_openai_api_version,
    )

    tools = [
        get_overall_traffic,
        get_daily_traffic,
        get_traffic_by_countries,
        get_daily_traffic_for_country,
        get_traffic_by_pages,
        get_daily_traffic_for_page,
    ]
    llm_with_tools = llm.bind_tools(tools)

    async def chatbot(state: ChatState) -> ChatState:
        response = llm_with_tools.invoke(state["messages"])
        return {"messages": [response]}

    tool_node = ToolNode(tools)

    def should_continue(state: ChatState) -> Literal["tool_node", "__end__"]:
        """
        Determines the next step. If the LLM made a tool call, route to the tool_node.
        Otherwise, end the conversation turn.
        """
        last_message = state["messages"][-1]
        if last_message.tool_calls:
            return "tool_node"
        return END

    builder = StateGraph(ChatState)

    builder.add_node("chat_node", chatbot)
    builder.add_node("tool_node", tool_node)

    builder.add_edge(START, "chat_node")
    builder.add_conditional_edges(
        "chat_node",
        should_continue,
    )
    builder.add_edge("tool_node", "chat_node")

    return builder.compile()
