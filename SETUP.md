# Setup Guide - Wedding Photo Booth

This guide will help you set up the Wedding Photo Booth application from scratch.

## Prerequisites

Before you begin, ensure you have:

- **Node.js** 18.x or higher ([Download](https://nodejs.org/))
- **npm** 9.x or higher (comes with Node.js)
- **Git** (optional, for cloning)
- A modern web browser (Chrome, Edge, Firefox, or Safari)
- (Optional) A printer connected to your PC for printing features

## Step-by-Step Setup

### 1. Install Dependencies
np
In the project root directory:

```bash
npm install
```

This will install all Angular dependencies including:
- Angular 18
- Fabric.js
- RxJS
- And other required packages

### 2. Install Print Agent Dependencies (Optional)

If you plan to use direct printing:

```bash
cd print-agent
npm install
cd ..
```

### 3. Create PWA Icons

The app needs icons for Progressive Web App functionality:

1. Create or obtain a 512x512 PNG icon for your app
2. Use an online tool like [PWA Builder Image Generator](https://www.pwabuilder.com/imageGenerator)
3. Generate all required sizes (72, 96, 128, 144, 152, 192, 384, 512)
4. Place them in `src/assets/icons/`

Or use ImageMagick:
```bash
cd src/assets/icons
# Place your source-icon.png here, then:
for size in 72 96 128 144 152 192 384 512; do
  convert source-icon.png -resize ${size}x${size} icon-${size}x${size}.png
done
```

### 4. Customize Branding (Optional)

#### Update Colors
Edit `src/styles.scss`:
```scss
:root {
  --primary-color: #your-color;
  --secondary-color: #your-color;
  // ... other colors
}
```

#### Update App Name
Edit `src/manifest.webmanifest`:
```json
{
  "name": "Your Event Photo Booth",
  "short_name": "Photo Booth"
  // ...
}
```

Edit `src/index.html`:
```html
<title>Your Event Photo Booth</title>
```

### 5. Add Custom Stickers (Optional)

1. Add SVG or PNG files to `src/assets/stickers/`
2. Update `src/app/shared/models/sticker.model.ts`
3. Add entries to the `STICKERS` array

### 6. Configure Print Settings

Edit `src/app/shared/services/export.service.ts` for default export settings:

```typescript
exportSettings: {
  format: 'jpeg',  // or 'png'
  quality: 0.95,   // 0.8-1.0 recommended
  dpi: 300,        // 150-300 for prints
  // ...
}
```

## Running the Application

### Development Mode

Start the Angular development server:

```bash
npm start
```

The app will be available at `http://localhost:4200`

Changes to files will automatically reload the browser.

### Production Build

Create an optimized production build:

```bash
npm run build
```

The output will be in `dist/wedding-photo-booth/`

### Running the Print Agent

In a separate terminal:

```bash
npm run print-agent
```

The print agent will start on `http://localhost:3000`

## Testing the Application

### 1. Test Basic Flow

1. Open `http://localhost:4200`
2. Click "Start Photo Booth"
3. Choose a layout
4. Select a frame (or skip)
5. Upload a test photo or use camera
6. Add text and stickers
7. Preview and export

### 2. Test Camera (Desktop)

1. Grant camera permissions when prompted
2. Try different countdown settings
3. Test capture and retake
4. Verify image quality

### 3. Test Camera (Mobile)

1. Open the app on your phone
2. Test front/back camera switching
3. Verify touch controls work smoothly
4. Test file upload alternative

### 4. Test Printing

#### Browser Print
1. Complete a design
2. Click "Print"
3. Select "Print with Browser"
4. Verify print preview looks correct
5. Test with your printer

#### Print Agent (Optional)
1. Start print agent: `npm run print-agent`
2. Verify agent shows in app
3. Select printer from dropdown
4. Send test print job
5. Check printer queue

## Deployment

### Deploy to Netlify

1. Build the app: `npm run build`
2. Create a Netlify account
3. Drag and drop the `dist/wedding-photo-booth` folder
4. Your site is live!

Or use Netlify CLI:
```bash
npm install -g netlify-cli
npm run build
netlify deploy --prod --dir=dist/wedding-photo-booth
```

### Deploy to Vercel

```bash
npm install -g vercel
vercel
```

Follow the prompts. Vercel will automatically detect Angular.

### Deploy to GitHub Pages

1. Install gh-pages:
```bash
npm install -g angular-cli-ghpages
```

2. Build and deploy:
```bash
npm run build
npx angular-cli-ghpages --dir=dist/wedding-photo-booth
```

### Self-Host with Docker

Build Docker image:
```bash
docker build -t photo-booth .
```

Run container:
```bash
docker run -d -p 80:80 photo-booth
```

## Kiosk Setup (Event Use)

For events where you want a dedicated kiosk:

### Hardware
- PC or laptop with camera
- Touch screen (optional but recommended)
- Photo printer (USB or network)
- Mouse/keyboard (for setup)

### Software Setup

1. Install Chrome or Edge
2. Set up auto-login to Windows/macOS
3. Configure browser to launch on startup
4. Enable kiosk mode:

**Chrome Kiosk Mode:**
```bash
chrome.exe --kiosk --app=http://localhost:4200
```

**Windows Startup:**
Create a shortcut in:
```
C:\Users\[YourUser]\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup
```

**macOS Startup:**
System Preferences → Users & Groups → Login Items

### Print Agent Setup

1. Start print agent automatically:

**Windows:** Create a batch file `start-print-agent.bat`:
```batch
@echo off
cd C:\path\to\photobooth\print-agent
node server.js
```

Add to startup.

**macOS/Linux:** Create a service or cron job

2. Configure default printer in Windows/macOS settings

3. Test automatic printing workflow

## Troubleshooting Setup

### npm install fails
- Clear npm cache: `npm cache clean --force`
- Delete `node_modules` and `package-lock.json`, try again
- Check Node.js version: `node --version`

### Build errors
- Check TypeScript version compatibility
- Ensure all files are saved
- Check for syntax errors in recent changes

### Camera not working in development
- Use HTTPS or localhost (required for getUserMedia)
- Check browser permissions
- Try a different browser

### Print agent won't start
- Check if port 3000 is in use
- Install print-agent dependencies
- Check firewall settings

### PWA not installing
- Build for production mode
- Verify all icon sizes exist
- Check manifest.webmanifest is valid
- Use HTTPS in production

## Next Steps

- [ ] Customize colors and branding
- [ ] Add your own stickers and frames
- [ ] Test on target devices
- [ ] Configure printer settings
- [ ] Train event staff on usage
- [ ] Prepare backup camera/upload options
- [ ] Print test pages to verify quality

## Support

- Check the main [README.md](README.md) for detailed documentation
- Review [Print Agent README](print-agent/README.md) for printing details
- Look at code comments for implementation details

---

**Ready to create amazing photo booth memories! 📸💕**

