import asyncio
import random
import numpy as np
import sounddevice as sd
from agents import (
    Agent,
    function_tool,
    set_tracing_disabled,
)
from agents.voice import (
    AudioInput,
    SingleAgentVoiceWorkflow,
    VoicePipeline,
)
from agents.extensions.handoff_prompt import prompt_with_handoff_instructions
from dotenv import load_dotenv

# Load environment variables
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

def play_beep():
    """
    Play a beep sound.
    """

    beep = np.sin(2 * np.pi * 440 * np.arange(0, 0.5, 1/24000)).astype(np.float32)
    sd.play(beep, 24000)
    sd.wait()

def capture_audio(duration=3):
    play_beep()
    with sd.InputStream(samplerate=24000, channels=1, dtype=np.int16) as stream:
        buffer = stream.read(int(duration * 24000))[0]
    play_beep()
    return buffer


async def main():
    pipeline = VoicePipeline(workflow=SingleAgentVoiceWorkflow(agent))

    buffer = capture_audio()
    audio_input = AudioInput(buffer=buffer)

    result = await pipeline.run(audio_input)

    # Create an audio player using `sounddevice`
    player = sd.OutputStream(samplerate=24000, channels=1, dtype=np.int16)
    player.start()

    # Play the audio stream as it comes in
    async for event in result.stream():
        if event.type == "voice_stream_event_audio":
            player.write(event.data)


if __name__ == "__main__":
    asyncio.run(main())