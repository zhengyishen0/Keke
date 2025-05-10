from collections.abc import AsyncIterator
from typing import Callable
from agents import Agent, Runner, TResponseInputItem
from agents.voice import VoiceWorkflowBase, VoiceWorkflowHelper


class MyWorkflow(VoiceWorkflowBase):
    def __init__(self, agent: Agent, callbacks: Callable[[str], None]):
        """Create a new single agent voice workflow.

        Args:
            agent: The agent to run.
            callbacks: Optional callbacks to call during the workflow.
        """
        self._input_history: list[TResponseInputItem] = []
        self._current_agent = agent
        self._callbacks = callbacks

    async def run(self, transcription: str) -> AsyncIterator[str]:
        if self._callbacks:
            self._callbacks(transcription)

        # Add the transcription to the input history
        self._input_history.append(
            {
                "role": "user",
                "content": transcription,
            }
        )

        result = Runner.run_streamed(self._current_agent, self._input_history)

        # Stream the text from the result
        async for chunk in VoiceWorkflowHelper.stream_text_from(result):
            yield chunk

        # Update the input history and current agent
        self._input_history = result.to_input_list()
        self._current_agent = result.last_agent
