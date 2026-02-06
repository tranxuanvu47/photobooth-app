# Contributing to Wedding Photo Booth

Thank you for your interest in contributing! This document provides guidelines for contributing to the project.

## Code of Conduct

- Be respectful and inclusive
- Welcome newcomers
- Focus on constructive feedback
- Help maintain a positive environment

## How to Contribute

### Reporting Bugs

Before creating a bug report:
1. Check existing issues to avoid duplicates
2. Test with the latest version
3. Verify it's reproducible

When reporting:
- Use a clear, descriptive title
- Describe steps to reproduce
- Include expected vs actual behavior
- Add screenshots if applicable
- Specify browser/device/OS details
- Include console error messages

### Suggesting Enhancements

Enhancement suggestions are welcome! Include:
- Clear description of the feature
- Use cases and benefits
- Mockups or examples if applicable
- Consider implementation complexity

### Pull Requests

1. **Fork and clone** the repository
2. **Create a branch** from `main`:
   ```bash
   git checkout -b feature/my-new-feature
   ```
3. **Make your changes** following code style guidelines
4. **Test thoroughly** on multiple devices/browsers
5. **Commit with clear messages**:
   ```bash
   git commit -m "Add feature: description of feature"
   ```
6. **Push to your fork**:
   ```bash
   git push origin feature/my-new-feature
   ```
7. **Open a Pull Request** with:
   - Clear title and description
   - Reference any related issues
   - Screenshots/videos of UI changes
   - List of testing done

## Development Guidelines

### Code Style

Follow the existing code style:

- **TypeScript**: Strict mode, explicit types
- **Naming**: 
  - Components: `PascalCase` (e.g., `CameraCapture`)
  - Files: `kebab-case` (e.g., `camera-capture.component.ts`)
  - Variables: `camelCase` (e.g., `isActive`)
  - Constants: `UPPER_SNAKE_CASE` (e.g., `MAX_FILE_SIZE`)
- **Formatting**: 2 spaces, single quotes
- **Comments**: Explain "why", not "what"

### Angular Best Practices

- Use standalone components
- Leverage Angular signals for state
- Implement `OnDestroy` for cleanup
- Use `inject()` function for DI
- Keep components focused and small
- Use reactive patterns with RxJS

### Component Structure

```typescript
import { Component, signal, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
// Other imports...

@Component({
  selector: 'app-my-component',
  standalone: true,
  imports: [CommonModule, ...],
  templateUrl: './my-component.component.html',
  styleUrls: ['./my-component.component.scss']
})
export class MyComponent {
  // Inject services
  private readonly myService = inject(MyService);
  
  // Signals
  readonly mySignal = signal<string>('');
  
  // Methods
  myMethod(): void {
    // Implementation
  }
}
```

### Testing

Add tests for:
- New features
- Bug fixes
- Complex logic
- Service methods

Run tests:
```bash
npm test
```

### Commit Messages

Format: `<type>: <subject>`

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes
- `refactor`: Code refactoring
- `test`: Test changes
- `chore`: Build/tooling changes

Examples:
```
feat: add watermark overlay option
fix: camera permission error on iOS Safari
docs: update print setup instructions
style: format code with prettier
refactor: extract layout logic to service
test: add countdown timer tests
chore: update Angular to v18.1
```

### Branch Naming

- `feature/description` - New features
- `fix/description` - Bug fixes
- `docs/description` - Documentation
- `refactor/description` - Code refactoring

## Project Areas for Contribution

### Easy Tasks (Good First Issues)
- Add new sticker designs
- Add new frame themes
- Improve error messages
- Add translations/i18n
- Documentation improvements
- Fix typos

### Medium Tasks
- Add new layout presets
- Enhance camera controls
- Improve mobile responsiveness
- Add new export formats
- Performance optimizations

### Advanced Tasks
- Implement advanced filters
- Add animation effects
- Improve print agent (better printer APIs)
- Add cloud storage integration
- Implement collaborative editing

## Testing Checklist

Before submitting, test:

- [ ] Desktop Chrome/Edge
- [ ] Desktop Firefox
- [ ] Desktop Safari (if Mac available)
- [ ] Mobile Chrome
- [ ] Mobile Safari (if iOS available)
- [ ] Camera capture works
- [ ] File upload works
- [ ] Text editing works
- [ ] Stickers work
- [ ] Export produces correct size
- [ ] Print preview looks correct
- [ ] All buttons/controls work
- [ ] No console errors
- [ ] Responsive on different screen sizes

## Documentation

Update documentation when:
- Adding new features
- Changing existing behavior
- Adding configuration options
- Modifying APIs

Update these files as needed:
- `README.md` - Main documentation
- `SETUP.md` - Setup instructions
- `print-agent/README.md` - Print agent docs
- Code comments
- TypeScript interfaces

## Questions?

- Open a discussion on GitHub
- Check existing issues and PRs
- Review the code for examples

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

Thank you for contributing! 🎉

