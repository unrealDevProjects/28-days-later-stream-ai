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

  // Estado para la cuenta atrás
  let showCountdown: boolean = false;
  let countdownNumber: number = 3;
  let countdownTimeoutId: number | null = null;

  // Función para iniciar la cuenta atrás
  export function startCountdown() {
    if (countdownTimeoutId !== null) {
      clearTimeout(countdownTimeoutId);
      countdownTimeoutId = null;
    }

    showCountdown = true;
    countdownNumber = 3;

    // Mostrar 3, luego 2, luego 1, luego 0, cada uno por 1 segundo
    // Después de mostrar 0 por 1 segundo, capturar la foto
    const showNextNumber = () => {
      // Después de 1 segundo, cambiar el número
      countdownTimeoutId = window.setTimeout(() => {
        if (countdownNumber > 0) {
          // Si todavía no es 0, reducir y continuar
          countdownNumber--;
          showNextNumber();
        } else {
          // Si ya es 0, después de mostrarlo 1 segundo, capturar
          showCountdown = false;
          countdownTimeoutId = null;
          takeSnapshot();
        }
      }, 1000); // 1 segundo por número
    };

    // Iniciar la cuenta atrás (mostrar 3 primero)
    showNextNumber();
  }

  // Función para detener la cuenta atrás
  export function stopCountdown() {
    if (countdownTimeoutId !== null) {
      clearTimeout(countdownTimeoutId);
      countdownTimeoutId = null;
    }
    showCountdown = false;
  }

  // Exportar función para que pueda ser llamada desde el componente padre
  export async function takeSnapshot() {
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
    // Detener cuenta atrás si está activa
    stopCountdown();
    
    // Detener el stream si está corriendo y volver a la pantalla principal
    if (isLCMRunning) {
      toggleLcmLive();
    }
    
    // Resetear a la pantalla inicial
    showInitialUI = true;
  }

  function handleStartExperience() {
    showInitialUI = false;
    toggleLcmLive();
  }
</script>

<!-- Contenedor principal con formato 9:16 (vertical/portrait) -->
<div bind:this={containerEl} class="relative mx-auto aspect-[9/16] w-full max-w-md self-center">
  <!-- Fondo: fondo.png - solo visible cuando showInitialUI es true -->
  {#if showInitialUI}
    <img
      src="/images/fondo.png"
      alt="Fondo"
      class="pointer-events-none absolute inset-0 z-0 h-full w-full object-contain"
    />
  {/if}

  <!-- Área donde se muestra el video/imagen procesada - solo visible cuando showInitialUI es false -->
  {#if !showInitialUI}
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
  {/if}

  <!-- Imagen del marco como overlay - sin blur -->
  <img
    src={frameImagePath}
    alt="Frame"
    class="pointer-events-none absolute inset-0 z-10 h-full w-full object-contain"
  />

  <!-- Cuenta atrás visual -->
  {#if showCountdown && !showInitialUI}
    <div class="absolute inset-0 z-50 flex items-center justify-center">
      <img
        src={`/images/${countdownNumber}.png`}
        alt="Countdown {countdownNumber}"
        class="max-h-[60%] max-w-[60%] object-contain drop-shadow-2xl"
        style="animation: pulse 0.5s ease-in-out;"
      />
    </div>
  {/if}

  <!-- UI inicial - se muestra sobre todo el marco -->
  {#if showInitialUI}
    <!-- Copy: copy.png arriba y centrado -->
    <img
      src="/images/copy.png"
      alt="Copy"
      class="pointer-events-none absolute left-1/2 top-20 z-50 -translate-x-1/2 object-contain"
      style="max-height: 30%; max-width: 70%;"
    />

    <!-- Botón: boton.png abajo y centrado -->
    <button
      on:click={handleStartExperience}
      class="absolute bottom-[30%] left-1/2 z-50 -translate-x-1/2 cursor-pointer border-none bg-transparent p-0 hover:opacity-90 active:opacity-80"
    >
      <img
        src="/images/boton.png"
        alt="Botón Start"
        class="pointer-events-none block object-contain"
        style="max-height: 100px; max-width: 150px; width: auto; height: auto; display: block; margin: 0 auto;"
      />
    </button>
  {/if}
</div>

<!-- Modal QR -->
<QRModal {photoUrl} show={showQRModal} on:close={closeQRModal} />

<style>
  @keyframes pulse {
    0%, 100% {
      transform: scale(1);
      opacity: 1;
    }
    50% {
      transform: scale(1.1);
      opacity: 0.9;
    }
  }
</style>
