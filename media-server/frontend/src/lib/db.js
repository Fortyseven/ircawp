const DB_NAME = "ircawp-media";
const DB_VERSION = 1;
const STORE = "history";

export const MAX_HISTORY = 50;

let dbPromise = null;

export function openDB() {
    if (!dbPromise) {
        dbPromise = new Promise((resolve, reject) => {
            const req = indexedDB.open(DB_NAME, DB_VERSION);
            req.onupgradeneeded = () => {
                const db = req.result;
                if (!db.objectStoreNames.contains(STORE)) {
                    db.createObjectStore(STORE, {
                        keyPath: "id",
                        autoIncrement: true,
                    });
                }
            };
            req.onsuccess = () => resolve(req.result);
            req.onerror = () => reject(req.error);
        });
    }
    return dbPromise;
}

function store(db, mode) {
    return db.transaction(STORE, mode).objectStore(STORE);
}

function toPromise(req) {
    return new Promise((resolve, reject) => {
        req.onsuccess = () => resolve(req.result);
        req.onerror = () => reject(req.error);
    });
}

async function prune(db) {
    const s = store(db, "readwrite");
    const count = await toPromise(s.count());
    if (count <= MAX_HISTORY) return;
    const oldestKeys = await toPromise(s.getAllKeys(null, count - MAX_HISTORY));
    for (const key of oldestKeys) s.delete(key);
}

export async function addGeneration(record) {
    const db = await openDB();
    const id = await toPromise(store(db, "readwrite").add(record));
    await prune(db);
    return id;
}

export async function getGenerations() {
    const db = await openDB();
    const all = await toPromise(store(db, "readonly").getAll());
    return all.sort((a, b) => b.id - a.id);
}

export async function deleteGeneration(id) {
    const db = await openDB();
    await toPromise(store(db, "readwrite").delete(id));
}

export async function clearHistory() {
    const db = await openDB();
    await toPromise(store(db, "readwrite").clear());
}
