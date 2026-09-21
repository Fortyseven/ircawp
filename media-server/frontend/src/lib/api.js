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

function postJSON(url, body) {
    return request(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
    });
}

export async function generateImage(params) {
    return postJSON("/images/generations", clean(params));
}

export async function editImage(params) {
    const { images, inputFidelity, ...rest } = params;
    const body = clean(rest);
    if (images !== undefined) {
        body.images = images.map((url) => ({ image_url: url }));
    }
    if (inputFidelity !== undefined) {
        body.input_fidelity = inputFidelity;
    }
    return postJSON("/images/edits", body);
}

export async function createImage(params) {
    if (params.images?.length) {
        return editImage(params);
    }

    const { images, ...generationParams } = params;
    return generateImage(generationParams);
}

export async function getBackends() {
    return request("/backends");
}
