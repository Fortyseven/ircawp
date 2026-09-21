<script>
    import { onMount } from "svelte";
    import PromptForm from "./components/PromptForm.svelte";
    import ResultGrid from "./components/ResultGrid.svelte";
    import History from "./components/History.svelte";
    import PromptRewriteSettings from "./components/PromptRewriteSettings.svelte";
    import { cancelImage, createImage, getBackends } from "./lib/api.js";
    import {
        getGenerations,
        addGeneration,
        deleteGeneration,
        clearHistory,
    } from "./lib/db.js";
    import { rewritePrompt } from "./lib/prompt-rewrite.js";
    import { loadSettings, saveSettings } from "./lib/settings.js";

    let backends = $state([]);
    let defaultBackend = $state("");
    const savedSettings = loadSettings();
    let settings = $state({
        ...savedSettings,
        rewritePrompt: savedSettings.rewritePrompt ?? false,
        promptRewrite: savedSettings.promptRewrite ?? {
            endpoint: "",
            apiKey: "",
            model: "",
        },
    });
    let showPromptRewriteSettings = $state(false);
    let generating = $state(false);
    let isRevising = $state(false);
    let error = $state("");
    let results = $state(null);
    let history = $state([]);
    let elapsed = $state(0);
    let timer = $state(null);
    let requestController = null;
    let activeRequestId = null;
    let promptFormRef = $state(null);

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
        isRevising = params.rewritePrompt;
        const requestId = crypto.randomUUID();
        activeRequestId = requestId;
        requestController = new AbortController();
        startTimer();
        try {
            let rewrittenPrompt = params.prompt;
            if (params.rewritePrompt) {
                try {
                    rewrittenPrompt = await rewritePrompt({
                        prompt: params.prompt,
                        endpoint: settings.promptRewrite.endpoint,
                        apiKey: settings.promptRewrite.apiKey,
                        model: settings.promptRewrite.model,
                        hasImages: params.images.length > 0,
                        images: params.images,
                        signal: requestController.signal,
                    });
                    console.info("prompt rewrite", "NEW: " + rewrittenPrompt);
                } catch (e) {
                    if (e.name === "AbortError") throw e;
                    console.info(
                        "prompt rewrite failed; generating original prompt",
                        e,
                    );
                }
            }
            isRevising = false;
            const generationParams = { ...params, prompt: rewrittenPrompt };
            const res = await createImage(
                { ...generationParams, request_id: requestId },
                requestController.signal,
            );
            const record = {
                prompt: params.prompt,
                model: params.model || defaultBackend,
                mode: params.images.length ? "edit" : "generate",
                size: params.size,
                outputSize: params.outputSize,
                aspectRatio: params.aspectRatio,
                trueCfgScale: params.trueCfgScale,
                seed: params.seed,
                n: params.n,
                steps: params.steps,
                sourceImage: params.images[0] ?? null,
                created: res.created,
                images: res.data,
            };
            await addGeneration(record);
            results = record;
            const nextSettings = {
                model: params.model,
                size: params.size,
                outputSize: params.outputSize,
                aspectRatio: params.aspectRatio,
                trueCfgScale: params.trueCfgScale,
                seed: params.seed,
                n: params.n,
                steps: params.steps,
                rewritePrompt: params.rewritePrompt,
                promptRewrite: settings.promptRewrite,
            };
            settings = { ...settings, ...nextSettings };
            saveSettings(nextSettings);
            await refreshHistory();
        } catch (e) {
            if (e.name !== "AbortError") {
                error = e.message;
            }
        } finally {
            generating = false;
            isRevising = false;
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

    function handleUsePrompt(prompt) {
        promptFormRef?.setPrompt(prompt);
    }

    async function handleDelete(id) {
        await deleteGeneration(id);
        refreshHistory();
    }

    async function handleClear() {
        await clearHistory();
        refreshHistory();
    }

    function handlePromptRewriteSettings(config) {
        const promptRewrite = {
            ...settings.promptRewrite,
            ...config.promptRewrite,
        };
        settings = {
            ...settings,
            promptRewrite,
        };
        saveSettings({ promptRewrite });
        showPromptRewriteSettings = false;
    }
</script>

<div class="app">
    <header class="header">
        <div class="brand">
            <span
                class="brand-mark"
                aria-hidden="true">◉</span
            >
            <h1>ircawp<span>media</span></h1>
        </div>
        <div
            class="status mono"
            class:offline={backends.length === 0}
        >
            <span
                class="status-dot"
                aria-hidden="true"
            ></span>
            {backends.length
                ? `${backends.length} backends · default ${defaultBackend}`
                : "connecting…"}
        </div>
        <button
            class="config-button"
            type="button"
            aria-label="Configure prompt rewriting"
            onclick={() => (showPromptRewriteSettings = true)}
        >
            settings
        </button>
    </header>

    <main
        class="content-shell"
        class:has-history={history.length > 0}
    >
        <section class="workspace">
            <div class="panel form-panel">
                <PromptForm
                    bind:this={promptFormRef}
                    {backends}
                    {defaultBackend}
                    {settings}
                    {generating}
                    ongenerate={handleGenerate}
                    onabort={handleAbort}
                />
            </div>

            <div class="panel result-panel">
                {#if generating}
                    <div class="generating">
                        <div
                            class="safelight"
                            aria-hidden="true"
                        ></div>
                        <p class="mono">
                            {isRevising ? "revising…" : "developing…"}
                            {fmtElapsed(elapsed)}
                        </p>
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
                    <p
                        class="error mono"
                        role="alert"
                    >
                        {error}
                    </p>
                {/if}
            </div>
        </section>

        <History
            items={history}
            activeId={results?.id ?? null}
            onview={viewHistoryItem}
            ondelete={handleDelete}
            onclear={handleClear}
            onuseprompt={handleUsePrompt}
        />
    </main>
</div>

{#if showPromptRewriteSettings}
    <PromptRewriteSettings
        config={settings.promptRewrite}
        onsave={handlePromptRewriteSettings}
        onclose={() => (showPromptRewriteSettings = false)}
    />
{/if}
