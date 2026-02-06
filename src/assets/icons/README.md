# PWA Icons

This directory contains icons for the Progressive Web App.

## Required Icon Sizes

For proper PWA support, you need icons in the following sizes:

- 72x72
- 96x96
- 128x128
- 144x144
- 152x152
- 192x192
- 384x384
- 512x512

## Generating Icons

You can generate all required sizes from a single source image using:

### Online Tools
- https://www.pwabuilder.com/imageGenerator
- https://realfavicongenerator.net/

### Command Line (ImageMagick)
```bash
convert source-icon.png -resize 72x72 icon-72x72.png
convert source-icon.png -resize 96x96 icon-96x96.png
convert source-icon.png -resize 128x128 icon-128x128.png
convert source-icon.png -resize 144x144 icon-144x144.png
convert source-icon.png -resize 152x152 icon-152x152.png
convert source-icon.png -resize 192x192 icon-192x192.png
convert source-icon.png -resize 384x384 icon-384x384.png
convert source-icon.png -resize 512x512 icon-512x512.png
```

## Design Guidelines

- Use a simple, recognizable design
- Ensure icon looks good at all sizes
- Use PNG format with transparency
- Consider using your brand colors
- Test on both light and dark backgrounds

## Placeholder Icons

The project includes placeholder icons. Replace them with your actual brand icons before deploying to production.

To create placeholder icons quickly, use a solid color background with your app initials or a camera icon.

