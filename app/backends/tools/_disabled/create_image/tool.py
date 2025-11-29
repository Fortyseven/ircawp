"""
Image creation tool - allows the LLM to generate images via media backend.

This tool enables the LLM to create images on demand using the configured
media generation backend.
"""

from ..ToolBase import tool, ToolResult
from pydantic import BaseModel, Field


class CreateImageInput(BaseModel):
    """Input schema for image creation."""

    prompt: str = Field(description="Detailed description of the image to generate")


@tool(
    name="create_image",
    description="Create an image for the user. Use this when you need to create, generate, or draw an image.",
    args_schema=CreateImageInput,
)
def create_image(
    prompt: str,
    backend=None,
    media_backend=None,
    console=None,
) -> ToolResult:
    # """
    # Generate an image using the media backend.

    # Args:
    #     prompt: Detailed description of the image to create
    #     style: Style or aesthetic for the image
    #     backend: Injected LLM backend for refining the prompt
    #     media_backend: Injected media generation backend
    #     console: Injected console for logging

    # Returns:
    #     ToolResult with confirmation text and path to generated image
    # """
    console.log(f"<TOOL:create_image> Generating image with prompt: '{prompt}'")

    if not media_backend:
        console.log("[red on cyan]<TOOL:create_image> No media backend available.")
        return ToolResult(
            text="Error: Image generation backend is not available.", images=[]
        )

    try:
        console.log(f"[black on cyan]<TOOL:create_image> Initial prompt: '{prompt}'")

        # Use the LLM to refine the prompt into a better image description
        # Similar to generateImageSummary() in ircawp.py
        refinement_request = f"Create a vivid, detailed image generation prompt based on this description:\n\n{prompt}\n\nProvide only the refined prompt, nothing else."

        refined_prompt, _ = backend.runInference(
            prompt=refinement_request,
            system_prompt="You are an expert at creating vivid image descriptions for AI image generation. Create detailed, visual prompts that capture mood, lighting, composition, and style.",
            use_tools=False,  # Prevent recursive tool calls
        )

        # Clean up the refined prompt
        refined_prompt = refined_prompt.strip()

        console.log(
            f"[yellow on cyan]<TOOL:create_image> Refined prompt: '{refined_prompt}'"
        )

        # Use refined prompt for image generation
        final_prompt = refined_prompt

        # Call media backend to generate the image
        image_path = media_backend.execute(prompt=final_prompt)

        if not image_path:
            console.log("[red on cyan]<TOOL:create_image> Image generation failed")
            return ToolResult(
                text="Error: Image generation failed - no image path returned.",
                images=[],
            )

        if console:
            console.log(
                f"[black on cyan]<TOOL:create_image> Image generated: {image_path}"
            )

        return ToolResult(
            text=f"(The `create_image` has created an image for the user using the prompt '{prompt}' and is including it with your response.).",
            images=[image_path],
        )

    except Exception as e:
        error_msg = f"Failed to generate image: {str(e)}"
        console.log(f"[red on cyan]<TOOL:create_image> {error_msg}")
        return ToolResult(text=error_msg, images=[])
