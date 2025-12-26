import { derived, get, writable, type Readable, type Writable } from 'svelte/store';

export const pipelineValues: Writable<Record<string, any>> = writable({});
let debounceTimeout: ReturnType<typeof setTimeout> | null = null;
let isAnimating = false; // Flag para saber si estamos animando

// Función para marcar que estamos animando (llamada desde +page.svelte)
export const setAnimating = (animating: boolean) => {
  isAnimating = animating;
};

export const deboucedPipelineValues: Readable<Record<string, any>> = derived(
  pipelineValues,
  ($pipelineValues, set) => {
    // Limpiar timeout anterior si existe
    if (debounceTimeout !== null) {
      clearTimeout(debounceTimeout);
    }

    // Durante la animación, usar un debounce más corto para mayor fluidez
    // Fuera de la animación, usar un debounce más largo para evitar llamadas excesivas
    const debounceTime = isAnimating ? 50 : 150;

    debounceTimeout = setTimeout(() => {
      set($pipelineValues);
      debounceTimeout = null;
    }, debounceTime);

    return () => {
      if (debounceTimeout !== null) {
        clearTimeout(debounceTimeout);
        debounceTimeout = null;
      }
    };
  }
);

export const getPipelineValues = () => get(pipelineValues);
