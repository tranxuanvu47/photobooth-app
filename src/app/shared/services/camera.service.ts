import { Injectable, signal } from '@angular/core';
import { CameraDevice, CameraOptions } from '../models/editor.model';

@Injectable({
  providedIn: 'root'
})
export class CameraService {
  private readonly stream = signal<MediaStream | null>(null);
  private readonly devices = signal<CameraDevice[]>([]);
  private readonly isActive = signal<boolean>(false);
  private readonly error = signal<string | null>(null);

  readonly stream$ = this.stream.asReadonly();
  readonly devices$ = this.devices.asReadonly();
  readonly isActive$ = this.isActive.asReadonly();
  readonly error$ = this.error.asReadonly();

  async enumerateDevices(): Promise<CameraDevice[]> {
    try {
      const devices = await navigator.mediaDevices.enumerateDevices();
      const videoDevices = devices
        .filter(device => device.kind === 'videoinput')
        .map(device => ({
          deviceId: device.deviceId,
          label: device.label || `Camera ${device.deviceId.slice(0, 8)}`,
          kind: 'videoinput' as const
        }));

      this.devices.set(videoDevices);
      return videoDevices;
    } catch (err) {
      const errorMessage = this.handleError(err);
      this.error.set(errorMessage);
      return [];
    }
  }

  async startCamera(options: CameraOptions = {}): Promise<MediaStream | null> {
    try {
      // Stop any existing stream first
      this.stopCamera();

      let videoConstraints: MediaTrackConstraints = {
        facingMode: options.facingMode || 'user',
        width: { ideal: options.width || 1920 },
        height: { ideal: options.height || 1080 }
      };

      if (options.aspectRatio) {
        videoConstraints.aspectRatio = options.aspectRatio;
      }

      if (options.deviceId) {
        videoConstraints = {
          ...videoConstraints,
          deviceId: { exact: options.deviceId }
        };
      }

      const constraints: MediaStreamConstraints = {
        video: videoConstraints,
        audio: false
      };

      const stream = await navigator.mediaDevices.getUserMedia(constraints);
      this.stream.set(stream);
      this.isActive.set(true);
      this.error.set(null);

      return stream;
    } catch (err) {
      const errorMessage = this.handleError(err);
      this.error.set(errorMessage);
      this.isActive.set(false);
      return null;
    }
  }

  stopCamera(): void {
    const currentStream = this.stream();
    if (currentStream) {
      currentStream.getTracks().forEach(track => track.stop());
      this.stream.set(null);
      this.isActive.set(false);
    }
  }

  captureFrame(video: HTMLVideoElement, rotate90: boolean = false): string | null {
    if (!video || video.readyState < 2) {
      return null;
    }

    const canvas = document.createElement('canvas');

    if (rotate90) {
      // Create canvas with swapped dimensions
      canvas.width = video.videoHeight;
      canvas.height = video.videoWidth;
    } else {
      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;
    }

    const ctx = canvas.getContext('2d');
    if (!ctx) {
      return null;
    }

    if (rotate90) {
      // Translate to center
      ctx.translate(canvas.width / 2, canvas.height / 2);
      // Rotate 90 degrees (PI/2)
      ctx.rotate(90 * Math.PI / 180);
      // Draw image centered at new origin
      ctx.drawImage(video, -video.videoWidth / 2, -video.videoHeight / 2);
    } else {
      ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    }

    return canvas.toDataURL('image/jpeg', 0.95);
  }

  async switchCamera(deviceId: string): Promise<MediaStream | null> {
    return this.startCamera({ deviceId });
  }

  checkCameraSupport(): boolean {
    return !!(
      navigator.mediaDevices &&
      navigator.mediaDevices.getUserMedia
    );
  }

  private handleError(err: unknown): string {
    if (err instanceof Error) {
      const name = (err as DOMException).name;

      switch (name) {
        case 'NotAllowedError':
        case 'PermissionDeniedError':
          return 'Camera permission denied. Please allow camera access in your browser settings.';
        case 'NotFoundError':
        case 'DevicesNotFoundError':
          return 'No camera found. Please connect a camera and try again.';
        case 'NotReadableError':
        case 'TrackStartError':
          return 'Camera is already in use by another application.';
        case 'OverconstrainedError':
          return 'Camera does not support the requested settings.';
        case 'SecurityError':
          return 'Camera access blocked due to security restrictions.';
        default:
          return err.message || 'Failed to access camera.';
      }
    }
    return 'An unknown error occurred while accessing the camera.';
  }

  ngOnDestroy(): void {
    this.stopCamera();
  }
}

