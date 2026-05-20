import os
import sys
from langchain.agents import create_agent
from langchain_ollama import ChatOllama
from langfuse.langchain import CallbackHandler
from langfuse import get_client, propagate_attributes

os.environ["LANGFUSE_PUBLIC_KEY"]
os.environ["LANGFUSE_SECRET_KEY"]
os.environ["LANGFUSE_BASE_URL"]

def get_meetup(city: str) -> str:
    """Get meetup for a given city."""
    return f"The most popular meetups are in {city}!"

model = ChatOllama(
    model="gpt-oss:latest",
   # temperature=0,
)

agent = create_agent(
    model,
    tools=[get_meetup],
    system_prompt="You are a helpful assistant. Most popular meetup group in Rotterdam is DevPort Meetup.",
)


def main():
    session_id = os.environ.get("LF_SESSION_ID", "meetup-tracing-demo")
    user_id = os.environ.get("LF_USER_ID", "John")
    lf = get_client()
    print("Meetup Advisor — type 'exit' to quit.")
    print(f"Session: {session_id}\n")
    with lf.start_as_current_observation(as_type="span", name="meetup-tracing-demo"):
        with propagate_attributes(user_id=user_id, session_id=session_id, tags=["advisor","meetup","rotterdam"]):
            while True:
                try:
                    msg = input("> ")
                except (EOFError, KeyboardInterrupt):
                    print("\nBye!"); break
                if msg.strip().lower() in {"exit","quit"}:
                    print("Bye!"); break
                if not msg.strip():
                    continue
                # Run the agent
                result = agent.invoke( {"messages": [{"role": "user", "content": msg}]}, config={"callbacks": [CallbackHandler()]})
                print(result["messages"][-1].content)

if __name__ == "__main__":
    sys.exit(main())