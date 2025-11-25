"""
Decorator-based calculator tool example.

Demonstrates LangChain-style tool definition using the @tool decorator.
"""

from ..ToolBase import tool
from pydantic import BaseModel, Field


# Simple decorator usage - description from docstring
@tool
def calculator(expression: str) -> str:
    """
    Evaluate a mathematical expression.

    Args:
        expression: A mathematical expression to evaluate (e.g., "2 + 2", "10 * 5")
    """
    try:
        # Note: eval() is used here for simplicity. In production, use a safer alternative
        result = eval(expression, {"__builtins__": {}}, {})
        return f"Result: {result}"
    except Exception as e:
        return f"Error evaluating expression: {str(e)}"


# Advanced usage with Pydantic schema
class CalculatorInput(BaseModel):
    """Input schema for advanced calculator."""

    expression: str = Field(description="Mathematical expression to evaluate")
    precision: int = Field(default=2, description="Number of decimal places for result")


@tool(
    name="advanced_calculator",
    description="Evaluate mathematical expressions with custom precision",
    args_schema=CalculatorInput,
)
def advanced_calc(expression: str, precision: int = 2) -> str:
    """Advanced calculator with precision control."""
    try:
        result = eval(expression, {"__builtins__": {}}, {})
        if isinstance(result, float):
            result = round(result, precision)
        return f"Result: {result}"
    except Exception as e:
        return f"Error: {str(e)}"
