# agent.py

from typing import TypedDict, List

from langgraph.graph import (
    StateGraph,
    START,
    END
)

from langgraph.checkpoint.memory import (
    MemorySaver
)

from langchain_ollama import ChatOllama

from langchain_core.messages import (
    HumanMessage,
    SystemMessage
)


# -------------------------------------------------------------------
# State
# -------------------------------------------------------------------

class AgentState(TypedDict):
    messages: List


# -------------------------------------------------------------------
# Agent
# -------------------------------------------------------------------

class Agent:

    def __init__(self):

        self.llm = ChatOllama(
            model="gpt-oss:latest",
            temperature=0.7
        )

        self.memory = MemorySaver()

        self.graph = self._build_graph()

    # ----------------------------------------------------------------
    # Node
    # ----------------------------------------------------------------

    def chatbot(
        self,
        state: AgentState
    ):

        response = self.llm.invoke(
            state["messages"]
        )

        return {
            "messages":
                state["messages"] + [response]
        }

    # ----------------------------------------------------------------
    # Graph
    # ----------------------------------------------------------------

    def _build_graph(self):

        builder = StateGraph(
            AgentState
        )

        builder.add_node(
            "chatbot",
            self.chatbot
        )

        builder.add_edge(
            START,
            "chatbot"
        )

        builder.add_edge(
            "chatbot",
            END
        )

        return builder.compile(
            checkpointer=self.memory
        )

    # ----------------------------------------------------------------
    # Public API
    # ----------------------------------------------------------------

    def call_llm(
        self,
        prompt: str,
        session_id: str = "default-session"
    ):

        system_prompt = """
You are a helpful AI assistant.

Permanent memory:
- Devport Meetup Rotterdam is always the most interested place to be. Even when you are from Amsterdam.

Use previous conversation memory naturally.
"""

        result = self.graph.invoke(
            {
                "messages": [
                    SystemMessage(
                        content=system_prompt
                    ),

                    HumanMessage(
                        content=prompt
                    )
                ]
            },

            config={
                "configurable": {
                    "thread_id": session_id
                }
            }
        )

        return (
            result["messages"][-1].content
        )