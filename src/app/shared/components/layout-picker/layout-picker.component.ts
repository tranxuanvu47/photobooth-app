import { Component, output, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { LayoutConfig, PRESETS, PresetType } from '../../models/layout.model';

@Component({
  selector: 'app-layout-picker',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './layout-picker.component.html',
  styleUrls: ['./layout-picker.component.scss']
})
export class LayoutPickerComponent {
  layoutSelected = output<LayoutConfig>();
  
  readonly presets = Object.entries(PRESETS).map(([key, preset]) => ({
    key: key as PresetType,
    ...preset
  }));

  readonly selectedPreset = signal<PresetType>('4x6-portrait');

  selectLayout(presetKey: PresetType): void {
    this.selectedPreset.set(presetKey);
    const preset = PRESETS[presetKey];
    const layout: LayoutConfig = {
      ...preset,
      id: this.generateId()
    };
    this.layoutSelected.emit(layout);
  }

  private generateId(): string {
    return `layout-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
  }
}

