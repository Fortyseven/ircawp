<script>
  import { onMount } from "svelte";
  import PromptForm from "./components/PromptForm.svelte";
  import ResultGrid from "./components/ResultGrid.svelte";
  import History from "./components/History.svelte";
  import { cancelImage, createImage, getBackends } from "./lib/api.js";
  import {
    getGenerations,
    addGeneration,
    deleteGeneration,
    clearHistory,
  } from "./lib/db.js";
  import { loadSettings, saveSettings } from "./lib/settings.js";

  let backends = $state([]);
  let defaultBackend = $state("");
  let settings = $state(loadSettings());
  let generating = $state(false);
  let error = $state("");
  let results = $state(null);
  let history = $state([]);
  let elapsed = $state(0);
  let timer = $state(null);
  let requestController = null;
  let activeRequestId = null;

  function fmtElapsed(s) {
    const m = Math.floor(s / 60);
    const sec = String(s % 60).padStart(2, "0");
    return `${m}:${sec}`;
  }

  async function refreshHistory() {
    history = await getGenerations();
  }

  onMount(async () => {
    try {
      const b = await getBackends();
      backends = b.backends;
      defaultBackend = b.default;
    } catch (e) {
      error = `backend list: ${e.message}`;
    }
    refreshHistory();
  });

  function startTimer() {
    elapsed = 0;
    timer = setInterval(() => (elapsed += 1), 1000);
  }

  function stopTimer() {
    clearInterval(timer);
    timer = null;
  }

  async function handleGenerate(params) {
    if (generating) return;
    error = "";
    generating = true;
    const requestId = crypto.randomUUID();
    activeRequestId = requestId;
    requestController = new AbortController();
    startTimer();
    try {
      const res = await createImage({ ...params, request_id: requestId }, requestController.signal);
      const record = {
        prompt: params.prompt,
        model: params.model || defaultBackend,
        mode: params.images.length ? "edit" : "generate",
        size: params.size,
        quality: params.quality,
        n: params.n,
        steps: params.steps,
        created: res.created,
        images: res.data,
      };
      await addGeneration(record);
      results = record;
      saveSettings({
        model: params.model,
        size: params.size,
        quality: params.quality,
        n: params.n,
        steps: params.steps,
      });
      await refreshHistory();
    } catch (e) {
      if (e.name !== "AbortError") {
        error = e.message;
      }
    } finally {
      generating = false;
      requestController = null;
      activeRequestId = null;
      stopTimer();
    }
  }

  async function handleAbort() {
    const requestId = activeRequestId;
    await cancelImage(requestId);
    requestController?.abort();
  }

  function viewHistoryItem(item) {
    results = item;
  }

  async function handleDelete(id) {
    await deleteGeneration(id);
    refreshHistory();
  }

  async function handleClear() {
    await clearHistory();
    refreshHistory();
  }
</script>

<div class="app">
  <header class="header">
    <div class="brand">
      <span class="brand-mark" aria-hidden="true">◉</span>
      <h1>ircawp<span>media</span></h1>
    </div>
    <div class="status mono" class:offline={backends.length === 0}>
      <span class="status-dot" aria-hidden="true"></span>
      {backends.length
        ? `${backends.length} backends · default ${defaultBackend}`
        : "connecting…"}
    </div>
  </header>

  <section class="workspace">
    <div class="panel form-panel">
      <PromptForm
        backends={backends}
        defaultBackend={defaultBackend}
        settings={settings}
        generating={generating}
        ongenerate={handleGenerate}
        onabort={handleAbort}
      />
    </div>

    <div class="panel result-panel">
      {#if generating}
        <div class="generating">
          <div class="safelight" aria-hidden="true"></div>
          <p class="mono">developing… {fmtElapsed(elapsed)}</p>
        </div>
      {:else if results}
        <ResultGrid result={results} />
      {:else}
        <div class="empty">
          <p>nothing on the tray yet</p>
          <p class="mono dim">prompt → generate</p>
        </div>
      {/if}
      {#if error}
        <p class="error mono" role="alert">{error}</p>
      {/if}
    </div>
  </section>

  <History
    items={history}
    activeId={results?.id ?? null}
    onview={viewHistoryItem}
    ondelete={handleDelete}
    onclear={handleClear}
  />
</div>
