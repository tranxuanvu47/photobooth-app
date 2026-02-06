import { Component, output, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Frame, FRAME_THEMES, FrameTheme } from '../../models/frame.model';

@Component({
  selector: 'app-frame-gallery',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './frame-gallery.component.html',
  styleUrls: ['./frame-gallery.component.scss']
})
export class FrameGalleryComponent {
  frameSelected = output<Frame>();
  
  readonly frames = FRAME_THEMES;
  readonly selectedFrame = signal<string | null>(null);
  readonly filterTheme = signal<FrameTheme | 'all'>('all');

  get filteredFrames(): Frame[] {
    const theme = this.filterTheme();
    if (theme === 'all') {
      return this.frames;
    }
    return this.frames.filter(f => f.theme === theme);
  }

  selectFrame(frame: Frame): void {
    this.selectedFrame.set(frame.id);
    this.frameSelected.emit(frame);
  }

  clearFrame(): void {
    this.selectedFrame.set(null);
    this.frameSelected.emit(null as any);
  }

  setFilter(theme: FrameTheme | 'all'): void {
    this.filterTheme.set(theme);
  }
}

