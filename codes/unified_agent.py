from ast import Dict, List
import asyncio
from agents import Agent, Runner, TResponseInputItem
from agents.extensions.handoff_prompt import prompt_with_handoff_instructions
from agents.voice import AudioInput, VoicePipeline
from ..utils.audio_utils import record_audio, play_audio_stream
from voice_workflow import VoiceWorkflow
from dotenv import load_dotenv

load_dotenv()


class UnifiedAgent:
    def __init__(self, instructions: str, name: str = "Assistant",  model: str = "gpt-4.1-nano"):
        self.agent = Agent(
            name=name,
            instructions=instructions,
            model=model,
        )
        self.chat_history: list[TResponseInputItem] = []

    async def handle_text_input(self, text: str = None):
        """Handle text input with streaming response"""

        self.chat_history.append({"role": "user", "content": text})
        result = Runner.run_streamed(self.agent, self.chat_history)
        self.chat_history = result.to_input_list()

        async for event in result.stream_events():
            if event.type == "raw_response_event" and event.data.type == "response.output_text.delta":
                print(event.data.delta, end="", flush=True)
        print("\n")
        # return result.final_output

    async def handle_voice_input(self):
        """Handle voice input with audio response"""
        workflow = VoiceWorkflow(self.agent, self.chat_history)
        pipeline = VoicePipeline(workflow=workflow)

        buffer = record_audio()
        audio_input = AudioInput(buffer=buffer)
        result = await pipeline.run(audio_input)
        await play_audio_stream(result)
        # return result.final_output


async def main():
    agent = UnifiedAgent("You are a helpful assistant.")

    print("\nWelcome! Type your message and press Enter to send.")
    print("Type '<>' to start voice recording.")
    print("Type 'exit' to quit.")

    while True:
        text = input("> ")
        if text.lower() == 'exit':
            break
        elif text.strip() == '<>':
            print("Recording... Press Ctrl+C to stop")
            await agent.handle_voice_input()
        elif text.strip():  # Only process non-empty input
            await agent.handle_text_input(text)

    # TODO: add interrupt handling


if __name__ == "__main__":
    asyncio.run(main())
