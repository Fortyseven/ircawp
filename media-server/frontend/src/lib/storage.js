function getStorage() {
    try {
        return typeof localStorage !== "undefined" ? localStorage : null;
    } catch {
        return null;
    }
}

export function loadStoredObject(key) {
    const storage = getStorage();
    if (!storage) return {};
    try {
        const raw = storage.getItem(key);
        if (!raw) return {};
        const parsed = JSON.parse(raw);
        return parsed && typeof parsed === "object" ? parsed : {};
    } catch {
        return {};
    }
}

export function saveStoredObject(key, value) {
    const storage = getStorage();
    if (!storage) return;
    try {
        storage.setItem(key, JSON.stringify(value));
    } catch {
        // Storage unavailable (e.g. quota exceeded) - ignore.
    }
}
