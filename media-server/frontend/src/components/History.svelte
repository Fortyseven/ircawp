<script>
    let {
        items = [],
        activeId = null,
        onview,
        ondelete,
        onclear,
        onuseprompt,
    } = $props();

    function itemTooltip(item) {
        const lines = [item.prompt];
        if (item.trueCfgScale != null) lines.push(`CFG: ${item.trueCfgScale}`);
        if (item.seed != null) lines.push(`Seed: ${item.seed}`);
        return lines.join("\n");
    }
</script>

{#if items.length}
    <section class="history">
        <div class="history-head">
            <h2 class="mono">history · {items.length}</h2>
            <button
                class="ghost mono"
                onclick={onclear}>clear all</button
            >
        </div>

        <div class="filmstrip">
            <div class="strip-track">
                {#each items as item (item.id)}
                    <div
                        class="frame"
                        class:active={item.id === activeId}
                    >
                        <button
                            type="button"
                            class="frame-view"
                            onclick={() => onview(item)}
                            title={itemTooltip(item)}
                        >
                            <img
                                src="data:image/png;base64,{item.images[0]
                                    ?.b64_json}"
                                alt={item.prompt}
                                loading="lazy"
                            />
                            <span class="frame-label mono"
                                >{item.model}{item.images.length > 1
                                    ? ` ×${item.images.length}`
                                    : ""}</span
                            >
                        </button>
                        <button
                            type="button"
                            class="frame-del"
                            aria-label="delete from history"
                            onclick={(e) => {
                                e.stopPropagation();
                                ondelete(item.id);
                            }}
                        >
                            ×
                        </button>
                        <button
                            type="button"
                            class="frame-useprompt"
                            aria-label="copy prompt to form"
                            title="use this prompt"
                            onclick={(e) => {
                                e.stopPropagation();
                                onuseprompt(item.prompt);
                            }}
                        >
                            ⎘
                        </button>
                    </div>
                {/each}
            </div>
        </div>
    </section>
{/if}
