from abc import ABC, abstractmethod

class Agent(ABC):
    def __init__(self):
        pass

    @abstractmethod
    def _build_prompt(self, *args, **kwargs) -> str:
        raise NotImplementedError

    @abstractmethod
    async def run(self, prompt: str):
        raise NotImplementedError