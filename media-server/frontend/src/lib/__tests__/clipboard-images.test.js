import { describe, expect, it, vi } from "vitest";
import { extractImageFiles } from "../clipboard-images.js";

function file(name, type) {
    return { name, type };
}

describe("extractImageFiles", () => {
    it("extracts only image file items from clipboard data", () => {
        const png = file("pasted.png", "image/png");
        const text = file("notes.txt", "text/plain");
        const getPng = vi.fn(() => png);
        const getText = vi.fn(() => text);

        const result = extractImageFiles({
            items: [
                { kind: "string", type: "text/plain", getAsFile: vi.fn() },
                { kind: "file", type: "text/plain", getAsFile: getText },
                { kind: "file", type: "image/png", getAsFile: getPng },
                { kind: "file", type: "image/jpeg", getAsFile: () => null },
            ],
            files: [png],
        });

        expect(result).toEqual([png]);
        expect(getPng).toHaveBeenCalledOnce();
        expect(getText).not.toHaveBeenCalled();
    });

    it("falls back to clipboard files when items provide no images", () => {
        const jpeg = file("fallback.jpg", "image/jpeg");

        expect(
            extractImageFiles({
                items: [
                    { kind: "string", type: "text/plain", getAsFile: vi.fn() },
                ],
                files: [file("notes.txt", "text/plain"), null, jpeg],
            }),
        ).toEqual([jpeg]);
    });

    it("does not append clipboard files when image items were extracted", () => {
        const itemImage = file("item.webp", "image/webp");
        const fileListImage = file("duplicate.webp", "image/webp");

        expect(
            extractImageFiles({
                items: [
                    {
                        kind: "file",
                        type: "image/webp",
                        getAsFile: () => itemImage,
                    },
                ],
                files: [fileListImage],
            }),
        ).toEqual([itemImage]);
    });

    it("returns an empty list when clipboard data is missing", () => {
        expect(extractImageFiles(null)).toEqual([]);
    });
});
