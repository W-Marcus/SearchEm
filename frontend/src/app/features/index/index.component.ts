import { Component, signal, inject } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { ApiService, IndexResponse } from '../../core/api.service';

@Component({
  selector: 'app-index',
  standalone: true,
  imports: [MatButtonModule, MatCardModule, MatIconModule, MatProgressBarModule],
  templateUrl: './index.component.html',
})
export class IndexComponent {
  private api = inject(ApiService);

  loading = signal(false);
  result = signal<IndexResponse | null>(null);
  error = signal<string | null>(null);

  index(): void {
    this.run(this.api.index());
  }

  reindexFull(): void {
    this.run(this.api.reindexFull());
  }

  private run(obs: ReturnType<ApiService['index']>): void {
    this.loading.set(true);
    this.result.set(null);
    this.error.set(null);
    obs.subscribe({
      next: res => { this.result.set(res); this.loading.set(false); },
      error: err => { this.error.set(err.error?.detail ?? err.message); this.loading.set(false); },
    });
  }
}
