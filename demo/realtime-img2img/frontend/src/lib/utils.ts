import * as piexif from 'piexifjs';
import html2canvas from 'html2canvas';
import ShareConfig from './config';

interface IImageInfo {
  prompt?: string;
  negative_prompt?: string;
  seed?: number;
  guidance_scale?: number;
}

interface SnapshotResult {
  success: boolean;
  photo_id?: string;
  photo_url?: string;
  error?: string;
}

// Función auxiliar para añadir metadatos EXIF
async function addExifMetadata(
  dataURL: string,
  info?: IImageInfo
): Promise<string> {
  try {
    const zeroth: { [key: string]: any } = {};
    const exif: { [key: string]: any } = {};
    const gps: { [key: string]: any } = {};
    
    zeroth[piexif.ImageIFD.Make] = 'Zombie Photo Booth';
    zeroth[piexif.ImageIFD.ImageDescription] =
      `prompt: ${info?.prompt} | negative_prompt: ${info?.negative_prompt} | seed: ${info?.seed} | guidance_scale: ${info?.guidance_scale}`;
    zeroth[piexif.ImageIFD.Software] = 'StreamDiffusion Zombie Experience';
    exif[piexif.ExifIFD.DateTimeOriginal] = new Date().toISOString();

    const exifObj = { '0th': zeroth, Exif: exif, GPS: gps };
    const exifBytes = piexif.dump(exifObj);
    
    return piexif.insert(exifBytes, dataURL);
  } catch (err) {
    console.error('Error añadiendo EXIF:', err);
    return dataURL; // Devolver sin EXIF si falla
  }
}

// Función para procesar y compartir la imagen
async function processAndShareImage(
  imageDataURL: string,
  info?: IImageInfo,
  formUrl?: string
): Promise<SnapshotResult> {
  try {
    // Añadir metadatos EXIF si es necesario
    const withExif = await addExifMetadata(imageDataURL, info);
    
    // Obtener modo de compartir (solo digitalocean o local ahora)
    const shareMode = localStorage.getItem('shareMode') || ShareConfig.mode;
    
    const requestBody: any = {
      image: withExif,
      mode: shareMode === 'digitalocean' ? 'external' : 'url',
      service: shareMode === 'digitalocean' ? 'digitalocean' : 'local'
    };
    
    // Agregar form_url si está disponible
    if (formUrl) {
      requestBody.form_url = formUrl;
    }
    
    const response = await fetch('/api/snapshot', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(requestBody)
    });

    if (!response.ok) {
      throw new Error(`Error del servidor: ${response.status}`);
    }

    const result = await response.json();
    return {
      success: true,
      photo_id: result.photo_id,
      photo_url: result.photo_url
    };
  } catch (err) {
    console.error('Error al procesar imagen:', err);
    return {
      success: false,
      error: err instanceof Error ? err.message : 'Error desconocido'
    };
  }
}

// Función para capturar el contenedor completo con el marco
export async function captureContainerWithFrame(
  containerEl: HTMLDivElement,
  imageEl: HTMLImageElement,
  frameEl: HTMLImageElement,
  info?: IImageInfo,
  formUrl?: string
): Promise<SnapshotResult> {
  let canvas: HTMLCanvasElement | null = null;
  try {
    // Esperar un momento para que las imágenes se carguen completamente
    await new Promise(resolve => setTimeout(resolve, 200));
    
    // Obtener las dimensiones REALES del contenedor tal como se ve en pantalla
    const rect = containerEl.getBoundingClientRect();
    const containerWidth = rect.width;
    const containerHeight = rect.height;
    const containerAspectRatio = containerWidth / containerHeight;
    
    console.log('📐 Dimensiones del contenedor:', { 
      width: containerWidth, 
      height: containerHeight,
      aspectRatio: containerAspectRatio.toFixed(4)
    });
    
    // Obtener dimensiones naturales de la imagen del stream (800x800 = 1:1)
    const streamNaturalWidth = imageEl.naturalWidth;
    const streamNaturalHeight = imageEl.naturalHeight;
    const streamAspectRatio = streamNaturalWidth / streamNaturalHeight;
    
    console.log('📸 Dimensiones naturales del stream:', { 
      width: streamNaturalWidth, 
      height: streamNaturalHeight,
      aspectRatio: streamAspectRatio.toFixed(4)
    });
    
    const scale = 2; // Escala para mayor resolución
    
    // Calcular dimensiones del canvas final (9:16)
    const finalWidth = Math.round(containerWidth * scale);
    const finalHeight = Math.round(containerHeight * scale);
    
    // Crear canvas final con dimensiones exactas del contenedor
    canvas = document.createElement('canvas');
    canvas.width = finalWidth;
    canvas.height = finalHeight;
    const ctx = canvas.getContext('2d');
    
    if (!ctx) {
      throw new Error('No se pudo obtener contexto 2D del canvas');
    }
    
    // Fondo negro
    ctx.fillStyle = '#000000';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    
    // Dibujar la imagen del stream manteniendo su aspect ratio natural (1:1)
    // LLENAR TODA LA ALTURA - la imagen se acercará y recortará por los lados si es necesario
    let streamDrawWidth: number;
    let streamDrawHeight: number;
    let streamOffsetX: number;
    let streamOffsetY: number;
    
    // FORZAR que llene TODA la altura del contenedor (sin barras negras arriba/abajo)
    streamDrawHeight = finalHeight; // Usar TODA la altura disponible
    streamDrawWidth = Math.round(streamDrawHeight * streamAspectRatio); // Mantener proporción 1:1
    
    // La imagen será más ancha que el contenedor (porque es 1:1 y el contenedor es 9:16)
    // Centrar horizontalmente - se recortará por los lados, pero llenará toda la altura
    streamOffsetX = Math.round((finalWidth - streamDrawWidth) / 2); // Centrar
    streamOffsetY = 0; // Comenzar desde arriba - SIN barras negras arriba/abajo
    
    console.log('🔍 Cálculo de escalado:', {
      contenedor: { width: finalWidth, height: finalHeight },
      imagenOriginal: { width: streamNaturalWidth, height: streamNaturalHeight, aspectRatio: streamAspectRatio },
      imagenEscalada: { width: streamDrawWidth, height: streamDrawHeight, offsetX: streamOffsetX, offsetY: streamOffsetY },
      ocupacion: {
        ancho: `${Math.min(100, (finalWidth / streamDrawWidth) * 100).toFixed(1)}%`,
        alto: '100%'
      }
    });
    
    // Dibujar la imagen del stream SIN estirar, escalada para ocupar más área
    ctx.drawImage(
      imageEl,
      0, 0, streamNaturalWidth, streamNaturalHeight, // Fuente completa
      streamOffsetX, streamOffsetY, streamDrawWidth, streamDrawHeight // Destino escalado pero proporcional
    );
    
    console.log('📸 Imagen del stream dibujada:', {
      source: { width: streamNaturalWidth, height: streamNaturalHeight },
      destination: { x: streamOffsetX, y: streamOffsetY, width: streamDrawWidth, height: streamDrawHeight }
    });
    
    // Dibujar el marco encima usando html2canvas para capturar correctamente
    if (frameEl && frameEl.complete) {
      const frameRect = frameEl.getBoundingClientRect();
      const frameCanvas = await html2canvas(frameEl, {
        backgroundColor: null,
        scale: scale,
        logging: false,
        useCORS: true,
        allowTaint: true,
        width: frameRect.width,
        height: frameRect.height
      });
      
      // Dibujar el marco en el canvas final
      ctx.drawImage(frameCanvas, 0, 0, finalWidth, finalHeight);
      
      // Limpiar el canvas temporal del marco
      const frameCtx = frameCanvas.getContext('2d');
      if (frameCtx) {
        frameCtx.clearRect(0, 0, frameCanvas.width, frameCanvas.height);
      }
      frameCanvas.width = 0;
      frameCanvas.height = 0;
      
      console.log('🖼️ Marco dibujado sobre la imagen');
    }

    console.log('✅ Canvas final creado:', { 
      width: canvas.width, 
      height: canvas.height,
      aspectRatio: (canvas.width / canvas.height).toFixed(4)
    });

    // Convertir a JPEG manteniendo las proporciones exactas
    const dataURL = canvas.toDataURL('image/jpeg', 0.95);
    
    // Limpiar canvas inmediatamente después de obtener la data URL
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    canvas.width = 0;
    canvas.height = 0;
    canvas = null;
    
    // Subir y compartir
    const result = await processAndShareImage(dataURL, info, formUrl);
    
    // Limpiar la data URL de memoria si es posible
    return result;
  } catch (err) {
    console.error('Error al capturar con marco:', err);
    // Asegurar limpieza incluso en caso de error
    if (canvas) {
      try {
        const ctx = canvas.getContext('2d');
        if (ctx) {
          ctx.clearRect(0, 0, canvas.width, canvas.height);
        }
        canvas.width = 0;
        canvas.height = 0;
      } catch (cleanupErr) {
        // Ignorar errores de limpieza
      }
    }
    return {
      success: false,
      error: err instanceof Error ? err.message : 'Error desconocido'
    };
  }
}

// Función principal para capturar snapshot con QR (mantener por compatibilidad)
export async function snapImageWithQR(
  imageEl: HTMLImageElement,
  info: IImageInfo,
  formUrl?: string
): Promise<SnapshotResult> {
  // Función antigua, usar processAndShareImage internamente
  const canvas = document.createElement('canvas');
  canvas.width = imageEl.naturalWidth;
  canvas.height = imageEl.naturalHeight;
  const ctx = canvas.getContext('2d') as CanvasRenderingContext2D;
  
  if (!ctx) {
    return {
      success: false,
      error: 'No se pudo obtener contexto 2D del canvas'
    };
  }
  
  ctx.drawImage(imageEl, 0, 0);
  const dataURL = canvas.toDataURL('image/jpeg', 0.95);
  
  // Limpiar canvas inmediatamente
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  canvas.width = 0;
  canvas.height = 0;
  
  const result = await processAndShareImage(dataURL, info);
  
  return result;
}

// Función original para descargar directamente (fallback)
export function snapImage(imageEl: HTMLImageElement, info: IImageInfo) {
  try {
    const zeroth: { [key: string]: any } = {};
    const exif: { [key: string]: any } = {};
    const gps: { [key: string]: any } = {};
    zeroth[piexif.ImageIFD.Make] = 'Zombie Photo Booth';
    zeroth[piexif.ImageIFD.ImageDescription] =
      `prompt: ${info?.prompt} | negative_prompt: ${info?.negative_prompt} | seed: ${info?.seed} | guidance_scale: ${info?.guidance_scale}`;
    zeroth[piexif.ImageIFD.Software] = 'StreamDiffusion Zombie Experience';
    exif[piexif.ExifIFD.DateTimeOriginal] = new Date().toISOString();

    const exifObj = { '0th': zeroth, Exif: exif, GPS: gps };
    const exifBytes = piexif.dump(exifObj);

    const canvas = document.createElement('canvas');
    canvas.width = imageEl.naturalWidth;
    canvas.height = imageEl.naturalHeight;
    const ctx = canvas.getContext('2d') as CanvasRenderingContext2D;
    ctx.drawImage(imageEl, 0, 0);
    const dataURL = canvas.toDataURL('image/jpeg');
    const withExif = piexif.insert(exifBytes, dataURL);

    const a = document.createElement('a');
    a.href = withExif;
    a.download = `zombie_photo_${Date.now()}.jpg`;
    a.click();
  } catch (err) {
    console.log(err);
  }
}

// Genera URL del QR usando API de Google Charts
export function generateQRUrl(url: string, size: number = 300): string {
  return `https://api.qrserver.com/v1/create-qr-code/?size=${size}x${size}&data=${encodeURIComponent(
    url
  )}`;
}