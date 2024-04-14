from typing import Optional


class BaseBackend:
    last_query_time = 0

    def __init__(self) -> None:
        pass

    def query(
        self,
        user_prompt: str,
        system_prompt: Optional[str],
        username: Optional[str],
        raw: Optional[bool] = False,
    ) -> tuple[str, str]:
        raise NotImplementedError("query() not implemented")
