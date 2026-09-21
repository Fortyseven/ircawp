<script>
    let { result = null } = $props();

    let comparing = $state(false);
    let sourceDimensions = $state(null);
    let outputDimensions = $state({});

    const sourceImage = $derived(result?.sourceImage ?? null);

    $effect(() => {
        result;
        comparing = false;
        sourceDimensions = null;
        outputDimensions = {};
    });

    function handleKeyDown(event) {
        if (event.key.toLowerCase() === "z" && sourceImage) {
            event.preventDefault();
            comparing = true;
        }
    }

    function handleKeyUp(event) {
        if (event.key.toLowerCase() === "z") comparing = false;
    }

    function saveSourceDimensions(event) {
        sourceDimensions = {
            width: event.currentTarget.naturalWidth,
            height: event.currentTarget.naturalHeight,
        };
    }

    function saveOutputDimensions(index, event) {
        outputDimensions[index] = {
            width: event.currentTarget.naturalWidth,
            height: event.currentTarget.naturalHeight,
        };
    }

    function comparisonStyle(index) {
        const output = outputDimensions[index];
        if (!sourceDimensions || !output) return undefined;

        const sourceEdge = Math.max(
            sourceDimensions.width,
            sourceDimensions.height,
        );
        const outputEdge = Math.max(output.width, output.height);
        if (sourceEdge >= outputEdge) return undefined;

        const scale = outputEdge / sourceEdge;
        return `width: ${sourceDimensions.width * scale}px;`;
    }
</script>

<svelte:window
    onkeydown={handleKeyDown}
    onkeyup={handleKeyUp}
    onblur={() => (comparing = false)}
/>

{#if result}
    <div class="result-meta mono">
        <span>{result.model}</span>
        {#if result.aspectRatio && result.outputSize}
            <span>{result.aspectRatio} · {result.outputSize}px</span>
        {:else if result.size}
            <span>{result.size}</span>
        {/if}
        {#if result.seed !== undefined}
            <span>seed {result.seed}</span>
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
                    src={comparing && sourceImage
                        ? sourceImage
                        : `data:image/png;base64,${img.b64_json}`}
                    alt={comparing ? "Original input image" : result.prompt}
                    style={comparing ? comparisonStyle(i) : undefined}
                    onload={(event) => {
                        if (comparing) {
                            saveSourceDimensions(event);
                        } else {
                            saveOutputDimensions(i, event);
                        }
                    }}
                />
                <figcaption class="mono">
                    {#if comparing}
                        <span class="comparison-label"
                            >original · release z</span
                        >
                    {:else if img.revised_prompt}
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

    {#if sourceImage}
        <p class="comparison-hint mono">hold z to compare original</p>
    {/if}

    <p class="prompt-line">“{result.prompt}”</p>
{/if}
