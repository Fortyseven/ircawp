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
    import { loadDraft, saveDraft } from "../lib/draft.js";

    let {
        backends = [],
        defaultBackend = "",
        settings = {},
        generating = false,
        ongenerate,
        onabort,
    } = $props();

    const initialSettings = untrack(() => settings);
    const initialDraft = untrack(() => loadDraft());
    const initialDraftSettings =
        initialDraft.settings && typeof initialDraft.settings === "object"
            ? initialDraft.settings
            : {};
    const initialImages = Array.isArray(initialDraft.images)
        ? initialDraft.images
        : [];

    let prompt = $state(initialDraft.prompt ?? "");
    let model = $state(
        initialDraftSettings.model ?? initialSettings.model ?? "",
    );
    let aspectRatio = $state(
        initialDraftSettings.aspectRatio ??
            initialSettings.aspectRatio ??
            DEFAULT_ASPECT_RATIO,
    );
    let outputSize = $state(
        initialDraftSettings.outputSize ??
            initialSettings.outputSize ??
            DEFAULT_OUTPUT_SIZE,
    );
    let trueCfgScale = $state(
        initialDraftSettings.trueCfgScale ??
            initialSettings.trueCfgScale ??
            1.0,
    );
    let seed = $state(
        initialDraftSettings.seed ?? initialSettings.seed ?? undefined,
    );
    let hadImages = initialImages.length > 0;
    let n = $state(initialDraftSettings.n ?? initialSettings.n ?? 1);
    let steps = $state(
        initialDraftSettings.steps ?? initialSettings.steps ?? undefined,
    );
    let images = $state(initialImages);
    let rewritePrompt = $state(
        initialDraftSettings.rewritePrompt ??
            initialSettings.rewritePrompt ??
            false,
    );

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

    $effect(() => {
        saveDraft({
            prompt,
            images,
            settings: {
                model,
                aspectRatio,
                outputSize,
                trueCfgScale,
                seed,
                n,
                steps,
                rewritePrompt,
            },
        });
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
            n,
            steps,
            images,
            rewritePrompt,
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

    <label class="rewrite-toggle">
        <input
            type="checkbox"
            bind:checked={rewritePrompt}
            disabled={generating}
        />
        <span>rewrite prompt before generating</span>
    </label>

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
