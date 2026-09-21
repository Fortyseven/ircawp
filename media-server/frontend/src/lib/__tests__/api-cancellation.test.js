import { afterEach, describe, expect, it, vi } from "vitest";
import { cancelImage, createImage } from "../api.js";

function jsonResponse(body, status = 200) {
    return {
        ok: status >= 200 && status < 300,
        status,
        json: async () => body,
    };
}

afterEach(() => {
    vi.unstubAllGlobals();
});

describe("image request cancellation API", () => {
    it("carries the caller-supplied request_id on a generation request", async () => {
        const fetchMock = vi.fn(async () =>
            jsonResponse({ created: 1, data: [] }),
        );
        vi.stubGlobal("fetch", fetchMock);

        await createImage({
            prompt: "a lighthouse",
            request_id: "generation-42",
        });

        const [url, options] = fetchMock.mock.calls[0];
        expect(url).toBe("/images/generations");
        expect(JSON.parse(options.body)).toMatchObject({
            prompt: "a lighthouse",
            request_id: "generation-42",
        });
    });

    it("cancels an active server generation by request ID", async () => {
        const fetchMock = vi.fn(async () => jsonResponse({ cancelled: true }));
        vi.stubGlobal("fetch", fetchMock);

        await cancelImage("generation-42");

        expect(fetchMock).toHaveBeenCalledWith(
            "/images/cancellations/generation-42",
            expect.objectContaining({ method: "POST" }),
        );
    });
});
