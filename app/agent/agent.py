from typing import Annotated, TypedDict

from langchain_openai import AzureChatOpenAI
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages

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

    def chatbot(state: ChatState) -> ChatState:
        response = llm.invoke(state["messages"])
        return {"messages": [response]}

    builder = StateGraph(ChatState)
    builder.add_node("chat_node", chatbot)
    builder.add_edge(START, "chat_node")
    builder.add_edge("chat_node", END)

    return builder.compile()
