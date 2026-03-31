import { Component, signal, inject, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatChipsModule, MatChipInputEvent } from '@angular/material/chips';
import { MatIconModule } from '@angular/material/icon';
import { COMMA, ENTER } from '@angular/cdk/keycodes';
import { ApiService } from '../../core/api.service';
import { IndexStateService } from '../../core/index-state.service';

@Component({
  selector: 'app-settings',
  standalone: true,
  imports: [
    FormsModule,
    MatFormFieldModule, MatInputModule, MatButtonModule,
    MatCardModule, MatChipsModule, MatIconModule,
  ],
  templateUrl: './settings.component.html',
})
export class SettingsComponent implements OnInit {
  private api = inject(ApiService);
  private indexState = inject(IndexStateService);

  model = signal('Qwen/Qwen3-VL-Embedding-2B');
  extensions = signal<string[]>([]);
  saved = signal(false);
  readonly separatorKeys = [ENTER, COMMA];

  ngOnInit(): void {
    this.api.getSettings().subscribe({
      next: s => {
        this.model.set(s.model);
        this.extensions.set(s.extensions);
      },
      error: () => {
        // fall back to localStorage if server unreachable
        const stored = localStorage.getItem('searchem-settings');
        if (stored) {
          const s = JSON.parse(stored);
          this.model.set(s.model ?? this.model());
          this.extensions.set(s.extensions ?? []);
        }
      }
    });
  }

  addExtension(event: MatChipInputEvent): void {
    const value = (event.value || '').trim();
    if (value) {
      const ext = value.startsWith('.') ? value : `.${value}`;
      // Deduplicate: only add if not already present
      if (!this.extensions().includes(ext)) {
        this.extensions.update(exts => [...exts, ext]);
      }
    }
    event.chipInput.clear();
  }

  removeExtension(ext: string): void {
    this.extensions.update(exts => exts.filter(e => e !== ext));
  }

  save(): void {
    this.api.patchSettings({
      model: this.model(),
      extensions: this.extensions(),
    }).subscribe({
      next: s => {
        // Update local state with what the server confirmed
        this.model.set(s.model);
        this.extensions.set(s.extensions);
        this.saved.set(true);
        setTimeout(() => this.saved.set(false), 2000);
      }
    });
  }

  applyAndReindex(): void {
    this.api.patchSettings({
      model: this.model(),
      extensions: this.extensions(),
    }).subscribe({
      next: s => {
        // Update local state with what the server confirmed
        this.model.set(s.model);
        this.extensions.set(s.extensions);
        // Use the SSE-based IndexStateService for the full reindex (GET /api/index/full)
        this.indexState.start('/api/index/full');
      }
    });
  }
}