export interface Sticker {
  id: string;
  name: string;
  category: StickerCategory;
  url: string;
  width: number;
  height: number;
  keywords: string[];
}

export type StickerCategory =
  | 'rings'
  | 'flowers'
  | 'hearts'
  | 'balloons'
  | 'confetti'
  | 'text-badges'
  | 'decorative';

export const STICKERS: Sticker[] = [
  // Rings
  {
    id: 'ring-1',
    name: 'Wedding Rings',
    category: 'rings',
    url: 'assets/stickers/wedding-rings.svg',
    width: 100,
    height: 100,
    keywords: ['wedding', 'rings', 'marriage']
  },
  {
    id: 'ring-2',
    name: 'Diamond Ring',
    category: 'rings',
    url: 'assets/stickers/diamond-ring.svg',
    width: 80,
    height: 80,
    keywords: ['engagement', 'diamond', 'ring']
  },

  // Flowers
  {
    id: 'flower-1',
    name: 'Rose',
    category: 'flowers',
    url: 'assets/stickers/rose.svg',
    width: 90,
    height: 90,
    keywords: ['rose', 'flower', 'romantic']
  },
  {
    id: 'flower-2',
    name: 'Bouquet',
    category: 'flowers',
    url: 'assets/stickers/bouquet.svg',
    width: 120,
    height: 120,
    keywords: ['bouquet', 'flowers', 'wedding']
  },
  {
    id: 'flower-3',
    name: 'Floral Corner',
    category: 'flowers',
    url: 'assets/stickers/floral-corner.svg',
    width: 150,
    height: 150,
    keywords: ['floral', 'corner', 'decoration']
  },

  // Hearts
  {
    id: 'heart-1',
    name: 'Red Heart',
    category: 'hearts',
    url: 'assets/stickers/red-heart.svg',
    width: 80,
    height: 80,
    keywords: ['heart', 'love', 'red']
  },
  {
    id: 'heart-2',
    name: 'Heart Outline',
    category: 'hearts',
    url: 'assets/stickers/heart-outline.svg',
    width: 70,
    height: 70,
    keywords: ['heart', 'outline', 'love']
  },
  {
    id: 'heart-3',
    name: 'Double Hearts',
    category: 'hearts',
    url: 'assets/stickers/double-hearts.svg',
    width: 100,
    height: 80,
    keywords: ['hearts', 'double', 'love']
  },

  // Balloons
  {
    id: 'balloon-1',
    name: 'Heart Balloon',
    category: 'balloons',
    url: 'assets/stickers/heart-balloon.svg',
    width: 70,
    height: 100,
    keywords: ['balloon', 'heart', 'party']
  },
  {
    id: 'balloon-2',
    name: 'Balloon Bunch',
    category: 'balloons',
    url: 'assets/stickers/balloon-bunch.svg',
    width: 120,
    height: 150,
    keywords: ['balloons', 'bunch', 'celebration']
  },

  // Confetti
  {
    id: 'confetti-1',
    name: 'Confetti Scatter',
    category: 'confetti',
    url: 'assets/stickers/confetti.svg',
    width: 150,
    height: 150,
    keywords: ['confetti', 'celebration', 'party']
  },
  {
    id: 'confetti-2',
    name: 'Star Confetti',
    category: 'confetti',
    url: 'assets/stickers/star-confetti.svg',
    width: 120,
    height: 120,
    keywords: ['stars', 'confetti', 'sparkle']
  },

  // Text Badges
  {
    id: 'badge-1',
    name: 'Just Married',
    category: 'text-badges',
    url: 'assets/stickers/just-married.svg',
    width: 200,
    height: 80,
    keywords: ['just married', 'wedding', 'text']
  },
  {
    id: 'badge-2',
    name: 'Love Banner',
    category: 'text-badges',
    url: 'assets/stickers/love-banner.svg',
    width: 180,
    height: 70,
    keywords: ['love', 'banner', 'text']
  },
  {
    id: 'badge-3',
    name: 'Mr & Mrs',
    category: 'text-badges',
    url: 'assets/stickers/mr-mrs.svg',
    width: 150,
    height: 60,
    keywords: ['mr and mrs', 'married', 'text']
  },

  // Decorative
  {
    id: 'deco-1',
    name: 'Laurel Wreath',
    category: 'decorative',
    url: 'assets/stickers/laurel-wreath.svg',
    width: 140,
    height: 140,
    keywords: ['laurel', 'wreath', 'frame']
  },
  {
    id: 'deco-2',
    name: 'Dove',
    category: 'decorative',
    url: 'assets/stickers/dove.svg',
    width: 90,
    height: 90,
    keywords: ['dove', 'peace', 'wedding']
  },
  {
    id: 'deco-3',
    name: 'Champagne Glasses',
    category: 'decorative',
    url: 'assets/stickers/champagne.svg',
    width: 100,
    height: 100,
    keywords: ['champagne', 'glasses', 'celebration']
  }
];

