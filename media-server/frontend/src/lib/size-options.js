export const DEFAULT_SIZE = "1024x1024";
export const MATCH_SOURCE = "match-source";
export const DEFAULT_ASPECT_RATIO = "1:1";
export const DEFAULT_OUTPUT_SIZE = 1024;
export const OUTPUT_SIZES = [512, 768, 1024, 1280, 1536, 2048, 3072, 4096];

const aspectRatioGroups = [
    {
        label: "Square",
        options: [{ label: "1:1", value: "1:1" }],
    },
    {
        label: "Landscape",
        options: ["21:9", "16:9", "4:3", "3:2"].map((value) => ({
            label: value,
            value,
        })),
    },
    {
        label: "Portrait",
        options: ["9:21", "9:16", "3:4", "2:3"].map((value) => ({
            label: value,
            value,
        })),
    },
];

const dimensionGroups = [
    {
        label: "Square",
        options: [{ label: "1:1", value: DEFAULT_SIZE }],
    },
    {
        label: "Landscape",
        options: [
            { label: "21:9", value: "1344x576" },
            { label: "16:9", value: "1280x720" },
            { label: "4:3", value: "1024x768" },
            { label: "3:2", value: "1152x768" },
        ],
    },
    {
        label: "Portrait",
        options: [
            { label: "9:21", value: "576x1344" },
            { label: "9:16", value: "720x1280" },
            { label: "3:4", value: "768x1024" },
            { label: "2:3", value: "768x1152" },
        ],
    },
];

const supportedSizes = new Set(
    dimensionGroups.flatMap((group) =>
        group.options.map((option) => option.value),
    ),
);

export function isSupportedSize(value) {
    return supportedSizes.has(value);
}

export function getSizeOptionGroups(mode) {
    if (mode === "edit") {
        return [
            {
                label: "Source",
                options: [{ label: "Match source", value: MATCH_SOURCE }],
            },
            ...dimensionGroups,
        ];
    }

    return dimensionGroups;
}

export function resolveSizeForSubmission(value) {
    return value === MATCH_SOURCE ? undefined : value;
}

export function getAspectRatioGroups(hasSourceImage = false) {
    if (hasSourceImage) {
        return [
            {
                label: "Source",
                options: [{ label: "Match source", value: MATCH_SOURCE }],
            },
            ...aspectRatioGroups,
        ];
    }
    return aspectRatioGroups;
}

export function dimensionsForAspect(aspectRatio, outputSize) {
    if (aspectRatio === MATCH_SOURCE) return undefined;

    const [ratioWidth, ratioHeight] = aspectRatio.split(":").map(Number);
    const edge = Number(outputSize);
    if (!ratioWidth || !ratioHeight || !edge) return DEFAULT_SIZE;

    const landscape = ratioWidth >= ratioHeight;
    const width = landscape
        ? edge
        : Math.max(16, Math.round((edge * ratioWidth) / ratioHeight / 16) * 16);
    const height = landscape
        ? Math.max(16, Math.round((edge * ratioHeight) / ratioWidth / 16) * 16)
        : edge;
    return `${width}x${height}`;
}
