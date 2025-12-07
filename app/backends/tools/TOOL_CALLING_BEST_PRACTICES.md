# Tool Calling Best Practices

This guide outlines how to write tools that LLMs will reliably call and use effectively.

## System-Level Improvements

The framework now includes several enhancements to improve tool-calling consistency:

### 1. Enhanced Tool Rules
- **Clear imperative language**: "You MUST call tools when..." instead of "You may use tools"
- **Explicit decision framework**: Tells the LLM exactly when to use each tool type
- **Error handling emphasis**: Ensures failures are reported to users
- **Temperature control**: Tool calls use temperature=0.1 for deterministic behavior

### 2. Schema Validation
- All tool schemas are validated during initialization
- Warnings logged for missing or incomplete descriptions
- Parameter descriptions are extracted automatically from docstrings

### 3. Low-Temperature Tool Calls
- Tool-calling requests use temperature=0.1 to ensure consistent, deterministic responses
- Regular responses can use higher temperature for creativity

## Best Practices for Tool Implementation

### 1. Clear, Specific Descriptions

**Bad:**
```python
@tool
def weather(location: str) -> str:
    """Get weather info."""
    ...
```

**Good:**
```python
@tool(description="Get current weather conditions for a specific location. Returns temperature, conditions, and forecast.")
def weather(location: str) -> str:
    """Get current weather for a location."""
    ...
```

### 2. Document All Parameters with Descriptions

**Bad:**
```python
class WeatherInput(BaseModel):
    location: str
    units: str
```

**Good:**
```python
class WeatherInput(BaseModel):
    location: str = Field(description="City name or coordinates (e.g., 'San Francisco', '40.7128,-74.0060')")
    units: str = Field(
        default="celsius",
        description="Temperature units: 'celsius', 'fahrenheit', or 'kelvin'"
    )
```

### 3. Use Google-Style Docstrings for Auto-Extraction

The framework automatically extracts parameter descriptions from docstrings:

```python
@tool
def calculator(expression: str) -> str:
    """
    Evaluate a mathematical expression and return the result.

    Args:
        expression: A mathematical expression to evaluate (e.g., "2 + 2", "10 * 5", "sqrt(16)")
    """
    ...
```

### 4. Provide Action-Oriented Names

- ✅ Good: `get_weather`, `search_news`, `calculate`, `translate`
- ❌ Bad: `weather`, `news`, `calc`, `trans`

### 5. Clear Return Values

Always return meaningful, informative results:

**Bad:**
```python
return "done"
```

**Good:**
```python
return f"Weather in {location}: 72°F, Partly Cloudy. Humidity: 65%"
```

### 6. Use Pydantic for Complex Inputs

For tools with multiple parameters or when you need validation:

```python
from pydantic import BaseModel, Field

class SearchInput(BaseModel):
    query: str = Field(description="Search query")
    max_results: int = Field(default=5, description="Maximum number of results to return")
    language: str = Field(default="en", description="Language code (e.g., 'en', 'es', 'fr')")

@tool(
    name="search",
    description="Search for information using a web search engine",
    args_schema=SearchInput
)
def search_web(query: str, max_results: int = 5, language: str = "en") -> str:
    """Search the web and return relevant results."""
    ...
```

### 7. Include Context in Descriptions

Help the LLM understand when to use each tool:

**Without context:**
```python
@tool
def translate(text: str, language: str) -> str:
    """Translate text to another language."""
    ...
```

**With context:**
```python
@tool(
    description="Translate text from one language to another. Use this when the user explicitly asks for translation or when responding in a different language is needed."
)
def translate(text: str, language: str) -> str:
    """Translate text to another language."""
    ...
```

### 8. Handle Errors Gracefully

Return clear error messages that help the LLM understand what went wrong:

**Bad:**
```python
try:
    result = some_operation()
except Exception as e:
    return "error"
```

**Good:**
```python
try:
    result = some_operation()
except FileNotFoundError:
    return "Error: Location data file not found. Unable to provide weather information."
except ConnectionError:
    return "Error: Unable to connect to weather service. Please try again later."
except Exception as e:
    return f"Error: {type(e).__name__}: {str(e)}"
```

## Example: Well-Designed Tool

```python
from pydantic import BaseModel, Field
from ..ToolBase import tool

class WikipediaInput(BaseModel):
    query: str = Field(description="Search query or topic name (e.g., 'Albert Einstein', 'Global Warming')")
    max_length: int = Field(
        default=500,
        description="Maximum length of the summary in characters"
    )

@tool(
    name="wikipedia_search",
    description="Search Wikipedia for information about a topic. Returns a summary of the most relevant article.",
    args_schema=WikipediaInput
)
def wikipedia_search(query: str, max_length: int = 500) -> str:
    """
    Search Wikipedia and return a summary of the most relevant article.

    Args:
        query: The search query (e.g., 'Albert Einstein', 'Global Warming')
        max_length: Maximum character length of the returned summary
    """
    try:
        import wikipedia

        # Search for the query
        results = wikipedia.search(query, results=3)
        if not results:
            return f"No Wikipedia articles found for '{query}'"

        # Get the summary of the first result
        summary = wikipedia.summary(results[0], sentences=5)

        # Trim if needed
        if len(summary) > max_length:
            summary = summary[:max_length] + "..."

        return f"Wikipedia: {results[0]}\n\n{summary}"
    except wikipedia.exceptions.DisambiguationError as e:
        return f"Disambiguation: '{query}' could refer to: {', '.join(e.options[:5])}"
    except wikipedia.exceptions.PageError:
        return f"Error: Page for '{query}' not found on Wikipedia"
    except Exception as e:
        return f"Error: {type(e).__name__}: {str(e)}"
```

## Monitoring and Debugging

The system provides detailed logging during tool initialization:

```
[cyan]Initializing tools with schema validation...
- [green]Registered tool: calculator
- [green]Registered tool: weather
- [yellow]Registered tool (schema warnings): wikipedia_search
  - [yellow]  - wikipedia_search.query: Missing parameter description
```

Address any warnings shown during initialization to improve tool reliability.

## Model-Specific Tips

### GPT-4o (Recommended)
- Very reliable at tool calling
- Respects temperature settings
- Works well with detailed descriptions

### Claude 3.5 Sonnet
- Excellent tool support
- Prefers imperative language in system prompts
- Benefits from explicit "when to use this tool" guidance

### Smaller Models (Llama, Mistral)
- More inconsistent tool calling
- Benefits from fewer, more focused tools
- Simpler tool descriptions work better
- Consider reducing tool count

## Common Issues and Solutions

| Issue | Cause | Solution |
|-------|-------|----------|
| Model rarely calls tools | Vague descriptions | Use specific, action-oriented descriptions |
| Wrong tool called | Overlapping descriptions | Make tool purposes distinct and clear |
| Missing parameters | No parameter descriptions | Add detailed parameter docs |
| Tool calls fail | Poor error handling | Return informative error messages |
| Inconsistent calling | High temperature during tool calls | Already fixed - uses temp=0.1 |

## Validation Checklist

Before deploying a new tool:

- [ ] Tool name is specific and action-oriented
- [ ] Tool description is at least 2-3 sentences
- [ ] All parameters have descriptions (even if using Pydantic)
- [ ] Tool description includes "when to use" guidance
- [ ] Tool returns informative results
- [ ] Errors are handled and clearly communicated
- [ ] No schema warnings during initialization
- [ ] Tool tested with actual LLM calls
