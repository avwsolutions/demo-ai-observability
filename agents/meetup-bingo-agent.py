import os
from typing import TypedDict, List, Set, Literal
from langfuse.langchain import CallbackHandler
from langfuse import get_client, propagate_attributes
from langgraph.graph import StateGraph, START, END
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

# --- Config ---
os.environ["LANGFUSE_PUBLIC_KEY"]
os.environ["LANGFUSE_SECRET_KEY"]
os.environ["LANGFUSE_BASE_URL"]
BUZZWORDS = [
  "Python","Cloud Computing","Webdevelopment","DevOps","Front-end developer","Cloud Integratie",
  "Microsoft Azure","PHP","Opensource","python","Angular","Backend","Kubernetes","ReactJS",
  "DevOps","automatisering","CI/CD","Platform engineering"
]
BINGO_THRESHOLD = 5  # adjust as you like

# --- State ---
class State(TypedDict):
    messages: List[str]
    hits: Set[str]
    bingo: bool
    report: str

# --- LLM setup ---
llm = ChatOllama(model="gpt-oss:latest")
parser = StrOutputParser()
extract_prompt = ChatPromptTemplate.from_template(
    "You will extract buzzwords found in the user's message.\n"
    "Candidate list (case-insensitive): {candidates}\n"
    "User message: {text}\n"
    "Return a comma-separated list of exact entries from the candidate list that appear in the message; "
    "if none, return an empty line."
)
extract_chain = extract_prompt | llm | parser

# --- Nodes ---
def extract_hits(state: State) -> State:
    last = state["messages"][-1]
    out = extract_chain.invoke({
        "candidates": "; ".join(BUZZWORDS),
        "text": last
    }, config={"callbacks": [CallbackHandler()]})
    found = {w.strip() for w in out.split(",") if w.strip()} if out else set()
    return {**state, "hits": set(state.get("hits", set())) | found}

def update_and_check(state: State) -> State:
    all_hits = state["hits"]
    bingo = len(all_hits) >= BINGO_THRESHOLD
    report = f"Hits ({len(all_hits)}): {sorted(all_hits)} | Bingo: {bingo}"
    return {**state, "bingo": bingo, "report": report}

# --- Graph ---
graph = StateGraph(State)
graph.add_node("extract_hits", extract_hits)
graph.add_node("update_and_check", update_and_check)
graph.add_edge(START, "extract_hits")
graph.add_edge("extract_hits", "update_and_check")
graph.add_edge("update_and_check", END)
app = graph.compile()

if __name__ == "__main__":
    # Optional: propagate session/user once for the whole trace
    lf = get_client()
    with lf.start_as_current_observation(as_type="span", name="buzzword-bingo"):
        with propagate_attributes(user_id="user_123", session_id="meetup_session"):
            s0: State = {"messages": [], "hits": set(), "bingo": False, "report": ""}
            # Simulate multiple meetup utterances
            inputs = [
                "We love Python and CI/CD with Kubernetes in our Platform engineering team.",
                "Front-end developer with ReactJS or Angular skills wanted; cloud integratie on Microsoft Azure.",
                "Our DevOps automatisering improves backend and opensource workflows in webdevelopment."
            ]
            for msg in inputs:
                s0["messages"].append(msg)
                s0 = app.invoke(s0, config={"callbacks": [CallbackHandler()]})
                print(s0["report"])
