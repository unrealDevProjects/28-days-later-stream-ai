<script lang="ts">
  import { lcmLiveStatus, LCMLiveStatus, streamId } from '$lib/lcmLive';
  import { getPipelineValues } from '$lib/store';
  import { mediaStream, mediaStreamStatus, MediaStreamStatusEnum } from '$lib/mediaStream';

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
  let frameEl: HTMLImageElement; // Referencia al elemento del marco
  let showInitialUI: boolean = true;
  let originalVideoEl: HTMLVideoElement; // Video element para la cámara original muy pequeña

  // Actualizar el video cuando cambie el mediaStream
  $: if (originalVideoEl && $mediaStream) {
    originalVideoEl.srcObject = $mediaStream;
  }

  // Estado para el modal QR
  let showQRModal: boolean = false;
  let photoUrl: string = '';
  let isTakingSnapshot: boolean = false;
  let qrModalTimeoutId: number | null = null; // Timeout para cerrar automáticamente el QR después de 40s

  // URL del formulario de Sony Pictures - puede venir como prop o desde config
  // Nota: Ya no se usa para mostrar el FormModal, el middleware se encarga de todo
  export let formUrl: string = '';

  // Estado para las instrucciones
  let showInstructions: boolean = false;
  let instructionsTimeoutId: number | null = null;
  let instructionsShown: boolean = false; // Flag para asegurar que solo se muestren una vez
  
  // Estado para la cuenta atrás
  let showCountdown: boolean = false;
  let countdownNumber: number = 3;
  let countdownTimeoutId: number | null = null;
  
  // Mostrar instrucciones cuando el stream esté visible
  $: if (isLCMRunning && $streamId && !showInitialUI && !instructionsShown) {
    // El stream está visible, mostrar instrucciones durante 5 segundos
    showInstructions = true;
    instructionsShown = true;
    
    // Limpiar timeout anterior si existe
    if (instructionsTimeoutId !== null) {
      clearTimeout(instructionsTimeoutId);
      instructionsTimeoutId = null;
    }
    
    // Ocultar instrucciones después de 5 segundos
    instructionsTimeoutId = window.setTimeout(() => {
      showInstructions = false;
      instructionsTimeoutId = null;
    }, 5000);
  }
  
  // Resetear el flag cuando se reinicia la experiencia
  $: if (showInitialUI) {
    instructionsShown = false;
    showInstructions = false;
    if (instructionsTimeoutId !== null) {
      clearTimeout(instructionsTimeoutId);
      instructionsTimeoutId = null;
    }
  }

  // Función para iniciar la cuenta atrás (sin instrucciones, ya se mostraron al inicio)
  export function startCountdown() {
    // Limpiar timeouts anteriores si existen
    if (countdownTimeoutId !== null) {
      clearTimeout(countdownTimeoutId);
      countdownTimeoutId = null;
    }

    // Iniciar la cuenta atrás directamente
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
          // Si ya es 0, después de mostrarlo 1 segundo, ocultar y capturar
          showCountdown = false;
          countdownTimeoutId = null;
          // Esperar un momento para que el DOM se actualice y oculte el contador antes de capturar
          setTimeout(() => {
            takeSnapshot();
          }, 100); // 100ms de delay para asegurar que el contador se oculte
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
    if (instructionsTimeoutId !== null) {
      clearTimeout(instructionsTimeoutId);
      instructionsTimeoutId = null;
    }
    showCountdown = false;
    showInstructions = false;
    instructionsShown = false;
  }

  // Exportar función para que pueda ser llamada desde el componente padre
  export async function takeSnapshot() {
    // Evitar múltiples capturas simultáneas - validación más estricta
    if (!isLCMRunning) {
      console.warn('Snapshot bloqueado - Stream no está corriendo');
      return;
    }
    
    if (isTakingSnapshot) {
      console.warn('Snapshot bloqueado - Ya hay una captura en progreso');
      return;
    }

    // Verificar que tenemos los elementos necesarios
    if (!containerEl || !imageEl) {
      console.error('Snapshot bloqueado - Elementos del DOM no disponibles');
      return;
    }

    isTakingSnapshot = true;
    console.log('Iniciando captura de foto...');

    let timeoutId: number | null = null;
    
    try {
      // Timeout de seguridad para evitar que se quede cargando indefinidamente
      const timeoutPromise = new Promise<never>((_, reject) => {
        timeoutId = window.setTimeout(() => {
          reject(new Error('Timeout: La captura tardó más de 15 segundos'));
        }, 15000);
      });

      const capturePromise = captureContainerWithFrame(containerEl, imageEl, frameEl, {
        prompt: getPipelineValues()?.prompt,
        negative_prompt: getPipelineValues()?.negative_prompt,
        seed: getPipelineValues()?.seed,
        guidance_scale: getPipelineValues()?.guidance_scale
      }, formUrl);

      const result = await Promise.race([capturePromise, timeoutPromise]);

      // Limpiar timeout si completó a tiempo
      if (timeoutId !== null) {
        clearTimeout(timeoutId);
        timeoutId = null;
      }

      if (result && result.success && result.photo_url) {
        photoUrl = result.photo_url;
        console.log('Foto capturada exitosamente, URL:', result.photo_url);
        // Mostrar directamente el QR modal (el middleware se encarga del formulario)
        showQRModal = true;
        // Iniciar timeout para cerrar automáticamente después de 40 segundos
        startQRModalAutoClose();
      } else {
        console.warn('Captura con marco falló, intentando fallback...');
        // Fallback: capturar solo la imagen sin marco
        const fallbackResult = await snapImageWithQR(imageEl, {
          prompt: getPipelineValues()?.prompt,
          negative_prompt: getPipelineValues()?.negative_prompt,
          seed: getPipelineValues()?.seed,
          guidance_scale: getPipelineValues()?.guidance_scale
        }, formUrl);
        if (fallbackResult && fallbackResult.success && fallbackResult.photo_url) {
          photoUrl = fallbackResult.photo_url;
          console.log('Fallback exitoso, URL:', fallbackResult.photo_url);
          // Mostrar directamente el QR modal (el middleware se encarga del formulario)
          showQRModal = true;
          // Iniciar timeout para cerrar automáticamente después de 40 segundos
          startQRModalAutoClose();
        } else {
          console.error('Ambos métodos de captura fallaron', fallbackResult);
        }
      }
    } catch (error) {
      console.error('Error al capturar foto:', error);
      
      // Limpiar timeout si aún está activo
      if (timeoutId !== null) {
        clearTimeout(timeoutId);
        timeoutId = null;
      }
      
      // Intentar fallback una vez más SOLO si el stream sigue corriendo
      if (isLCMRunning && imageEl) {
        try {
          const fallbackResult = await snapImageWithQR(imageEl, {
            prompt: getPipelineValues()?.prompt,
            negative_prompt: getPipelineValues()?.negative_prompt,
            seed: getPipelineValues()?.seed,
            guidance_scale: getPipelineValues()?.guidance_scale
          });
          if (fallbackResult && fallbackResult.success && fallbackResult.photo_url) {
            photoUrl = fallbackResult.photo_url;
            // Mostrar directamente el QR modal (el middleware se encarga del formulario)
            showQRModal = true;
            // Iniciar timeout para cerrar automáticamente después de 40 segundos
            startQRModalAutoClose();
          } else {
            console.error('Fallback también falló:', fallbackResult);
          }
        } catch (fallbackError) {
          console.error('Error en fallback también:', fallbackError);
        }
      }
    } finally {
      // Limpiar timeout si aún está activo
      if (timeoutId !== null) {
        clearTimeout(timeoutId);
      }
      
      // SIEMPRE resetear el estado, sin importar qué pasó
      isTakingSnapshot = false;
      console.log('Estado de snapshot reseteado');
    }
  }

  // Función para iniciar el timeout de cierre automático del QR
  function startQRModalAutoClose() {
    // Limpiar timeout anterior si existe
    if (qrModalTimeoutId !== null) {
      clearTimeout(qrModalTimeoutId);
      qrModalTimeoutId = null;
    }
    
    // Configurar timeout de 40 segundos para cerrar automáticamente
    qrModalTimeoutId = window.setTimeout(() => {
      console.log('Timeout de 40s alcanzado, cerrando QR modal automáticamente...');
      closeQRModal();
    }, 40000); // 40 segundos
  }

  // Función para limpiar el timeout del QR
  function clearQRModalTimeout() {
    if (qrModalTimeoutId !== null) {
      clearTimeout(qrModalTimeoutId);
      qrModalTimeoutId = null;
    }
  }

  function closeQRModal() {
    console.log('Cerrando QR modal, recargando página...');
    
    // Limpiar el timeout si existe
    clearQRModalTimeout();
    
    // Cerrar modal
    showQRModal = false;
    
    // Recargar la página inmediatamente usando múltiples métodos para asegurar que funcione
    // Esto resetea completamente el estado de la aplicación
    try {
      // Método 1: Forzar reload desde el servidor
      window.location.reload(true);
    } catch (e) {
      // Método 2: Fallback usando href
      try {
        window.location.href = window.location.href;
      } catch (e2) {
        // Método 3: Último recurso - replace
        window.location.replace(window.location.pathname);
      }
    }
  }

  function handleStartExperience() {
    showInitialUI = false;
    // Iniciar el stream inmediatamente - las instrucciones se mostrarán cuando el stream esté visible
    toggleLcmLive();
  }
</script>

<!-- Contenedor principal con formato 9:16 (vertical/portrait) - ajustado al tamaño del marco -->
<div bind:this={containerEl} class="relative mx-auto aspect-[9/16] w-full max-w-full h-full max-h-screen self-center" style="width: min(100vw, 56.25vh); height: min(100vh, 177.78vw);">
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
    <div class="absolute left-[0%] top-[0%] z-0 h-[100%] w-[100%] bg-black overflow-hidden">
      <!-- svelte-ignore a11y-missing-attribute -->
      {#if isLCMRunning && $streamId}
        <img
          bind:this={imageEl}
          class="h-full w-full object-cover object-center"
          style="image-rendering: -webkit-optimize-contrast; image-rendering: crisp-edges;"
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

  <!-- Vista previa de cámara original muy pequeña (10x10px, circular, siempre visible pero casi imperceptible) -->
  {#if !showInitialUI && isLCMRunning && $mediaStreamStatus === MediaStreamStatusEnum.CONNECTED && $mediaStream}
    <video
      bind:this={originalVideoEl}
      class="absolute left-[8%] top-[3%] z-20 rounded-full"
      autoplay
      muted
      playsinline
      style="pointer-events: none; width: 10px; height: 10px; object-fit: cover;"
    ></video>
  {/if}

  <!-- Imagen del marco como overlay - sin blur -->
  <img
    bind:this={frameEl}
    src={frameImagePath}
    alt="Frame"
    class="pointer-events-none absolute inset-0 z-10 h-full w-full object-contain"
  />

  <!-- Instrucciones visuales (encima del stream, durante 5 segundos) -->
  {#if showInstructions && !showInitialUI && isLCMRunning && $streamId}
    <div class="absolute inset-0 z-50 flex items-start justify-center pt-20">
      <img
        src="/images/instrucciones.svg"
        alt="Instrucciones: Quédate quieto"
        class="max-h-[20%] max-w-[60%] object-contain drop-shadow-2xl"
        style="animation: fadeIn 0.3s ease-out;"
      />
    </div>
  {/if}

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
