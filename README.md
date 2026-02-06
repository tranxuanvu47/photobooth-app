# Wedding Photo Booth

A production-ready Angular web application for creating beautiful photo booth prints at weddings and events. Works seamlessly on desktop PCs and mobile devices.

![Angular](https://img.shields.io/badge/Angular-18.x-red)
![TypeScript](https://img.shields.io/badge/TypeScript-5.4-blue)
![License](https://img.shields.io/badge/license-MIT-green)

## ✨ Features

### 🎨 **Customizable Layouts**
- Multiple photo layouts: 1, 2, 4, and 6 photos
- Pre-configured presets for 4×6 and 2×6 print sizes
- Adjustable padding, margins, and background colors
- Custom header/footer areas for names and dates

### 🖼️ **Beautiful Frames**
- 12+ professionally designed frame themes
- Classic, minimal, floral, gold, modern, vintage, and more
- Customizable colors, borders, and shadows
- Compatible with all layout sizes

### 📸 **Camera Capture**
- Live camera preview with `getUserMedia` API
- Countdown timer (0s, 3s, 5s, 10s)
- Front/back camera switching on mobile
- File upload support for existing photos
- Retake and multi-shot capabilities

### ✏️ **Advanced Editor**
- Fabric.js-powered canvas editing
- Add and customize text with multiple fonts
- Drag, resize, rotate, and layer objects
- 20+ wedding-themed stickers
- Undo/redo functionality

### 🖨️ **Print & Export**
- Professional 300 DPI output
- Export as PNG, JPEG, or PDF
- Browser-based printing
- Optional direct print agent for silent printing
- Mobile sharing capabilities

### 📱 **Multi-Device Support**
- Responsive design for desktop and mobile
- Touch-optimized controls
- PWA with offline support
- Works on Chrome, Edge, Safari, and Firefox

## 🚀 Quick Start

### Prerequisites

- Node.js 18+ and npm
- Modern web browser
- Optional: Printer connected to PC for direct printing

### Installation

1. **Clone the repository**
```bash
git clone <repository-url>
cd photobooth
```

2. **Install dependencies**
```bash
npm install
```

3. **Start the development server**
```bash
npm start
```

4. **Open your browser**
Navigate to `http://localhost:4200`

### Production Build

```bash
npm run build
```

The build artifacts will be in the `dist/` directory.

## 📖 Usage Guide

### Basic Workflow

1. **Choose Layout** - Select from 4×6 portrait, 4×6 landscape, or 2×6 photo strip
2. **Select Frame** - Pick a frame theme or go frameless
3. **Capture Photos** - Take photos with camera or upload existing ones
4. **Decorate** - Add text, stickers, and customize your design
5. **Preview & Export** - Review and export for printing or sharing

### Camera Capture

#### Desktop
- Click "Start Camera" to activate webcam
- Select countdown duration
- Click "Capture" to take photo
- Use "Retake" to try again or "Use Photo" to add to canvas

#### Mobile
- Grant camera permission when prompted
- Switch between front/back cameras
- Use large touch targets for easy control
- Alternatively, tap "Upload Photo" to use existing images

### Canvas Editor

#### Adding Text
1. Switch to "Text" tab
2. Enter your text
3. Press Enter or click "Add Text"
4. Adjust font, size, color, and style
5. Drag to position, resize, or rotate

#### Adding Stickers
1. Switch to "Stickers" tab
2. Filter by category if desired
3. Click a sticker to add to canvas
4. Drag, resize, or rotate as needed

#### Layer Management
- **Delete**: Select object and click trash icon
- **Bring to Front**: Move object above others
- **Send to Back**: Move object below others

### Printing

#### Browser Print (Recommended for Most Users)
1. Complete your design
2. Click "Print" in the preview
3. Select "Print with Browser"
4. Configure print settings
5. Click "Print with Browser" button
6. Use browser's print dialog

#### Direct Print Agent (Advanced)
For kiosk setups with automatic printing:

1. **Start the print agent**
```bash
cd print-agent
npm install
npm start
```

2. **In the app**
- The app automatically detects the running agent
- Select "Print with Agent"
- Choose your printer
- Click "Print with Agent" button
- Print job sends directly without dialog

See [Print Agent Documentation](print-agent/README.md) for details.

## 🎨 Customization

### Adding Frames

Edit `src/app/shared/models/frame.model.ts`:

```typescript
export const FRAME_THEMES: Frame[] = [
  // ... existing frames
  {
    id: 'my-custom-frame',
    name: 'My Frame',
    theme: 'custom',
    description: 'My custom frame design',
    previewUrl: 'assets/frames/my-frame-preview.png',
    config: {
      borderWidth: 50,
      borderColor: '#hexcolor',
      borderStyle: 'solid',
      cornerRadius: 8,
      shadowOffsetX: 0,
      shadowOffsetY: 4,
      shadowBlur: 10,
      shadowColor: 'rgba(0, 0, 0, 0.2)'
    }
  }
];
```

### Adding Stickers

1. Add SVG/PNG files to `src/assets/stickers/`
2. Update `src/app/shared/models/sticker.model.ts`:

```typescript
export const STICKERS: Sticker[] = [
  // ... existing stickers
  {
    id: 'my-sticker',
    name: 'My Sticker',
    category: 'decorative',
    url: 'assets/stickers/my-sticker.svg',
    width: 100,
    height: 100,
    keywords: ['custom', 'special']
  }
];
```

### Custom Layouts

Edit `src/app/shared/models/layout.model.ts` to add presets:

```typescript
export const PRESETS: Record<PresetType, Omit<LayoutConfig, 'id'>> = {
  // ... existing presets
  'my-layout': {
    name: 'My Custom Layout',
    type: 4,
    preset: 'my-layout',
    width: 1800,  // pixels at 300 DPI
    height: 1200,
    slots: [
      // Define photo slot positions
    ],
    // ... other config
  }
};
```

## 🏗️ Project Structure

```
photobooth/
├── src/
│   ├── app/
│   │   ├── features/           # Feature modules
│   │   │   ├── home/          # Landing page
│   │   │   ├── editor/        # Main editor
│   │   │   └── print/         # Print page
│   │   ├── shared/
│   │   │   ├── components/    # Reusable components
│   │   │   │   ├── layout-picker/
│   │   │   │   ├── frame-gallery/
│   │   │   │   ├── camera-capture/
│   │   │   │   └── canvas-editor/
│   │   │   ├── models/        # TypeScript interfaces
│   │   │   └── services/      # Business logic
│   │   │       ├── camera.service.ts
│   │   │       ├── countdown.service.ts
│   │   │       ├── editor-state.service.ts
│   │   │       ├── export.service.ts
│   │   │       └── print.service.ts
│   │   └── app.routes.ts
│   ├── assets/
│   │   ├── stickers/          # SVG/PNG stickers
│   │   └── frames/            # Frame overlays
│   └── styles.scss            # Global styles
├── print-agent/               # Optional print server
│   ├── server.js
│   └── package.json
├── angular.json
├── package.json
└── tsconfig.json
```

## 📱 Browser Compatibility

### Desktop
- ✅ Chrome 90+
- ✅ Edge 90+
- ✅ Firefox 88+
- ✅ Safari 14+

### Mobile
- ✅ Chrome for Android
- ✅ Safari iOS 14+
- ⚠️ iOS Safari has camera limitations (requires user gesture)

### Known Limitations

#### iOS Safari
- Camera must be activated by user tap (autoplay restrictions)
- Some camera resolutions may not be available
- Print dialog cannot be truly silent

#### All Mobile Browsers
- Canvas performance depends on device capabilities
- High-resolution exports may take longer on older devices

## 🔧 Configuration

### Environment-Specific Settings

Create `src/environments/environment.ts`:

```typescript
export const environment = {
  production: false,
  printAgentUrl: 'http://localhost:3000',
  defaultDpi: 300,
  maxImageSize: 5242880 // 5MB
};
```

### Print Settings

Default print settings in `src/app/shared/services/export.service.ts`:

```typescript
exportSettings: {
  format: 'jpeg',  // or 'png', 'pdf'
  quality: 0.95,   // JPEG quality 0-1
  dpi: 300,        // Print resolution
  includeBleed: false,
  showGuides: false
}
```

## 🧪 Testing

### Unit Tests
```bash
npm test
```

### E2E Tests
```bash
npm run e2e
```

### Key Test Coverage
- ✅ Countdown timer accuracy
- ✅ Camera permission handling
- ✅ Layout calculations
- ✅ Export scaling
- ✅ Print size conversions

## 🚀 Deployment

### Static Hosting (Netlify, Vercel, GitHub Pages)

1. Build for production:
```bash
npm run build
```

2. Deploy the `dist/wedding-photo-booth` folder

### Docker

```dockerfile
FROM node:18-alpine as build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist/wedding-photo-booth /usr/share/nginx/html
EXPOSE 80
```

Build and run:
```bash
docker build -t photo-booth .
docker run -p 80:80 photo-booth
```

### PWA Installation

Users can install the app:
1. Click browser menu (⋮)
2. Select "Install app" or "Add to Home Screen"
3. Launch from home screen for full-screen experience

## 🎯 Performance Optimization

### Implemented Optimizations
- ✅ Lazy loading of feature modules
- ✅ Service worker caching
- ✅ Image compression for exports
- ✅ Canvas rendering optimization
- ✅ Standalone components
- ✅ Signals for efficient reactivity

### Tips for Better Performance
- Use lower DPI (150-200) for proofs
- Limit sticker count per design
- Clear browser cache periodically
- Use wired connection for print agent

## 🔐 Security Considerations

- 📸 Camera permissions requested only when needed
- 💾 Images processed locally (no server upload)
- 🔒 Print agent should run on trusted networks only
- 🛡️ CORS configured for localhost development only

## 🐛 Troubleshooting

### Camera Not Working
- **Check permissions**: Grant camera access in browser settings
- **Check device**: Ensure camera is not in use by another app
- **iOS**: Tap "Start Camera" (user gesture required)
- **Try upload**: Use "Upload Photo" as alternative

### Print Quality Issues
- **Increase DPI**: Use 300 DPI for final prints
- **Check printer**: Verify printer settings (quality, paper size)
- **Use correct paper**: 4×6 or 2×6 photo paper
- **Calibrate**: Adjust margins if print is cut off

### Print Agent Not Connecting
- **Check if running**: `http://localhost:3000/status` should respond
- **Restart agent**: Stop and restart the print agent
- **Check port**: Ensure port 3000 is not in use
- **Firewall**: Allow Node.js through firewall

### Performance Issues
- **Reduce DPI**: Use 150 DPI during editing
- **Limit objects**: Keep text/stickers under 20 per design
- **Clear cache**: Clear browser cache and localStorage
- **Update browser**: Use latest browser version

## 📚 Additional Resources

- [Angular Documentation](https://angular.io/docs)
- [Fabric.js Documentation](http://fabricjs.com/docs/)
- [MDN Web APIs - getUserMedia](https://developer.mozilla.org/en-US/docs/Web/API/MediaDevices/getUserMedia)
- [Print Agent Details](print-agent/README.md)

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License.

## 🎉 Credits

Built with:
- [Angular](https://angular.io/)
- [Fabric.js](http://fabricjs.com/)
- [Express](https://expressjs.com/)

## 📞 Support

For issues and questions:
- Open an issue on GitHub
- Check the troubleshooting section above
- Review browser console for error messages

---

**Made with ❤️ for unforgettable wedding memories**

