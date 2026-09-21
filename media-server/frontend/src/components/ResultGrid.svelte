<script>
    let { result = null } = $props();
</script>

{#if result}
    <div class="result-meta mono">
        <span>{result.model}</span>
        {#if result.aspectRatio && result.outputSize}
            <span>{result.aspectRatio} · {result.outputSize}px</span>
        {:else if result.size}
            <span>{result.size}</span>
        {/if}
        {#if result.quality && result.quality !== "standard"}
            <span>{result.quality}</span>
        {/if}
        <span>{new Date(result.created * 1000).toLocaleTimeString()}</span>
    </div>

    <div
        class="grid"
        class:multi={result.images.length > 1}
    >
        {#each result.images as img, i}
            <figure class="shot">
                <img
                    src="data:image/png;base64,{img.b64_json}"
                    alt={result.prompt}
                />
                <figcaption class="mono">
                    {#if img.revised_prompt}
                        <span
                            class="revised"
                            title={img.revised_prompt}>revised</span
                        >
                    {/if}
                    <a
                        class="dl"
                        href="data:image/png;base64,{img.b64_json}"
                        download="ircawp-{result.created}-{i + 1}.png"
                    >
                        download
                    </a>
                </figcaption>
            </figure>
        {/each}
    </div>

    <p class="prompt-line">“{result.prompt}”</p>
{/if}
