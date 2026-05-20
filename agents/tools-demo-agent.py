from langchain_ollama import ChatOllama
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage
from langchain.agents import create_agent

# --- Tools ---

@tool
def add(a: int, b: int) -> int:
    """Add two numbers."""
    return a + b


@tool
def multiply(a: int, b: int) -> int:
    """Multiply two numbers."""
    return a * b


@tool
def square(a: int) -> int:
    """Calculate the square of a number."""
    return a * a


# --- Model ---

# Connects to a locally running Ollama instance (default: http://localhost:11434).
# Override base_url if Ollama is on a different host/port, e.g.:
#   ChatOllama(model="gpt-oss:latest", base_url="http://192.168.1.10:11434")
llm = ChatOllama(model="gpt-oss:latest", temperature=0)

# --- System prompt ---

SYSTEM_PROMPT = """You are a mathematical assistant.
Use your tools to answer questions. If you do not have a tool to
answer the question, say so.

Return only the answers. e.g
Human: What is 1 + 1?
AI: 2
"""

# --- Agent (LangGraph ReAct, replaces AgentExecutor) ---

tools = [add, multiply, square]

agent = create_agent(
    model=llm,
    tools=tools,
    system_prompt=SYSTEM_PROMPT,
)

# --- Run ---

result = agent.invoke(
    {"messages": [HumanMessage(content="what is 250 + 250 + 500 + 1 * 5?")]}
)

# The final answer is in the last message
print(result["messages"][-1].content)
