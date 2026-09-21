<script>
    import { extractImageFiles } from "../lib/clipboard-images.js";

    let { images = $bindable([]) } = $props();
    let dragging = $state(false);
    let draggedIndex = $state(null);
    let fileInput;

    function readFile(file) {
        return new Promise((resolve) => {
            const reader = new FileReader();
            reader.onload = () => resolve(reader.result);
            reader.onerror = () => resolve(null);
            reader.readAsDataURL(file);
        });
    }

    async function addFiles(files) {
        const imageFiles = [...files].filter((file) =>
            file.type.startsWith("image/"),
        );
        const loadedImages = (
            await Promise.all(imageFiles.map(readFile))
        ).filter(Boolean);
        if (loadedImages.length) images = [...images, ...loadedImages];
    }

    function handlePaste(event) {
        const files = extractImageFiles(event.clipboardData);
        if (!files.length) return;

        event.preventDefault();
        addFiles(files);
    }

    function removeAt(i) {
        images = images.filter((_, j) => j !== i);
    }

    function moveImage(from, to) {
        if (from === null || from === to) return;
        const reordered = [...images];
        const [image] = reordered.splice(from, 1);
        reordered.splice(to, 0, image);
        images = reordered;
    }
</script>

<svelte:window onpaste={handlePaste} />

<div
    class="upload"
    class:dragging
    role="group"
    aria-label="Image uploads"
    ondragover={(e) => {
        e.preventDefault();
        dragging = true;
    }}
    ondragleave={() => (dragging = false)}
    ondrop={(e) => {
        e.preventDefault();
        dragging = false;
        addFiles(e.dataTransfer.files);
    }}
>
    <input
        bind:this={fileInput}
        type="file"
        accept="image/*"
        multiple
        hidden
        onchange={() => addFiles(fileInput.files)}
    />
    <button
        type="button"
        class="dropzone"
        onclick={() => fileInput.click()}
    >
        <span class="mono"
            >{images.length
                ? "add more images"
                : "drop or paste images, or browse"}</span
        >
    </button>

    {#if images.length}
        <div
            class="thumbs"
            role="list"
        >
            {#each images as img, i}
                <div
                    class="thumb"
                    role="listitem"
                    draggable={true}
                    ondragstart={() => (draggedIndex = i)}
                    ondragend={() => (draggedIndex = null)}
                    ondragover={(event) => event.preventDefault()}
                    ondrop={(event) => {
                        event.preventDefault();
                        event.stopPropagation();
                        moveImage(draggedIndex, i);
                    }}
                >
                    <img
                        src={img}
                        alt="upload {i + 1}"
                    />
                    <button
                        type="button"
                        class="thumb-del"
                        onclick={() => removeAt(i)}
                        aria-label="remove image {i + 1}"
                    >
                        ×
                    </button>
                </div>
            {/each}
        </div>
    {/if}
</div>
