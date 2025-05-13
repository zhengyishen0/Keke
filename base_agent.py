import asyncio
from agents import Agent, Runner, TResponseInputItem
from dotenv import load_dotenv

load_dotenv()


class BaseAgent(Agent):
    def __init__(self, name: str, instructions: str, model: str):
        """
        A base agent class that can be used to create other agents. It has built in chat history and methods for running and streaming.
        """
        super().__init__(
            name=name,
            instructions=instructions,
            model=model,
        )

        self.chat_history: list[TResponseInputItem] = []

    async def run(self, text: str) -> str:
        self.chat_history.append({"role": "user", "content": text})
        result = await Runner.run(self, self.chat_history)
        self.chat_history = result.to_input_list()

        print(result.final_output)
        return result.final_output

    async def stream(self, text: str) -> str:
        self.chat_history.append({"role": "user", "content": text})
        result = Runner.run_streamed(self, self.chat_history)

        async for event in result.stream_events():
            if event.type == "raw_response_event" and event.data.type == "response.output_text.delta":
                print(event.data.delta, end="", flush=True)
                pass

        self.chat_history = result.to_input_list()
        final_output = result.to_input_list()[-1]["content"][0]["text"]
        print(final_output)
        return final_output


if __name__ == "__main__":
    questions = [
        "What is the largest country in South America?",
        "What is the capital of that country?",
        "what did you just say?",
    ]

    stories = [
        "create a short story about a cat",
    ]
    agent = BaseAgent("test", "You are a helpful assistant.", "gpt-4.1-nano")
    for text in stories:
        asyncio.run(agent.run(text))
        asyncio.run(agent.stream(text))
