import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { loadDraft, saveDraft } from "../draft.js";

function createLocalStorageMock() {
    const store = new Map();
    return {
        getItem: (key) => (store.has(key) ? store.get(key) : null),
        setItem: (key, value) => {
            store.set(key, String(value));
        },
        removeItem: (key) => {
            store.delete(key);
        },
        clear: () => store.clear(),
        key: (index) => [...store.keys()][index] ?? null,
        get length() {
            return store.size;
        },
    };
}

beforeEach(() => {
    vi.stubGlobal("localStorage", createLocalStorageMock());
});

afterEach(() => {
    vi.unstubAllGlobals();
});

describe("image edit draft storage", () => {
    it("restores an in-progress edit draft after a reload", () => {
        const draft = {
            prompt: "Replace the cloudy sky with a vivid sunset",
            images: [
                "data:image/png;base64,c291cmNlLWltYWdlLTE=",
                "data:image/jpeg;base64,c291cmNlLWltYWdlLTI=",
            ],
            settings: {
                model: "qwenimage21",
                size: "1024x1024",
                trueCfgScale: 4.5,
                seed: 8675309,
                steps: 28,
                customBackendOption: { strength: 0.72 },
            },
        };

        saveDraft(draft);

        expect(loadDraft()).toEqual(draft);
    });
});
