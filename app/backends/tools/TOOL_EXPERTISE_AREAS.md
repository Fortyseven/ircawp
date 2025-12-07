# Tool Expertise Areas & Capability Matrix

## Overview

Tools can now optionally define their areas of expertise, which helps the LLM understand what each tool specializes in. This information is compiled into a **Capability Matrix** that's included in the system prompt, making tool selection more intelligent and reliable.

## How It Works

### 1. Define Expertise Areas in Tools

Each tool can specify its areas of expertise using the `expertise_areas` parameter:

```python
from ..ToolBase import tool

@tool(
    expertise_areas=["weather", "climate", "meteorology"]
)
def get_weather(location: str) -> str:
    """Get weather for a location."""
    # implementation
```

### 2. Automatic Matrix Generation

During initialization, the system:
- Collects expertise areas from all tools
- Builds a capability matrix showing which tools handle which areas
- Includes the matrix in the system prompt
- Logs the matrix for debugging

### 3. LLM Uses Matrix for Decision-Making

The LLM receives the capability matrix in the system prompt, enabling better tool selection. For example:

```
Tool Expertise Matrix:
────────────────────────────────────────────────
  arithmetic............................ calculator
  calculations......................... calculator
  climate.............................. get_weather
  knowledge............................. wikipedia
  mathematics.......................... calculator
  meteorology.......................... get_weather
────────────────────────────────────────────────
```

When the user asks "What's the capital of France?", the LLM sees that `wikipedia` handles "knowledge" and makes the right choice.

## Defining Expertise Areas

### Basic Usage

```python
@tool(expertise_areas=["mathematics", "calculations"])
def calculator(expression: str) -> str:
    """Evaluate math expressions."""
    return str(eval(expression))
```

### With Other Parameters

```python
from pydantic import BaseModel, Field

class WeatherInput(BaseModel):
    location: str = Field(description="City name")

@tool(
    name="get_weather",
    description="Get current weather for a location",
    args_schema=WeatherInput,
    expertise_areas=["weather", "climate", "temperature", "forecasting"]
)
def weather(location: str) -> str:
    """Get weather information."""
    return fetch_weather(location)
```

### With Class-Based Tools

Override the `expertise_areas` class attribute:

```python
from ..ToolBase import ToolBase, ToolResult

class MyCustomTool(ToolBase):
    name = "my_tool"
    description = "Does something useful"
    expertise_areas = ["domain1", "domain2", "domain3"]

    def execute(self, **kwargs) -> ToolResult:
        return ToolResult(text="result")
```

## Expertise Area Best Practices

### Choose Specific, Meaningful Areas

**Good:**
- `"mathematics"`, `"calculations"`, `"arithmetic"`
- `"weather"`, `"climate"`, `"temperature"`
- `"knowledge"`, `"facts"`, `"definitions"`, `"research"`

**Avoid:**
- Too generic: `"information"`, `"data"`
- Too vague: `"stuff"`, `"things"`
- Too specific: `"square-root-of-256"` (use category instead)

### Use Hyphens for Multi-Word Areas

```python
expertise_areas=[
    "weather",
    "domain-registration",  # hyphenated
    "network-diagnostics"   # hyphenated
]
```

### Cover Primary Use Cases

Think about all the things your tool can do:

```python
@tool(
    expertise_areas=[
        "networking",        # primary domain
        "connectivity",      # what it checks
        "diagnostics",       # what kind of info
        "latency",          # specific metric
        "availability",     # another key metric
    ]
)
def network_ping(domain_or_ip: str) -> str:
    """Ping a host to test connectivity."""
```

### Keep List Reasonable

Aim for 3-6 expertise areas per tool. Too many dilutes the signal.

## Examples

### Weather Tool
```python
@tool(
    expertise_areas=[
        "weather",
        "climate",
        "meteorology",
        "forecasting",
        "temperature"
    ]
)
def get_weather(location: str) -> str:
    """Get current weather for a location."""
```

### Calculator Tool
```python
@tool(
    expertise_areas=[
        "mathematics",
        "calculations",
        "arithmetic",
        "algebra"
    ]
)
def calculator(expression: str) -> str:
    """Evaluate a mathematical expression."""
```

### Wikipedia Tool
```python
@tool(
    expertise_areas=[
        "knowledge",
        "research",
        "facts",
        "definitions",
        "history",
        "biography",
        "general-information"
    ]
)
def wikipedia(topic: str) -> str:
    """Search Wikipedia for information."""
```

### Network Diagnostics Tool
```python
@tool(
    expertise_areas=[
        "networking",
        "connectivity",
        "diagnostics",
        "latency",
        "availability"
    ]
)
def network_ping(domain_or_ip: str) -> str:
    """Ping to test connectivity and latency."""
```

### Domain Information Tool
```python
@tool(
    expertise_areas=[
        "domain-information",
        "dns",
        "registration",
        "network-data",
        "web-infrastructure"
    ]
)
def network_whois(domain: str) -> str:
    """Look up domain registration details."""
```

## How It Improves Tool Calling

### Before (Without Expertise Areas)
```
User: "Tell me about the weather in Paris"
LLM: [decides between tools using only descriptions]
     ❓ Less reliable selection
```

### After (With Expertise Areas)
```
User: "Tell me about the weather in Paris"
LLM: [sees capability matrix: weather → get_weather]
     [sees capability matrix: knowledge → wikipedia]
     ✅ Clear choice: get_weather is for "weather"
```

## Capability Matrix in System Prompt

The matrix is automatically added to the system prompt when tools are enabled:

```
Tool Expertise Matrix:
────────────────────────────────────────────────────────────
  algebra........................... calculator, advanced_calculator
  arithmetic......................... calculator
  availability....................... network_ping
  biography.......................... wikipedia
  calculations....................... calculator, advanced_calculator
  climate........................... get_weather
  connectivity....................... network_ping
  definitions........................ wikipedia
  diagnostics........................ network_ping
  dns............................... network_whois
  domain-information................. network_whois
  facts............................. wikipedia
  forecasting........................ get_weather
  general-information................ wikipedia
  history........................... wikipedia
  knowledge.......................... wikipedia
  latency........................... network_ping
  mathematics........................ calculator, advanced_calculator
  meteorology........................ get_weather
  network-data....................... network_whois
  networking......................... network_ping
  precision-math..................... advanced_calculator
  registration....................... network_whois
  research........................... wikipedia
  temperature........................ get_weather
  web-infrastructure................. network_whois
────────────────────────────────────────────────────────────
```

## Debugging Expertise Areas

### View the Matrix During Initialization

When your app starts, watch for the capability matrix in logs:

```
[cyan]Initializing tools with schema validation...
- [green]Registered tool: calculator
- [green]Registered tool: get_weather
- [green]Registered tool: wikipedia
- [green]Registered tool: network_ping
- [green]Registered tool: network_whois

Tool Expertise Matrix:
────────────────────────────────────────────────────────────
  arithmetic........................ calculator
  calculations........................ calculator
  ...
────────────────────────────────────────────────────────────
```

### Check Tool Expertise Programmatically

```python
from app.backends.tools_manager import ToolManager

# Get expertise areas for a tool
tool = tool_manager.available_tools['calculator']
areas = tool.get_expertise_areas()
print(f"Calculator expertise: {areas}")
# Output: Calculator expertise: ['mathematics', 'calculations', 'arithmetic', 'algebra']
```

### Get Full Capability Matrix

```python
matrix = tool_manager.get_capability_matrix()
print(matrix)
```

## Implementation Details

### How It's Used in Inference

1. **Tool initialization** - Expertise areas collected from all tools
2. **System prompt construction** - Matrix added to system prompt
3. **LLM receives prompt** - LLM sees which tools do what
4. **Better tool selection** - LLM uses matrix to make smarter choices

### Backward Compatibility

- **Tools without expertise areas** - Still work fine, just won't appear in matrix
- **Existing code** - No changes required to continue using tools
- **Optional feature** - Expertise areas are optional but recommended

## Best Practices Checklist

- [ ] Each tool has 3-6 expertise areas
- [ ] Expertise areas are specific and meaningful
- [ ] Multi-word areas use hyphens
- [ ] Areas match what users would think of
- [ ] No overlapping tools for the same area (unless intentional)
- [ ] Expertise areas documented in tool file
- [ ] Matrix is visible in initialization logs
- [ ] Tool selection is more reliable with matrix present

---

**Created:** December 6, 2025
**Status:** Implemented and active in all tools
