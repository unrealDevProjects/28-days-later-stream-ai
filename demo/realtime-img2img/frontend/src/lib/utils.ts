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
  info?: IImageInfo
): Promise<SnapshotResult> {
  try {
    // Añadir metadatos EXIF si es necesario
    const withExif = await addExifMetadata(imageDataURL, info);
    
    // Obtener modo de compartir (solo digitalocean o local ahora)
    const shareMode = localStorage.getItem('shareMode') || ShareConfig.mode;
    
    const response = await fetch('/api/snapshot', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        image: withExif,
        mode: shareMode === 'digitalocean' ? 'external' : 'url',
        service: shareMode === 'digitalocean' ? 'digitalocean' : 'local'
      })
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
  info?: IImageInfo
): Promise<SnapshotResult> {
  try {
    // Esperar un momento para que el DOM se estabilice
    await new Promise(resolve => setTimeout(resolve, 100));
    
    // Capturar con html2canvas - opciones básicas
    const canvas = await html2canvas(containerEl, {
      backgroundColor: null,
      scale: 1.5,
      logging: false,
      useCORS: true,
      allowTaint: true
    });

    // Convertir a JPEG
    const dataURL = canvas.toDataURL('image/jpeg', 0.9);
    
    // Subir y compartir
    const result = await processAndShareImage(dataURL, info);
    
    return result;
  } catch (err) {
    console.error('Error al capturar con marco:', err);
    return {
      success: false,
      error: err instanceof Error ? err.message : 'Error desconocido'
    };
  }
}

// Función principal para capturar snapshot con QR (mantener por compatibilidad)
export async function snapImageWithQR(
  imageEl: HTMLImageElement,
  info: IImageInfo
): Promise<SnapshotResult> {
  // Función antigua, usar processAndShareImage internamente
  const canvas = document.createElement('canvas');
  canvas.width = imageEl.naturalWidth;
  canvas.height = imageEl.naturalHeight;
  const ctx = canvas.getContext('2d') as CanvasRenderingContext2D;
  ctx.drawImage(imageEl, 0, 0);
  const dataURL = canvas.toDataURL('image/jpeg', 0.95);
  
  return await processAndShareImage(dataURL, info);
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