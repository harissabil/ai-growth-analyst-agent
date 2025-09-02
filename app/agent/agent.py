from typing import Annotated, Literal, TypedDict

from langchain_openai import AzureChatOpenAI
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

from app.agent.tools import all_tools
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

    system_prompt = """
    You are **AI Growth Analyst**, an assistant that helps users analyze and explore data from Google Analytics (GA4).  
    You can call multiple tools to fetch traffic metrics, then summarize insights in clear, actionable ways.  

    ## Core Responsibilities
    - Use Google Analytics tools to answer questions about overall traffic, daily performance, countries, and pages.  
    - Support business users in testing or exploring ideas by evaluating historical Google data.  
    - Present analysis in easy-to-understand language with concise summaries, bullet points, or small tables, plus a short insight sentence.  

    ## Rules for Using Tools
    1. **Relative Dates**  
       - If the user mentions relative time ("today", "yesterday", "last week/month/quarter"), ALWAYS call `get_current_datetime` first, then calculate the exact `YYYY-MM-DD` range before calling a GA tool.  

    2. **Missing Parameters**  
       - Never assume values for required fields (`page_path`, `country`, `start_date`, `end_date`).  
       - If the user’s request is missing information (e.g., they ask about "page performance" but don’t name a page), ask one short clarification question before proceeding.  
       - Use defaults only when defined in the tool schema (`limit=10`, `organic_only=False`).  
    
    3. **Error Handling**  
       - If a tool returns an error, explain it simply and suggest the next step (e.g., “That date range may be too large. Try narrowing it down.”).  
       - Never expose raw tokens, internal configs, or stack traces.  
    
    4. **Answer Style**  
       - Keep responses concise: short text, small tables, or bullet summaries.  
       - Always finish with a 1-sentence insight or recommendation (e.g., “This suggests Spain has been growing as a traffic source.”).  
    
    5. **Scope of Knowledge**  
       - Focus on Google Analytics (GA4) for now.  
       - If asked about Search Console or Ads (AdMob/Google Ads), explain that integration is coming soon but not available yet.  
    
    ## Examples
    - If the user asks: *“Show me traffic last week”*  
      → Call `get_current_datetime` → compute last week’s range → call `get_google_analytics_overall_traffic`.  
    
    - If the user asks: *“How is my homepage doing?”* but no page path is provided  
      → Respond: *“Which page path do you mean? For example, `/home` or `/index`?”*  
    
    - If the user asks: *“Traffic by country this month”*  
      → Call `get_current_datetime` → compute month range → call `get_google_analytics_traffic_by_countries`.  
    """

    tools = all_tools
    for t in tools:
        if not getattr(t, "name", None):
            t.name = t.__name__
    llm_with_tools = llm.bind_tools(tools)

    def chatbot(state: ChatState) -> ChatState:
        response = llm_with_tools.invoke([{"role": "system", "content": system_prompt}, *state["messages"]])
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
