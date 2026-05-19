import os, sys
from typing import TypedDict, List, Set
from langfuse.langchain import CallbackHandler
from langfuse import get_client, propagate_attributes
from langgraph.graph import StateGraph, START, END
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

os.environ["LANGFUSE_PUBLIC_KEY"]
os.environ["LANGFUSE_SECRET_KEY"]
os.environ["LANGFUSE_BASE_URL"]

BUZZWORDS = [
  "Python","Cloud Computing","Webdevelopment","DevOps","Front-end developer","Cloud Integratie",
  "Microsoft Azure","PHP","Opensource","python","Angular","Backend","Kubernetes","ReactJS",
  "DevOps","automatisering","CI/CD","Platform engineering"
]
BINGO_THRESHOLD = 5

class State(TypedDict):
    messages: List[str]
    hits: Set[str]
    bingo: bool
    report: str

llm = ChatOllama(model="gpt-oss:latest")
extract_chain = (
    ChatPromptTemplate.from_template(
      "Extract matched buzzwords from this candidate list (case-insensitive): {candidates}\n"
      "User message: {text}\n"
      "Return a comma-separated list of exact candidate entries that appear; else empty."
    )
    | llm
    | StrOutputParser()
)

def extract_hits(state: State) -> State:
    out = extract_chain.invoke(
        {"candidates": "; ".join(BUZZWORDS), "text": state["messages"][-1]},
        config={"callbacks": [CallbackHandler()]},
    )
    new = {w.strip() for w in out.split(",") if w.strip()} if out else set()
    return {**state, "hits": state.get("hits", set()) | new}

def update_and_check(state: State) -> State:
    hits = state["hits"]
    bingo = len(hits) >= BINGO_THRESHOLD
    return {**state, "bingo": bingo, "report": f"Hits ({len(hits)}): {sorted(hits)} | Bingo: {bingo}"}

graph = StateGraph(State)
graph.add_node("extract_hits", extract_hits)
graph.add_node("update_and_check", update_and_check)
graph.add_edge(START, "extract_hits")
graph.add_edge("extract_hits", "update_and_check")
graph.add_edge("update_and_check", END)
app = graph.compile()

def main():
    session_id = os.environ.get("LF_SESSION_ID", "meetup_bingo_console")
    user_id = os.environ.get("LF_USER_ID", "cli_user")
    lf = get_client()
    print("Buzzword Bingo — type 'exit' to quit.")
    print(f"Session: {session_id} | Threshold: {BINGO_THRESHOLD}\n")

    state: State = {"messages": [], "hits": set(), "bingo": False, "report": ""}
    with lf.start_as_current_observation(as_type="span", name="buzzword-bingo-session"):
        with propagate_attributes(user_id=user_id, session_id=session_id, tags=["bingo","console","ollama"]):
            while True:
                try:
                    msg = input("> ")
                except (EOFError, KeyboardInterrupt):
                    print("\nBye!"); break
                if msg.strip().lower() in {"exit","quit"}:
                    print("Bye!"); break
                if not msg.strip():
                    continue
                state["messages"].append(msg)
                state = app.invoke(state, config={"callbacks": [CallbackHandler()]})
                print(state["report"])
                if state["bingo"]:
                    print("BINGO! 🎉 Keep going or 'exit'.")

if __name__ == "__main__":
    sys.exit(main())
