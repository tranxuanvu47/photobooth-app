import { Injectable } from '@angular/core';
import { EditorState } from '../models/editor.model';

@Injectable({
  providedIn: 'root'
})
export class ExportService {
  async exportAsImage(
    canvas: HTMLCanvasElement,
    state: EditorState
  ): Promise<{ blob: Blob; url: string; filename: string }> {
    const { format, quality, dpi } = state.exportSettings;

    // Create high-resolution export canvas
    const exportCanvas = await this.createExportCanvas(canvas, dpi);

    return new Promise((resolve, reject) => {
      exportCanvas.toBlob(
        blob => {
          if (!blob) {
            reject(new Error('Failed to create blob'));
            return;
          }

          const url = URL.createObjectURL(blob);
          const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
          const filename = `photo-booth-${timestamp}.${format}`;

          resolve({ blob, url, filename });
        },
        `image/${format}`,
        quality
      );
    });
  }

  async exportAsPDF(
    canvas: HTMLCanvasElement,
    state: EditorState
  ): Promise<{ blob: Blob; url: string; filename: string }> {
    // For PDF export, we'll create a simple implementation
    // In production, consider using jsPDF library
    const { blob, url } = await this.exportAsImage(canvas, state);
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
    const filename = `photo-booth-${timestamp}.pdf`;

    // For now, return as image blob (upgrade to actual PDF later with jsPDF)
    return { blob, url, filename };
  }

  private async createExportCanvas(sourceCanvas: HTMLCanvasElement, dpi: number): Promise<HTMLCanvasElement> {
    const scale = dpi / 96; // 96 is default screen DPI
    const exportCanvas = document.createElement('canvas');
    exportCanvas.width = sourceCanvas.width * scale;
    exportCanvas.height = sourceCanvas.height * scale;

    const ctx = exportCanvas.getContext('2d', {
      alpha: true,
      willReadFrequently: false
    });
    if (!ctx) {
      throw new Error('Failed to get canvas context');
    }

    // Enable high-quality image smoothing for export
    ctx.imageSmoothingEnabled = true;
    ctx.imageSmoothingQuality = 'high';

    // Scale the context to draw at higher DPI
    ctx.scale(scale, scale);
    ctx.drawImage(sourceCanvas, 0, 0);

    return exportCanvas;
  }

  downloadFile(url: string, filename: string): void {
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  }

  async shareFile(blob: Blob, filename: string): Promise<boolean> {
    if (navigator.share && navigator.canShare) {
      try {
        const file = new File([blob], filename, { type: blob.type });

        if (navigator.canShare({ files: [file] })) {
          await navigator.share({
            files: [file],
            title: 'Photo Booth',
            text: 'Check out my photo booth creation!'
          });
          return true;
        }
      } catch (err) {
        if ((err as Error).name !== 'AbortError') {
          console.error('Share failed:', err);
        }
      }
    }
    return false;
  }

  revokeUrl(url: string): void {
    URL.revokeObjectURL(url);
  }

  calculatePhysicalSize(width: number, height: number, dpi: number): { widthInches: number; heightInches: number } {
    return {
      widthInches: width / dpi,
      heightInches: height / dpi
    };
  }

  calculatePixelSize(widthInches: number, heightInches: number, dpi: number): { width: number; height: number } {
    return {
      width: Math.round(widthInches * dpi),
      height: Math.round(heightInches * dpi)
    };
  }
}

