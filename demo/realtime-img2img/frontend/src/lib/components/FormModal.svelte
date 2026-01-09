<script lang="ts">
  import { createEventDispatcher, onMount } from 'svelte';
  import Button from './Button.svelte';

  export let formUrl: string = '';
  export let show: boolean = false;

  const dispatch = createEventDispatcher();
  let iframeEl: HTMLIFrameElement;

  function close() {
    dispatch('close');
  }

  // Intentar detectar cuando el formulario se completa
  // Nota: Por CORS puede que no funcione, pero lo intentamos
  onMount(() => {
    if (iframeEl) {
      try {
        // Escuchar mensajes del iframe si Sony Pictures los envía
        const handleMessage = (event: MessageEvent) => {
          // Verificar origen por seguridad (ajusta según la URL de Sony)
          if (event.data === 'form-submitted' || event.data?.type === 'form-submitted') {
            close();
          }
        };
        window.addEventListener('message', handleMessage);
        return () => window.removeEventListener('message', handleMessage);
      } catch (e) {
        // Si hay error de CORS, simplemente continuamos sin detectar submit
        console.log('No se puede acceder al iframe por CORS, se requerirá cierre manual');
      }
    }
  });
</script>

{#if show && formUrl}
  <!-- svelte-ignore a11y-no-noninteractive-element-interactions -->
  <!-- Overlay oscuro -->
  <div
    class="fixed inset-0 z-[110] flex items-center justify-center bg-black/90 backdrop-blur-sm"
    on:click={close}
    on:keydown={(e) => e.key === 'Escape' && close()}
    role="dialog"
    aria-modal="true"
    tabindex="-1"
  >
    <!-- svelte-ignore a11y-no-noninteractive-element-interactions -->
    <!-- Modal con formulario -->
    <div
      class="relative mx-4 flex max-w-2xl flex-col rounded-2xl border-2 border-red-600 bg-gradient-to-b from-gray-900 to-black shadow-2xl"
      on:click|stopPropagation
      on:keydown|stopPropagation
      role="document"
      style="width: min(90vw, 600px); height: min(80vh, 700px);"
    >
      <!-- Botón cerrar -->
      <button
        class="absolute right-3 top-3 z-10 rounded-full bg-black/50 p-2 text-2xl text-white/70 transition-colors hover:bg-black/70 hover:text-white"
        on:click={close}
        aria-label="Cerrar formulario"
        title="Cerrar"
      >
        ×
      </button>

      <!-- Título opcional -->
      <!-- <h2 class="mb-2 px-6 pt-6 text-center text-xl font-bold text-red-500">
        Completa el formulario
      </h2> -->

      <!-- Iframe con el formulario -->
      <div class="flex-1 overflow-hidden rounded-2xl">
        <iframe
          bind:this={iframeEl}
          src={formUrl}
          class="h-full w-full border-0"
          title="Formulario"
          allow="camera; microphone; autoplay; encrypted-media"
        ></iframe>
      </div>

      <!-- Botón de cerrar en la parte inferior -->
      <div class="p-4">
        <Button on:click={close} classList="w-full !bg-gray-700 hover:!bg-gray-600">
          Cerrar
        </Button>
      </div>
    </div>
  </div>
{/if}

<style>
  /* Animación de entrada */
  div[role='dialog'] {
    animation: fadeIn 0.2s ease-out;
  }

  div[role='document'] {
    animation: slideUp 0.3s ease-out;
  }

  @keyframes fadeIn {
    from {
      opacity: 0;
    }
    to {
      opacity: 1;
    }
  }

  @keyframes slideUp {
    from {
      opacity: 0;
      transform: translateY(20px);
    }
    to {
      opacity: 1;
      transform: translateY(0);
    }
  }
</style>
