from langchain.agents import create_agent
from langchain_ollama import ChatOllama

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

# Run the agent
result = agent.invoke(
    {"messages": [{"role": "user", "content": "How exciting is the meetup scene in Rotterdam?"}]}
)

print(result["messages"][-1].content)

result = agent.invoke(
    {"messages": [{"role": "user", "content": "what is the most popular meetup group in Rotterdam?"}]}
)

print(result["messages"][-1].content)