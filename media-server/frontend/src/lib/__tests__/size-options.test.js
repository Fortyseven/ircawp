import { describe, expect, it } from "vitest";
import {
    getSizeOptionGroups,
    resolveSizeForSubmission,
} from "../size-options.js";

const dimensionGroups = [
    {
        label: "Square",
        options: [{ label: "1:1", value: "1024x1024" }],
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

describe("size options", () => {
    it("groups the supported aspect ratios for generation", () => {
        expect(getSizeOptionGroups("generate")).toEqual(dimensionGroups);
    });

    it("offers Match source only when editing", () => {
        expect(getSizeOptionGroups("edit")).toEqual([
            {
                label: "Source",
                options: [{ label: "Match source", value: "match-source" }],
            },
            ...dimensionGroups,
        ]);

        const generateLabels = getSizeOptionGroups("generate").flatMap(
            (group) => group.options.map((option) => option.label),
        );
        expect(generateLabels).not.toContain("Match source");
    });

    it("omits size for Match source and submits concrete dimensions unchanged", () => {
        expect(resolveSizeForSubmission("match-source")).toBeUndefined();
        expect(resolveSizeForSubmission("1280x720")).toBe("1280x720");
    });
});
