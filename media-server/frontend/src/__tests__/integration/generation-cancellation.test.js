import { describe, expect, it } from "vitest";
import { readFile } from "node:fs/promises";

const appSource = new URL("../../App.svelte", import.meta.url);

describe("generation cancellation lifecycle", () => {
    it("assigns a fresh request ID and cancels the server before aborting its fetch", async () => {
        const source = await readFile(appSource, "utf8");

        expect(source).toMatch(
            /import\s*{(?=[^}]*\bcancelImage\b)(?=[^}]*\bcreateImage\b)[^}]*}\s*from\s*["']\.\/lib\/api\.js["']/,
        );
        expect(source).toMatch(
            /const\s+requestId\s*=\s*crypto\.randomUUID\(\)/,
        );
        expect(source).toMatch(
            /createImage\(\{\s*\.\.\.params,\s*request_id:\s*requestId\s*}/s,
        );

        const abortHandler = source.match(
            /async function handleAbort\(\)\s*{([\s\S]*?)\n\s*}/,
        )?.[1];
        expect(abortHandler).toBeDefined();
        expect(abortHandler).toMatch(/await\s+cancelImage\(requestId\)/);
        expect(
            abortHandler.indexOf("await cancelImage(requestId)"),
        ).toBeLessThan(abortHandler.indexOf("requestController?.abort()"));
    });
});
