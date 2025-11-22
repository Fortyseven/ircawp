from typing import Any


Aux = dict[str, Any]
# MediaResponse = tuple[str, set[str]]
MediaResponse = str
InfResponse = tuple[str, MediaResponse, bool]
