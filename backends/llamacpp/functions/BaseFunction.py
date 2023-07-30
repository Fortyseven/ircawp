from backends import BaseBackend


class BaseFunction:
    def execute(self, query: str, backend: BaseBackend) -> str:
        raise NotImplementedError("execute() not implemented")
