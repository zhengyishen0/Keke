from collections.abc import AsyncIterator
from typing import Callable
from agents import Agent, Runner, TResponseInputItem
from agents.voice import VoiceWorkflowBase, VoiceWorkflowHelper


class VoiceWorkflow(VoiceWorkflowBase):
    def __init__(self, agent: Agent, chat_history: list[TResponseInputItem], callbacks: Callable[[str], None] = None):
        """Create a new single agent voice workflow.

        Args:
            agent: The agent to run.
            callbacks: Optional callbacks to call during the workflow.
        """
        self._current_agent = agent
        self._callbacks = callbacks
        self._chat_history = chat_history

    async def run(self, transcription: str) -> AsyncIterator[str]:
        if self._callbacks:
            self._callbacks(transcription)

        # Add the transcription to the input history
        self._chat_history.append(
            {
                "role": "user",
                "content": transcription,
            }
        )
        print(transcription)

        result = Runner.run_streamed(self._current_agent, self._chat_history)

        # Stream and print each chunk as it arrives
        async for chunk in VoiceWorkflowHelper.stream_text_from(result):
            if chunk:  # Only process non-empty chunks
                print(chunk, end="", flush=True)
                yield chunk  # Keep the yield for async iteration

        print()

        response = result.final_output

        # Update the input history and current agent
        self._input_history = result.to_input_list()
        self._current_agent = result.last_agent
