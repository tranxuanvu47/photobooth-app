# Quick Start Guide 🚀

Get the Wedding Photo Booth running in 5 minutes!

## Prerequisites

- Node.js 18+ installed
- A modern web browser

## Installation (2 minutes)

```bash
# 1. Navigate to project directory
cd photobooth

# 2. Install dependencies
npm install

# 3. Start the application
npm start
```

The app will open at `http://localhost:4200`

## First Run (3 minutes)

### 1. Test Basic Flow
1. Click **"Start Photo Booth"**
2. Select **"4x6 Portrait"** layout
3. Choose a frame or skip
4. Click **"Next"** to photos
5. Click **"Upload Photo"** (easier than camera for first test)
6. Select a test image
7. Click **"Next"** to edit
8. Add some text or stickers
9. Click **"Next"** to preview
10. Click **"Download"** to save

### 2. Test Camera (Optional)
1. Go back to photos step
2. Click **"Start Camera"**
3. Allow camera permissions
4. Select countdown (try 3s)
5. Click **"Capture"**
6. Click **"Use Photo"**

### 3. Test Print Agent (Optional)
```bash
# In a new terminal
cd print-agent
npm install
npm start
```

Then in the app:
1. Complete a design
2. Go to print page
3. You should see "Print Agent Available"
4. Select printer
5. Click **"Print with Agent"**

## Common Tasks

### Add Custom Stickers

1. Add your SVG file to `src/assets/stickers/my-sticker.svg`
2. Edit `src/app/shared/models/sticker.model.ts`:

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
    keywords: ['custom']
  }
];
```

3. Restart the dev server

### Change Colors

Edit `src/styles.scss`:

```scss
:root {
  --primary-color: #your-color;
  --primary-dark: #your-darker-color;
}
```

Colors update immediately (hot reload).

### Add a New Frame

Edit `src/app/shared/models/frame.model.ts`:

```typescript
{
  id: 'my-frame',
  name: 'My Frame',
  theme: 'custom',
  description: 'My custom frame',
  previewUrl: 'assets/frames/preview.png',
  config: {
    borderWidth: 40,
    borderColor: '#hexcolor',
    borderStyle: 'solid',
    cornerRadius: 8,
    shadowOffsetX: 0,
    shadowOffsetY: 4,
    shadowBlur: 10,
    shadowColor: 'rgba(0, 0, 0, 0.2)'
  }
}
```

## Troubleshooting

### npm install fails
```bash
# Clear cache and try again
npm cache clean --force
rm -rf node_modules package-lock.json
npm install
```

### Camera not working
- Check browser permissions
- Use `http://localhost` or HTTPS
- Try "Upload Photo" instead

### Print agent won't start
```bash
cd print-agent
npm install
node server.js
```

Check if port 3000 is available.

### Build fails
```bash
# Check Node.js version
node --version  # Should be 18+

# Clean build
rm -rf .angular dist
npm run build
```

## Build for Production

```bash
npm run build
```

Output is in `dist/wedding-photo-booth/`

Deploy this folder to:
- Netlify (drag & drop)
- Vercel (`vercel` command)
- GitHub Pages
- Any static hosting

## Testing Checklist

Quick test before going live:

- [ ] Home page loads
- [ ] Can select layout
- [ ] Can select frame
- [ ] Can upload photo
- [ ] Photo appears on canvas
- [ ] Can add text
- [ ] Can add stickers
- [ ] Can drag/resize objects
- [ ] Can delete objects
- [ ] Export/download works
- [ ] Print preview looks correct
- [ ] Works on mobile (if available)

## Performance Tips

- Use JPEG for export (smaller files)
- Limit stickers to ~10 per design
- Use 150 DPI for editing, 300 for final
- Clear localStorage occasionally

## Event Day Checklist

### Equipment
- [ ] PC/laptop with browser
- [ ] Camera (or allow uploads)
- [ ] Printer connected and tested
- [ ] Enough paper and ink
- [ ] Backup device ready

### Software
- [ ] App running in browser
- [ ] Print agent started (if using)
- [ ] Test print completed
- [ ] Printer queue clear
- [ ] Browser cache cleared

### Setup
- [ ] Full screen / kiosk mode
- [ ] Disable screensaver
- [ ] Disable sleep mode
- [ ] Good lighting for camera
- [ ] Sign with instructions

## Getting Help

1. Check the main [README.md](README.md)
2. Look at [SETUP.md](SETUP.md) for details
3. Review [ARCHITECTURE.md](ARCHITECTURE.md) for technical info
4. Check browser console for errors

## Keyboard Shortcuts (Editor)

- `Delete` - Delete selected object
- `Ctrl+Z` - Undo (coming soon)
- `Ctrl+Y` - Redo (coming soon)
- `Escape` - Deselect object

## Mobile Tips

- Use large touch targets
- Test camera switching
- Verify text input works
- Test sticker placement
- Check export/share

## Demo Mode

For demonstrations without printer:

1. Start just the app (skip print agent)
2. Use "Upload Photo" instead of camera
3. Use "Download" instead of print
4. Show share functionality on mobile

---

**That's it! You're ready to create amazing photo booth memories! 📸✨**

For detailed documentation, see [README.md](README.md)

