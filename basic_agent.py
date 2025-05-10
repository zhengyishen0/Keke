import asyncio
from agents import Agent, Runner, TResponseInputItem
from dotenv import load_dotenv

load_dotenv()

questions = [
    "What is the largest country in South America?",
    "What is the capital of that country?",
    "what did you just say?",
]

agent = Agent(
    name="Assistant",
    instructions="You are a helpful assistant. be VERY concise.",
    model="gpt-4.1-nano",
)


async def agent_run():
    chat_history: list[TResponseInputItem] = []

    for input in questions:
        chat_history.append({"role": "user", "content": input})
        result = await Runner.run(agent, chat_history)
        chat_history = result.to_input_list()

        print(f"Q: {input}")
        print(result.final_output)
        print()


async def agent_stream():
    chat_history: list[TResponseInputItem] = []

    for input in questions:
        chat_history.append({"role": "user", "content": input})
        result = await Runner.run_streamed(agent, chat_history)

        async for event in result.stream_events():
            if event.type == "raw_response_event" and event.data.type == "response.output_text.delta":
                print(event.data.delta, end="", flush=True)

        chat_history = result.to_input_list()
        print(f"Q: {input}")
        print(f"A: {result.final_output}")
        print()


if __name__ == "__main__":
    asyncio.run(agent_run())
    asyncio.run(agent_stream())
