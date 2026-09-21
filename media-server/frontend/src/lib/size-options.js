export const DEFAULT_SIZE = "1024x1024";
export const MATCH_SOURCE = "match-source";

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
