import asyncio
from agents import Agent, function_tool
from agents.voice import AudioInput, SingleAgentVoiceWorkflow, VoicePipeline
from agents.extensions.handoff_prompt import prompt_with_handoff_instructions
from audio_utils import capture_audio, play_audio_stream
from dotenv import load_dotenv

load_dotenv()


# def is_goodbye(response: str) -> bool:
#     """Identify the response as a goodbye message."""
#     return any(word in response.lower() for word in ["goodbye", "bye", "see you later"])


agent = Agent(
    name="Assistant",
    model="gpt-4.1-nano",
)


async def main():
    workflow = SingleAgentVoiceWorkflow(agent)
    pipeline = VoicePipeline(workflow=workflow)

    while True:
        try:
            buffer = capture_audio()
            audio_input = AudioInput(buffer=buffer)

            result = await pipeline.run(audio_input)
            await play_audio_stream(result)

        except KeyboardInterrupt:
            print("\nGoodbye!")
            break


if __name__ == "__main__":
    asyncio.run(main())
