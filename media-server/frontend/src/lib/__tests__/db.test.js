import "fake-indexeddb/auto";
import { beforeEach, describe, expect, it } from "vitest";
import {
    openDB,
    addGeneration,
    getGenerations,
    deleteGeneration,
    clearHistory,
    MAX_HISTORY,
} from "../db.js";

function makeRecord(i) {
    return {
        prompt: `prompt ${i}`,
        model: "flux2klein",
        mode: "generate",
        size: "512x512",
        quality: "medium",
        n: 1,
        created: Date.now() + i,
        images: [{ b64_json: `b64-${i}`, revised_prompt: `revised ${i}` }],
    };
}

beforeEach(async () => {
    await clearHistory();
});

describe("openDB", () => {
    it("resolves to an IDBDatabase named ircawp-media", async () => {
        const db = await openDB();
        expect(db.name).toBe("ircawp-media");
        expect(typeof db.transaction).toBe("function");
        expect(db.objectStoreNames.contains("history")).toBe(true);
    });
});

describe("addGeneration / getGenerations", () => {
    it("returns the new id and stores the record", async () => {
        const id = await addGeneration(makeRecord(1));
        expect(typeof id).toBe("number");

        const all = await getGenerations();
        expect(all).toHaveLength(1);
        expect(all[0].id).toBe(id);
        expect(all[0].prompt).toBe("prompt 1");
        expect(all[0].images).toEqual([
            { b64_json: "b64-1", revised_prompt: "revised 1" },
        ]);
    });

    it("returns records sorted by id DESC (newest first)", async () => {
        const id1 = await addGeneration(makeRecord(1));
        const id2 = await addGeneration(makeRecord(2));
        const id3 = await addGeneration(makeRecord(3));

        const all = await getGenerations();
        expect(all.map((r) => r.id)).toEqual([id3, id2, id1]);
    });
});

describe("history cap", () => {
    it("exports MAX_HISTORY as 50", () => {
        expect(MAX_HISTORY).toBe(50);
    });

    it("deletes the oldest records when the store exceeds MAX_HISTORY", async () => {
        const ids = [];
        for (let i = 1; i <= MAX_HISTORY + 2; i++) {
            ids.push(await addGeneration(makeRecord(i)));
        }

        const all = await getGenerations();
        expect(all).toHaveLength(MAX_HISTORY);
        // The two oldest (lowest ids) were pruned.
        expect(all.map((r) => r.id)).not.toContain(ids[0]);
        expect(all.map((r) => r.id)).not.toContain(ids[1]);
        expect(all.map((r) => r.id)).toContain(ids[ids.length - 1]);
    });
});

describe("deleteGeneration", () => {
    it("removes the record with the given id", async () => {
        const id1 = await addGeneration(makeRecord(1));
        const id2 = await addGeneration(makeRecord(2));

        await deleteGeneration(id1);

        const all = await getGenerations();
        expect(all.map((r) => r.id)).toEqual([id2]);
    });
});

describe("clearHistory", () => {
    it("removes all records", async () => {
        await addGeneration(makeRecord(1));
        await addGeneration(makeRecord(2));

        await clearHistory();

        expect(await getGenerations()).toEqual([]);
    });
});
