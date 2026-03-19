import { Component, ElementRef, ViewChild, output, signal, OnInit, OnDestroy, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { CameraService } from '../../services/camera.service';
import { CountdownService } from '../../services/countdown.service';
import { CameraDevice } from '../../models/editor.model';

@Component({
  selector: 'app-camera-capture',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './camera-capture.component.html',
  styleUrls: ['./camera-capture.component.scss']
})
export class CameraCaptureComponent implements OnInit, OnDestroy {
  @ViewChild('video') videoElement!: ElementRef<HTMLVideoElement>;

  photoCaptured = output<string>();

  private readonly cameraService = inject(CameraService);
  private readonly countdownService = inject(CountdownService);

  readonly isCameraActive = this.cameraService.isActive$;
  readonly cameraError = this.cameraService.error$;
  readonly availableDevices = this.cameraService.devices$;
  readonly countdownValue = this.countdownService.currentValue$;
  readonly isCountingDown = this.countdownService.isRunning$;

  readonly selectedDeviceId = signal<string>('');
  readonly selectedCountdown = signal<0 | 3 | 5 | 10>(3);
  readonly showDeviceSelector = signal<boolean>(false);
  readonly capturedImage = signal<string | null>(null);

  readonly countdownOptions = [
    { value: 0, label: 'No Delay' },
    { value: 3, label: '3 Seconds' },
    { value: 5, label: '5 Seconds' },
    { value: 10, label: '10 Seconds' }
  ] as const;

  readonly isMobile = signal<boolean>(false);

  async ngOnInit(): Promise<void> {
    // Check if mobile
    const userAgent = navigator.userAgent || navigator.vendor || (window as any).opera;
    if (/android/i.test(userAgent) || /iPad|iPhone|iPod/.test(userAgent)) {
      this.isMobile.set(true);
    }

    // Check if camera is supported
    if (!this.cameraService.checkCameraSupport()) {
      return;
    }

    // Enumerate devices
    await this.cameraService.enumerateDevices();
  }

  async startCamera(): Promise<void> {
    const deviceId = this.selectedDeviceId();
    const options: any = deviceId ? { deviceId } : { facingMode: 'user' };

    // For mobile, prefer 4:3 aspect ratio
    if (this.isMobile()) {
      options.aspectRatio = 4 / 3;
      // Also set width/height constraints if needed for 4:3
      options.width = 1024;
      options.height = 768; // 4:3
    }

    const stream = await this.cameraService.startCamera(options);

    if (stream && this.videoElement) {
      const video = this.videoElement.nativeElement;
      video.srcObject = stream;

      // Wait for video metadata to load before playing
      video.onloadedmetadata = async () => {
        try {
          await video.play();
        } catch (err) {
          console.error('Error playing video:', err);
        }
      };
    }
  }

  stopCamera(): void {
    this.cameraService.stopCamera();
    if (this.videoElement) {
      this.videoElement.nativeElement.srcObject = null;
    }
  }

  async switchCamera(deviceId: string): Promise<void> {
    this.selectedDeviceId.set(deviceId);

    const options: any = { deviceId };

    // For mobile, prefer 4:3 aspect ratio
    if (this.isMobile()) {
      options.aspectRatio = 4 / 3;
      options.width = 1024;
      options.height = 768;
    }

    const stream = await this.cameraService.startCamera(options);

    if (stream && this.videoElement) {
      const video = this.videoElement.nativeElement;
      video.srcObject = stream;

      // Wait for video metadata to load before playing
      video.onloadedmetadata = async () => {
        try {
          await video.play();
        } catch (err) {
          console.error('Error playing video:', err);
        }
      };
    }
  }

  capture(): void {
    const duration = this.selectedCountdown();

    this.countdownService.start({
      duration,
      onTick: (remaining) => {
        // Tick handled by signal
      },
      onComplete: () => {
        this.performCapture();
      }
    });
  }

  private performCapture(): void {
    if (!this.videoElement) {
      return;
    }

    const video = this.videoElement.nativeElement;
    const imageData = this.cameraService.captureFrame(video);

    if (imageData) {
      this.capturedImage.set(imageData);
      this.photoCaptured.emit(imageData);
    }
  }

  retake(): void {
    this.capturedImage.set(null);
  }

  usePhoto(): void {
    const image = this.capturedImage();
    if (image) {
      this.photoCaptured.emit(image);
      this.capturedImage.set(null);
    }
  }

  handleFileUpload(event: Event): void {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0];

    if (!file) {
      return;
    }

    const reader = new FileReader();
    reader.onload = (e) => {
      const imageData = e.target?.result as string;
      this.photoCaptured.emit(imageData);
    };
    reader.readAsDataURL(file);
  }

  ngOnDestroy(): void {
    this.stopCamera();
  }
}

