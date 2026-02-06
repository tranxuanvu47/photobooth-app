export type LayoutType = 1 | 2 | 4 | 6;

export type PresetType = '4x6-portrait' | '4x6-landscape' | '2x6-strip' | 'calendar-polaroid';

export interface LayoutSlot {
  id: string;
  x: number;
  y: number;
  width: number;
  height: number;
  aspectRatio?: number;
  fitMode: 'fit' | 'fill';
  imageUrl?: string;
  rotation?: number;
  scale?: number;
  offsetX?: number;
  offsetY?: number;
}

export interface LayoutConfig {
  id: string;
  name: string;
  type: LayoutType;
  preset: PresetType;
  width: number; // in pixels at 300 DPI
  height: number; // in pixels at 300 DPI
  slots: LayoutSlot[];
  backgroundColor: string;
  backgroundTexture?: string;
  borderStyle?: BorderStyle;
  padding: number;
  margin: number;
  hasHeader: boolean;
  hasFooter: boolean;
  headerText?: string;
  footerText?: string;
}

export interface BorderStyle {
  width: number;
  color: string;
  style: 'solid' | 'dashed' | 'dotted' | 'double';
  radius: number;
}

export const PRESETS: Record<PresetType, Omit<LayoutConfig, 'id'>> = {
  '4x6-portrait': {
    name: '4x6 Portrait',
    type: 1,
    preset: '4x6-portrait',
    width: 1200, // 4 inches * 300 DPI
    height: 1800, // 6 inches * 300 DPI
    slots: [
      {
        id: 'slot-1',
        x: 100,
        y: 100,
        width: 1000,
        height: 1500,
        fitMode: 'fill'
      }
    ],
    backgroundColor: '#ffffff',
    padding: 50,
    margin: 50,
    hasHeader: false,
    hasFooter: true
  },
  '4x6-landscape': {
    name: '4x6 Landscape',
    type: 1,
    preset: '4x6-landscape',
    width: 1800, // 6 inches * 300 DPI
    height: 1200, // 4 inches * 300 DPI
    slots: [
      {
        id: 'slot-1',
        x: 150,
        y: 100,
        width: 1500,
        height: 1000,
        fitMode: 'fill'
      }
    ],
    backgroundColor: '#ffffff',
    padding: 50,
    margin: 50,
    hasHeader: false,
    hasFooter: true
  },
  '2x6-strip': {
    name: '2x6 Photo Strip',
    type: 4,
    preset: '2x6-strip',
    width: 600, // 2 inches * 300 DPI
    height: 1800, // 6 inches * 300 DPI
    slots: [
      {
        id: 'slot-1',
        x: 50,
        y: 50,
        width: 500,
        height: 375,
        fitMode: 'fill'
      },
      {
        id: 'slot-2',
        x: 50,
        y: 475,
        width: 500,
        height: 375,
        fitMode: 'fill'
      },
      {
        id: 'slot-3',
        x: 50,
        y: 900,
        width: 500,
        height: 375,
        fitMode: 'fill'
      },
      {
        id: 'slot-4',
        x: 50,
        y: 1325,
        width: 500,
        height: 375,
        fitMode: 'fill'
      }
    ],
    backgroundColor: '#ffffff',
    padding: 25,
    margin: 25,
    hasHeader: false,
    hasFooter: true
  },
  'calendar-polaroid': {
    name: 'Calendar Polaroid',
    type: 1,
    preset: 'calendar-polaroid',
    width: 1200, // 4 inches * 300 DPI
    height: 1800, // 6 inches * 300 DPI
    slots: [
      {
        id: 'slot-1',
        x: 130,   // Shifted right to avoid overlapping heart
        y: 70,    // Moved up
        width: 920,
        height: 920, // Slightly smaller to clear heart shape
        fitMode: 'fit' // Use fit mode to prevent overflow - image must stay within red box
      }
    ],
    backgroundColor: '#ffffff',
    padding: 50,
    margin: 50,
    hasHeader: false,
    hasFooter: false
  }
};

