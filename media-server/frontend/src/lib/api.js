async function request(url, options) {
    const res = await fetch(url, options);
    let body;
    try {
        body = await res.json();
    } catch {
        // Non-JSON error body (e.g. uvicorn's plain-text 500 page).
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        throw new Error("invalid JSON response");
    }
    if (!res.ok) {
        throw new Error(body?.detail ?? `HTTP ${res.status}`);
    }
    return body;
}

function clean(obj) {
    const out = {};
    for (const [key, value] of Object.entries(obj)) {
        if (value !== undefined) out[key] = value;
    }
    return out;
}

function imageRequestBody(params) {
    const {
        images,
        inputFidelity,
        outputSize,
        aspectRatio,
        trueCfgScale,
        ...rest
    } = params;
    const body = clean(rest);
    if (outputSize !== undefined) body.output_size = outputSize;
    if (trueCfgScale !== undefined) body.true_cfg_scale = trueCfgScale;
    if (images !== undefined) {
        body.images = images.map((url) => ({ image_url: url }));
    }
    if (inputFidelity !== undefined) body.input_fidelity = inputFidelity;
    return body;
}

function postJSON(url, body, signal) {
    return request(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
        signal,
    });
}

export async function generateImage(params, signal) {
    const { images, ...generationParams } = params;
    return postJSON(
        "/images/generations",
        imageRequestBody(generationParams),
        signal,
    );
}

export async function editImage(params, signal) {
    return postJSON("/images/edits", imageRequestBody(params), signal);
}

export async function createImage(params, signal) {
    if (params.images?.length) {
        return editImage(params, signal);
    }

    const { images, ...generationParams } = params;
    return generateImage(generationParams, signal);
}

export async function cancelImage(requestId) {
    return postJSON(`/images/cancellations/${encodeURIComponent(requestId)}`);
}

export async function getImageProgress(requestId) {
    return request(`/images/progress/${encodeURIComponent(requestId)}`);
}

export async function getBackends() {
    return request("/backends");
}
