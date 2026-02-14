import re
from typing import Any, Dict, Iterable, List, Tuple


ArgumentSpec = Dict[str, Any]


def _build_patterns(names: Iterable[str], is_flag: bool = False) -> List[str]:
    patterns: List[str] = []
    for name in names:
        escaped = re.escape(name)
        if is_flag:
            # For boolean flags, only match the flag itself
            patterns.append(rf"{escaped}\b")
        else:
            # For value arguments, match various forms
            # --arg value
            patterns.append(rf"{escaped}\s+(\S+)")
            # --arg=value
            patterns.append(rf"{escaped}=(\S+)")
            # --arg (fallback to treat as flag)
            patterns.append(rf"{escaped}\b")
    return patterns


def help_arguments(arg_specs: Dict[str, ArgumentSpec]) -> str:
    help_text = "Available subcommands:\n"

    for arg, spec in arg_specs.items():
        names = ", ".join(f"`{name}`" for name in spec["names"])
        description = spec["description"]
        help_text += f"{names}: {description}\n"

    return help_text.strip()


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
        # Check if this is a boolean flag
        is_flag = spec.get("type") == bool
        for pattern in _build_patterns(names, is_flag):
            compiled.append((re.compile(pattern, re.IGNORECASE), logical_name, spec))

    for regex, logical_name, spec in compiled:
        matches = list(regex.finditer(cleaned_prompt))
        if not matches:
            continue

        # Check if the pattern has a capturing group (value) or is just a flag
        last_match = matches[-1]
        if last_match.lastindex == 1:
            value = last_match.group(1)
            caster = spec.get("type", str)
            try:
                cast_value = caster(value)
            except Exception:
                cast_value = value
            config[logical_name] = cast_value
        else:
            # No value group: treat as boolean flag
            config[logical_name] = True

        for match in reversed(matches):
            cleaned_prompt = (
                cleaned_prompt[: match.start()] + cleaned_prompt[match.end() :]
            )

    cleaned_prompt = " ".join(cleaned_prompt.split())
    return cleaned_prompt.strip(), config
