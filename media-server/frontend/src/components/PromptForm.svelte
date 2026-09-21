<script>
    import { untrack } from "svelte";
    import ImageUpload from "./ImageUpload.svelte";
    import {
        DEFAULT_ASPECT_RATIO,
        DEFAULT_OUTPUT_SIZE,
        MATCH_SOURCE,
        OUTPUT_SIZES,
        dimensionsForAspect,
        getAspectRatioGroups,
    } from "../lib/size-options.js";

    let {
        backends = [],
        defaultBackend = "",
        settings = {},
        generating = false,
        ongenerate,
        onabort,
    } = $props();

    const initialSettings = untrack(() => settings);

    let prompt = $state("");
    let model = $state(initialSettings.model ?? "");
    let aspectRatio = $state(
        initialSettings.aspectRatio ?? DEFAULT_ASPECT_RATIO,
    );
    let outputSize = $state(initialSettings.outputSize ?? DEFAULT_OUTPUT_SIZE);
    let trueCfgScale = $state(initialSettings.trueCfgScale ?? 2.0);
    let seed = $state(initialSettings.seed ?? undefined);
    let hadImages = false;
    let quality = $state(initialSettings.quality ?? "standard");
    let n = $state(initialSettings.n ?? 1);
    let steps = $state(initialSettings.steps ?? undefined);
    let images = $state([]);

    const aspectRatioGroups = $derived(getAspectRatioGroups(images.length > 0));
    const matchesSource = $derived(aspectRatio === MATCH_SOURCE);
    const supportsQwenControls = $derived(
        (model || defaultBackend) === "qwenimage21",
    );

    const canSubmit = $derived(!generating && prompt.trim());

    $effect(() => {
        const hasImages = images.length > 0;

        if (hasImages && !hadImages) {
            aspectRatio = MATCH_SOURCE;
        } else if (!hasImages && matchesSource) {
            aspectRatio = DEFAULT_ASPECT_RATIO;
        }

        hadImages = hasImages;
    });

    function submit() {
        if (!canSubmit) return;
        ongenerate({
            prompt: prompt.trim(),
            model: model || undefined,
            size: dimensionsForAspect(aspectRatio, outputSize),
            outputSize: matchesSource ? undefined : outputSize,
            aspectRatio,
            trueCfgScale: supportsQwenControls ? trueCfgScale : undefined,
            seed: supportsQwenControls ? seed : undefined,
            quality,
            n,
            steps,
            images,
        });
    }

    function handleShortcut(event) {
        if (event.key === "Escape" && generating) {
            event.preventDefault();
            onabort();
            return;
        }

        if (
            event.ctrlKey &&
            (event.key === "Enter" || event.key.toLowerCase() === "e")
        ) {
            event.preventDefault();
            submit();
        }
    }
</script>

<svelte:window onkeydown={handleShortcut} />

<form
    class="form"
    onsubmit={(e) => {
        e.preventDefault();
        submit();
    }}
>
    <label class="field">
        <span class="label mono">prompt</span>
        <textarea
            bind:value={prompt}
            rows="4"
            placeholder="a lighthouse in a storm, oil painting…"
            disabled={generating}
        ></textarea>
    </label>

    <ImageUpload bind:images />

    <div class="row">
        <label class="field grow">
            <span class="label mono">model</span>
            <select
                bind:value={model}
                disabled={generating}
            >
                <option value="">default ({defaultBackend || "…"})</option>
                {#each backends as b}
                    <option value={b}>{b}</option>
                {/each}
            </select>
        </label>

        <label class="field">
            <span class="label mono">images</span>
            <select
                bind:value={n}
                disabled={generating}
            >
                <option value={1}>1</option>
                <option value={2}>2</option>
                <option value={3}>3</option>
                <option value={4}>4</option>
            </select>
        </label>
    </div>

    <div class="row">
        <label class="field">
            <span class="label mono">aspect</span>
            <select
                bind:value={aspectRatio}
                disabled={generating}
            >
                {#each aspectRatioGroups as group}
                    <optgroup label={group.label}>
                        {#each group.options as option}
                            <option value={option.value}>{option.label}</option>
                        {/each}
                    </optgroup>
                {/each}
            </select>
        </label>

        <label class="field">
            <span class="label mono">output</span>
            <select
                bind:value={outputSize}
                disabled={generating || matchesSource}
            >
                {#each OUTPUT_SIZES as edge}
                    <option value={edge}>{edge}px</option>
                {/each}
            </select>
        </label>

        <label class="field">
            <span class="label mono">quality</span>
            <select
                bind:value={quality}
                disabled={generating}
            >
                <option value="standard">standard</option>
                <option value="high">high (remaster)</option>
                <option value="low">low</option>
            </select>
        </label>

        <label class="field">
            <span class="label mono">steps</span>
            <input
                type="number"
                bind:value={steps}
                min="1"
                max="100"
                disabled={generating}
            />
        </label>

        {#if supportsQwenControls}
            <label class="field">
                <span class="label mono">true cfg</span>
                <input
                    type="number"
                    bind:value={trueCfgScale}
                    min="0"
                    step="0.1"
                    placeholder="default"
                    disabled={generating}
                />
            </label>

            <label class="field">
                <span class="label mono">seed</span>
                <input
                    type="number"
                    bind:value={seed}
                    min="0"
                    max="4294967295"
                    step="1"
                    placeholder="random"
                    disabled={generating}
                />
            </label>
        {/if}
    </div>

    {#if n > 1}
        <p class="hint mono">
            {n} images render sequentially — allow ~{n}× the time
        </p>
    {/if}

    <button
        class="cta"
        type="submit"
        disabled={!canSubmit}
    >
        {generating ? "developing…" : images.length ? "edit" : "generate"}
    </button>
</form>
