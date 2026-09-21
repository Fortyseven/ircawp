import { loadStoredObject, saveStoredObject } from "./storage.js";

const KEY = "ircawp-media-draft";

export function loadDraft() {
    return loadStoredObject(KEY);
}

export function saveDraft(draft) {
    saveStoredObject(KEY, draft);
}
