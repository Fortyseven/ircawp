<script>
    let { config = {}, onsave, onclose } = $props();

    let endpoint = $state("");
    let apiKey = $state("");
    let model = $state("");

    $effect(() => {
        endpoint = config.endpoint ?? "";
        apiKey = config.apiKey ?? "";
        model = config.model ?? "";
    });

    function save() {
        onsave?.({
            promptRewrite: { endpoint, apiKey, model },
        });
    }

    function closeFromBackdrop(event) {
        if (event.currentTarget === event.target) onclose?.();
    }

    function handleKeydown(event) {
        if (event.key === "Escape") onclose?.();
    }
</script>

<svelte:window onkeydown={handleKeydown} />

<div
    class="modal-backdrop"
    role="presentation"
    onclick={closeFromBackdrop}
>
    <div
        class="rewrite-dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="rewrite-settings-title"
    >
        <div class="dialog-head">
            <h2 id="rewrite-settings-title">prompt rewrite</h2>
            <button
                type="button"
                class="dialog-close"
                aria-label="Close settings"
                onclick={() => onclose?.()}>close</button
            >
        </div>
        <form
            onsubmit={(event) => {
                event.preventDefault();
                save();
            }}
        >
            <label class="field">
                <span class="label mono">endpoint</span>
                <input
                    type="url"
                    bind:value={endpoint}
                    placeholder="https://api.example.com/v1/chat/completions"
                />
            </label>
            <label class="field">
                <span class="label mono">API key</span>
                <input
                    type="password"
                    bind:value={apiKey}
                />
            </label>
            <label class="field">
                <span class="label mono">model</span>
                <input
                    type="text"
                    bind:value={model}
                />
            </label>
            <div class="dialog-actions">
                <button
                    type="button"
                    class="ghost"
                    onclick={() => onclose?.()}>cancel</button
                >
                <button
                    type="submit"
                    class="cta">save</button
                >
            </div>
        </form>
    </div>
</div>
