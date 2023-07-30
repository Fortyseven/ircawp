from backends import BaseBackend
from backends.llamacpp.functions import BaseFunction


class HelpFunction(BaseFunction.BaseFunction):
    def execute(self, query: str, backend: BaseBackend) -> str:
        from backends.llamacpp.functions import FUNCTIONS  # lazy load

        return "AVAILABLE SLASH COMMANDS :\n\n" + "\n".join(
            [
                f'- `/{x["name"]}` - {x["description"]}'
                for x in FUNCTIONS
                if not x.get("hide", False)
            ]
        )
