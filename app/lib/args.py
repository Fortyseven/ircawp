import re
from typing import Any, Dict, Iterable, List, Tuple


ArgumentSpec = Dict[str, Any]


def _build_patterns(names: Iterable[str]) -> List[str]:
    patterns: List[str] = []
    for name in names:
        escaped = re.escape(name)
        # --arg value
        patterns.append(rf"{escaped}\s+(\S+)")
        # --arg=value
        patterns.append(rf"{escaped}=(\S+)")
    return patterns


def parse_arguments(
    prompt: str,
    arg_specs: Dict[str, ArgumentSpec],
) -> Tuple[str, Dict[str, Any]]:
    """Generic parser for command-line-style arguments embedded in a prompt.

    `arg_specs` is a mapping of logical option name -> spec dict with:
      - "names": iterable of flag strings (e.g. ["--aspect"]) required
      - "type": callable to cast value (default: str)

    Returns (cleaned_prompt, config_dict).
    """

    config: Dict[str, Any] = {}
    cleaned_prompt = prompt

    compiled: List[Tuple[re.Pattern[str], str, ArgumentSpec]] = []
    for logical_name, spec in arg_specs.items():
        names = spec.get("names") or []
        if not names:
            continue
        for pattern in _build_patterns(names):
            compiled.append((re.compile(pattern, re.IGNORECASE), logical_name, spec))

    for regex, logical_name, spec in compiled:
        matches = list(regex.finditer(cleaned_prompt))
        if not matches:
            continue

        value = matches[-1].group(1)
        caster = spec.get("type", str)
        try:
            cast_value = caster(value)
        except Exception:
            cast_value = value

        config[logical_name] = cast_value

        for match in reversed(matches):
            cleaned_prompt = (
                cleaned_prompt[: match.start()] + cleaned_prompt[match.end() :]
            )

    cleaned_prompt = " ".join(cleaned_prompt.split())
    return cleaned_prompt.strip(), config
