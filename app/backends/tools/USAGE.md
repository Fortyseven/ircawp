# Tool System - LangChain-Style Implementation

The tool system now mimics LangChain's decorator-based approach, supporting both `@tool` decorator and class-based tool definitions.

## Quick Start

### Decorator-Based Tool (Recommended)

```python
from app.backends.tools import tool

@tool
def search_database(query: str, limit: int = 10) -> str:
    """
    Search the customer database for records matching the query.

    Args:
        query: Search terms to look for
        limit: Maximum number of results to return
    """
    return f"Found {limit} results for '{query}'"
```

### With Pydantic Schema

```python
from app.backends.tools import tool
from pydantic import BaseModel, Field

class WeatherInput(BaseModel):
    """Input for weather queries."""
    location: str = Field(description="City name or coordinates")
    units: str = Field(default="celsius", description="Temperature unit")
    include_forecast: bool = Field(default=False, description="Include 5-day forecast")

@tool(args_schema=WeatherInput)
def get_weather(location: str, units: str = "celsius", include_forecast: bool = False) -> str:
    """Get current weather and optional forecast."""
    temp = 22 if units == "celsius" else 72
    result = f"Weather in {location}: {temp}°{units[0].upper()}"
    if include_forecast:
        result += "\nNext 5 days: Sunny"
    return result
```

### Class-Based Tool (Legacy)

```python
from app.backends.tools import ToolBase, ToolResult

class MyTool(ToolBase):
    name = "my_tool"
    description = "Description for the LLM"

    def execute(self, **kwargs) -> ToolResult:
        param = kwargs.get("param", "default")
        return ToolResult(text=f"Result: {param}")

    def get_schema(self):
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "param": {"type": "string", "description": "Parameter description"}
                    },
                    "required": ["param"]
                }
            }
        }
```

## Tool Features

### Type Hints as Schema

Type hints automatically generate the tool schema:

```python
@tool
def calculate(x: int, y: int, operation: str = "add") -> str:
    """Perform arithmetic operations."""
    if operation == "add":
        return str(x + y)
    elif operation == "multiply":
        return str(x * y)
    return "Unknown operation"
```

### Custom Names and Descriptions

```python
@tool(name="web_search", description="Search the web for information")
def search(query: str) -> str:
    """This docstring is overridden by the description parameter."""
    return f"Results for: {query}"
```

### Accessing Backend Services

Tools can access the LLM backend and media backend:

```python
@tool
def summarize_with_ai(text: str, backend=None) -> str:
    """Summarize text using the LLM."""
    if backend:
        return backend.runInference(
            prompt=f"Summarize: {text}",
            use_tools=False  # Prevent recursion
        )
    return "Backend not available"
```

### Returning Images

```python
from app.backends.tools import ToolResult

@tool
def generate_chart(data: str) -> ToolResult:
    """Generate a chart from data."""
    chart_path = "/path/to/generated/chart.png"
    return ToolResult(
        text="Chart generated successfully",
        images=[chart_path]
    )
```

## Project Structure

```
app/backends/tools/
├── __init__.py              # Auto-discovery and exports
├── ToolBase.py              # Base classes and @tool decorator
├── weather/                 # Class-based tool example
│   ├── __init__.py
│   └── tool.py
└── calculator/              # Decorator-based tool example
    ├── __init__.py
    └── tool.py
```

## Creating a New Tool

### 1. Create Directory

```bash
mkdir -p app/backends/tools/my_tool
```

### 2. Create `tool.py`

```python
# app/backends/tools/my_tool/tool.py
from ..ToolBase import tool
from pydantic import BaseModel, Field

class MyInput(BaseModel):
    query: str = Field(description="Search query")
    max_results: int = Field(default=10, description="Maximum results")

@tool(args_schema=MyInput)
def my_tool(query: str, max_results: int = 10) -> str:
    """Search for items matching the query."""
    return f"Found {max_results} results for '{query}'"
```

### 3. Create `__init__.py`

```python
# app/backends/tools/my_tool/__init__.py
"""My tool submodule."""
```

### 4. Done!

Tools are automatically discovered on import. No registration needed!

## Usage in Code

### Enable/Disable Tools

In `config.json`:

```json
{
  "openai": {
    "tools_enabled": true
  }
}
```

### Use Tools in Inference

```python
# With tools (default)
response = backend.runInference(
    prompt="What's 25 * 17?",
    use_tools=True
)

# Without tools
response = backend.runInference(
    prompt="Just answer directly",
    use_tools=False
)
```

## Comparison with LangChain

| Feature | LangChain | This Implementation |
|---------|-----------|---------------------|
| `@tool` decorator | ✅ | ✅ |
| Pydantic schemas | ✅ | ✅ |
| Type hint inference | ✅ | ✅ |
| Custom names/descriptions | ✅ | ✅ |
| Auto-discovery | ❌ (manual registration) | ✅ |
| Backend injection | Via ToolRuntime | Via parameters |
| Return types | String or dict | ToolResult (text + images) |

## Best Practices

1. **Use `@tool` for new tools** - Cleaner and more Pythonic
2. **Provide good docstrings** - They become the tool description
3. **Use type hints** - They generate the input schema
4. **Use Pydantic for complex inputs** - Better validation and documentation
5. **Return ToolResult for images** - Supports multimodal responses
6. **Set `use_tools=False`** when calling backend from within a tool to prevent recursion

## Examples

See the included tools for examples:
- `weather/` - Class-based tool with external API calls
- `calculator/` - Decorator-based tool with Pydantic schemas
- `example/` - Simple class-based tool

## Migration from Class-Based to Decorator-Based

Before:
```python
class MyTool(ToolBase):
    name = "search"
    description = "Search for items"

    def execute(self, query: str) -> ToolResult:
        return ToolResult(text=f"Results for {query}")

    def get_schema(self):
        return {...}  # Complex schema definition
```

After:
```python
@tool
def search(query: str) -> str:
    """Search for items."""
    return f"Results for {query}"
```

Much simpler! 🎉
