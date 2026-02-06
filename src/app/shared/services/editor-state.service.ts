import { Injectable, signal } from '@angular/core';
import { EditorState, CanvasObject, HistoryState } from '../models/editor.model';
import { LayoutConfig, PRESETS } from '../models/layout.model';
import { Frame } from '../models/frame.model';

const MAX_HISTORY = 50;

@Injectable({
  providedIn: 'root'
})
export class EditorStateService {
  private readonly state = signal<EditorState>(this.createInitialState());

  readonly state$ = this.state.asReadonly();

  private createInitialState(): EditorState {
    return {
      id: this.generateId(),
      layout: this.createLayoutFromPreset('4x6-portrait'),
      frame: null,
      canvasObjects: [],
      history: [],
      historyIndex: -1,
      exportSettings: {
        format: 'jpeg',
        quality: 1,
        dpi: 300,
        includeBleed: false,
        showGuides: false
      }
    };
  }

  private createLayoutFromPreset(presetType: '4x6-portrait' | '4x6-landscape' | '2x6-strip'): LayoutConfig {
    const preset = PRESETS[presetType];
    return {
      ...preset,
      id: this.generateId()
    };
  }

  setLayout(layoutConfig: LayoutConfig): void {
    this.state.update(state => ({
      ...state,
      layout: layoutConfig
    }));
    this.saveHistory();
  }

  setFrame(frame: Frame | null): void {
    this.state.update(state => ({
      ...state,
      frame
    }));
    this.saveHistory();
  }

  addObject(obj: CanvasObject): void {
    this.state.update(state => ({
      ...state,
      canvasObjects: [...state.canvasObjects, obj]
    }));
    this.saveHistory();
  }

  updateObject(id: string, updates: Partial<CanvasObject>): void {
    this.state.update(state => ({
      ...state,
      canvasObjects: state.canvasObjects.map(obj =>
        obj.id === id ? { ...obj, ...updates } : obj
      )
    }));
    this.saveHistory();
  }

  removeObject(id: string): void {
    this.state.update(state => ({
      ...state,
      canvasObjects: state.canvasObjects.filter(obj => obj.id !== id)
    }));
    this.saveHistory();
  }

  bringToFront(id: string): void {
    this.state.update(state => {
      const objects = [...state.canvasObjects];
      const maxZIndex = Math.max(...objects.map(o => o.zIndex), 0);
      return {
        ...state,
        canvasObjects: objects.map(obj =>
          obj.id === id ? { ...obj, zIndex: maxZIndex + 1 } : obj
        )
      };
    });
    this.saveHistory();
  }

  sendToBack(id: string): void {
    this.state.update(state => {
      const objects = [...state.canvasObjects];
      const minZIndex = Math.min(...objects.map(o => o.zIndex), 0);
      return {
        ...state,
        canvasObjects: objects.map(obj =>
          obj.id === id ? { ...obj, zIndex: minZIndex - 1 } : obj
        )
      };
    });
    this.saveHistory();
  }

  undo(): void {
    const currentState = this.state();
    if (currentState.historyIndex > 0) {
      const newIndex = currentState.historyIndex - 1;
      const historyState = currentState.history[newIndex];
      
      this.state.update(state => ({
        ...state,
        canvasObjects: historyState.objects,
        historyIndex: newIndex
      }));
    }
  }

  redo(): void {
    const currentState = this.state();
    if (currentState.historyIndex < currentState.history.length - 1) {
      const newIndex = currentState.historyIndex + 1;
      const historyState = currentState.history[newIndex];
      
      this.state.update(state => ({
        ...state,
        canvasObjects: historyState.objects,
        historyIndex: newIndex
      }));
    }
  }

  canUndo(): boolean {
    return this.state().historyIndex > 0;
  }

  canRedo(): boolean {
    const currentState = this.state();
    return currentState.historyIndex < currentState.history.length - 1;
  }

  private saveHistory(): void {
    this.state.update(state => {
      const newHistory: HistoryState = {
        timestamp: Date.now(),
        objects: JSON.parse(JSON.stringify(state.canvasObjects))
      };

      // Remove any redo history when making a new change
      const history = state.history.slice(0, state.historyIndex + 1);
      history.push(newHistory);

      // Keep history within max limit
      const trimmedHistory = history.slice(-MAX_HISTORY);

      return {
        ...state,
        history: trimmedHistory,
        historyIndex: trimmedHistory.length - 1
      };
    });
  }

  saveToLocalStorage(): void {
    const currentState = this.state();
    localStorage.setItem(`photobooth-draft-${currentState.id}`, JSON.stringify(currentState));
  }

  loadFromLocalStorage(id: string): boolean {
    const saved = localStorage.getItem(`photobooth-draft-${id}`);
    if (saved) {
      try {
        const state = JSON.parse(saved) as EditorState;
        this.state.set(state);
        return true;
      } catch (err) {
        console.error('Failed to load draft:', err);
        return false;
      }
    }
    return false;
  }

  reset(): void {
    this.state.set(this.createInitialState());
  }

  private generateId(): string {
    return `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
  }
}

