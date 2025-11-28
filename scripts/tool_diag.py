#!/usr/bin/env python
"""
Tool diagnostics CLI.

Allows manual listing, describing, and invoking of registered LLM tools
outside of the agent runtime.

Usage examples:
  python scripts/tool_diag.py list
  python scripts/tool_diag.py describe create_image
  python scripts/tool_diag.py invoke get_weather --arg location=Tokyo
  python scripts/tool_diag.py invoke advanced_calculator --arg expression="2+2*5" --arg precision=4
  python scripts/tool_diag.py invoke create_image --arg prompt="sunset over mountains" --arg style=cinematic

You can also pass JSON args:
  python scripts/tool_diag.py invoke create_image --json '{"prompt":"cityscape","style":"cyberpunk"}'

Flags:
  --no-backend    Invoke tool without backend injection (skips LLM refinement)
  --raw           Output only raw tool text result (no formatting)
  --config PATH   Use alternate config file (default: config.json)
"""

from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path
from typing import Any
from rich.console import Console
from rich.table import Table
from rich import print

# Project imports
sys.path.append(str(Path(__file__).resolve().parent.parent))  # add repo root (../)

from app.lib.config import config as global_config  # type: ignore
from app.backends.openai import Openai
from app.backends.Ircawp_Backend import Ircawp_Backend
from app.backends.tools import get_all_tools

console = Console()


def load_config(path: str | None) -> dict:
    if not path:
        return global_config
    p = Path(path)
    if not p.is_file():
        console.print(f"[red]Config file not found: {path}")
        sys.exit(2)
    try:
        return json.loads(p.read_text())
    except Exception as e:
        console.print(f"[red]Failed to read config: {e}")
        sys.exit(2)


def instantiate_backend(cfg: dict, use_backend: bool) -> Ircawp_Backend | None:
    if not use_backend:
        return None
    backend_id = cfg.get("backend", "openai")
    if backend_id != "openai":
        console.print(
            "[yellow]Only 'openai' backend supported for refinement; using none"
        )
        return None
    try:
        backend = Openai(console=console, parent=None, config=cfg)
        # If imagegen configured, attach it (mimic ircawp.py logic)
        imagegen_id = cfg.get("imagegen_backend")
        if imagegen_id:
            try:
                mod = __import__(
                    f"app.media_backends.{imagegen_id}", fromlist=[imagegen_id]
                )
                imagegen_cls = getattr(mod, imagegen_id)
                backend.update_media_backend(imagegen_cls(backend))  # type: ignore
            except Exception as e:
                console.print(
                    f"[yellow]Failed to setup media backend '{imagegen_id}': {e}"
                )
        return backend
    except Exception as e:
        console.print(f"[red]Failed to instantiate backend: {e}")
        return None


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="LLM tool diagnostics CLI")
    sub = p.add_subparsers(dest="command", required=True)

    # list
    sub.add_parser("list", help="List registered tools")

    # describe
    sp_desc = sub.add_parser("describe", help="Show schema/details for a tool")
    sp_desc.add_argument("name", help="Tool name")

    # invoke
    sp_inv = sub.add_parser("invoke", help="Invoke a tool manually")
    sp_inv.add_argument("name", help="Tool name to invoke")
    sp_inv.add_argument(
        "--arg", action="append", default=[], help="Key=Value argument (repeatable)"
    )
    sp_inv.add_argument("--json", help="Raw JSON object of arguments", default=None)
    sp_inv.add_argument(
        "--no-backend",
        action="store_true",
        help="Do not inject backend (skip LLM refinement)",
    )
    sp_inv.add_argument(
        "--raw", action="store_true", help="Print only tool text output"
    )

    p.add_argument("--config", help="Alternate config file path", default=None)

    return p


def parse_args_to_kwargs(arg_list: list[str], json_blob: str | None) -> dict[str, Any]:
    kwargs: dict[str, Any] = {}
    if json_blob:
        try:
            parsed = json.loads(json_blob)
            if not isinstance(parsed, dict):
                raise ValueError("JSON must be an object")
            kwargs.update(parsed)
        except Exception as e:
            console.print(f"[red]Invalid JSON arguments: {e}")
            sys.exit(2)
    for kv in arg_list:
        if "=" not in kv:
            console.print(
                f"[yellow]Ignoring malformed --arg '{kv}' (expected key=value)"
            )
            continue
        k, v = kv.split("=", 1)
        kwargs[k.strip()] = v.strip()
    return kwargs


def list_command():
    tools = get_all_tools()
    if not tools:
        console.print("[yellow]No tools registered.")
        return
    table = Table(title="Registered Tools")
    table.add_column("Name", style="cyan")
    table.add_column("Description", style="green")
    table.add_column("Parameters", style="magenta")
    for name, factory in tools.items():
        try:
            # Create ephemeral instance (no backend/media)
            inst = factory(backend=None, media_backend=None, console=console)
            schema = inst.get_schema().get("function", {})
            params = schema.get("parameters", {}).get("properties", {})
            param_list = ", ".join(params.keys()) or "(none)"
            table.add_row(
                name, getattr(inst, "description", "(no description)"), param_list
            )
        except Exception as e:
            table.add_row(name, f"Error: {e}", "?")
    console.print(table)


def describe_command(name: str):
    tools = get_all_tools()
    factory = tools.get(name)
    if not factory:
        console.print(f"[red]Tool not found: {name}")
        sys.exit(1)
    inst = factory(backend=None, media_backend=None, console=console)
    schema = inst.get_schema().get("function", {})
    console.print(f"[bold cyan]{name}")
    console.print(f"Description: {getattr(inst, 'description', '(no description)')}")
    console.print("Schema:")
    console.print(json.dumps(schema, indent=2))


def invoke_command(
    name: str, kwargs: dict[str, Any], use_backend: bool, raw: bool, cfg: dict
):
    tools = get_all_tools()
    factory = tools.get(name)
    if not factory:
        console.print(f"[red]Tool not found: {name}")
        sys.exit(1)

    backend = instantiate_backend(cfg, use_backend)

    # Instantiate tool with backend + media backend if available
    media_backend = getattr(backend, "media_backend", None) if backend else None
    inst = factory(backend=backend, media_backend=media_backend, console=console)

    # Pydantic args schema validation (if decorator-based tool with schema)
    if hasattr(inst, "args_schema") and inst.args_schema is not None:
        try:
            model = inst.args_schema(**kwargs)  # type: ignore
            kwargs = model.model_dump()
        except Exception as e:
            console.print(f"[red]Argument validation failed: {e}")
            sys.exit(2)

    result = inst.execute(**kwargs)

    if raw:
        print(result.text)
        return

    console.rule(f"Tool Result: {name}")
    console.print(f"[bold]Text:[/bold]\n{result.text or '(no text)'}")
    if result.images:
        console.print(f"[bold]Images ({len(result.images)}):[/bold]")
        for img in result.images:
            console.print(f"  • {img}")
    else:
        console.print("[bold]Images:[/bold] (none)")
    console.rule()


def main():
    parser = build_arg_parser()
    args = parser.parse_args()
    cfg = load_config(args.config)

    match args.command:
        case "list":
            list_command()
        case "describe":
            describe_command(args.name)
        case "invoke":
            kwargs = parse_args_to_kwargs(args.arg, args.json)
            invoke_command(args.name, kwargs, not args.no_backend, args.raw, cfg)
        case _:
            console.print(f"[red]Unknown command: {args.command}")
            sys.exit(1)


if __name__ == "__main__":
    main()
