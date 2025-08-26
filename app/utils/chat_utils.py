from langchain.schema import AIMessage, HumanMessage, SystemMessage


def convert_message(msg) -> dict:
    if isinstance(msg, HumanMessage):
        return {"role": "user", "content": msg.content}
    elif isinstance(msg, AIMessage):
        return {"role": "assistant", "content": msg.content}
    elif isinstance(msg, SystemMessage):
        return {"role": "system", "content": msg.content}
    else:
        raise ValueError(f"Unsupported message type: {type(msg)}")
