import asyncio
import numpy as np
import sounddevice as sd
from agents.voice import StreamedAudioInput, VoicePipeline
from my_workflow import MyWorkflow

# Audio configuration
SAMPLE_RATE = 24000
CHANNELS = 1
FORMAT = np.int16
CHUNK_LENGTH_S = 0.05  # 50ms chunks


async def test_workflow():
    audio_input = StreamedAudioInput()

    workflow = MyWorkflow(secret_word="test",
                          on_start=lambda x: print(f"Transcription: {x}"))
    pipeline = VoicePipeline(workflow=workflow)
    result = await pipeline.run(audio_input)

    # Simulate some audio input
    test_audio = np.zeros((int(SAMPLE_RATE * 0.5), CHANNELS),
                          dtype=FORMAT)  # 0.5 seconds of silence
    await audio_input.add_audio(test_audio)

    # Process the stream
    async for event in result.stream():
        if event.type == "voice_stream_event_audio":
            print(
                f"Received audio: {len(event.data) if event.data is not None else '0'} bytes")
        elif event.type == "voice_stream_event_lifecycle":
            print(f"Lifecycle event: {event.event}")

if __name__ == "__main__":
    asyncio.run(test_workflow())
