import { describe, expect, it } from "vitest";
import { readFile } from "node:fs/promises";

const appSource = new URL("../../App.svelte", import.meta.url);
const promptFormSource = new URL(
    "../../components/PromptForm.svelte",
    import.meta.url,
);
const promptRewriteSettingsSource = new URL(
    "../../components/PromptRewriteSettings.svelte",
    import.meta.url,
);

describe("prompt rewrite generation workflow", () => {
    it("rewrites enabled prompts before creating an image and keeps generation available if rewriting fails", async () => {
        const source = await readFile(appSource, "utf8");
        const handleGenerate = source.match(
            /async function handleGenerate\(params\)\s*{([\s\S]*?)\n\s*}\n\s*async function handleAbort/,
        )?.[1];

        expect(source).toMatch(
            /import\s*{\s*rewritePrompt\s*}\s*from\s*["']\.\/lib\/prompt-rewrite\.js["']/,
        );
        expect(source).toMatch(
            /import\s+PromptRewriteSettings\s+from\s*["']\.\/components\/PromptRewriteSettings\.svelte["']/,
        );
        expect(source).toMatch(/<PromptRewriteSettings\b/);
        expect(handleGenerate).toBeDefined();
        expect(handleGenerate).toMatch(/if\s*\(params\.rewritePrompt\)/);
        expect(handleGenerate).toMatch(
            /isRevising\s*=\s*params\.rewritePrompt/,
        );
        expect(handleGenerate).toMatch(
            /isRevising\s*=\s*false\s*;[\s\S]*?createImage\s*\(/,
        );
        expect(handleGenerate).toMatch(
            /await\s+rewritePrompt\s*\(\s*{(?=[\s\S]*?prompt\s*:\s*params\.prompt)(?=[\s\S]*?hasImages\s*:\s*(?:params\.images\?\.length|params\.images\.length\s*>\s*0))(?=[\s\S]*?images\s*:\s*params\.images)(?=[\s\S]*?endpoint\s*:\s*settings\.promptRewrite\.endpoint)(?=[\s\S]*?apiKey\s*:\s*settings\.promptRewrite\.apiKey)(?=[\s\S]*?model\s*:\s*settings\.promptRewrite\.model)(?=[\s\S]*?signal\s*:\s*requestController\.signal)[\s\S]*?}\s*\)/,
        );
        expect(handleGenerate).toMatch(
            /console\.info\s*\([^)]*params\.prompt[^)]*rewrittenPrompt[^)]*\)/,
        );
        expect(handleGenerate).toMatch(
            /if\s*\(params\.rewritePrompt\)\s*{\s*try\s*{[\s\S]*?rewritePrompt[\s\S]*?}\s*catch\s*\([^)]*\)\s*{[\s\S]*?console\.info\s*\(/,
        );
        expect(handleGenerate.indexOf("rewritePrompt(")).toBeLessThan(
            handleGenerate.indexOf("createImage("),
        );
        expect(handleGenerate).toMatch(
            /const\s+generationParams\s*=\s*{\s*\.\.\.params\s*,\s*prompt\s*:\s*rewrittenPrompt\s*}/,
        );
        expect(handleGenerate).toMatch(
            /createImage\s*\(\s*{\s*\.\.\.generationParams\s*,\s*request_id\s*:\s*requestId\s*}/,
        );
        expect(handleGenerate).toMatch(
            /const\s+record\s*=\s*{[\s\S]*?prompt\s*:\s*params\.prompt/,
        );
        expect(source).toMatch(
            /isRevising\s*\?\s*["']revising…["']\s*:\s*["']developing…["']/,
        );
    });

    it("lets users enable rewriting from saved settings and configure its connection", async () => {
        const [formSource, settingsSource] = await Promise.all([
            readFile(promptFormSource, "utf8"),
            readFile(promptRewriteSettingsSource, "utf8"),
        ]);

        expect(formSource).toMatch(
            /let\s+rewritePrompt\s*=\s*\$state\([\s\S]*?rewritePrompt[\s\S]*?\?\?\s*false\s*,?\s*\)/,
        );
        expect(formSource).toMatch(
            /type="checkbox"[\s\S]*?bind:checked=\{rewritePrompt\}/,
        );
        expect(formSource).toMatch(/rewritePrompt\s*,/);

        expect(settingsSource).toMatch(/role="dialog"|<dialog\b/);
        expect(settingsSource).toMatch(
            /bind:value=\{(?:endpoint|promptRewriteEndpoint)\}/,
        );
        expect(settingsSource).toMatch(
            /type="password"[\s\S]*?bind:value=\{(?:apiKey|promptRewriteApiKey)\}/,
        );
        expect(settingsSource).toMatch(
            /bind:value=\{(?:model|promptRewriteModel)\}/,
        );
        expect(settingsSource).toMatch(
            /(?:onsave|onSave)\s*\?\.\s*\(\s*{(?=[\s\S]*?(?:promptRewriteEndpoint|endpoint))(?=[\s\S]*?(?:promptRewriteApiKey|apiKey))(?=[\s\S]*?(?:promptRewriteModel|model))[\s\S]*?}\s*\)/,
        );
    });
});
