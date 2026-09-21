import { readFile } from "node:fs/promises";
import { describe, expect, it } from "vitest";

const imageUploadSource = new URL(
    "../../components/ImageUpload.svelte",
    import.meta.url,
);
const promptFormSource = new URL(
    "../../components/PromptForm.svelte",
    import.meta.url,
);
const appSource = new URL("../../App.svelte", import.meta.url);

describe("image upload reordering", () => {
    it("uses the dragged thumbnail order as the image sequence submitted for generation", async () => {
        const [upload, form, app] = await Promise.all([
            readFile(imageUploadSource, "utf8"),
            readFile(promptFormSource, "utf8"),
            readFile(appSource, "utf8"),
        ]);

        expect(upload).toMatch(
            /#each images as img, i[\s\S]*?<div\s+class="thumb"[\s\S]*?draggable=\{true\}[\s\S]*?ondragstart=/,
        );
        expect(upload).toMatch(
            /ondrop=\{[^}]*?(?:reorder|move|splice)[^}]*?\}/,
        );
        expect(form).toMatch(/images\s*,\s*\n?\s*rewritePrompt/);
        expect(app).toMatch(
            /createImage\(\s*{\s*\.\.\.params,\s*request_id:\s*requestId\s*}/,
        );
    });
});
