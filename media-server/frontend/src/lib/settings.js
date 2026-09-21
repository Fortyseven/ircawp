const KEY = "ircawp-media-settings";

function getStorage() {
    try {
        return typeof localStorage !== "undefined" ? localStorage : null;
    } catch {
        return null;
    }
}

export function loadSettings() {
    const storage = getStorage();
    if (!storage) return {};
    try {
        const raw = storage.getItem(KEY);
        if (!raw) return {};
        const parsed = JSON.parse(raw);
        return parsed && typeof parsed === "object" ? parsed : {};
    } catch {
        return {};
    }
}

export function saveSettings(settings) {
    const storage = getStorage();
    if (!storage) return;
    try {
        storage.setItem(
            KEY,
            JSON.stringify({ ...loadSettings(), ...settings }),
        );
    } catch {
        // Storage unavailable (e.g. quota exceeded) — ignore.
    }
}
