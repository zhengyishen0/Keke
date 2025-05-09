import asyncio
import random
from agents import Agent,function_tool
from agents.voice import AudioInput, SingleAgentVoiceWorkflow, VoicePipeline
from agents.extensions.handoff_prompt import prompt_with_handoff_instructions
from audio_utils import capture_audio, play_audio_stream
from dotenv import load_dotenv


load_dotenv()


@function_tool
def get_weather(city: str) -> str:
    """Get the weather for a given city."""
    print(f"[debug] get_weather called with city: {city}")
    choices = ["sunny", "cloudy", "rainy", "snowy"]
    return f"The weather in {city} is {random.choice(choices)}."


spanish_agent = Agent(
    name="Spanish",
    handoff_description="A spanish speaking agent.",
    instructions=prompt_with_handoff_instructions(
        "You're speaking to a human, so be polite and concise. Speak in Spanish.",
    ),
    model="gpt-4.1-nano",
)

agent = Agent(
    name="Assistant",
    instructions=prompt_with_handoff_instructions(
        "You're speaking to a human, so be polite and concise. If the user speaks in Spanish, handoff to the spanish agent.",
    ),
    model="gpt-4.1-nano",
    handoffs=[spanish_agent],
    tools=[get_weather],
)



async def main():
    pipeline = VoicePipeline(workflow=SingleAgentVoiceWorkflow(agent))

    buffer = capture_audio()
    audio_input = AudioInput(buffer=buffer)

    result = await pipeline.run(audio_input)
    await play_audio_stream(result)


if __name__ == "__main__":
    asyncio.run(main())
    