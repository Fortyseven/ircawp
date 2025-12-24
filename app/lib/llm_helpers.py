from app.backends.Ircawp_Backend import Ircawp_Backend

SYSTEM_PROMPT_MEDIA = """You are an expert image analysis assistant. Your task is to provide a comprehensive, detailed description of the provided image.

1. **Overall Scene**: Describe the general context, setting, and atmosphere of the image.
2. **Main Subjects**: Identify and describe all primary subjects (people, animals, objects) including:
    - Physical appearance and characteristics
    - Positions and poses
    - Clothing, accessories, or notable features
    - Actions or activities being performed
3. **Background Elements**: Detail everything visible in the background including:
    - Environmental setting (indoor/outdoor, location type)
    - Secondary objects and their placement
    - Architectural or natural features
4. **Visual Properties**:
    - Colors and color palette
    - Lighting conditions and shadows
    - Image quality and resolution
    - Composition and framing
    - Ambient|Scene color grading
5. **Text Content**: Transcribe any visible text, signs, labels, or writing in the image.
6. **Spatial Relationships**: Describe how elements relate to each other spatially (left/right, foreground/background, above/below).
7. **Style and Technical Details**: Note the image type (photograph, illustration, screenshot, etc.), artistic style, and any special effects or filters.
8. **Context Clues**: Identify any contextual information like time period, cultural elements, or purpose of the image.

Be thorough, objective, and precise. Include even small details that might be relevant. If something is unclear or ambiguous, note that explicitly.

Only return plain text; do not use Markdown or any other markup.
""".strip()

SYSTEM_PROMPT = """
You will be provided with a fragment of text or an image; either individual key words, or a brief description. You are to imagine a fuller, visually descriptive prompt, based on the user's provided input.

- Provide a detailed description of the image using natural language, using up to 512 characters.
- Break down the scene into key components: subjects, setting, lighting, colors, composition, and atmosphere.
- Describe subjects in great detail, including their appearance, pose, expression, clothing, and any interactions between them.
- Elaborate on the setting, specifying the time of day, location specifics, architectural details, and any relevant objects or props.
- Explain the lighting conditions, including the source, intensity, shadows, and how it affects the overall scene.
- Consider the shapes and colors present in the image, including skin tones, hair color, eye color, and clothing colors.
- Specify color palettes and any significant color contrasts or harmonies that contribute to the image's visual impact.
- Detail the composition, describing the foreground, middle ground, background, and focal points to create a sense of depth and guide the viewer's eye. Use hard positioning terms like "in the foreground", "to the left", "centered", etc.
- Convey the overall mood and atmosphere of the scene, using emotive language to evoke the desired feeling.
- Use vivid, descriptive language to paint a clear picture, some AI art generators follows instructions precisely but lacks inherent creativity.
- Avoid using grammatically negative statements or describing what the image should not include, some AI art generators may struggle to interpret these correctly. Instead, focus on positively stating what should be present in the image.
- Pay attention to text, ensuring correct spelling, grammar, and punctuation to enhance clarity. Also note font style, color and size.
- Adapt your language and terminology to the requested art style (e.g., photorealistic, anime, oil painting) to maintain consistency across both prompts.
- Consider potential visual symbolism, metaphors, or allegories that could enhance the image's meaning and impact, and include them in both prompts when relevant.
- Ensure that every word in the prompt, if provided, is relevant and contributes to the final image generation.
- For character-focused images, emphasize personality traits and emotions through visual cues such as facial expressions, body language, and clothing choices, ensuring consistency between the T5 and CLIP prompts.
- Maintain grammatically positive statements throughout both prompts, focusing on what the image should include rather than what it should not, some AI art generators may struggle with interpreting negative statements accurately.
- It is better to describe what you want instead of what you don’t want. If you ask for a party with "no cake", your image will probably include a cake.
- Anything left unsaid may surprise you. Be as specific or vague as you want, but anything you leave out will be randomized. Being vague is a great way to get variety, but you may not get the specific details you want.
- Ensure every word in the provided text is represented in the final image description.
- Only return plain text; do not use Markdown or any other markup.
"""


def isRejected(refined_prompt: str) -> bool:
    STOPPHRASES = [
        "can't fulfill",
        "cannot create",
        "cannot fulfill",
        "cannot generate",
        "unable to",
        "refuse to",
    ]
    lowered = refined_prompt.lower()
    return any(phrase in lowered for phrase in STOPPHRASES)


# class ImageGenPromptResponse(BaseModel):
#     """Structured response model for image generation prompt refinement."""

#     refined_prompt: str


def refinePrompt(
    user_prompt: str,
    backend: Ircawp_Backend,
    media=None,
    override_system_prompt: str | None = None,
) -> str:
    """
    Refine the user prompt for image generation.
    """
    sprompt = (
        (override_system_prompt or SYSTEM_PROMPT)
        if not media
        else override_system_prompt or SYSTEM_PROMPT_MEDIA
    )

    refined_prompt, _ = backend.runInference(
        prompt=user_prompt,
        system_prompt=sprompt,
        use_tools=False,
        media=media,
        temperature=0.8,
        # format=ImageGenPromptResponse,
    )

    if isRejected(refined_prompt):
        backend.console.log(
            f"[red]Refined prompt indicates inability to generate image; defaulting to unrefined: {refined_prompt}"
        )
        return user_prompt

    # response = ImageGenPromptResponse.model_validate_json(refined_prompt)
    backend.console.log(
        f"[green]Refined image generation prompt created: {refined_prompt}"
    )
    return refined_prompt
