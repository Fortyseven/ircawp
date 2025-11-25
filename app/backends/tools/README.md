# Tool Calling System

The tool calling system allows LLMs to extend their capabilities by calling external functions, APIs, or data sources during inference.

## Architecture

### Structure

```
app/backends/tools/
├── __init__.py           # Tool discovery and registration
├── ToolBase.py           # Base class for all tools
└── example/              # Example tool implementation
    ├── __init__.py
    └── tool.py
```

### Components

#### ToolBase
Base class that all tools must inherit from. Provides:
- Access to the LLM backend (for making additional inferences)
- Access to the media backend (for image generation)
- Console for logging
- Abstract `execute()` method for tool logic
- `get_schema()` method for OpenAI function calling schema

#### ToolResult
Data class for tool execution results containing:
- `text`: String content to return to the LLM
- `images`: List of image paths (local files or URLs) to include in the response

## Creating a New Tool

### 1. Create Tool Directory

Create a new subdirectory under `app/backends/tools/`:

```bash
mkdir -p app/backends/tools/my_tool
```

### 2. Implement Tool Class

Create `tool.py` in your tool directory:

```python
from ..ToolBase import ToolBase, ToolResult
from typing import Any, Dict


class MyTool(ToolBase):
    """Description of what your tool does."""

    name = "my_tool"
    description = "A clear description for the LLM to understand when to use this tool"

    def execute(self, **kwargs) -> ToolResult:
        """
        Execute your tool logic.

        Args:
            param1: Description of parameter 1
            param2: Description of parameter 2

        Returns:
            ToolResult with text and/or images
        """
        param1 = kwargs.get("param1", "default")
        param2 = kwargs.get("param2", 0)

        self.log(f"Executing with param1={param1}, param2={param2}")

        # Your tool logic here
        result_text = f"Processed {param1} with value {param2}"
        result_images = []  # Optional: list of image paths

        return ToolResult(text=result_text, images=result_images)

    def get_schema(self) -> Dict[str, Any]:
        """Define the OpenAI function schema for this tool."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "param1": {
                            "type": "string",
                            "description": "Description of parameter 1"
                        },
                        "param2": {
                            "type": "number",
                            "description": "Description of parameter 2"
                        }
                    },
                    "required": ["param1"]  # List required parameters
                }
            }
        }
```

### 3. Add __init__.py

Create `__init__.py` in your tool directory:

```python
"""My tool submodule."""
```

### 4. Tool Auto-Discovery

Tools are automatically discovered on import. No registration needed!

## Using Tools in Code

### Enable/Disable Tools Globally

In `config.json`:

```json
{
  "openai": {
    "api_url": "https://api.openai.com",
    "api_key": "your-key",
    "model": "gpt-4",
    "tools_enabled": true
  }
}
```

### Bypass Tools for Specific Inference

```python
# With tools (default)
response = backend.runInference(
    prompt="What's the weather like?",
    use_tools=True
)

# Without tools
response = backend.runInference(
    prompt="Just respond directly",
    use_tools=False
)
```

## Tool Capabilities

### Accessing Backend Services

Tools have access to:

```python
self.backend         # The LLM backend - make additional inferences
self.media_backend   # Media generation backend - create images
self.console         # Rich console for logging
```

Example using backend:

```python
def execute(self, **kwargs):
    # Make an additional LLM call
    summary = self.backend.runInference(
        prompt="Summarize this: " + kwargs.get("text"),
        use_tools=False  # Don't recurse into tools
    )
    return ToolResult(text=summary)
```

### Returning Images

Tools can return images by providing file paths:

```python
def execute(self, **kwargs):
    # Generate or locate an image
    image_path = "/path/to/generated/image.png"

    return ToolResult(
        text="Here's the image you requested",
        images=[image_path]
    )
```

Images are automatically converted to data URIs and included in the conversation.

### Error Handling

Tool execution errors are caught and returned as error messages to the LLM:

```python
def execute(self, **kwargs):
    try:
        # Your logic here
        result = do_something()
        return ToolResult(text=str(result))
    except Exception as e:
        # Error automatically logged and returned to LLM
        raise
```

## How It Works

1. **Tool Discovery**: On backend initialization, all tools in `app/backends/tools/*/tool.py` are discovered and instantiated
2. **Schema Generation**: Each tool's `get_schema()` method provides its OpenAI function definition
3. **Inference**: When `runInference()` is called with `use_tools=True`:
   - Tool schemas are passed to the LLM
   - If LLM decides to call a tool, the function name and arguments are extracted
   - Tool is executed with the provided arguments
   - Tool result (text + images) is added to the conversation
   - A second LLM call is made with the tool results
   - Final response is returned
4. **Bypass**: Setting `use_tools=False` skips all tool logic

## Best Practices

1. **Clear Descriptions**: Write detailed descriptions in `get_schema()` so the LLM knows when to use your tool
2. **Parameter Validation**: Validate parameters in `execute()` and provide sensible defaults
3. **Logging**: Use `self.log()` to track tool execution for debugging
4. **Error Messages**: Return helpful error messages in ToolResult when things go wrong
5. **Avoid Recursion**: When calling `backend.runInference()` from a tool, set `use_tools=False`
6. **Test Independently**: Test tool logic separately before integrating with LLM

## Example: Weather Tool

```python
from ..ToolBase import ToolBase, ToolResult
import requests


class WeatherTool(ToolBase):
    name = "get_weather"
    description = "Get current weather for a location"

    def execute(self, **kwargs) -> ToolResult:
        location = kwargs.get("location")
        if not location:
            return ToolResult(text="Error: location parameter required")

        self.log(f"Fetching weather for {location}")

        # Call weather API (example)
        # response = requests.get(f"https://api.weather.com/?q={location}")
        # data = response.json()

        # Mock result
        weather_text = f"The weather in {location} is sunny, 72°F"

        return ToolResult(text=weather_text)

    def get_schema(self):
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "location": {
                            "type": "string",
                            "description": "City name or zip code"
                        }
                    },
                    "required": ["location"]
                }
            }
        }
```
