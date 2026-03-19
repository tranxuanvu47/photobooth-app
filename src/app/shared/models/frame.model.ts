export interface Frame {
  id: string;
  name: string;
  theme: FrameTheme;
  description: string;
  previewUrl: string;
  overlayUrl?: string;
  config: FrameConfig;
}

export type FrameTheme =
  | 'classic'
  | 'minimal'
  | 'floral'
  | 'gold'
  | 'modern'
  | 'vintage'
  | 'pastel'
  | 'elegant-black'
  | 'watercolor'
  | 'luxury'
  | 'rustic'
  | 'geometric'
  | 'seasonal';

export interface FrameConfig {
  borderWidth: number;
  borderColor: string;
  borderStyle: 'solid' | 'double' | 'groove' | 'ridge' | 'inset' | 'outset';
  cornerRadius: number;
  shadowOffsetX: number;
  shadowOffsetY: number;
  shadowBlur: number;
  shadowColor: string;
  backgroundColor?: string;
  innerBorderWidth?: number;
  innerBorderColor?: string;
  pattern?: string;
}

export const FRAME_THEMES: Frame[] = [
  {
    id: 'classic-1',
    name: 'Classic White',
    theme: 'classic',
    description: 'Timeless white frame with subtle shadow',
    previewUrl: 'assets/frames/classic-preview.png',
    config: {
      borderWidth: 40,
      borderColor: '#ffffff',
      borderStyle: 'solid',
      cornerRadius: 0,
      shadowOffsetX: 0,
      shadowOffsetY: 4,
      shadowBlur: 8,
      shadowColor: 'rgba(0, 0, 0, 0.15)'
    }
  },
  {
    id: 'minimal-1',
    name: 'Minimal Black',
    theme: 'minimal',
    description: 'Clean thin black border',
    previewUrl: 'assets/frames/minimal-preview.png',
    config: {
      borderWidth: 10,
      borderColor: '#000000',
      borderStyle: 'solid',
      cornerRadius: 0,
      shadowOffsetX: 0,
      shadowOffsetY: 0,
      shadowBlur: 0,
      shadowColor: 'transparent'
    }
  },
  {
    id: 'floral-1',
    name: 'Floral Romance',
    theme: 'floral',
    description: 'Romantic floral pattern frame',
    previewUrl: 'assets/frames/floral-preview.png',
    config: {
      borderWidth: 60,
      borderColor: '#fde7e9',
      borderStyle: 'solid',
      cornerRadius: 8,
      shadowOffsetX: 0,
      shadowOffsetY: 2,
      shadowBlur: 6,
      shadowColor: 'rgba(253, 162, 176, 0.3)',
      pattern: 'floral'
    }
  },
  {
    id: 'gold-1',
    name: 'Elegant Gold',
    theme: 'gold',
    description: 'Luxurious gold frame with depth',
    previewUrl: 'assets/frames/gold-preview.png',
    config: {
      borderWidth: 50,
      borderColor: '#d4af37',
      borderStyle: 'ridge',
      cornerRadius: 4,
      shadowOffsetX: 0,
      shadowOffsetY: 4,
      shadowBlur: 10,
      shadowColor: 'rgba(212, 175, 55, 0.4)',
      innerBorderWidth: 5,
      innerBorderColor: '#f4e5c0'
    }
  },
  {
    id: 'modern-1',
    name: 'Modern Gradient',
    theme: 'modern',
    description: 'Contemporary gradient frame',
    previewUrl: 'assets/frames/modern-preview.png',
    config: {
      borderWidth: 30,
      borderColor: '#667eea',
      borderStyle: 'solid',
      cornerRadius: 12,
      shadowOffsetX: 0,
      shadowOffsetY: 6,
      shadowBlur: 12,
      shadowColor: 'rgba(102, 126, 234, 0.25)'
    }
  },
  {
    id: 'vintage-1',
    name: 'Vintage Sepia',
    theme: 'vintage',
    description: 'Nostalgic vintage style',
    previewUrl: 'assets/frames/vintage-preview.png',
    config: {
      borderWidth: 55,
      borderColor: '#8b7355',
      borderStyle: 'groove',
      cornerRadius: 0,
      shadowOffsetX: 2,
      shadowOffsetY: 2,
      shadowBlur: 8,
      shadowColor: 'rgba(101, 67, 33, 0.3)',
      innerBorderWidth: 8,
      innerBorderColor: '#d4c4a8'
    }
  },
  {
    id: 'pastel-1',
    name: 'Pastel Dream',
    theme: 'pastel',
    description: 'Soft pastel colors',
    previewUrl: 'assets/frames/pastel-preview.png',
    config: {
      borderWidth: 45,
      borderColor: '#b8a3c5',
      borderStyle: 'solid',
      cornerRadius: 16,
      shadowOffsetX: 0,
      shadowOffsetY: 3,
      shadowBlur: 8,
      shadowColor: 'rgba(184, 163, 197, 0.2)',
      innerBorderWidth: 3,
      innerBorderColor: '#fdeef4'
    }
  },
  {
    id: 'elegant-black-1',
    name: 'Elegant Black',
    theme: 'elegant-black',
    description: 'Sophisticated black frame',
    previewUrl: 'assets/frames/elegant-black-preview.png',
    config: {
      borderWidth: 60,
      borderColor: '#1a1a1a',
      borderStyle: 'solid',
      cornerRadius: 0,
      shadowOffsetX: 0,
      shadowOffsetY: 5,
      shadowBlur: 15,
      shadowColor: 'rgba(0, 0, 0, 0.4)',
      innerBorderWidth: 10,
      innerBorderColor: '#c0c0c0'
    }
  },
  {
    id: 'watercolor-1',
    name: 'Watercolor Wash',
    theme: 'watercolor',
    description: 'Artistic watercolor effect',
    previewUrl: 'assets/frames/watercolor-preview.png',
    config: {
      borderWidth: 70,
      borderColor: '#e8f4f8',
      borderStyle: 'solid',
      cornerRadius: 20,
      shadowOffsetX: 0,
      shadowOffsetY: 2,
      shadowBlur: 10,
      shadowColor: 'rgba(168, 218, 220, 0.3)',
      pattern: 'watercolor'
    }
  },
  {
    id: 'luxury-1',
    name: 'Luxury Pearl',
    theme: 'luxury',
    description: 'Premium pearl finish',
    previewUrl: 'assets/frames/luxury-preview.png',
    config: {
      borderWidth: 80,
      borderColor: '#f8f8ff',
      borderStyle: 'outset',
      cornerRadius: 8,
      shadowOffsetX: 0,
      shadowOffsetY: 6,
      shadowBlur: 18,
      shadowColor: 'rgba(184, 184, 208, 0.35)',
      innerBorderWidth: 15,
      innerBorderColor: '#e6e6fa'
    }
  },
  {
    id: 'rustic-1',
    name: 'Rustic Wood',
    theme: 'rustic',
    description: 'Natural wood texture',
    previewUrl: 'assets/frames/rustic-preview.png',
    config: {
      borderWidth: 65,
      borderColor: '#8b6f47',
      borderStyle: 'ridge',
      cornerRadius: 4,
      shadowOffsetX: 1,
      shadowOffsetY: 3,
      shadowBlur: 6,
      shadowColor: 'rgba(101, 67, 33, 0.25)',
      pattern: 'wood'
    }
  },
  {
    id: 'geometric-1',
    name: 'Geometric Modern',
    theme: 'geometric',
    description: 'Bold geometric patterns',
    previewUrl: 'assets/frames/geometric-preview.png',
    config: {
      borderWidth: 40,
      borderColor: '#2d3748',
      borderStyle: 'solid',
      cornerRadius: 0,
      shadowOffsetX: 4,
      shadowOffsetY: 4,
      shadowBlur: 0,
      shadowColor: 'rgba(45, 55, 72, 0.5)',
      pattern: 'geometric'
    }
  },
  {
    id: 'march-2026-calendar',
    name: 'March 2026 Calendar',
    theme: 'seasonal',
    description: 'March 2026 calendar with heart marking the 8th',
    previewUrl: 'assets/frames/march-2026-calendar-preview.png',
    overlayUrl: 'assets/frames/march-2026-calendar_v3.png',
    config: {
      borderWidth: 0,
      borderColor: 'transparent',
      borderStyle: 'solid',
      cornerRadius: 0,
      shadowOffsetX: 0,
      shadowOffsetY: 0,
      shadowBlur: 0,
      shadowColor: 'transparent'
    }
  }
];

