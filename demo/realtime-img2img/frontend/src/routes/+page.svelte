<script lang="ts">
  import { onMount } from 'svelte';
  import type { Fields, PipelineInfo } from '$lib/types';
  import { PipelineMode } from '$lib/types';
  import ImagePlayer from '$lib/components/ImagePlayer.svelte';
  import VideoInput from '$lib/components/VideoInput.svelte';
  import Button from '$lib/components/Button.svelte';
  import PipelineOptions from '$lib/components/PipelineOptions.svelte';
  import Spinner from '$lib/icons/spinner.svelte';
  import Warning from '$lib/components/Warning.svelte';
  import { lcmLiveStatus, lcmLiveActions, LCMLiveStatus } from '$lib/lcmLive';
  import { mediaStreamActions, onFrameChangeStore } from '$lib/mediaStream';
  import {
    getPipelineValues,
    deboucedPipelineValues,
    pipelineValues,
    setAnimating
  } from '$lib/store';

  let pipelineParams: Fields;
  let pipelineInfo: PipelineInfo;
  let pageContent: string;
  let isImageMode: boolean = false;
  let maxQueueSize: number = 0;
  let currentQueueSize: number = 0;
  let queueCheckerRunning: boolean = false;
  let warningMessage: string = '';

  onMount(() => {
    getSettings();
  });

  async function getSettings() {
    const settings = await fetch('/api/settings').then((r) => r.json());
    pipelineParams = settings.input_params.properties;
    pipelineInfo = settings.info.properties;
    isImageMode = pipelineInfo.input_mode.default === PipelineMode.IMAGE;
    maxQueueSize = settings.max_queue_size;
    pageContent = settings.page_content;
    console.log(pipelineParams);

    // Inicializar el slider de intensidad a 0.0
    pipelineValues.update((values) => ({
      ...values,
      denoise_strength: 0.0
    }));

    toggleQueueChecker(true);
  }
  function toggleQueueChecker(start: boolean) {
    queueCheckerRunning = start && maxQueueSize > 0;
    if (start) {
      getQueueSize();
    }
  }
  async function getQueueSize() {
    if (!queueCheckerRunning) {
      return;
    }
    const data = await fetch('/api/queue').then((r) => r.json());
    currentQueueSize = data.queue_size;
    setTimeout(getQueueSize, 10000);
  }

  function getSreamdata() {
    if (isImageMode) {
      return [getPipelineValues(), $onFrameChangeStore?.blob];
    } else {
      return [$deboucedPipelineValues];
    }
  }

  $: isLCMRunning = $lcmLiveStatus !== LCMLiveStatus.DISCONNECTED;
  $: if ($lcmLiveStatus === LCMLiveStatus.TIMEOUT) {
    warningMessage = 'Session timed out. Please try again.';
  }

  // Handler para cuando el usuario interactúa directamente con el slider
  function handleSliderUserInput() {
    // Detener la animación si está corriendo
    if (isAnimating) {
      stopAnimationIfRunning();
    }
  }
  let disabled = false;
  let intensityAnimationId: number | null = null;
  let isAnimating = false; // Flag para saber si estamos animando automáticamente
  let lastManualValue: number | null = null; // Para detectar cambios manuales
  let imagePlayerRef: ImagePlayer; // Referencia al componente ImagePlayer
  let autoCaptureTimeoutId: number | null = null; // ID del timeout para captura automática
  let showSettings: boolean = false; // Estado para mostrar/ocultar controles
  
  // URL del formulario de Sony Pictures
  // Intentamos añadir parámetros para indicar que está en iframe y evitar el banner de cookies
  let sonyFormUrl: string = 'https://www.sonypictures.es/form/28-ad-peor-selfie?iframe=true&embedded=true&skipBanner=true';

  // Función para animar la intensidad de 0 a 1 de manera fluida
  // El blend se hace en el backend sin llamar a prepare(), así que es instantáneo
  function animateIntensity(duration: number = 5000) {
    // Detener animación anterior si existe
    if (intensityAnimationId !== null) {
      cancelAnimationFrame(intensityAnimationId);
      intensityAnimationId = null;
    }

    isAnimating = true;
    setAnimating(true);

    const startValue = 0.0;
    const endValue = 1.0; // Ahora va de 0 a 1 (blend completo)
    const startTime = performance.now();
    let lastValue = startValue;
    let frameCount = 0;

    function updateIntensity() {
      const now = performance.now();
      const elapsed = now - startTime;
      const progress = Math.min(elapsed / duration, 1.0);

      // Easing suave (ease-in-out)
      const easedProgress =
        progress < 0.5 ? 2 * progress * progress : 1 - Math.pow(-2 * progress + 2, 2) / 2;

      const currentValue = startValue + (endValue - startValue) * easedProgress;
      const newValue = Number(currentValue.toFixed(3));

      // Actualizar cada ~3 frames para reducir carga pero mantener fluidez
      frameCount++;
      if (frameCount % 3 === 0 || progress >= 1.0) {
        if (Math.abs(newValue - lastValue) > 0.005 || progress >= 1.0) {
          pipelineValues.update((values) => ({
            ...values,
            denoise_strength: newValue
          }));
          lastValue = newValue;
        }
      }

      if (progress < 1.0) {
        intensityAnimationId = requestAnimationFrame(updateIntensity);
      } else {
        pipelineValues.update((values) => ({
          ...values,
          denoise_strength: endValue
        }));
        // Log deshabilitado para mejor rendimiento
        // console.log('Animación completada en:', endValue);
        intensityAnimationId = null;
        isAnimating = false; // Marcar que terminó la animación
        setAnimating(false); // Notificar al store que terminó la animación
        
        // Esperar 11 segundos y luego iniciar cuenta atrás (cuenta atrás dura 4 segundos = 15 total)
        if (autoCaptureTimeoutId !== null) {
          clearTimeout(autoCaptureTimeoutId);
        }
        autoCaptureTimeoutId = window.setTimeout(() => {
          if (imagePlayerRef && isLCMRunning) {
            console.log('Iniciando cuenta atrás antes de captura automática');
            imagePlayerRef.startCountdown();
          }
          autoCaptureTimeoutId = null;
        }, 5000); // 5 segundos antes de iniciar cuenta atrás (4 segundos de cuenta atrás = 15 total)
      }
    }

    // Iniciar la animación
    // Log deshabilitado para mejor rendimiento
    // console.log('Iniciando animación de intensidad de', startValue, 'a', endValue);
    intensityAnimationId = requestAnimationFrame(updateIntensity);
  }

  // Función para detener la animación si el usuario mueve el slider manualmente
  function stopAnimationIfRunning() {
    if (isAnimating && intensityAnimationId !== null) {
      cancelAnimationFrame(intensityAnimationId);
      intensityAnimationId = null;
      isAnimating = false;
      setAnimating(false); // Notificar al store que terminó la animación
      // Log deshabilitado para mejor rendimiento
      // console.log('Animación detenida por cambio manual del slider');
    }
    // Cancelar captura automática si está programada
    if (autoCaptureTimeoutId !== null) {
      clearTimeout(autoCaptureTimeoutId);
      autoCaptureTimeoutId = null;
    }
    // Detener cuenta atrás si está activa
    if (imagePlayerRef) {
      imagePlayerRef.stopCountdown();
    }
  }

  async function toggleLcmLive() {
    try {
      if (!isLCMRunning) {
        if (isImageMode) {
          await mediaStreamActions.enumerateDevices();
          await mediaStreamActions.start();
        }
        disabled = true;

        // Resetear el slider a 0 antes de iniciar
        lastManualValue = 0.0;
        pipelineValues.update((values) => ({
          ...values,
          denoise_strength: 0.0
        }));

        // Pequeño delay para asegurar que el valor se propague
        await new Promise((resolve) => setTimeout(resolve, 100));

        await lcmLiveActions.start(getSreamdata);
        disabled = false;
        toggleQueueChecker(false);

        // Pequeño delay antes de iniciar la animación para asegurar que el stream esté listo
        await new Promise((resolve) => setTimeout(resolve, 500));

        // Iniciar la animación automática de intensidad
        // Duración de 15 segundos (15000ms) para una transformación más lenta y suave
        animateIntensity(15000);
      } else {
        // Detener animación si está corriendo
        stopAnimationIfRunning();
        
        // Cancelar captura automática si está programada
        if (autoCaptureTimeoutId !== null) {
          clearTimeout(autoCaptureTimeoutId);
          autoCaptureTimeoutId = null;
        }
        // Detener cuenta atrás si está activa
        if (imagePlayerRef) {
          imagePlayerRef.stopCountdown();
        }

        // Forzar limpieza de memoria si hay una captura pendiente
        if (imagePlayerRef) {
          // Resetear cualquier estado de snapshot bloqueado
          setTimeout(() => {
            if (imagePlayerRef && !isLCMRunning) {
              // Asegurar limpieza completa
              console.log('Limpieza de memoria después de detener stream');
            }
          }, 100);
        }

        if (isImageMode) {
          mediaStreamActions.stop();
        }
        lcmLiveActions.stop();
        toggleQueueChecker(true);
      }
    } catch (e) {
      warningMessage = e instanceof Error ? e.message : '';
      disabled = false;
      toggleQueueChecker(true);

      // Detener animación en caso de error
      stopAnimationIfRunning();
    }
  }
</script>

<svelte:head>
  <script
    src="https://cdnjs.cloudflare.com/ajax/libs/iframe-resizer/4.3.9/iframeResizer.contentWindow.min.js"
  ></script>
</svelte:head>

<main class="flex min-h-screen w-full flex-col items-center justify-center bg-gray-900 p-0 overflow-hidden">
  <Warning bind:message={warningMessage}></Warning>
  
  {#if pipelineParams}
    <!-- Botón de Settings flotante -->
    <button
      on:click={() => showSettings = !showSettings}
      class="fixed right-4 top-4 z-50 rounded-full bg-transparent p-3 text-white shadow-lg hover:bg-blue-700 transition-colors"
      title="Settings"
    >
      <svg xmlns="http://www.w3.org/2000/svg" class="h-1 w-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
      </svg>
    </button>

    <!-- VideoInput siempre renderizado pero muy pequeño (10x10px) para que funcione el stream -->
    {#if isImageMode}
      <div class="video-input-mini" style="position: fixed; top: 4px; left: 4px; width: 10px; height: 10px; z-index: 1; overflow: hidden;">
        <VideoInput
          width={Number(pipelineParams.width.default)}
          height={Number(pipelineParams.width.default)}
        ></VideoInput>
      </div>
    {/if}

    <!-- Panel de Settings (oculto por defecto) -->
    {#if showSettings}
      <div class="fixed right-4 top-20 z-50 max-w-md rounded-lg bg-white p-4 shadow-2xl max-h-[80vh] overflow-y-auto">
        <h2 class="mb-4 text-xl font-bold text-gray-800">Configuración</h2>
        
        <div class="mb-4">
          <Button on:click={toggleLcmLive} {disabled} classList={'text-lg my-1 p-2 w-full'}>
            {#if isLCMRunning}
              Stop
            {:else}
              Start
            {/if}
          </Button>
        </div>
        
        <PipelineOptions {pipelineParams} on:userInput={handleSliderUserInput}></PipelineOptions>
        
        {#if maxQueueSize > 0}
          <div class="mt-4 text-sm text-gray-600">
            <p>
              Hay <span class="font-bold">{currentQueueSize}</span> usuario(s) compartiendo la misma GPU.
            </p>
          </div>
        {/if}
        
        {#if pageContent}
          <div class="mt-4 text-sm text-gray-600">
            {@html pageContent}
          </div>
        {/if}
      </div>
    {/if}

    <!-- Contenedor principal con ImagePlayer centrado y ajustado a pantalla -->
    <div class="flex items-center justify-center w-full h-screen">
      <ImagePlayer bind:this={imagePlayerRef} {toggleLcmLive} formUrl={sonyFormUrl} />
    </div>
  {:else}
    <!-- loading -->
    <div class="flex items-center justify-center gap-3 py-48 text-2xl text-white">
      <Spinner classList={'animate-spin opacity-50'}></Spinner>
      <p>Loading...</p>
    </div>
  {/if}
</main>

<style lang="postcss">
  :global(html) {
    @apply text-black dark:bg-gray-900 dark:text-white;
  }

  :global(.video-input-mini > div) {
    width: 10px !important;
    height: 10px !important;
    min-width: 10px !important;
    min-height: 10px !important;
    max-width: 10px !important;
    max-height: 10px !important;
  }

  :global(.video-input-mini video),
  :global(.video-input-mini canvas) {
    width: 10px !important;
    height: 10px !important;
    min-width: 10px !important;
    min-height: 10px !important;
  }
</style>
