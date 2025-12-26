import * as piexif from 'piexifjs';

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

// Función original para descargar directamente
export function snapImage(imageEl: HTMLImageElement, info: IImageInfo) {
  try {
    const zeroth: { [key: string]: any } = {};
    const exif: { [key: string]: any } = {};
    const gps: { [key: string]: any } = {};
    zeroth[piexif.ImageIFD.Make] = 'LCM Image-to-Image ControNet';
    zeroth[piexif.ImageIFD.ImageDescription] =
      `prompt: ${info?.prompt} | negative_prompt: ${info?.negative_prompt} | seed: ${info?.seed} | guidance_scale: ${info?.guidance_scale}`;
    zeroth[piexif.ImageIFD.Software] =
      'https://github.com/radames/Real-Time-Latent-Consistency-Model';
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
    a.download = `lcm_txt_2_img${Date.now()}.png`;
    a.click();
  } catch (err) {
    console.log(err);
  }
}

// Nueva función para subir al servidor y obtener URL para QR
export async function snapImageWithQR(
  imageEl: HTMLImageElement,
  info: IImageInfo
): Promise<SnapshotResult> {
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
    const dataURL = canvas.toDataURL('image/jpeg', 0.95);
    const withExif = piexif.insert(exifBytes, dataURL);

    // Enviar al servidor
    const response = await fetch('/api/snapshot', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ image: withExif })
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
    console.error('Error al guardar snapshot:', err);
    return {
      success: false,
      error: err instanceof Error ? err.message : 'Error desconocido'
    };
  }
}

// Genera URL del QR usando API de Google Charts
export function generateQRUrl(url: string, size: number = 300): string {
  return `https://api.qrserver.com/v1/create-qr-code/?size=${size}x${size}&data=${encodeURIComponent(
    url
  )}`;
}
