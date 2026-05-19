import os

from langchain_ollama import ChatOllama
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage
from langchain.agents import create_agent

from langfuse import get_client, propagate_attributes
from langfuse.langchain import CallbackHandler

os.environ["LANGFUSE_PUBLIC_KEY"]
os.environ["LANGFUSE_SECRET_KEY"]
os.environ["LANGFUSE_BASE_URL"]

# Initialise Langfuse client and verify credentials on startup
session_id = os.environ.get("LF_SESSION_ID", "math-agent-session")
user_id = os.environ.get("LF_USER_ID", "cli_user")
langfuse = get_client()
if not langfuse.auth_check():
    raise RuntimeError(
        "Langfuse authentication failed. "
        "Check LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY and LANGFUSE_BASE_URL."
    )
print("Langfuse connected.\n")

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

# --- Agent ---

tools = [add, multiply, square]

agent = create_agent(
    model=llm,
    tools=tools,
    system_prompt=SYSTEM_PROMPT,
)

# --- Interactive REPL ---

print("Math Agent ready. Type 'exit' or 'quit' to stop.\n")

turn = 0

with langfuse.start_as_current_observation(as_type="span", name=f"math-agent-turn-{turn}"):
    with propagate_attributes(user_id=user_id, session_id=session_id, tags=["math","agent","interactive"]):
        while True:
            try:
                user_input = input("You: ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nBye!")
                break
            if not user_input:
                continue
            if user_input.lower() in {"exit", "quit"}:
                print("Bye!")
                break
            turn += 1
            # A fresh CallbackHandler per turn = one named trace per question in Langfuse
            #with propagate_attributes(
            #    trace_name=f"math-agent-turn-{turn}",
            #    tags=["math-agent", "interactive"],
            #    metadata={"turn": turn, "model": "gpt-oss:latest"},
            #):
            langfuse_handler = CallbackHandler()
            result = agent.invoke(
                {"messages": [HumanMessage(content=user_input)]},
                config={"callbacks": [langfuse_handler]},
            )   
            # Flush to ensure the trace is sent before the next prompt
            # langfuse_handler.flush()
            print(f"Agent: {result['messages'][-1].content}\n")
