<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import { generateQRUrl } from '$lib/utils';
  import Button from './Button.svelte';

  export let photoUrl: string = '';
  export let show: boolean = false;

  const dispatch = createEventDispatcher();

  function close() {
    dispatch('close');
  }

  $: qrImageUrl = photoUrl ? generateQRUrl(photoUrl, 250) : '';
</script>

{#if show}
  <!-- svelte-ignore a11y-no-noninteractive-element-interactions -->
  <!-- Overlay oscuro -->
  <div
    class="fixed inset-0 z-[100] flex items-center justify-center bg-black/80 backdrop-blur-sm"
    on:click={close}
    on:keydown={(e) => e.key === 'Escape' && close()}
    role="dialog"
    aria-modal="true"
    tabindex="-1"
  >
    <!-- svelte-ignore a11y-no-noninteractive-element-interactions -->
    <!-- Modal -->
    <div
      class="relative mx-4 flex max-w-sm flex-col items-center rounded-2xl border-2 border-red-600 bg-gradient-to-b from-gray-900 to-black p-6 shadow-2xl"
      on:click|stopPropagation
      on:keydown|stopPropagation
      role="document"
    >
      <!-- Botón cerrar -->
      <button
        class="absolute right-3 top-3 text-3xl text-white/70 transition-colors hover:text-white"
        on:click={close}
        aria-label="Cerrar"
      >
        ×
      </button>

      <!-- Título -->
      <h2 class="mb-4 text-center text-2xl font-bold text-red-500">¡TU FOTO ZOMBIE!</h2>

      <!-- Subtítulo -->
      <p class="mb-4 text-center text-sm text-gray-300">
        Escanea el código QR para descargar tu foto
      </p>

      <!-- QR Code -->
      <div class="mb-4 rounded-lg bg-white p-3 shadow-lg">
        {#if qrImageUrl}
          <img
            src={qrImageUrl}
            alt="Código QR para descargar tu foto"
            class="h-[250px] w-[250px]"
          />
        {:else}
          <div class="flex h-[250px] w-[250px] items-center justify-center text-gray-500">
            Generando QR...
          </div>
        {/if}
      </div>

      <!-- URL (truncada) -->
      <p class="mb-4 max-w-full truncate text-xs text-gray-500">
        {photoUrl}
      </p>

      <!-- Botones -->
      <div class="flex w-full gap-3">
        <Button
          on:click={() => window.open(photoUrl, '_blank')}
          classList="flex-1 !bg-gray-700 hover:!bg-gray-600"
        >
          Ver foto
        </Button>
        <Button on:click={close} classList="flex-1 !bg-red-600 hover:!bg-red-700">Cerrar</Button>
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



