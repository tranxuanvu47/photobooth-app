import { LayoutConfig } from './layout.model';
import { Frame } from './frame.model';

export interface EditorState {
  id: string;
  layout: LayoutConfig;
  frame: Frame | null;
  canvasObjects: CanvasObject[];
  history: HistoryState[];
  historyIndex: number;
  exportSettings: ExportSettings;
}

export interface CanvasObject {
  id: string;
  type: 'image' | 'text' | 'sticker';
  left: number;
  top: number;
  width: number;
  height: number;
  angle: number;
  scaleX: number;
  scaleY: number;
  opacity: number;
  locked: boolean;
  zIndex: number;
  data: ImageData | TextData | StickerData;
}

export interface ImageData {
  url: string;
  slotId?: string;
  filters?: string[];
}

export interface TextData {
  text: string;
  fontFamily: string;
  fontSize: number;
  fontWeight: 'normal' | 'bold';
  fontStyle: 'normal' | 'italic';
  textDecoration: 'none' | 'underline';
  fill: string;
  stroke?: string;
  strokeWidth?: number;
  textAlign: 'left' | 'center' | 'right';
  backgroundColor?: string;
}

export interface StickerData {
  url: string;
  category: string;
}

export interface HistoryState {
  timestamp: number;
  objects: CanvasObject[];
}

export interface ExportSettings {
  format: 'png' | 'jpeg' | 'pdf';
  quality: number;
  dpi: number;
  includeBleed: boolean;
  showGuides: boolean;
}

export interface CameraDevice {
  deviceId: string;
  label: string;
  kind: 'videoinput';
}

export interface CameraOptions {
  deviceId?: string;
  facingMode?: 'user' | 'environment';
  width?: number;
  height?: number;
  aspectRatio?: number;
}

export interface CountdownConfig {
  duration: 0 | 3 | 5 | 10;
  onTick?: (remaining: number) => void;
  onComplete?: () => void;
}

