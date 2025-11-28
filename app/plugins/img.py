"""
Bot plugin that allows the user to pass a raw prompt to the system imagegen backend and post a response.
"""

from app.backends.Ircawp_Backend import Ircawp_Backend
from app.media_backends.MediaBackend import MediaBackend
from .__PluginBase import PluginBase


def img(
    prompt: str,
    media: list,
    backend: Ircawp_Backend,
    media_backend: MediaBackend = None,
) -> tuple[str, str, bool]:
    # we don't run the imagegen here, we just pass it all back
    # to ircawp to process without inference

    if prompt[0] == "!":
        refined_prompt = prompt[1:]
        backend.console.log(f"[white on green] skipping prompt refinement")
    else:
        refined_prompt, _ = backend.runInference(
            prompt=prompt,
            system_prompt="""
            You will be provided with a fragment of text or an image; either individual key words, or a brief description.
    You are to imagine a fuller, more visually descriptive T5 prompt suitable for SDXL or Flux, based on the user's provided input.

    - Provide a detailed description of the image using natural language, using up to 70 characters.
    - Break down the scene into key components: subjects, setting, lighting, colors, composition, and atmosphere.
    - Describe subjects in great detail, including their appearance, pose, expression, clothing, and any interactions between them.
    - Elaborate on the setting, specifying the time of day, location specifics, architectural details, and any relevant objects or props.
    - Explain the lighting conditions, including the source, intensity, shadows, and how it affects the overall scene.
    - Specify color palettes and any significant color contrasts or harmonies that contribute to the image's visual impact.
    - Detail the composition, describing the foreground, middle ground, background, and focal points to create a sense of depth and guide the viewer's eye.
    - Convey the overall mood and atmosphere of the scene, using emotive language to evoke the desired feeling.
    - Use vivid, descriptive language to paint a clear picture, some AI art generators follows instructions precisely but lacks inherent creativity.
    - Avoid using grammatically negative statements or describing what the image should not include, some AI art generators may struggle to interpret these correctly. Instead, focus on positively stating what should be present in the image.
    - Adapt your language and terminology to the requested art style (e.g., photorealistic, anime, oil painting) to maintain consistency across both prompts.
    - Consider potential visual symbolism, metaphors, or allegories that could enhance the image's meaning and impact, and include them in both prompts when relevant.
    - For character-focused images, emphasize personality traits and emotions through visual cues such as facial expressions, body language, and clothing choices, ensuring consistency between the T5 and CLIP prompts.
    - Maintain grammatically positive statements throughout both prompts, focusing on what the image should include rather than what it should not, some AI art generators may struggle with interpreting negative statements accurately.
    - Do not use markdown, only return the new prompt in plaintext.
    """,
            use_tools=False,  # Prevent recursive tool calls
        )

    # Clean up the refined prompt
    final_prompt = refined_prompt.strip()

    if "i'm sorry" in final_prompt.lower() or "i cannot" in final_prompt.lower():
        backend.console.log("[pink on red] prompt refinement refused, using original")
        final_prompt = prompt.strip()

    backend.console.log(f"[black on green] refined prompt: '{final_prompt}'")

    # Call media backend to generate the image
    image_path = media_backend.execute(prompt=final_prompt)

    # return "Refined prompt:\n```" + final_prompt.strip() + "```", image_path, False
    return "", image_path, False


plugin = PluginBase(
    name="Image Generator",
    description="Pass a raw prompt to the image generator.",
    triggers=["img"],
    system_prompt="",
    emoji_prefix="",
    msg_empty_query="No prompt provided",
    msg_exception_prefix="ARTISTIC PROBLEMS",
    main=img,
    use_imagegen=True,
)
