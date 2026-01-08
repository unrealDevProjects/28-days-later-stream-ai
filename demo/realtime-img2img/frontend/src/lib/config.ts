/**
 * Configuración simplificada para compartir fotos
 * Solo dos opciones: DigitalOcean Spaces o Local
 */

export const ShareConfig = {
  /**
   * Modo de compartir:
   * - 'digitalocean': Usa DigitalOcean Spaces (permanente, requiere credenciales)
   * - 'local': Usa servidor local (temporal, requiere acceso a la red local)
   */
  mode: 'digitalocean', // o 'local'

  /**
   * Configurar automáticamente al cargar la página
   */
  autoConfig: true
};

// Aplicar configuración automáticamente
if (typeof window !== 'undefined' && ShareConfig.autoConfig) {
  localStorage.setItem('shareMode', ShareConfig.mode);

  console.log(`[Config] Modo de compartir: ${ShareConfig.mode}`);
}

export default ShareConfig;