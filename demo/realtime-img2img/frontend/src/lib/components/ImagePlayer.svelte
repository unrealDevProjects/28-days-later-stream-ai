<script lang="ts">
  import { lcmLiveStatus, LCMLiveStatus, streamId } from '$lib/lcmLive';
  import { getPipelineValues } from '$lib/store';

  import Button from '$lib/components/Button.svelte';
  import Floppy from '$lib/icons/floppy.svelte';
  import QRModal from '$lib/components/QRModal.svelte';
  import { snapImage, snapImageWithQR, captureContainerWithFrame } from '$lib/utils';

  // Ruta de la imagen del marco (debe estar en static/)
  // En SvelteKit, los archivos en static/ se sirven desde la raíz, sin /static/
  // Si tu imagen está en static/images/frame.png, la ruta es /images/frame.png
  export let frameImagePath: string = '/images/frame-2.png';

  // Función para iniciar el procesamiento, pasada desde el componente padre
  export let toggleLcmLive: () => Promise<void>;

  $: isLCMRunning = $lcmLiveStatus !== LCMLiveStatus.DISCONNECTED;
  $: console.log('isLCMRunning', isLCMRunning);
  let imageEl: HTMLImageElement;
  let containerEl: HTMLDivElement;
  let showInitialUI: boolean = true;

  // Estado para el modal QR
  let showQRModal: boolean = false;
  let photoUrl: string = '';
  let isTakingSnapshot: boolean = false;

  async function takeSnapshot() {
    if (isLCMRunning && !isTakingSnapshot) {
      isTakingSnapshot = true;

      // Capturar el contenedor completo con el marco
      const result = await captureContainerWithFrame(containerEl, {
        prompt: getPipelineValues()?.prompt,
        negative_prompt: getPipelineValues()?.negative_prompt,
        seed: getPipelineValues()?.seed,
        guidance_scale: getPipelineValues()?.guidance_scale
      });

      if (result.success && result.photo_url) {
        photoUrl = result.photo_url;
        showQRModal = true;
      } else {
        console.error('Error al tomar foto:', result.error);
        // Fallback: descargar directamente si falla el servidor
        snapImage(imageEl, {
          prompt: getPipelineValues()?.prompt,
          negative_prompt: getPipelineValues()?.negative_prompt,
          seed: getPipelineValues()?.seed,
          guidance_scale: getPipelineValues()?.guidance_scale
        });
      }

      isTakingSnapshot = false;
    }
  }

  function closeQRModal() {
    showQRModal = false;
    photoUrl = '';
  }

  function handleStartExperience() {
    showInitialUI = false;
    toggleLcmLive();
  }
</script>

<!-- Contenedor principal con formato 9:16 (vertical/portrait) -->
<div bind:this={containerEl} class="relative mx-auto aspect-[9/16] w-full max-w-md self-center">
  <!-- Área donde se muestra el video/imagen procesada - VA PRIMERO -->
  <!-- Ajusta estos valores (top, left, width, height) según la posición del hueco en tu marco -->
  <div class="absolute left-[7%] top-[2%] z-0 h-[86%] w-[84%]">
    <!-- svelte-ignore a11y-missing-attribute -->
    {#if isLCMRunning && $streamId}
      <img
        bind:this={imageEl}
        class="h-full w-full object-cover"
        src={'/api/stream/' + $streamId}
      />
      <div class="absolute bottom-1 right-1 z-10">
        <Button
          on:click={takeSnapshot}
          disabled={!isLCMRunning || isTakingSnapshot}
          title={'Tomar Foto'}
          classList={'text-sm ml-auto text-white p-2 shadow-lg rounded-lg ' +
            (isTakingSnapshot ? 'opacity-100 !bg-red-600' : 'opacity-70 hover:opacity-100')}
        >
          {#if isTakingSnapshot}
            <svg
              class="h-5 w-5 animate-spin"
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
            >
              <circle
                class="opacity-25"
                cx="12"
                cy="12"
                r="10"
                stroke="currentColor"
                stroke-width="4"
              ></circle>
              <path
                class="opacity-75"
                fill="currentColor"
                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
              ></path>
            </svg>
          {:else}
            <Floppy classList={''} />
          {/if}
        </Button>
      </div>
    {:else}
      <img
        class="h-full w-full bg-slate-200 object-cover"
        src="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="
      />
    {/if}
  </div>

  <!-- Imagen del marco como overlay - VA DESPUÉS del video con z-index mayor -->
  <img
    src={frameImagePath}
    alt="Frame"
    class="pointer-events-none absolute inset-0 z-10 h-full w-full object-contain"
  />

  <!-- UI inicial - se muestra sobre todo el marco -->
  {#if showInitialUI}
    <!-- Overlay con blur para el fondo -->
    <div class="absolute inset-0 z-40 backdrop-blur-sm"></div>

    <!-- Overlay de UI inicial centrado sobre el ImagePlayer -->
    <div
      class="absolute left-1/2 top-[43.5%] z-50 flex h-[75%] w-[75%] max-w-md -translate-x-1/2 -translate-y-1/2 flex-col items-center justify-center rounded-lg border-2 border-white bg-[url('/images/ui_start.jpeg')] bg-cover bg-center shadow-2xl"
      style="background-size: cover; background-position: center;"
    >
      <h2 class="mb-8 px-4 text-center text-3xl font-bold text-white md:text-4xl">
        CONVIÉRTETE EN UN ZOMBIE Y RECIBE TU RECUERDO
      </h2>
      <Button
        on:click={handleStartExperience}
        classList={'relative top-[155px] text-xl px-8 py-4 !bg-red-600 hover:!bg-red-700 w-[90%]'}
      >
        COMENZAR
      </Button>
    </div>
  {/if}
</div>

<!-- Modal QR -->
<QRModal {photoUrl} show={showQRModal} on:close={closeQRModal} />
