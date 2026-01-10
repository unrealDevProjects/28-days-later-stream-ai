declare module 'piexifjs' {
  export namespace ImageIFD {
    export const Make: number;
    export const ImageDescription: number;
    export const Software: number;
  }

  export namespace ExifIFD {
    export const DateTimeOriginal: number;
  }

  export interface ExifObject {
    '0th': { [key: string]: any };
    Exif: { [key: string]: any };
    GPS: { [key: string]: any };
  }

  export function dump(exifObj: ExifObject): string;
  export function insert(exifBytes: string, dataURL: string): string;
}
