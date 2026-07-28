from __future__ import annotations

from abc import ABC, abstractmethod

from adapter.schemas import AgentRunResult, BenchmarkTask


class FrameworkAdapter(ABC):
    framework_name: str

    @abstractmethod
    def run_task(self, task: BenchmarkTask) -> AgentRunResult:
        pass
