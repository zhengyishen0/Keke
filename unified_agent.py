import asyncio
from agents import Agent, Runner, TResponseInputItem
from agents.extensions.handoff_prompt import prompt_with_handoff_instructions
from agents.voice import AudioInput, VoicePipeline
from voice_agent.audio_utils import record_audio, play_audio_stream
from voice_agent.my_workflow import MyWorkflow
from dotenv import load_dotenv

load_dotenv()


class UnifiedAgent:
    def __init__(self):
        self.agent = Agent(
            name="Assistant",
            instructions=prompt_with_handoff_instructions(
                "You're speaking to a human, so be polite and concise.",
            ),
            model="gpt-4.1-nano",
        )
        self.chat_history: list[TResponseInputItem] = []

    async def handle_text_input(self, text: str):
        """Handle text input with streaming response"""
        self.chat_history.append({"role": "user", "content": text})
        result = Runner.run_streamed(self.agent, self.chat_history)
        self.chat_history = result.to_input_list()

        async for event in result.stream_events():
            if event.type == "raw_response_event" and event.data.type == "response.output_text.delta":
                print(event.data.delta, end="", flush=True)
        print("\n")

    async def handle_voice_input(self):
        """Handle voice input with audio response"""
        workflow = MyWorkflow(self.agent, self.chat_history)
        pipeline = VoicePipeline(workflow=workflow)

        buffer = record_audio()
        audio_input = AudioInput(buffer=buffer)
        result = await pipeline.run(audio_input)
        await play_audio_stream(result)


async def main():
    agent = UnifiedAgent()

    while True:

        print("\nChoose input mode:")
        print("1. Text input")
        print("2. Voice input")
        print("3. Exit")

        choice = input("Enter your choice (1-3): ")

        if choice == "1":
            text = input("Enter your text: ")
            await agent.handle_text_input(text)
        elif choice == "2":
            print("Recording... Press Ctrl+C to stop")
            await agent.handle_voice_input()
        elif choice == "3":
            break
        else:
            print("Invalid choice. Please try again.")


if __name__ == "__main__":
    asyncio.run(main())
