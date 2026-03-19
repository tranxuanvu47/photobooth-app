import { Component, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { PrintService, PrintOptions } from '../../shared/services/print.service';

@Component({
  selector: 'app-print',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './print.component.html',
  styleUrls: ['./print.component.scss']
})
export class PrintComponent implements OnInit {
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly printService = inject(PrintService);

  readonly imageUrl = signal<string | null>(null);
  readonly isPrinting = signal<boolean>(false);
  readonly printOptions = signal<PrintOptions>({
    copies: 1,
    paperSize: '4x6',
    orientation: 'portrait',
    fitToPage: true,
    margins: 'none'
  });

  readonly agentAvailable = this.printService.agentAvailable$;
  readonly availablePrinters = this.printService.agentPrinters$;
  readonly selectedPrinter = signal<string>('');

  ngOnInit(): void {
    const printId = this.route.snapshot.paramMap.get('id');
    if (printId) {
      const url = localStorage.getItem(`print-${printId}`);
      if (url) {
        this.imageUrl.set(url);
      } else {
        // Redirect back if no image found
        this.router.navigate(['/editor']);
      }
    }

    // Refresh print agent status
    this.printService.refreshAgentStatus();
  }

  updatePrintOptions<K extends keyof PrintOptions>(key: K, value: PrintOptions[K]): void {
    this.printOptions.update(opts => ({ ...opts, [key]: value }));
  }

  async printWithBrowser(): Promise<void> {
    const url = this.imageUrl();
    if (!url) {
      return;
    }

    this.isPrinting.set(true);
    try {
      await this.printService.printWithBrowser(url, this.printOptions());
    } catch (err) {
      console.error('Print failed:', err);
      alert('Failed to print. Please try again.');
    } finally {
      this.isPrinting.set(false);
    }
  }

  async printWithAgent(): Promise<void> {
    const url = this.imageUrl();
    if (!url) {
      return;
    }

    this.isPrinting.set(true);
    try {
      // Convert data URL to blob
      const response = await fetch(url);
      const blob = await response.blob();
      
      const printerName = this.selectedPrinter() || undefined;
      await this.printService.printWithAgent(blob, this.printOptions(), printerName);
      
      alert('Print job sent successfully!');
    } catch (err) {
      console.error('Print failed:', err);
      alert(`Failed to print: ${(err as Error).message}`);
    } finally {
      this.isPrinting.set(false);
    }
  }

  goBack(): void {
    this.router.navigate(['/editor']);
  }
}

