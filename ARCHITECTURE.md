# Architecture Overview - Wedding Photo Booth

This document provides a technical overview of the Wedding Photo Booth application architecture.

## Technology Stack

### Frontend
- **Angular 18** - Standalone components architecture
- **TypeScript 5.4** - Strict mode enabled
- **RxJS 7.8** - Reactive programming
- **Fabric.js 6.0** - Canvas manipulation
- **SCSS** - Styling with CSS variables

### Backend (Optional Print Agent)
- **Node.js 18+** - JavaScript runtime
- **Express 4.18** - Web server
- **Multer** - File upload handling

### Build & Tools
- **Angular CLI** - Build tooling
- **Service Worker** - PWA offline support
- **TypeScript Compiler** - Type checking

## Application Structure

```
┌─────────────────────────────────────────┐
│           Browser (PWA)                 │
├─────────────────────────────────────────┤
│  Angular Application                    │
│  ┌───────────────────────────────────┐  │
│  │  Router (Lazy Loading)            │  │
│  │  ├─ Home                          │  │
│  │  ├─ Editor (Main)                 │  │
│  │  └─ Print                         │  │
│  └───────────────────────────────────┘  │
│  ┌───────────────────────────────────┐  │
│  │  Shared Components                │  │
│  │  ├─ LayoutPicker                  │  │
│  │  ├─ FrameGallery                  │  │
│  │  ├─ CameraCapture                 │  │
│  │  └─ CanvasEditor (Fabric.js)      │  │
│  └───────────────────────────────────┘  │
│  ┌───────────────────────────────────┐  │
│  │  Services (Signals + RxJS)        │  │
│  │  ├─ CameraService                 │  │
│  │  ├─ CountdownService              │  │
│  │  ├─ EditorStateService            │  │
│  │  ├─ ExportService                 │  │
│  │  └─ PrintService                  │  │
│  └───────────────────────────────────┘  │
└─────────────────────────────────────────┘
              ↕ HTTP (Optional)
┌─────────────────────────────────────────┐
│     Print Agent (Node.js)               │
│     Running on PC (localhost:3000)      │
│  ┌───────────────────────────────────┐  │
│  │  Express Server                   │  │
│  │  ├─ /status - Check availability  │  │
│  │  ├─ /print - Print job endpoint   │  │
│  │  └─ /health - Health check        │  │
│  └───────────────────────────────────┘  │
│              ↕                          │
│     System Printer APIs                 │
└─────────────────────────────────────────┘
```

## Core Design Patterns

### 1. Standalone Components
All components use Angular's standalone architecture:
- No NgModules required
- Explicit imports in each component
- Better tree-shaking and lazy loading
- Simplified dependency management

### 2. Signals for State Management
Leveraging Angular Signals for reactive state:
- Computed values
- Automatic change detection
- Simple API
- Better performance than observables for simple state

```typescript
readonly isActive = signal<boolean>(false);
readonly count = signal<number>(0);
readonly doubled = computed(() => this.count() * 2);
```

### 3. Dependency Injection with inject()
Modern DI pattern:
```typescript
private readonly myService = inject(MyService);
```

### 4. Service-Based Architecture
Business logic centralized in services:
- `CameraService` - Camera access and capture
- `CountdownService` - Timer functionality
- `EditorStateService` - Canvas state management
- `ExportService` - Image export and conversion
- `PrintService` - Print coordination

### 5. Component Composition
Small, focused components composed together:
- Each component has single responsibility
- Easy to test and maintain
- Reusable across features

## Data Flow

### 1. User Creates Design

```
User → LayoutPicker → EditorState.setLayout()
     → FrameGallery → EditorState.setFrame()
     → CameraCapture → CanvasEditor.addImage()
     → CanvasEditor → Fabric.js Canvas
```

### 2. Export & Print Flow

```
CanvasEditor → EditorState
            → ExportService.exportAsImage()
            → Canvas → Blob → Data URL
            → PrintComponent
            → PrintService.printWithBrowser() or
            → PrintService.printWithAgent() → Print Agent → Printer
```

## Key Technical Decisions

### Why Fabric.js?
- Powerful canvas manipulation
- Object-oriented API
- Built-in transformations (drag, rotate, scale)
- Layer management
- Good TypeScript support
- Active community

### Why Signals over NgRx?
- Simpler API for this use case
- Less boilerplate
- Sufficient for app's complexity
- Better performance for local state
- Easier to learn and maintain

### Why Standalone Components?
- Modern Angular best practice
- Better code splitting
- Clearer dependencies
- Easier lazy loading
- Future-proof architecture

### Why Optional Print Agent?
- Browser printing works for most users
- Agent provides better kiosk experience
- Keeps main app simple
- Easy to deploy without agent
- Agent runs locally (security)

## Performance Considerations

### 1. Lazy Loading
Features loaded on-demand:
```typescript
{
  path: 'editor',
  loadComponent: () => import('./features/editor/...')
}
```

### 2. Service Worker Caching
- App shell cached for offline use
- Assets prefetched
- Updates in background

### 3. Image Optimization
- Canvas rendering optimized
- Export only when needed
- DPI scaling for performance
- Compression for file size

### 4. Change Detection
- OnPush strategy where applicable
- Signals for granular updates
- Minimal re-renders

## Security Model

### Client-Side Only Processing
- All image processing in browser
- No images uploaded to servers
- User privacy maintained
- Works offline

### Print Agent Security
- Runs only on localhost
- Should not be exposed to internet
- CORS configured for local dev only
- No authentication (local trust model)

### Content Security
- Angular's built-in XSS protection
- Sanitized dynamic content
- No eval() or dangerous patterns

## State Management

### Application State
```typescript
interface EditorState {
  id: string;                    // Session ID
  layout: LayoutConfig;          // Selected layout
  frame: Frame | null;           // Selected frame
  canvasObjects: CanvasObject[]; // Canvas elements
  history: HistoryState[];       // Undo/redo
  historyIndex: number;
  exportSettings: ExportSettings;
}
```

### State Persistence
- LocalStorage for drafts
- SessionStorage for temp data
- No database required

### Undo/Redo
- History stack (max 50 items)
- Snapshot-based (full state)
- Efficient for small states

## Testing Strategy

### Unit Tests
- Service logic
- Pure functions
- Component methods
- Calculations (DPI, sizing)

### Integration Tests
- Component interactions
- Service coordination
- Data flow

### Manual Testing
- Browser compatibility
- Device testing
- Print quality
- Camera functionality

## Deployment Considerations

### Static Hosting
App is fully static:
- No backend required
- Deploy to any CDN
- Works with GitHub Pages, Netlify, Vercel
- Fast loading with CDN edge caching

### PWA Benefits
- Install on devices
- Offline functionality
- App-like experience
- Home screen icon

### Print Agent Deployment
- Runs on event PC
- Started before event
- Configured for local printer
- Can restart if crashes

## Browser API Usage

### getUserMedia
- Camera access
- Permission handling
- Device enumeration
- Stream management

### Canvas API
- Image manipulation
- Drawing and compositing
- Export to image

### Web Share API
- Native sharing (mobile)
- Fallback to download

### Print API
- window.print()
- @media print CSS
- Print preview

## Scalability

### Current Limitations
- Client-side processing only
- Limited by device capabilities
- Single user per session

### Future Enhancements
- Cloud storage integration
- Multi-user collaboration
- Advanced filters
- Video capture
- QR code pairing
- Analytics

## Code Organization

### File Naming Conventions
- Components: `*.component.ts`
- Services: `*.service.ts`
- Models: `*.model.ts`
- All files: `kebab-case`

### Import Order
1. Angular core
2. Angular common
3. RxJS
4. Third-party
5. Application imports
6. Relative imports

### Folder Structure
```
features/       - Feature modules
shared/
  components/   - Reusable components
  models/       - TypeScript interfaces
  services/     - Business logic
assets/         - Static files
  stickers/     - SVG/PNG stickers
  frames/       - Frame overlays
```

## Performance Metrics

### Target Metrics
- **LCP**: < 2.5s (Largest Contentful Paint)
- **FID**: < 100ms (First Input Delay)
- **CLS**: < 0.1 (Cumulative Layout Shift)
- **Bundle Size**: < 2MB initial

### Optimization Techniques
- Tree shaking
- Code splitting
- Lazy loading
- Service worker caching
- Image optimization
- Minimal dependencies

## Monitoring & Debugging

### Development Tools
- Angular DevTools extension
- Browser DevTools
- Source maps enabled
- Console logging (dev mode)

### Production Monitoring
- Service worker updates
- Error tracking (add Sentry/similar)
- Performance metrics
- User analytics (optional)

## Accessibility

### ARIA Labels
- Semantic HTML
- Screen reader support
- Keyboard navigation
- Focus management

### Touch Targets
- Minimum 44px (iOS guidelines)
- Adequate spacing
- Visual feedback

## Browser Compatibility Matrix

| Feature | Chrome | Edge | Firefox | Safari | iOS Safari |
|---------|--------|------|---------|--------|------------|
| Basic UI | ✅ | ✅ | ✅ | ✅ | ✅ |
| Camera | ✅ | ✅ | ✅ | ✅ | ⚠️ |
| Canvas | ✅ | ✅ | ✅ | ✅ | ✅ |
| Print | ✅ | ✅ | ✅ | ✅ | ⚠️ |
| PWA | ✅ | ✅ | ⚠️ | ✅ | ✅ |
| Share API | ✅ | ✅ | ❌ | ✅ | ✅ |

✅ Full support | ⚠️ Partial/limitations | ❌ Not supported

---

**This architecture provides a solid foundation for a production-ready photo booth application while remaining maintainable and extensible.**

