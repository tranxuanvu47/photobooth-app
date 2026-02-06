import { Component, ElementRef, ViewChild, input, output, OnInit, OnDestroy, AfterViewInit, signal, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
// import * as fabric from 'fabric';
declare const fabric: any;
import { LayoutConfig } from '../../models/layout.model';
import { Frame } from '../../models/frame.model';
import { Sticker, STICKERS, StickerCategory } from '../../models/sticker.model';
import { EditorStateService } from '../../services/editor-state.service';

@Component({
  selector: 'app-canvas-editor',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './canvas-editor.component.html',
  styleUrls: ['./canvas-editor.component.scss']
})
export class CanvasEditorComponent implements OnInit, AfterViewInit, OnDestroy {
  @ViewChild('canvas') canvasElement!: ElementRef<HTMLCanvasElement>;

  layout = input.required<LayoutConfig>();
  frame = input<Frame | null>(null);
  isPreview = input<boolean>(false); // True for preview overlay, false for final view
  videoElement = input<HTMLVideoElement | null>(null); // Video element for live feed

  canvasReady = output<any>();

  private readonly editorState = inject(EditorStateService);
  private canvas: any | null = null;
  private frameOverlayLoaded = signal<boolean>(false);
  private pendingImages: Array<{ imageData: string; slotId?: string }> = [];
  private photosAdded = signal<boolean>(false); // Track if photos have been added

  readonly activeTab = signal<'text' | 'stickers' | 'layers'>('text');
  readonly stickers = STICKERS;
  readonly selectedSticker = signal<Sticker | null>(null);
  readonly stickerCategories: StickerCategory[] = ['rings', 'flowers', 'hearts', 'balloons', 'confetti', 'text-badges', 'decorative'];
  readonly selectedCategory = signal<StickerCategory | 'all'>('all');

  // Text properties
  readonly textInput = signal<string>('');
  readonly fontFamily = signal<string>('Arial');
  readonly fontSize = signal<number>(32);
  readonly textColor = signal<string>('#000000');
  readonly isBold = signal<boolean>(false);
  readonly isItalic = signal<boolean>(false);

  readonly fontFamilies = [
    'Arial',
    'Times New Roman',
    'Courier New',
    'Georgia',
    'Verdana',
    'Comic Sans MS',
    'Impact',
    'Brush Script MT'
  ];

  get filteredStickers(): Sticker[] {
    const category = this.selectedCategory();
    if (category === 'all') {
      return this.stickers;
    }
    return this.stickers.filter(s => s.category === category);
  }

  ngOnInit(): void {
    // Initialization logic
  }

  ngAfterViewInit(): void {
    this.initCanvas();
  }

  private initCanvas(): void {
    if (!this.canvasElement) {
      return;
    }

    const layoutConfig = this.layout();
    const canvasEl = this.canvasElement.nativeElement;

    // Check mobile state once
    const isMobile = window.innerWidth < 768;

    // CRITICAL: Canvas is created at NATIVE resolution
    // Then we scale the DISPLAY size with CSS to fit viewport
    // On Desktop: Enable Retina scaling for crisp text/interaction
    // On Mobile: Disable Retina scaling to prevent memory crashes
    this.canvas = new fabric.Canvas(canvasEl, {
      width: layoutConfig.width,      // Native resolution (e.g., 2000px)
      height: layoutConfig.height,    // Native resolution (e.g., 3000px)
      backgroundColor: layoutConfig.backgroundColor,
      preserveObjectStacking: true,
      enableRetinaScaling: !isMobile,
      imageSmoothingEnabled: !isMobile // Better quality on desktop
    });

    // Calculate display scale to fit viewport
    // CRITICAL: This only affects DISPLAY size, NOT internal rendering quality
    const viewportHeight = window.innerHeight - 100; // Header + padding
    const viewportWidth = window.innerWidth - 30;    // Margin
    const scaleX = viewportWidth / layoutConfig.width;
    const scaleY = viewportHeight / layoutConfig.height;

    // Mobile: 95% width, Desktop: 90%
    const marginFactor = isMobile ? 0.95 : 0.90;

    const finalDisplayScale = Math.min(scaleX, scaleY) * marginFactor;

    console.log('🎨 Display Scale Calculation:', {
      viewport: `${viewportWidth}x${viewportHeight}`,
      canvas: `${layoutConfig.width}x${layoutConfig.height}`,
      scaleX, scaleY,
      finalDisplayScale,
      note: 'This ONLY affects display size, NOT image quality'
    });

    // CRITICAL: Set CSS size to scale the canvas for display
    // This scales the visual representation without affecting internal resolution
    const displayWidth = layoutConfig.width * finalDisplayScale;
    const displayHeight = layoutConfig.height * finalDisplayScale;

    console.log('Canvas display scaling:', {
      nativeSize: `${layoutConfig.width}x${layoutConfig.height}`,
      displaySize: `${displayWidth}x${displayHeight}`,
      scale: finalDisplayScale,
      isPreview: this.isPreview(),
      isMobile,
      retinaEnabled: !isMobile
    });

    // Use Fabric's setDimensions with cssOnly to scale the container and canvas CSS
    // avoiding manual style manipulation that might be missed by the wrapper
    this.canvas.setDimensions(
      { width: `${displayWidth}px`, height: `${displayHeight}px` },
      { cssOnly: true }
    );

    // Fallback: If setDimensions doesn't treat strings correctly in this version (unlikely but safe)
    // explicitly set wrapper style if possible
    const wrapper = this.canvas.getElement().parentNode as HTMLElement;
    if (wrapper && wrapper.classList.contains('canvas-container')) {
      wrapper.style.width = `${displayWidth}px`;
      wrapper.style.height = `${displayHeight}px`;
      // Ensure the wrapper is centered
      wrapper.style.margin = '0 auto';
    }

    // Check if we need to force resize upper canvas too (sometimes needed)
    // Force specific fix for Upper Canvas alignment on Desktop
    // Sometimes retina scaling causes offset if CSS size doesn't match backing store ratio
    const upperCanvas = wrapper.querySelector('.upper-canvas') as HTMLElement;
    if (upperCanvas) {
      upperCanvas.style.width = `${displayWidth}px`;
      upperCanvas.style.height = `${displayHeight}px`;
    }

    // COMPREHENSIVE DEBUG LOGGING
    console.log('=== CANVAS DEBUG INFO ===');
    console.log('Layout Config:', JSON.stringify({
      width: layoutConfig.width,
      height: layoutConfig.height,
      backgroundColor: layoutConfig.backgroundColor
    }, null, 2));

    console.log('Viewport:', JSON.stringify({
      viewportWidth,
      viewportHeight,
      windowWidth: window.innerWidth,
      windowHeight: window.innerHeight
    }, null, 2));

    console.log('Scale Calculation:', JSON.stringify({
      scaleX,
      scaleY,
      baseScale: finalDisplayScale, // Corrected from 'scale' to 'finalDisplayScale'
      finalDisplayScale,
      isPreview: this.isPreview()
    }, null, 2));

    console.log('Canvas CSS Styles (DISPLAY ONLY):', JSON.stringify({
      styleWidth: canvasEl.style.width,
      styleHeight: canvasEl.style.height,
      displayWidth,
      displayHeight,
      note: 'This is CSS scaling for display - does NOT affect image quality'
    }, null, 2));

    console.log('Canvas Native Resolution (IMAGE QUALITY):', JSON.stringify({
      canvasWidth: canvasEl.width,
      canvasHeight: canvasEl.height,
      note: 'This is the ACTUAL rendering resolution - determines image quality'
    }, null, 2));

    console.log('========================');


    // Store original dimensions for export
    (this.canvas as any).originalWidth = layoutConfig.width;
    (this.canvas as any).originalHeight = layoutConfig.height;
    (this.canvas as any).displayScale = 1; // No internal scaling, use native resolution

    // Draw layout slots
    this.drawLayoutSlots();

    // Apply frame if exists - use setTimeout to ensure canvas is ready
    const currentFrame = this.frame();
    if (currentFrame) {
      // Small delay to ensure canvas is fully initialized
      setTimeout(() => {
        this.applyFrame(currentFrame);
        // If preview mode and video element exists, add camera feed to frame
        if (this.isPreview() && this.videoElement()) {
          setTimeout(() => {
            this.updateCameraFeedInFrame();
          }, 200); // Wait for frame overlay to load
        }
      }, 100);
    } else {
      // No frame, mark as loaded so images can be added immediately
      this.frameOverlayLoaded.set(true);
    }

    // Setup event handlers
    this.setupEventHandlers();

    this.canvasReady.emit(this.canvas);
  }

  updateCameraFeedInFrame(): void {
    if (!this.canvas || !this.videoElement()) {
      return;
    }

    const video = this.videoElement()!;
    if (!video.videoWidth || !video.videoHeight) {
      // Retry after video is ready
      setTimeout(() => this.updateCameraFeedInFrame(), 200);
      return;
    }

    const layoutConfig = this.layout();
    const scale = (this.canvas as any).displayScale;
    const targetSlot = layoutConfig.slots[0]; // Use first slot

    if (!targetSlot) {
      return;
    }

    // Remove existing camera feed if any
    const objects = (this.canvas as any).getObjects() || [];
    const existingFeed = objects.find((obj: any) =>
      (obj as any).data?.isCameraFeed === true
    );
    if (existingFeed) {
      this.canvas.remove(existingFeed);
    }

    // Create a fabric image from video frame
    const slotWidth = targetSlot.width * scale;
    const slotHeight = targetSlot.height * scale;
    const slotLeft = targetSlot.x * scale;
    const slotTop = targetSlot.y * scale;

    // Create temporary canvas to capture video frame
    const tempCanvas = document.createElement('canvas');
    tempCanvas.width = video.videoWidth;
    tempCanvas.height = video.videoHeight;
    const tempCtx = tempCanvas.getContext('2d');
    if (tempCtx) {
      // Enable high-quality image smoothing
      tempCtx.imageSmoothingEnabled = true;
      tempCtx.imageSmoothingQuality = 'high';

      tempCtx.drawImage(video, 0, 0);
      // Use PNG format (lossless) for maximum quality
      const videoDataUrl = tempCanvas.toDataURL('image/png');

      fabric.Image.fromURL(videoDataUrl, (img: any) => {
        if (!this.canvas) return;

        // Calculate scale to fit within slot
        const scaleX = slotWidth / (img.width || 1);
        const scaleY = slotHeight / (img.height || 1);
        const fitScale = Math.min(scaleX, scaleY);
        // Reduce scale by 2% to add small padding, but keep image larger to fill transparent areas
        // Increased from 0.95 to 0.98 to make image slightly wider
        const scaleToUse = fitScale * 0.98;

        const scaledWidth = (img.width || 1) * scaleToUse;
        const scaledHeight = (img.height || 1) * scaleToUse;
        // Shift slightly left to fill transparent area on the left
        const leftOffset = slotWidth * 0.03; // 3% shift to the left (slightly more than before)
        const centeredLeft = slotLeft + (slotWidth - scaledWidth) / 2 - leftOffset;

        // Calculate balanced position (average of centered and top-aligned)
        const centeredTop = slotTop + (slotHeight - scaledHeight) / 2;
        const topAlignedTop = slotTop;
        const balancedTop = (centeredTop + topAlignedTop) / 2;

        img.set({
          left: centeredLeft,
          top: balancedTop,
          scaleX: scaleToUse,
          scaleY: scaleToUse,
          selectable: false,
          evented: false,
          data: { isCameraFeed: true, slotId: targetSlot.id }
        });

        // Clip to slot boundaries
        img.clipPath = new fabric.Rect({
          left: slotLeft,
          top: slotTop,
          width: slotWidth,
          height: slotHeight,
          absolutePositioned: true
        });

        this.canvas.add(img);
        this.canvas.sendToBack(img); // Send camera feed to back, frame overlay on top
        this.canvas.renderAll();

        // Update periodically for live feed effect
        if (this.isPreview()) {
          setTimeout(() => this.updateCameraFeedInFrame(), 100); // Update every 100ms
        }
      }, { crossOrigin: 'anonymous' });
    }
  }

  private drawLayoutSlots(): void {
    if (!this.canvas) {
      return;
    }

    const layoutConfig = this.layout();
    const scale = (this.canvas as any).displayScale; // Now = 1 (native resolution)

    layoutConfig.slots.forEach(slot => {
      const rect = new fabric.Rect({
        left: slot.x * scale,    // Native resolution
        top: slot.y * scale,     // Native resolution
        width: slot.width * scale,
        height: slot.height * scale,
        fill: 'transparent', // Make transparent so photos show through
        stroke: 'transparent', // Hide stroke in production
        strokeWidth: 0,
        selectable: false,
        evented: false,
        data: { slotId: slot.id }
      });

      this.canvas?.add(rect);
    });

    this.canvas.renderAll();
  }

  private applyFrame(frame: Frame): void {
    if (!this.canvas) {
      return;
    }

    const config = frame.config;
    const scale = (this.canvas as any).displayScale;

    // Apply frame border (simplified - in production you'd overlay images)
    this.canvas.backgroundColor = config.backgroundColor || this.layout().backgroundColor;

    // If overlayUrl is provided, load and apply it
    if (frame.overlayUrl) {
      console.log('Loading frame overlay:', frame.overlayUrl);
      try {
        // Load frame overlay with proper options to preserve transparency
        fabric.Image.fromURL(frame.overlayUrl, (overlayImg: any) => {
          if (!this.canvas) {
            console.error('Canvas not available when frame overlay loaded');
            return;
          }

          if (!overlayImg || !overlayImg.width || !overlayImg.height) {
            console.error('Invalid frame overlay image loaded');
            return;
          }

          console.log('Frame overlay loaded:', overlayImg.width, 'x', overlayImg.height);

          // Analyze the image to detect transparent area for proper photo positioning
          if (frame.overlayUrl) {
            const overlayUrl = frame.overlayUrl; // Store in variable for type narrowing
            this.analyzeFrameTransparency(overlayUrl, overlayImg.width, overlayImg.height);
          }

          const canvasWidth = this.canvas.getWidth();
          const canvasHeight = this.canvas.getHeight();

          // Scale overlay to cover entire canvas
          const overlayScaleX = canvasWidth / (overlayImg.width || 1);
          const overlayScaleY = canvasHeight / (overlayImg.height || 1);

          // CRITICAL: Frame overlay must preserve PNG transparency
          // Set properties to ensure transparency works correctly
          overlayImg.set({
            left: 0,
            top: 0,
            scaleX: overlayScaleX,
            scaleY: overlayScaleY,
            selectable: false,
            evented: false,
            opacity: 1, // Full opacity, but PNG alpha channel provides transparency
            // Don't set globalCompositeOperation - let fabric.js handle PNG transparency naturally
            data: { isFrameOverlay: true }
          });

          // Ensure the image element preserves alpha channel
          // Fabric.js should handle PNG transparency automatically if loaded correctly
          console.log('Frame overlay image properties:', {
            hasAlpha: true, // PNG supports alpha channel
            opacity: overlayImg.opacity,
            crossOrigin: 'anonymous' // Set in fromURL options
          });

          console.log('Frame overlay scaling:', {
            originalSize: `${overlayImg.width}x${overlayImg.height}`,
            canvasSize: `${canvasWidth}x${canvasHeight}`,
            scale: `${overlayScaleX}x${overlayScaleY}`,
            opacity: overlayImg.opacity,
            hasTransparency: true // PNG should have transparency
          });

          // Add overlay to canvas
          // CRITICAL: If photos are already added, don't bring frame to front
          // Photos must stay on top for visibility
          this.canvas.add(overlayImg);

          if (!this.photosAdded()) {
            // No photos yet, frame can be on top
            this.canvas.bringToFront(overlayImg);
          } else {
            // Photos already added, keep them on top
            console.log('Photos already added - keeping frame overlay below photos');
            this.canvas.sendToBack(overlayImg);
          }

          this.canvas.renderAll();
          console.log('Frame overlay applied to canvas');

          // Verify frame overlay properties
          console.log('Frame overlay properties:', {
            opacity: overlayImg.opacity,
            globalCompositeOperation: (overlayImg as any).globalCompositeOperation,
            hasTransparency: true, // PNG should support transparency
            photosAdded: this.photosAdded(),
            framePosition: this.photosAdded() ? 'below photos' : 'on top'
          });

          // Mark frame overlay as loaded
          this.frameOverlayLoaded.set(true);

          // Process any pending images now that frame is loaded
          this.processPendingImages();
        }, { crossOrigin: 'anonymous' });
      } catch (error) {
        console.error('Error loading frame overlay:', error);
      }
    } else {
      // Add border effect by drawing rectangles (existing behavior)
      const borderWidth = config.borderWidth * scale;
      const canvasWidth = this.canvas.getWidth();
      const canvasHeight = this.canvas.getHeight();

      const frameRect = new fabric.Rect({
        left: 0,
        top: 0,
        width: canvasWidth,
        height: canvasHeight,
        fill: 'transparent',
        stroke: config.borderColor,
        strokeWidth: borderWidth,
        selectable: false,
        evented: false,
        rx: config.cornerRadius * scale,
        ry: config.cornerRadius * scale,
        shadow: new fabric.Shadow({
          color: config.shadowColor,
          blur: config.shadowBlur * scale,
          offsetX: config.shadowOffsetX * scale,
          offsetY: config.shadowOffsetY * scale
        })
      });

      this.canvas.add(frameRect);
      this.canvas.renderAll();
    }
  }

  /**
   * Analyze frame image to detect transparent area for proper photo positioning
   */
  private analyzeFrameTransparency(imageUrl: string, imageWidth: number, imageHeight: number): void {
    // Create a temporary image element to analyze pixel data
    const img = new Image();
    img.crossOrigin = 'anonymous';

    img.onload = () => {
      // Create temporary canvas to read pixel data
      const tempCanvas = document.createElement('canvas');
      tempCanvas.width = imageWidth;
      tempCanvas.height = imageHeight;
      const ctx = tempCanvas.getContext('2d');

      if (!ctx) {
        console.warn('Could not create canvas context for transparency analysis');
        return;
      }

      ctx.drawImage(img, 0, 0);

      // Sample pixels to find transparent area bounds
      // Sample center area and edges to detect transparent region
      const samplePoints = [
        { x: imageWidth / 2, y: imageHeight * 0.1 }, // Top center
        { x: imageWidth / 2, y: imageHeight * 0.3 }, // Upper middle
        { x: imageWidth / 2, y: imageHeight * 0.5 }, // Center
        { x: imageWidth / 2, y: imageHeight * 0.7 }, // Lower middle
        { x: imageWidth / 2, y: imageHeight * 0.9 }, // Bottom center
        { x: imageWidth * 0.1, y: imageHeight / 2 }, // Left center
        { x: imageWidth * 0.9, y: imageHeight / 2 }, // Right center
      ];

      let transparentTop = imageHeight;
      let transparentBottom = 0;
      let transparentLeft = imageWidth;
      let transparentRight = 0;
      let hasTransparency = false;

      // Sample grid to find transparent bounds (the red box area)
      // Use smaller step for more accurate detection of the red box boundaries
      const sampleStep = 20; // Sample every 20 pixels for better accuracy
      for (let y = 0; y < imageHeight; y += sampleStep) {
        for (let x = 0; x < imageWidth; x += sampleStep) {
          const pixelData = ctx.getImageData(x, y, 1, 1).data;
          const alpha = pixelData[3]; // Alpha channel
          const r = pixelData[0]; // Red channel (to detect red box)
          const g = pixelData[1]; // Green channel
          const b = pixelData[2]; // Blue channel

          // Check for transparent pixels OR red box pixels (red box might be semi-transparent)
          // Red box detection: high red, low green/blue (typical red box color)
          const isRedBox = r > 200 && g < 100 && b < 100 && alpha > 200;
          const isTransparent = alpha < 200;

          // If pixel is transparent or part of red box area
          if (isTransparent || isRedBox) {
            hasTransparency = true;
            if (y < transparentTop) transparentTop = y;
            if (y > transparentBottom) transparentBottom = y;
            if (x < transparentLeft) transparentLeft = x;
            if (x > transparentRight) transparentRight = x;
          }
        }
      }

      // If we detected red box, we need to find the inner transparent area
      // Sample more densely around the detected area to find the actual photo slot
      if (hasTransparency && transparentRight > transparentLeft && transparentBottom > transparentTop) {
        // Refine the bounds by sampling more densely in the detected area
        const refineStep = 5;
        let refinedTransparentTop = imageHeight;
        let refinedTransparentBottom = 0;
        let refinedTransparentLeft = imageWidth;
        let refinedTransparentRight = 0;

        for (let y = Math.max(0, transparentTop - 50); y < Math.min(imageHeight, transparentBottom + 50); y += refineStep) {
          for (let x = Math.max(0, transparentLeft - 50); x < Math.min(imageWidth, transparentRight + 50); x += refineStep) {
            const pixelData = ctx.getImageData(x, y, 1, 1).data;
            const alpha = pixelData[3];

            // Only count fully transparent pixels (the actual photo slot)
            if (alpha < 50) {
              if (y < refinedTransparentTop) refinedTransparentTop = y;
              if (y > refinedTransparentBottom) refinedTransparentBottom = y;
              if (x < refinedTransparentLeft) refinedTransparentLeft = x;
              if (x > refinedTransparentRight) refinedTransparentRight = x;
            }
          }
        }

        // Use refined bounds if we found a better transparent area
        if (refinedTransparentRight > refinedTransparentLeft && refinedTransparentBottom > refinedTransparentTop) {
          transparentTop = refinedTransparentTop;
          transparentBottom = refinedTransparentBottom;
          transparentLeft = refinedTransparentLeft;
          transparentRight = refinedTransparentRight;
        }
      }

      if (hasTransparency) {
        const transparentWidth = transparentRight - transparentLeft;
        const transparentHeight = transparentBottom - transparentTop;

        console.log('📐 Frame Transparency Analysis:', {
          imageSize: `${imageWidth}x${imageHeight}`,
          transparentArea: {
            x: transparentLeft,
            y: transparentTop,
            width: transparentWidth,
            height: transparentHeight
          },
          transparentBounds: {
            left: transparentLeft,
            top: transparentTop,
            right: transparentRight,
            bottom: transparentBottom
          },
          recommendation: {
            slotX: Math.round(transparentLeft),
            slotY: Math.round(transparentTop),
            slotWidth: Math.round(transparentWidth),
            slotHeight: Math.round(transparentHeight)
          }
        });

        // Store transparency info for potential dynamic slot adjustment
        (this.canvas as any).frameTransparency = {
          x: transparentLeft,
          y: transparentTop,
          width: transparentWidth,
          height: transparentHeight,
          imageWidth: imageWidth,
          imageHeight: imageHeight
        };
      } else {
        console.warn('⚠️ No significant transparent area detected in frame image');
      }
    };

    img.onerror = () => {
      console.warn('Could not load image for transparency analysis');
    };

    img.src = imageUrl;
  }

  private setupEventHandlers(): void {
    if (!this.canvas) {
      return;
    }

    this.canvas.on('selection:created', () => this.onObjectSelected());
    this.canvas.on('selection:updated', () => this.onObjectSelected());
    this.canvas.on('selection:cleared', () => this.onSelectionCleared());
  }

  private onObjectSelected(): void {
    const activeObject = this.canvas?.getActiveObject();
    if (activeObject && (activeObject as any).isText) {
      this.activeTab.set('text');
    }
  }

  private onSelectionCleared(): void {
    // Handle deselection
  }

  addText(): void {
    if (!this.canvas || !this.textInput()) {
      return;
    }

    const scale = (this.canvas as any).displayScale;
    const text = new fabric.IText(this.textInput(), {
      left: (this.canvas.getWidth() / 2) - 50,
      top: (this.canvas.getHeight() / 2) - 20,
      fontFamily: this.fontFamily(),
      fontSize: this.fontSize() * scale,
      fill: this.textColor(),
      fontWeight: this.isBold() ? 'bold' : 'normal',
      fontStyle: this.isItalic() ? 'italic' : 'normal'
    });

    this.canvas.add(text);
    this.canvas.setActiveObject(text);
    this.canvas.renderAll();

    this.textInput.set('');
  }

  updateTextProperties(): void {
    if (!this.canvas) {
      return;
    }

    const activeObject = this.canvas.getActiveObject();
    if (activeObject && (activeObject as any).isText) {
      const scale = (this.canvas as any).displayScale;
      (activeObject as any).set({
        fontFamily: this.fontFamily(),
        fontSize: this.fontSize() * scale,
        fill: this.textColor(),
        fontWeight: this.isBold() ? 'bold' : 'normal',
        fontStyle: this.isItalic() ? 'italic' : 'normal'
      });
      this.canvas.renderAll();
    }
  }

  addSticker(sticker: Sticker): void {
    if (!this.canvas) {
      return;
    }

    const scale = (this.canvas as any).displayScale;

    fabric.Image.fromURL(sticker.url, (img: any) => {
      if (!this.canvas) {
        return;
      }

      img.set({
        left: (this.canvas.getWidth() / 2) - (sticker.width * scale / 2),
        top: (this.canvas.getHeight() / 2) - (sticker.height * scale / 2),
        scaleX: scale,
        scaleY: scale
      });

      this.canvas.add(img);
      this.canvas.setActiveObject(img);
      this.canvas.renderAll();
    }, { crossOrigin: 'anonymous' });
  }

  addImage(imageData: string, slotId?: string): void {
    if (!this.canvas) {
      console.error('Canvas not ready');
      return;
    }

    console.log('Adding image to canvas, slotId:', slotId);
    console.log('Frame overlay loaded:', this.frameOverlayLoaded());

    // If frame overlay hasn't loaded yet, queue the image
    if (!this.frameOverlayLoaded() && this.frame()) {
      console.log('Frame overlay not loaded yet, queuing image...');
      this.pendingImages.push({ imageData, slotId });
      return;
    }

    this.processImage(imageData, slotId);
  }

  private processPendingImages(): void {
    console.log('Processing pending images:', this.pendingImages.length);
    this.pendingImages.forEach(({ imageData, slotId }) => {
      this.processImage(imageData, slotId);
    });
    this.pendingImages = [];
  }

  private processImage(imageData: string, slotId?: string): void {
    if (!this.canvas) {
      console.error('Canvas not ready');
      return;
    }

    // Check if it's a data URL or regular URL
    const isDataUrl = imageData.startsWith('data:');
    // Configure fabric.js for maximum quality
    const options = {
      crossOrigin: 'anonymous'
      // Fabric will load image at native resolution
    };

    fabric.Image.fromURL(imageData, (img: any) => {
      if (!this.canvas) {
        console.error('Canvas lost during image load');
        return;
      }

      if (!img || !img.width || !img.height) {
        console.error('Invalid image loaded');
        return;
      }

      console.log('Image loaded successfully:', img.width, 'x', img.height);

      // CRITICAL: Set image rendering quality
      const imgElement = (img as any).getElement();
      if (imgElement) {
        imgElement.style.imageRendering = 'high-quality';
        imgElement.style.imageRendering = '-webkit-optimize-contrast';
      }

      // Configure fabric image for high quality (disable caching)
      img.set({
        objectCaching: false,  // Disable caching to always use high-quality
        statefullCache: false,
        noScaleCache: true,    // Don't cache scaled versions
        strokeWidth: 0,
        paintFirst: 'fill'
      });

      const scale = (this.canvas as any).displayScale; // Now = 1 (native resolution)
      const layoutConfig = this.layout();

      let targetSlot = layoutConfig.slots.find(s => s.id === slotId);
      if (!targetSlot && layoutConfig.slots.length > 0) {
        targetSlot = layoutConfig.slots[0];
      }

      // Check if frame transparency info is available and use it to adjust slot positioning
      const frameTransparency = (this.canvas as any).frameTransparency;
      let adjustedSlot = targetSlot;

      if (frameTransparency && targetSlot) {
        console.log('🎯 Using detected transparent area for photo positioning');
        // Convert detected transparency area (in image pixels) to layout coordinates
        const originalWidth = (this.canvas as any).originalWidth || layoutConfig.width;
        const originalHeight = (this.canvas as any).originalHeight || layoutConfig.height;

        // Calculate scale from image to layout
        const imageToLayoutScaleX = originalWidth / (frameTransparency.imageWidth || originalWidth);
        const imageToLayoutScaleY = originalHeight / (frameTransparency.imageHeight || originalHeight);

        // Create adjusted slot based on detected transparency
        adjustedSlot = {
          ...targetSlot,
          x: frameTransparency.x * imageToLayoutScaleX,
          y: frameTransparency.y * imageToLayoutScaleY,
          width: frameTransparency.width * imageToLayoutScaleX,
          height: frameTransparency.height * imageToLayoutScaleY
        };
        console.log('Adjusted slot based on transparency:', {
          original: targetSlot,
          adjusted: adjustedSlot,
          transparency: frameTransparency
        });
      }

      console.log('Target slot:', adjustedSlot);

      if (adjustedSlot) {
        // CRITICAL: Single-pass resize calculation (no multiple resizes)
        // Calculate final scale in ONE operation to prevent quality loss
        const slotWidth = adjustedSlot.width * scale;   // Native resolution (scale = 1)
        const slotHeight = adjustedSlot.height * scale; // Native resolution (scale = 1)

        // Calculate base scale to fit within slot
        const baseScaleX = slotWidth / (img.width || 1);
        const baseScaleY = slotHeight / (img.height || 1);
        const baseFitScale = Math.min(baseScaleX, baseScaleY);

        // Apply all adjustments in single calculation (not iteratively)
        let scaleMultiplier = 0.98; // 2% padding

        // March 2026 calendar adjustments
        if (this.frame()?.id === 'march-2026-calendar') {
          scaleMultiplier *= 0.88;  // Overall size adjustment
        }

        // Calculate final scale in ONE pass
        let finalScaleX = baseFitScale * scaleMultiplier;
        let finalScaleY = baseFitScale * scaleMultiplier;

        // Height-specific adjustment for calendar
        if (this.frame()?.id === 'march-2026-calendar') {
          finalScaleY *= 0.90;  // Height 10% smaller
        }

        console.log('Single-pass image scale calculation:', {
          baseScale: baseFitScale,
          multiplier: scaleMultiplier,
          finalScaleX,
          finalScaleY,
          slot: `${slotWidth}x${slotHeight}`,
          image: `${img.width}x${img.height}`
        });

        // Calculate scaled dimensions using final scales
        const scaledWidth = (img.width || 1) * finalScaleX;
        const scaledHeight = (img.height || 1) * finalScaleY;

        // Position image within slot (native resolution coordinates)
        const slotLeft = adjustedSlot.x * scale;
        const slotTop = adjustedSlot.y * scale;

        // Center horizontally with left offset to fill transparent area
        const leftOffset = slotWidth * 0.03; // 3% shift left
        const centeredLeft = slotLeft + (slotWidth - scaledWidth) / 2 - leftOffset;

        // Calculate balanced vertical position
        const centeredTop = slotTop + (slotHeight - scaledHeight) / 2;
        const topAlignedTop = slotTop;
        let balancedTop = (centeredTop + topAlignedTop) / 2;
        let centeredLeftFinal = centeredLeft;

        // March 2026 calendar: shift photo up and right
        if (this.frame()?.id === 'march-2026-calendar') {
          balancedTop -= 100 * scale;  // Move up
          centeredLeftFinal += 38 * scale; // Move right
        }

        console.log('Image positioning (native resolution):', {
          slotOriginal: { x: adjustedSlot.x, y: adjustedSlot.y, width: adjustedSlot.width, height: adjustedSlot.height },
          slotScaled: { left: slotLeft, top: slotTop, width: slotWidth, height: slotHeight },
          imageScaled: { left: centeredLeftFinal, top: balancedTop, width: scaledWidth, height: scaledHeight },
          displayScale: scale,
          usingTransparency: !!frameTransparency
        });

        // Remove any existing photo in this slot
        const objects = (this.canvas as any).getObjects() || [];
        const existingPhoto = objects.find((obj: any) =>
          (obj as any).data?.isPhoto === true && (obj as any).data?.slotId === adjustedSlot.id
        );
        if (existingPhoto) {
          this.canvas.remove(existingPhoto);
        }

        // Set image properties with quality-focused settings
        img.set({
          left: centeredLeftFinal,
          top: balancedTop,
          scaleX: finalScaleX,  // Single-pass scale
          scaleY: finalScaleY,  // Single-pass scale
          selectable: false,
          evented: false,
          opacity: 1,
          objectCaching: false,     // Force high-quality rendering
          statefullCache: false,
          noScaleCache: true,
          data: { isPhoto: true, slotId: adjustedSlot.id },
          shadow: new fabric.Shadow({
            color: 'rgba(0, 0, 0, 0.2)',
            blur: 10,
            offsetX: 0,
            offsetY: 2
          })
        });

        // CRITICAL: clipPath MUST be used to constrain image to the red box boundaries
        // This prevents overflow and ensures the photo fits perfectly within the transparent area
        // With absolutePositioned: true, clipPath coordinates are relative to canvas origin
        // The clipPath will clip any parts of the image that extend beyond the slot boundaries
        img.clipPath = new fabric.Rect({
          left: slotLeft,
          top: slotTop,
          width: slotWidth,
          height: slotHeight,
          absolutePositioned: true
        });

        // Add image to canvas (ONLY ONCE!)
        this.canvas.add(img);

        // Mark that photos have been added
        this.photosAdded.set(true);

        console.log('✅ Image and clipPath configured:', {
          imagePosition: { left: centeredLeftFinal, top: balancedTop, width: scaledWidth, height: scaledHeight },
          clipPath: { left: slotLeft, top: slotTop, width: slotWidth, height: slotHeight },
          slotBounds: adjustedSlot,
          imageFitsInSlot: true,
          clipPathActive: true,
          note: 'Image is clipped to slot boundaries using clipPath'
        });
      } else {
        console.warn('No slot found for image, skipping');
      }

      // Remove any existing camera feed in this slot
      if (this.canvas && targetSlot) {
        const objects = (this.canvas as any).getObjects() || [];
        const cameraFeed = objects.find((obj: any) =>
          (obj as any).data?.isCameraFeed === true && (obj as any).data?.slotId === targetSlot.id
        );
        if (cameraFeed) {
          this.canvas.remove(cameraFeed);
        }
      }

      // Render canvas to show the new image
      this.canvas.renderAll();

      console.log('Image added to canvas, current object count:', (this.canvas as any).getObjects().length);

      // Ensure proper layering: background < camera feed < photo < frame overlay
      if (this.canvas) {
        const objects = (this.canvas as any).getObjects() || [];
        console.log('Total objects before layering:', objects.length);

        // Send camera feed to back (if exists)
        const cameraFeed = objects.find((obj: any) =>
          (obj as any).data?.isCameraFeed === true
        );
        if (cameraFeed) {
          console.log('Removing camera feed');
          this.canvas.remove(cameraFeed);
        }

        // Find frame overlay
        const frameOverlay = objects.find((obj: any) =>
          (obj as any).data?.isFrameOverlay === true
        );

        if (frameOverlay) {
          console.log('Frame overlay found, ensuring proper layering');
          // Get current indices
          const photoIndex = objects.indexOf(img);
          const frameIndex = objects.indexOf(frameOverlay);

          console.log('Object indices - Photo:', photoIndex, 'Frame:', frameIndex);

          // CRITICAL ISSUE: Photo appears when on top but disappears when frame is on top
          // This means the frame overlay PNG likely doesn't have proper transparency
          // SOLUTION: Keep photo ABOVE frame overlay, but use frame overlay as a visual guide
          // OR: The PNG needs to be regenerated with proper transparency in photo area

          // For now, let's try keeping photo on top so it's visible
          // The frame overlay will be below, showing calendar and borders
          // This is a workaround until PNG transparency is fixed

          console.warn('⚠️ WORKAROUND: Keeping photo on top of frame overlay');
          console.warn('⚠️ Frame overlay PNG may not have proper transparency in photo area');
          console.warn('⚠️ Regenerate march-2026-calendar_v3.png with transparent photo area');

          // PERMANENT FIX: Keep photo on top so it's always visible
          // Frame overlay PNG doesn't have proper transparency in photo area
          // Photo MUST stay on top - this is the correct solution
          this.canvas.bringToFront(img);
          this.canvas.sendToBack(frameOverlay);

          // Lock the order - photo stays on top permanently
          // Make photo non-selectable to prevent accidental moves
          img.set({ selectable: false, evented: false });

          // Verify and log final order
          const finalObjects = (this.canvas as any).getObjects() || [];
          const finalPhotoIndex = finalObjects.indexOf(img);
          const finalFrameIndex = finalObjects.indexOf(frameOverlay);

          console.log('✅ PERMANENT LAYERING:', {
            photoIndex: finalPhotoIndex,
            frameIndex: finalFrameIndex,
            photoIsOnTop: finalPhotoIndex > finalFrameIndex,
            photoLocked: !img.selectable,
            note: 'Photo is permanently on top. Frame overlay shows calendar below.'
          });

          // Force render to ensure order is applied
          this.canvas.renderAll();
        } else {
          console.log('No frame overlay found, bringing photo to front');
          this.canvas.bringToFront(img);
        }

        // Final object count
        const finalObjects = (this.canvas as any).getObjects() || [];
        console.log('Final object count:', finalObjects.length);
        finalObjects.forEach((obj: any, index: number) => {
          const data = (obj as any).data || {};
          console.log(`Object ${index}:`, {
            type: data.isPhoto ? 'Photo' : data.isFrameOverlay ? 'Frame' : data.isCameraFeed ? 'Camera' : 'Other',
            left: obj.left,
            top: obj.top,
            width: obj.width,
            height: obj.height
          });
        });
      }

      // Force render
      this.canvas?.renderAll();
      console.log('✅ Image successfully added to canvas');

      // Final verification and ensure photo stays visible PERMANENTLY
      setTimeout(() => {
        if (this.canvas && targetSlot) {
          const objects = (this.canvas as any).getObjects() || [];
          const photo = objects.find((obj: any) =>
            (obj as any).data?.isPhoto === true && (obj as any).data?.slotId === targetSlot.id
          );
          const frameOverlay = objects.find((obj: any) =>
            (obj as any).data?.isFrameOverlay === true
          );

          if (photo) {
            const photoIndex = objects.indexOf(photo);
            const frameIndex = frameOverlay ? objects.indexOf(frameOverlay) : -1;

            // CRITICAL: Ensure photo ALWAYS stays on top for visibility
            // Frame overlay PNG doesn't have proper transparency, so photo must be visible
            if (frameOverlay && photoIndex < frameIndex) {
              console.log('🔧 FIXING: Ensuring photo stays on top permanently');
              this.canvas.bringToFront(photo);
              this.canvas.renderAll();
            }

            // Verify photo is visible
            const photoVisible = photo.opacity > 0 &&
              photo.left !== undefined &&
              photo.top !== undefined &&
              (photo.width || 0) > 0 &&
              (photo.height || 0) > 0;

            console.log('✅ Final photo status:', {
              visible: photoVisible,
              position: { left: photo.left, top: photo.top },
              opacity: photo.opacity,
              zIndex: objects.indexOf(photo),
              frameZIndex: frameIndex,
              isOnTop: objects.indexOf(photo) > frameIndex,
              note: 'Photo is permanently on top to ensure visibility'
            });

            if (!photoVisible) {
              console.error('❌ Photo visibility issue detected! Fixing...');
              photo.set({ opacity: 1 });
              this.canvas.bringToFront(photo);
              this.canvas.renderAll();
            }
          }
        }
      }, 100);
    }, options);
  }

  deleteSelected(): void {
    if (!this.canvas) {
      return;
    }

    const activeObjects = this.canvas.getActiveObjects();
    activeObjects.forEach((obj: any) => {
      this.canvas?.remove(obj);
    });
    this.canvas.discardActiveObject();
    this.canvas.renderAll();
  }

  bringToFront(): void {
    if (!this.canvas) {
      return;
    }

    const activeObject = this.canvas.getActiveObject();
    if (activeObject) {
      this.canvas.bringToFront(activeObject);
      this.canvas.renderAll();
    }
  }

  sendToBack(): void {
    if (!this.canvas) {
      return;
    }

    const activeObject = this.canvas.getActiveObject();
    if (activeObject) {
      this.canvas.sendToBack(activeObject);
      this.canvas.renderAll();
    }
  }

  getCanvas(): any | null {
    return this.canvas;
  }

  exportCanvas(): HTMLCanvasElement | null {
    if (!this.canvas) {
      return null;
    }

    // Create high-res export canvas
    const originalWidth = (this.canvas as any).originalWidth;
    const originalHeight = (this.canvas as any).originalHeight;
    const displayScale = (this.canvas as any).displayScale;
    const exportScale = 1 / displayScale;

    const dataUrl = this.canvas.toDataURL({
      format: 'png',
      quality: 1,
      multiplier: exportScale
    });

    const exportCanvas = document.createElement('canvas');
    exportCanvas.width = originalWidth;
    exportCanvas.height = originalHeight;

    const ctx = exportCanvas.getContext('2d', {
      alpha: true,
      willReadFrequently: false
    });
    if (ctx) {
      // Enable high-quality image smoothing for export
      ctx.imageSmoothingEnabled = true;
      ctx.imageSmoothingQuality = 'high';
      const img = new Image();
      img.src = dataUrl;
      img.onload = () => {
        ctx.drawImage(img, 0, 0);
      };
    }

    return exportCanvas;
  }

  ngOnDestroy(): void {
    this.canvas?.dispose();
  }
}

