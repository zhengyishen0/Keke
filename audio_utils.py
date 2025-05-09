import numpy as np
import sounddevice as sd


def play_beep():
    """
    Play a beep sound.
    """
    beep = np.sin(2 * np.pi * 440 * np.arange(0, 0.5, 1/24000)).astype(np.float32)
    sd.play(beep, 24000)
    sd.wait()


def capture_audio(duration=5):
    """
    Capture audio from the microphone for a specified duration.
    
    Args:
        duration (int): Duration of audio capture in seconds
        
    Returns:
        numpy.ndarray: Audio buffer containing the captured audio
    """
    play_beep()
    with sd.InputStream(samplerate=24000, channels=1, dtype=np.int16) as stream:
        buffer = stream.read(int(duration * 24000))[0]
    play_beep()
    return buffer


async def play_audio_stream(result):
    """
    Play an audio stream as it comes in.
    
    Args:
        result: The result object containing the audio stream
    """
    # Create an audio player using `sounddevice`
    player = sd.OutputStream(samplerate=24000, channels=1, dtype=np.int16)
    player.start()

    # Play the audio stream as it comes in
    async for event in result.stream():
        if event.type == "voice_stream_event_audio":
            player.write(event.data) 