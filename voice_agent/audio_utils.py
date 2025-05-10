import numpy.typing as npt
import time
import curses
import numpy as np
import sounddevice as sd


def play_beep():
    """
    Play a beep sound.
    """
    beep = np.sin(2 * np.pi * 440 * np.arange(0,
                  0.5, 1/24000)).astype(np.float32)
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


async def play_audio_stream_1(result):
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


def _record_audio(screen: curses.window) -> npt.NDArray[np.float32]:
    screen.nodelay(True)  # Non-blocking input
    screen.clear()
    screen.addstr(
        "Press <spacebar> to start recording. Press <spacebar> again to stop recording.\n"
    )
    screen.refresh()

    recording = False
    audio_buffer: list[npt.NDArray[np.float32]] = []

    def _audio_callback(indata, frames, time_info, status):
        if status:
            screen.addstr(f"Status: {status}\n")
            screen.refresh()
        if recording:
            audio_buffer.append(indata.copy())

    # Open the audio stream with the callback.
    with sd.InputStream(samplerate=24000, channels=1, dtype=np.float32, callback=_audio_callback):
        while True:
            key = screen.getch()
            if key == ord(" "):
                recording = not recording
                if recording:
                    screen.addstr("Recording started...\n")
                else:
                    screen.addstr("Recording stopped.\n")
                    break
                screen.refresh()
            time.sleep(0.01)

    # Combine recorded audio chunks.
    if audio_buffer:
        audio_data = np.concatenate(audio_buffer, axis=0)
    else:
        audio_data = np.empty((0,), dtype=np.float32)

    return audio_data


def record_audio():
    # Using curses to record audio in a way that:
    # - doesn't require accessibility permissions on macos
    # - doesn't block the terminal
    audio_data = curses.wrapper(_record_audio)
    return audio_data


class AudioPlayer:
    def __enter__(self):
        self.stream = sd.OutputStream(
            samplerate=24000, channels=1, dtype=np.int16)
        self.stream.start()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.stream.stop()  # wait for the stream to finish
        self.stream.close()

    def add_audio(self, audio_data: npt.NDArray[np.int16]):
        self.stream.write(audio_data)


async def play_audio_stream(result):
    with AudioPlayer() as player:
        async for event in result.stream():
            if event.type == "voice_stream_event_audio":
                player.add_audio(event.data)
                print("Received audio")
            elif event.type == "voice_stream_event_lifecycle":
                print(f"Received lifecycle event: {event.event}")

        # Add 1 second of silence to the end of the stream to avoid cutting off the last audio
        player.add_audio(np.zeros(24000 * 1, dtype=np.int16))
