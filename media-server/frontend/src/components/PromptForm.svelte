<script>
  import { untrack } from "svelte";
  import ImageUpload from "./ImageUpload.svelte";
  import {
    DEFAULT_SIZE,
    MATCH_SOURCE,
    getSizeOptionGroups,
    isSupportedSize,
    resolveSizeForSubmission,
  } from "../lib/size-options.js";

  let {
    backends = [],
    defaultBackend = "",
    settings = {},
    generating = false,
    ongenerate,
    onabort,
  } = $props();

  const persistedSize = $derived(
    isSupportedSize(settings.size) ? settings.size : undefined,
  );

  const initialSettings = untrack(() => settings);

  let prompt = $state("");
  let model = $state(initialSettings.model ?? "");
  let size = $state(
    isSupportedSize(initialSettings.size) ? initialSettings.size : DEFAULT_SIZE,
  );
  let quality = $state(initialSettings.quality ?? "standard");
  let n = $state(initialSettings.n ?? 1);
  let steps = $state(initialSettings.steps ?? undefined);
  let images = $state([]);

  const sizeOptionGroups = $derived(
    getSizeOptionGroups(images.length ? "edit" : "generate"),
  );

  const canSubmit = $derived(!generating && prompt.trim());

  $effect(() => {
    if (images.length === 0 && size === MATCH_SOURCE) {
      size = persistedSize ?? DEFAULT_SIZE;
    }
  });

  function submit() {
    if (!canSubmit) return;
    ongenerate({
      prompt: prompt.trim(),
      model: model || undefined,
      size: resolveSizeForSubmission(size),
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

    if (event.ctrlKey && (event.key === "Enter" || event.key.toLowerCase() === "e")) {
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
      <select bind:value={model} disabled={generating}>
        <option value="">default ({defaultBackend || "…"})</option>
        {#each backends as b}
          <option value={b}>{b}</option>
        {/each}
      </select>
    </label>

    <label class="field">
      <span class="label mono">images</span>
      <select bind:value={n} disabled={generating}>
        <option value={1}>1</option>
        <option value={2}>2</option>
        <option value={3}>3</option>
        <option value={4}>4</option>
      </select>
    </label>
  </div>

  <div class="row">
    <label class="field">
      <span class="label mono">size</span>
      <select bind:value={size} disabled={generating}>
        {#each sizeOptionGroups as group}
          <optgroup label={group.label}>
            {#each group.options as option}
              <option value={option.value}>{option.label}</option>
            {/each}
          </optgroup>
        {/each}
      </select>
    </label>

    <label class="field">
      <span class="label mono">quality</span>
      <select bind:value={quality} disabled={generating}>
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
  </div>

  {#if n > 1}
    <p class="hint mono">{n} images render sequentially — allow ~{n}× the time</p>
  {/if}

  <button class="cta" type="submit" disabled={!canSubmit}>
    {generating ? "developing…" : images.length ? "edit" : "generate"}
  </button>
</form>
