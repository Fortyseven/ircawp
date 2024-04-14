class BaseBackend:
    last_query_time = 0

    def __init__(self) -> None:
        pass

    def query(self, user_prompt: str, system_prompt: str) -> str:
        raise NotImplementedError("query() not implemented")
