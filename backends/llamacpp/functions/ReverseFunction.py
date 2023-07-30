from backends import BaseBackend
from backends.llamacpp.functions import BaseFunction


class ReverseFunction(BaseFunction.BaseFunction):
    def execute(self, query: str, backend: BaseBackend) -> str:
        if not query:
            return "No query provided for summary function"

        return query[::-1]
