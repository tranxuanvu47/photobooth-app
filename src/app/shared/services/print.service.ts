import { Injectable, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { catchError, of, map } from 'rxjs';

export interface PrintOptions {
  copies: number;
  paperSize: '4x6' | '2x6';
  orientation: 'portrait' | 'landscape';
  fitToPage: boolean;
  margins: 'none' | 'minimal' | 'normal';
}

export interface PrintAgentStatus {
  available: boolean;
  version?: string;
  printers?: string[];
}

@Injectable({
  providedIn: 'root'
})
export class PrintService {
  private readonly agentUrl = 'http://localhost:3000';
  private readonly agentAvailable = signal<boolean>(false);
  private readonly agentPrinters = signal<string[]>([]);

  readonly agentAvailable$ = this.agentAvailable.asReadonly();
  readonly agentPrinters$ = this.agentPrinters.asReadonly();

  constructor(private http: HttpClient) {
    this.checkAgentAvailability();
  }

  private checkAgentAvailability(): void {
    this.http.get<PrintAgentStatus>(`${this.agentUrl}/status`).pipe(
      map(response => {
        this.agentAvailable.set(true);
        if (response.printers) {
          this.agentPrinters.set(response.printers);
        }
        return true;
      }),
      catchError(() => {
        this.agentAvailable.set(false);
        this.agentPrinters.set([]);
        return of(false);
      })
    ).subscribe();
  }

  async printWithBrowser(imageUrl: string, options: PrintOptions): Promise<void> {
    // Open print dialog with the image
    const printWindow = window.open('', '_blank');
    if (!printWindow) {
      throw new Error('Failed to open print window. Please allow popups.');
    }

    // Canon Selphy CP uses 4x6 inch paper (100x150mm)
    const paperWidth = options.paperSize === '4x6' 
      ? (options.orientation === 'portrait' ? '4in' : '6in')
      : '2in';
    
    const paperHeight = options.paperSize === '4x6'
      ? (options.orientation === 'portrait' ? '6in' : '4in')
      : '6in';

    const marginStyle = this.getMarginStyle(options.margins);

    printWindow.document.write(`
      <!DOCTYPE html>
      <html>
        <head>
          <title>Print Photo - Canon Selphy CP</title>
          <style>
            @page {
              size: ${paperWidth} ${paperHeight};
              margin: ${marginStyle};
            }
            body {
              margin: 0;
              padding: 0;
              display: flex;
              justify-content: center;
              align-items: center;
              min-height: 100vh;
            }
            img {
              max-width: 100%;
              max-height: 100%;
              ${options.fitToPage ? 'width: 100%; height: 100%; object-fit: contain;' : ''}
            }
            @media print {
              body {
                margin: 0;
                padding: 0;
              }
              @page {
                size: ${paperWidth} ${paperHeight};
                margin: ${marginStyle};
              }
            }
          </style>
        </head>
        <body>
          <img src="${imageUrl}" alt="Photo to print" onload="
            setTimeout(() => {
              window.print();
              setTimeout(() => window.close(), 100);
            }, 100);
          " />
        </body>
      </html>
    `);
    printWindow.document.close();
  }

  async printWithAgent(
    imageBlob: Blob,
    options: PrintOptions,
    printerName?: string
  ): Promise<boolean> {
    if (!this.agentAvailable()) {
      throw new Error('Print agent is not available');
    }

    try {
      const formData = new FormData();
      formData.append('image', imageBlob, 'photo.jpg');
      formData.append('copies', options.copies.toString());
      formData.append('paperSize', options.paperSize);
      formData.append('orientation', options.orientation);
      if (printerName) {
        formData.append('printer', printerName);
      }

      const response = await fetch(`${this.agentUrl}/print`, {
        method: 'POST',
        body: formData
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.message || 'Print failed');
      }

      return true;
    } catch (err) {
      console.error('Print agent error:', err);
      throw err;
    }
  }

  private getMarginStyle(margins: 'none' | 'minimal' | 'normal'): string {
    switch (margins) {
      case 'none':
        return '0';
      case 'minimal':
        return '0.125in';
      case 'normal':
        return '0.25in';
      default:
        return '0';
    }
  }

  async refreshAgentStatus(): Promise<void> {
    this.checkAgentAvailability();
  }
}

