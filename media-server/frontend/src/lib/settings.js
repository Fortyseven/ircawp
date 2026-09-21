import { loadStoredObject, saveStoredObject } from "./storage.js";

const KEY = "ircawp-media-settings";

export function loadSettings() {
    return loadStoredObject(KEY);
}

export function saveSettings(settings) {
    saveStoredObject(KEY, settings);
}
