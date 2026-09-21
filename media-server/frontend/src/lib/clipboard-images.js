export function extractImageFiles(clipboardData) {
    if (!clipboardData) return [];

    const itemImages = [...(clipboardData.items ?? [])]
        .filter(
            (item) => item.kind === "file" && item.type.startsWith("image/"),
        )
        .map((item) => item.getAsFile())
        .filter(Boolean);

    if (itemImages.length) return itemImages;

    return [...(clipboardData.files ?? [])].filter((file) =>
        file?.type.startsWith("image/"),
    );
}
