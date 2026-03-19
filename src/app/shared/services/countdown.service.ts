import { Injectable, signal } from '@angular/core';
import { CountdownConfig } from '../models/editor.model';

@Injectable({
  providedIn: 'root'
})
export class CountdownService {
  private readonly isRunning = signal<boolean>(false);
  private readonly currentValue = signal<number>(0);
  private timerId: number | null = null;

  readonly isRunning$ = this.isRunning.asReadonly();
  readonly currentValue$ = this.currentValue.asReadonly();

  start(config: CountdownConfig): void {
    // Stop any existing countdown
    this.stop();

    if (config.duration === 0) {
      // Immediate capture
      this.currentValue.set(0);
      config.onComplete?.();
      return;
    }

    this.isRunning.set(true);
    this.currentValue.set(config.duration);
    config.onTick?.(config.duration);

    this.timerId = window.setInterval(() => {
      const current = this.currentValue();
      const next = current - 1;

      if (next <= 0) {
        this.stop();
        config.onComplete?.();
      } else {
        this.currentValue.set(next);
        config.onTick?.(next);
      }
    }, 1000);
  }

  stop(): void {
    if (this.timerId !== null) {
      clearInterval(this.timerId);
      this.timerId = null;
    }
    this.isRunning.set(false);
    this.currentValue.set(0);
  }

  ngOnDestroy(): void {
    this.stop();
  }
}

