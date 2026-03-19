import { Component, ViewChild, ElementRef, signal, inject, OnDestroy, AfterViewInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
// import * as fabric from 'fabric';
declare const fabric: any;
import { LayoutPickerComponent } from '../../shared/components/layout-picker/layout-picker.component';
import { FrameGalleryComponent } from '../../shared/components/frame-gallery/frame-gallery.component';
import { CanvasEditorComponent } from '../../shared/components/canvas-editor/canvas-editor.component';
import { EditorStateService } from '../../shared/services/editor-state.service';
import { ExportService } from '../../shared/services/export.service';
import { LayoutConfig, PRESETS } from '../../shared/models/layout.model';
import { Frame, FRAME_THEMES } from '../../shared/models/frame.model';

@Component({
  selector: 'app-editor',
  standalone: true,
  imports: [
    CommonModule,
    LayoutPickerComponent,
    FrameGalleryComponent,
    CanvasEditorComponent
  ],
  templateUrl: './editor.component.html',
  styleUrls: ['./editor.component.scss']
})
export class EditorComponent implements AfterViewInit, OnDestroy {
  @ViewChild(CanvasEditorComponent) canvasEditor!: CanvasEditorComponent;
  @ViewChild('video') videoElement!: ElementRef<HTMLVideoElement>;

  private readonly editorState = inject(EditorStateService);
  private readonly exportService = inject(ExportService);
  private readonly router = inject(Router);

  readonly activeTab = signal<'layout' | 'frame'>('layout');
  readonly selectedLayout = signal<LayoutConfig | null>(null);
  readonly selectedFrame = signal<Frame | null>(null);
  readonly canvas = signal<any | null>(null);
  readonly isExporting = signal<boolean>(false);
  readonly isProcessing = signal<boolean>(false);
  readonly isMobile = signal<boolean>(false);
  readonly cameraRotation = signal<number>(0); // 0, 90, 180, 270

  // Camera and capture state
  readonly isCapturing = signal<boolean>(false);
  readonly capturedPhotos = signal<string[]>([]);
  readonly currentPhotoIndex = signal<number>(0);
  readonly countdownValue = signal<number>(0);
  readonly totalPhotos = signal<number>(0);
  readonly countdownTime = signal<number>(3); // Default 3 seconds, user can change in banner

  // Countdown time options (in seconds)
  readonly countdownOptions = [0, 1, 2, 3, 5, 10];

  private stream: MediaStream | null = null;
  private countdownInterval: any = null;


  onLayoutSelected(layout: LayoutConfig): void {
    this.selectedLayout.set(layout);
    this.editorState.setLayout(layout);
    this.totalPhotos.set(layout.type);

    // Auto-select frame for calendar-polaroid layout (only 1 image in 1 frame)
    if (layout.preset === 'calendar-polaroid') {
      const calendarFrame = FRAME_THEMES.find(f => f.id === 'march-2026-calendar');
      if (calendarFrame) {
        this.selectedFrame.set(calendarFrame);
        this.editorState.setFrame(calendarFrame);
      }
    }

    // Auto-switch to frame tab after selecting layout
    this.activeTab.set('frame');
  }

  onFrameSelected(frame: Frame | null): void {
    this.selectedFrame.set(frame);
    this.editorState.setFrame(frame);
  }

  onCountdownTimeChange(event: Event): void {
    const selectElement = event.target as HTMLSelectElement;
    const value = parseInt(selectElement.value, 10);
    console.log('🔄 Countdown time changed to:', value, 'seconds');
    this.countdownTime.set(value);
  }

  rotateCamera(): void {
    const current = this.cameraRotation();
    const next = (current + 90) % 360;
    console.log('🔄 Camera rotation changed to:', next, 'degrees');
    this.cameraRotation.set(next);
  }

  onCanvasReady(canvas: any): void {
    console.log('Canvas ready event received');
    this.canvas.set(canvas);

    // Only add photos if we have captured photos (final canvas view, not preview)
    const photos = this.capturedPhotos();
    if (photos.length > 0) {
      this.isProcessing.set(true); // Start processing

      // Wait longer for frame overlay to load, then add photos
      setTimeout(() => {
        const layout = this.selectedLayout();
        const frame = this.selectedFrame();

        console.log('Adding photos to canvas:', photos.length, 'photos');
        console.log('Layout:', layout?.name, 'Slots:', layout?.slots.length);
        console.log('Frame:', frame?.name);

        if (this.canvasEditor && layout) {
          // Add photos with slight delay between each for smooth animation
          let processedCount = 0;

          photos.forEach((photo, index) => {
            setTimeout(() => {
              const slotId = layout.slots[index]?.id;
              console.log(`Adding photo ${index + 1} to slot ${slotId}`);
              this.canvasEditor.addImage(photo, slotId);

              processedCount++;
              if (processedCount === photos.length) {
                // All photos added, give a small buffer then finish processing
                setTimeout(() => {
                  this.isProcessing.set(false);
                }, 500);
              }
            }, index * 100); // Stagger by 100ms for smooth appearance
          });
        } else {
          console.error('Cannot add photos:', {
            hasEditor: !!this.canvasEditor,
            photosCount: photos.length,
            hasLayout: !!layout
          });
          this.isProcessing.set(false);
        }
      }, 500); // Increased delay to ensure frame overlay is loaded
    }
  }

  async ngAfterViewInit(): Promise<void> {
    // Check mobile
    const userAgent = navigator.userAgent || navigator.vendor || (window as any).opera;
    if (/android/i.test(userAgent) || /iPad|iPhone|iPod/.test(userAgent)) {
      this.isMobile.set(true);
    }

    // Auto-select calendar layout and frame
    this.initializeCalendarLayout();

    // Start camera immediately when component loads
    await this.startCamera();

    // Listen for Enter key
    // Listen for Enter key
    this.setupKeyboardListeners();
  }

  private stopCamera(): void {
    if (this.stream) {
      this.stream.getTracks().forEach(track => track.stop());
      this.stream = null;
    }
  }

  private isCameraRestarting = false;


  checkOrientation(): void {
    if (!this.isMobile() || !this.stream || this.isCameraRestarting) return;

    // Simple landscape check
    const isLandscape = window.innerWidth > window.innerHeight;
    const track = this.stream.getVideoTracks()[0];
    const settings = track?.getSettings();

    // If we are in landscape, but stream is portrait (height > width)
    if (isLandscape && settings && settings.height && settings.width && settings.height > settings.width) {
      console.log('Orientation mismatch: Restarting camera for landscape');
      this.isCameraRestarting = true;
      // Small delay to let browser settle
      setTimeout(() => {
        this.startCamera().then(() => {
          this.isCameraRestarting = false;
        });
      }, 500);
    }
  }

  private initializeCalendarLayout(): void {
    // Create calendar-polaroid layout
    const calendarPreset = PRESETS['calendar-polaroid'];
    const calendarLayout: LayoutConfig = {
      ...calendarPreset,
      id: `layout-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
    };

    // Auto-select calendar layout
    this.selectedLayout.set(calendarLayout);
    this.editorState.setLayout(calendarLayout);
    this.totalPhotos.set(calendarLayout.type);

    // Auto-select March 2026 Calendar frame
    const calendarFrame = FRAME_THEMES.find(f => f.id === 'march-2026-calendar');
    if (calendarFrame) {
      this.selectedFrame.set(calendarFrame);
      this.editorState.setFrame(calendarFrame);
    }
  }

  private async startCamera(): Promise<void> {
    this.stopCamera();

    try {
      const constraints: MediaStreamConstraints = {
        video: {
          facingMode: 'user',
          width: { ideal: 3840 },
          height: { ideal: 2160 }
        },
        audio: false
      };

      if (this.isMobile()) {
        constraints.video = {
          facingMode: 'user',
          // Default to whatever the camera provides, we will rotate it manually
          width: { ideal: 1920 },
          height: { ideal: 1080 }
        };
      }

      this.stream = await navigator.mediaDevices.getUserMedia(constraints);

      if (this.videoElement) {
        const video = this.videoElement.nativeElement;
        video.srcObject = this.stream;
        video.onloadedmetadata = () => {
          video.play();
          console.log('Camera started successfully');
        };
      }
    } catch (err) {
      console.error('Camera error:', err);
      // alert('Failed to access camera. Please allow camera permissions and refresh the page.');
      // Suppress alert on restart to avoid spamming
    }
  }

  private setupKeyboardListeners(): void {
    document.addEventListener('keydown', (event: KeyboardEvent) => {
      if (event.key === 'Enter' && !this.isCapturing() && this.capturedPhotos().length === 0) {
        this.startCapture();
      }
    });
  }

  startCapture(): void {
    const layout = this.selectedLayout();
    if (!layout || this.isCapturing()) return;

    console.log('Starting capture sequence');
    this.isCapturing.set(true);
    this.capturedPhotos.set([]);
    this.currentPhotoIndex.set(0);
    this.totalPhotos.set(layout.type);

    // Start capture sequence immediately if no countdown, otherwise small delay
    const countdownSeconds = this.countdownTime();
    if (countdownSeconds === 0) {
      // No countdown - capture immediately
      this.captureNextPhoto();
    } else {
      // Small delay before starting countdown
      setTimeout(() => this.captureNextPhoto(), 100);
    }
  }

  private captureNextPhoto(): void {
    const currentIndex = this.currentPhotoIndex();
    const total = this.totalPhotos();

    if (currentIndex >= total) {
      // All photos captured
      this.finishCapture();
      return;
    }

    // Start countdown with user-selected time
    const countdownSeconds = this.countdownTime();
    console.log('🎯 Countdown time selected:', countdownSeconds, 'seconds');

    if (countdownSeconds === 0) {
      // No countdown, capture immediately
      console.log('⚡ No countdown - capturing immediately');
      this.countdownValue.set(0);
      this.performCapture();
      return;
    }

    // Set countdown value and start countdown
    console.log('⏱️ Starting countdown from', countdownSeconds, 'seconds');
    this.countdownValue.set(countdownSeconds);
    this.countdownInterval = setInterval(() => {
      const current = this.countdownValue();
      if (current <= 1) {
        clearInterval(this.countdownInterval);
        this.countdownValue.set(0);
        // Capture the photo
        this.performCapture();
      } else {
        this.countdownValue.set(current - 1);
      }
    }, 1000);
  }

  private performCapture(): void {
    if (!this.videoElement) {
      console.error('Video element not found');
      return;
    }

    const video = this.videoElement.nativeElement;

    if (!video.videoWidth || !video.videoHeight) {
      console.error('Video not ready:', video.videoWidth, 'x', video.videoHeight);
      return;
    }

    // Determine capture resolution
    // Limit to 1920px max dimension to prevent memory crashes on mobile
    const maxDimension = 1920;
    let width = video.videoWidth;
    let height = video.videoHeight;

    // Scale down if video stream is too huge (e.g. 4K on mobile)
    if (width > maxDimension || height > maxDimension) {
      const ratio = width / height;
      if (width > height) {
        width = maxDimension;
        height = Math.round(width / ratio);
      } else {
        height = maxDimension;
        width = Math.round(height * ratio);
      }
    }

    // Rotate 90 degrees if mobile AND in portrait mode
    // If user is in landscape, browser gives landscape stream, so no rotation needed.
    const isPortrait = window.innerWidth < window.innerHeight;
    const rotate90 = this.isMobile() && isPortrait;

    // Calculate crop dimensions
    // We want the final result (after rotation if applicable) to be 4:3 aspect ratio.
    const targetRatio = 4 / 3;

    // If rotating 90deg, the "source" crop should be 3:4 (0.75).
    // If not rotating, source crop is 4:3 (1.33).
    const cropRatio = rotate90 ? 3 / 4 : 4 / 3;
    const sourceRatio = width / height;

    let sourceW = width;
    let sourceH = height;
    let sourceX = 0;
    let sourceY = 0;

    if (sourceRatio > cropRatio) {
      // Source is wider than target: Crop Width (sides)
      sourceW = height * cropRatio;
      sourceX = (width - sourceW) / 2;
    } else {
      // Source is taller than target: Crop Height (top/bottom)
      sourceH = width / cropRatio;
      sourceY = (height - sourceH) / 2;
    }

    // Canvas dimensions will match the CROP dimensions (swapped if rotating)
    const canvas = document.createElement('canvas');

    if (rotate90) {
      canvas.width = sourceH;
      canvas.height = sourceW;
    } else {
      canvas.width = sourceW;
      canvas.height = sourceH;
    }

    const ctx = canvas.getContext('2d');
    if (ctx) {
      // Enable high-quality image smoothing for crisp rendering
      ctx.imageSmoothingEnabled = true;
      ctx.imageSmoothingQuality = 'high';

      if (rotate90) {
        // Rotation Logic:
        // 1. Move origin to center of destination canvas
        ctx.translate(canvas.width / 2, canvas.height / 2);

        // 2. Rotate 90 degrees
        ctx.rotate(90 * Math.PI / 180);

        // 3. Draw image centered. 
        // We draw the CROPPED region from video to the centered rect
        // Dest rect is -sourceW/2, -sourceH/2, sourceW, sourceH
        ctx.drawImage(video, sourceX, sourceY, sourceW, sourceH, -sourceW / 2, -sourceH / 2, sourceW, sourceH);
      } else {
        // Draw cropped video to canvas
        ctx.drawImage(video, sourceX, sourceY, sourceW, sourceH, 0, 0, sourceW, sourceH);
      }

      // Process image to ensure it's under 5MB
      const maxSizeBytes = 5 * 1024 * 1024; // 5MB
      let imageData = canvas.toDataURL('image/png'); // Default High Quality

      // Check size (base64 length * 0.75 is approx binary size)
      let approxSize = imageData.length * 0.75;

      console.log('Initial Capture Size:', (approxSize / 1024 / 1024).toFixed(2), 'MB');

      if (approxSize > maxSizeBytes) {
        console.warn('⚠️ Image too large, compressing...');

        // Try JPEG with high quality first (usually drastic reduction)
        imageData = canvas.toDataURL('image/jpeg', 0.95);
        approxSize = imageData.length * 0.75;
        console.log('JPEG 0.95 Size:', (approxSize / 1024 / 1024).toFixed(2), 'MB');

        // If still too big, scale down the canvas
        if (approxSize > maxSizeBytes) {
          let scale = 0.9;
          // Iteratively scale down until under limit
          while (approxSize > maxSizeBytes && scale > 0.1) {
            const newWidth = Math.floor(canvas.width * scale);
            const newHeight = Math.floor(canvas.height * scale);

            const scaledCanvas = document.createElement('canvas');
            scaledCanvas.width = newWidth;
            scaledCanvas.height = newHeight;
            const scaledCtx = scaledCanvas.getContext('2d');

            if (scaledCtx) {
              scaledCtx.imageSmoothingEnabled = true;
              scaledCtx.imageSmoothingQuality = 'high';
              scaledCtx.drawImage(canvas, 0, 0, newWidth, newHeight);

              // Use JPEG 0.9 for scaled versions
              imageData = scaledCanvas.toDataURL('image/jpeg', 0.90);
              approxSize = imageData.length * 0.75;
              console.log(`Scaled (${scale.toFixed(1)}) Size:`, (approxSize / 1024 / 1024).toFixed(2), 'MB');

              if (approxSize <= maxSizeBytes) break;

              scale -= 0.1;
            } else {
              console.error('Failed to create scaled context');
              break;
            }
          }
        }
      }

      console.log('Final image base64 length:', imageData.length);

      // Add to captured photos
      const photos = this.capturedPhotos();
      this.capturedPhotos.set([...photos, imageData]);

      console.log('Total photos captured:', this.capturedPhotos().length);

      // Move to next photo
      this.currentPhotoIndex.set(this.currentPhotoIndex() + 1);

      // Wait a bit then capture next
      // If no countdown for next photo, capture immediately, otherwise small delay
      const nextCountdown = this.countdownTime();
      const delay = nextCountdown === 0 ? 100 : 1500;
      setTimeout(() => this.captureNextPhoto(), delay);
    }
  }

  private finishCapture(): void {
    // Stop camera
    if (this.stream) {
      this.stream.getTracks().forEach(track => track.stop());
      this.stream = null;
    }

    this.isCapturing.set(false);
    this.isProcessing.set(true); // Show loading overlay immediately while transitioning
  }

  async retakePhotos(): Promise<void> {
    this.capturedPhotos.set([]);
    this.currentPhotoIndex.set(0);
    this.countdownValue.set(0);
    this.isCapturing.set(false);

    // Restart camera if needed
    if (!this.stream) {
      await this.startCamera();
    }
  }

  async exportAndPrint(): Promise<void> {
    if (!this.canvasEditor) {
      return;
    }

    this.isExporting.set(true);

    try {
      const canvas = this.canvasEditor.getCanvas();
      if (!canvas) {
        throw new Error('Canvas not available');
      }

      const canvasElement = canvas.getElement() as HTMLCanvasElement;
      const state = this.editorState.state$();

      const { blob, url, filename } = await this.exportService.exportAsImage(canvasElement, state);

      // Save to state for printing
      const printId = Date.now().toString();
      localStorage.setItem(`print-${printId}`, url);

      // Navigate to print page
      this.router.navigate(['/print', printId]);
    } catch (err) {
      console.error('Export failed:', err);
      alert('Failed to export image. Please try again.');
    } finally {
      this.isExporting.set(false);
    }
  }

  async downloadImage(): Promise<void> {
    if (!this.canvasEditor) {
      return;
    }

    this.isExporting.set(true);

    try {
      const canvas = this.canvasEditor.getCanvas();
      if (!canvas) {
        throw new Error('Canvas not available');
      }

      const canvasElement = canvas.getElement() as HTMLCanvasElement;
      const state = this.editorState.state$();

      const { url, filename } = await this.exportService.exportAsImage(canvasElement, state);
      this.exportService.downloadFile(url, filename);

      // Clean up
      setTimeout(() => {
        this.exportService.revokeUrl(url);
      }, 100);
    } catch (err) {
      console.error('Download failed:', err);
      alert('Failed to download image. Please try again.');
    } finally {
      this.isExporting.set(false);
    }
  }

  async shareImage(): Promise<void> {
    if (!this.canvasEditor) {
      return;
    }

    this.isExporting.set(true);

    try {
      const canvas = this.canvasEditor.getCanvas();
      if (!canvas) {
        throw new Error('Canvas not available');
      }

      const canvasElement = canvas.getElement() as HTMLCanvasElement;
      const state = this.editorState.state$();

      const { blob, filename } = await this.exportService.exportAsImage(canvasElement, state);
      const shared = await this.exportService.shareFile(blob, filename);

      if (!shared) {
        // Fallback to download if sharing is not available
        await this.downloadImage();
      }
    } catch (err) {
      console.error('Share failed:', err);
      alert('Failed to share image. Please try again.');
    } finally {
      this.isExporting.set(false);
    }
  }

  startOver(): void {
    if (confirm('Are you sure you want to start over? All changes will be lost.')) {
      // Stop camera if running
      if (this.stream) {
        this.stream.getTracks().forEach(track => track.stop());
        this.stream = null;
      }

      if (this.countdownInterval) {
        clearInterval(this.countdownInterval);
      }

      this.editorState.reset();
      this.selectedLayout.set(null);
      this.selectedFrame.set(null);
      this.capturedPhotos.set([]);
      this.isCapturing.set(false);
      this.isProcessing.set(false);
      this.currentPhotoIndex.set(0);
      this.countdownValue.set(0);
      this.activeTab.set('layout');
    }
  }

  ngOnDestroy(): void {
    if (this.stream) {
      this.stream.getTracks().forEach(track => track.stop());
    }
    if (this.countdownInterval) {
      clearInterval(this.countdownInterval);
    }
  }
}

