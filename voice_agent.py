import asyncio
from agents import Agent, function_tool
from agents.extensions.handoff_prompt import prompt_with_handoff_instructions
from agents.voice import (
    AudioInput,
    SingleAgentVoiceWorkflow,
    SingleAgentWorkflowCallbacks,
    VoicePipeline,
)
from audio_utils import record_audio, play_audio_stream, play_beep
from my_workflow import MyWorkflow
from dotenv import load_dotenv

load_dotenv()


agent = Agent(
    name="Assistant",
    instructions=prompt_with_handoff_instructions(
        "You're speaking to a human, so be polite and concise. If the user speaks in Spanish, handoff to the spanish agent.",
    ),
    model="gpt-4.1-nano",
)


class WorkflowCallbacks(SingleAgentWorkflowCallbacks):
    def on_run(self, workflow: SingleAgentVoiceWorkflow, transcription: str) -> None:
        print(f"[debug] on_run called with transcription: {transcription}")


async def main():
    # workflow = SingleAgentVoiceWorkflow(agent, callbacks=WorkflowCallbacks())
    workflow = MyWorkflow(
        agent=agent, callbacks=lambda x: print(f"Transcription: {x}"))
    pipeline = VoicePipeline(workflow=workflow)

    while True:
        try:
            buffer = record_audio()
            audio_input = AudioInput(buffer=buffer)
            result = await pipeline.run(audio_input)
            await play_audio_stream(result)

        except KeyboardInterrupt:
            break


if __name__ == "__main__":
    asyncio.run(main())
