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
        animateIntensity(25000);
      } else {
        // Detener animación si está corriendo
        stopAnimationIfRunning();

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

<main class="container mx-auto flex max-w-5xl flex-col gap-3 px-4 py-4">
  <Warning bind:message={warningMessage}></Warning>
  <article class="text-center">
    {#if pageContent}
      {@html pageContent}
    {/if}
    {#if maxQueueSize > 0}
      <p class="text-sm">
        There are <span id="queue_size" class="font-bold">{currentQueueSize}</span>
        user(s) sharing the same GPU, affecting real-time performance. Maximum queue size is {maxQueueSize}.
        <a
          href="https://huggingface.co/spaces/radames/Real-Time-Latent-Consistency-Model?duplicate=true"
          target="_blank"
          class="text-blue-500 underline hover:no-underline">Duplicate</a
        > and run it on your own GPU.
      </p>
    {/if}
  </article>
  {#if pipelineParams}
    <article class="my-3 grid grid-cols-1 gap-3 sm:grid-cols-2">
      {#if isImageMode}
        <div class="max-w-[1rem]">
          <VideoInput
            width={Number(pipelineParams.width.default)}
            height={Number(pipelineParams.width.default)}
          ></VideoInput>
        </div>
      {/if}
      <div class="relative flex items-center justify-center sm:col-span-2">
        <ImagePlayer {toggleLcmLive} />
      </div>
      <div class="sm:col-span-2">
        <Button on:click={toggleLcmLive} {disabled} classList={'text-lg my-1 p-2'}>
          {#if isLCMRunning}
            Stop
          {:else}
            Start
          {/if}
        </Button>
        <PipelineOptions {pipelineParams} on:userInput={handleSliderUserInput}></PipelineOptions>
      </div>
    </article>
  {:else}
    <!-- loading -->
    <div class="flex items-center justify-center gap-3 py-48 text-2xl">
      <Spinner classList={'animate-spin opacity-50'}></Spinner>
      <p>Loading...</p>
    </div>
  {/if}
</main>

<style lang="postcss">
  :global(html) {
    @apply text-black dark:bg-gray-900 dark:text-white;
  }
</style>
