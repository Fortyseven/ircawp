import { afterEach, describe, expect, it, vi } from "vitest";
import { createImage, generateImage, editImage, getBackends } from "../api.js";

function jsonResponse(body, status = 200) {
    return {
        ok: status >= 200 && status < 300,
        status,
        json: async () => body,
    };
}

function mockFetch(response) {
    const fetchMock = vi.fn(async (url, options = {}) =>
        response(url, options),
    );
    vi.stubGlobal("fetch", fetchMock);
    return fetchMock;
}

afterEach(() => {
    vi.unstubAllGlobals();
});

describe("generateImage", () => {
    it("POSTs the full body to /images/generations and returns parsed JSON", async () => {
        const payload = {
            created: 123,
            data: [{ b64_json: "aGk=", url: "/x", revised_prompt: "p" }],
        };
        const fetchMock = mockFetch(() => jsonResponse(payload));

        const result = await generateImage({
            prompt: "a cat",
            model: "flux2klein",
            n: 2,
            size: "512x512",
            quality: "medium",
        });

        expect(fetchMock).toHaveBeenCalledTimes(1);
        const [url, options] = fetchMock.mock.calls[0];
        expect(url).toBe("/images/generations");
        expect(options.method).toBe("POST");
        expect(JSON.parse(options.body)).toEqual({
            prompt: "a cat",
            model: "flux2klein",
            n: 2,
            size: "512x512",
            quality: "medium",
        });
        expect(result).toEqual(payload);
    });

    it("omits undefined fields from the request body", async () => {
        const fetchMock = mockFetch(() =>
            jsonResponse({ created: 1, data: [] }),
        );

        await generateImage({ prompt: "a dog" });

        const [, options] = fetchMock.mock.calls[0];
        expect(JSON.parse(options.body)).toEqual({ prompt: "a dog" });
    });
});

describe("editImage", () => {
    it("POSTs to /images/edits with images mapped to {image_url} objects", async () => {
        const payload = {
            created: 1,
            data: [{ b64_json: "Ynk=", url: "/y", revised_prompt: "q" }],
        };
        const fetchMock = mockFetch(() => jsonResponse(payload));
        const images = [
            "data:image/png;base64,AAA",
            "data:image/png;base64,BBB",
        ];

        const result = await editImage({
            prompt: "make it blue",
            images,
            model: "sdxs",
            n: 1,
            size: "768x768",
            quality: "high",
            inputFidelity: 0.5,
        });

        const [url, options] = fetchMock.mock.calls[0];
        expect(url).toBe("/images/edits");
        expect(options.method).toBe("POST");
        expect(JSON.parse(options.body)).toEqual({
            prompt: "make it blue",
            images: [
                { image_url: "data:image/png;base64,AAA" },
                { image_url: "data:image/png;base64,BBB" },
            ],
            model: "sdxs",
            n: 1,
            size: "768x768",
            quality: "high",
            input_fidelity: 0.5,
        });
        expect(result).toEqual(payload);
    });

    it("omits undefined fields from the request body", async () => {
        const fetchMock = mockFetch(() =>
            jsonResponse({ created: 1, data: [] }),
        );

        await editImage({
            prompt: "crop it",
            images: ["data:image/png;base64,AAA"],
        });

        const [, options] = fetchMock.mock.calls[0];
        expect(JSON.parse(options.body)).toEqual({
            prompt: "crop it",
            images: [{ image_url: "data:image/png;base64,AAA" }],
        });
    });
});

describe("createImage", () => {
    it("generates an image when no source images are provided", async () => {
        const payload = { created: 1, data: [{ b64_json: "Z2VuZXJhdGVk" }] };
        const fetchMock = mockFetch(() => jsonResponse(payload));

        const result = await createImage({
            prompt: "a lighthouse",
            images: [],
            model: "flux2klein",
            n: 2,
            size: "512x512",
            quality: "medium",
        });

        const [url, options] = fetchMock.mock.calls[0];
        expect(url).toBe("/images/generations");
        expect(JSON.parse(options.body)).toEqual({
            prompt: "a lighthouse",
            model: "flux2klein",
            n: 2,
            size: "512x512",
            quality: "medium",
        });
        expect(result).toEqual(payload);
    });

    it("edits an image when one or more source images are provided", async () => {
        const payload = { created: 1, data: [{ b64_json: "ZWRpdGVk" }] };
        const fetchMock = mockFetch(() => jsonResponse(payload));

        const result = await createImage({
            prompt: "add fog",
            images: ["data:image/png;base64,AAA"],
            model: "sdxs",
            n: 1,
            size: "768x768",
            quality: "high",
            inputFidelity: 0.5,
        });

        const [url, options] = fetchMock.mock.calls[0];
        expect(url).toBe("/images/edits");
        expect(JSON.parse(options.body)).toEqual({
            prompt: "add fog",
            images: [{ image_url: "data:image/png;base64,AAA" }],
            model: "sdxs",
            n: 1,
            size: "768x768",
            quality: "high",
            input_fidelity: 0.5,
        });
        expect(result).toEqual(payload);
    });
});

describe("getBackends", () => {
    it("GETs /backends and returns parsed JSON", async () => {
        const payload = {
            default: "flux2klein",
            backends: ["flux2klein", "sdxs"],
        };
        const fetchMock = mockFetch(() => jsonResponse(payload));

        const result = await getBackends();

        const [url, options] = fetchMock.mock.calls[0];
        expect(url).toBe("/backends");
        expect(options?.method).toBeUndefined(); // GET — no explicit method needed
        expect(result).toEqual(payload);
    });
});

describe("error handling", () => {
    it("throws an Error with the detail field when the response is not ok", async () => {
        mockFetch(() => jsonResponse({ detail: "model not found" }, 404));

        await expect(generateImage({ prompt: "x" })).rejects.toThrow(
            "model not found",
        );
    });

    it("falls back to HTTP <status> when the error body has no detail", async () => {
        mockFetch(() => jsonResponse({ message: "nope" }, 500));

        await expect(getBackends()).rejects.toThrow("HTTP 500");
    });

    it("handles non-JSON error bodies (e.g. uvicorn 500 text) without crashing", async () => {
        vi.stubGlobal(
            "fetch",
            vi.fn(async () => ({
                ok: false,
                status: 500,
                json: async () => {
                    throw new SyntaxError("Unexpected token 'I'");
                },
            })),
        );

        await expect(generateImage({ prompt: "x" })).rejects.toThrow(
            "HTTP 500",
        );
    });
});
