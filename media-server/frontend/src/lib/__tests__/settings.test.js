import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { loadSettings, saveSettings } from "../settings.js";

const KEY = "ircawp-media-settings";

function createLocalStorageMock() {
    const store = new Map();
    return {
        getItem: (k) => (store.has(k) ? store.get(k) : null),
        setItem: (k, v) => {
            store.set(k, String(v));
        },
        removeItem: (k) => {
            store.delete(k);
        },
        clear: () => store.clear(),
        key: (i) => [...store.keys()][i] ?? null,
        get length() {
            return store.size;
        },
    };
}

let localStorageMock;

beforeEach(() => {
    localStorageMock = createLocalStorageMock();
    vi.stubGlobal("localStorage", localStorageMock);
});

afterEach(() => {
    vi.unstubAllGlobals();
});

describe("loadSettings", () => {
    it("returns {} when no settings have been saved", () => {
        expect(loadSettings()).toEqual({});
    });

    it("returns {} when the stored blob is corrupt JSON", () => {
        localStorageMock.setItem(KEY, "{not valid json");
        expect(loadSettings()).toEqual({});
    });

    it("returns the parsed settings object", () => {
        const settings = {
            model: "sdxs",
            size: "768x768",
            quality: "high",
            n: 2,
        };
        localStorageMock.setItem(KEY, JSON.stringify(settings));
        expect(loadSettings()).toEqual(settings);
    });
});

describe("saveSettings", () => {
    it("writes the settings as a JSON blob to the settings key", () => {
        const settings = {
            model: "flux2klein",
            size: "512x512",
            quality: "medium",
            n: 1,
        };
        saveSettings(settings);

        expect(localStorageMock.getItem(KEY)).toBe(JSON.stringify(settings));
        // Round-trips through loadSettings.
        expect(loadSettings()).toEqual(settings);
    });

    it("does not throw when localStorage is unavailable", () => {
        vi.stubGlobal("localStorage", undefined);
        expect(() => saveSettings({ model: "sdxs" })).not.toThrow();
    });
});
