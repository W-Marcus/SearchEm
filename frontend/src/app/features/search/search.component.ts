import { Component, signal, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { DatePipe, DecimalPipe, SlicePipe } from '@angular/common';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatCardModule } from '@angular/material/card';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatChipsModule } from '@angular/material/chips';
import { ApiService, QueryResult } from '../../core/api.service';

@Component({
  selector: 'app-search',
  standalone: true,
  imports: [
    FormsModule, DatePipe, DecimalPipe, SlicePipe,
    MatFormFieldModule, MatInputModule, MatButtonModule,
    MatIconModule, MatCardModule, MatProgressSpinnerModule, MatChipsModule,
  ],
  templateUrl: './search.component.html',
})
export class SearchComponent {
  private api = inject(ApiService);

  query = '';
  topK = 5;
  results = signal<QueryResult[]>([]);
  loading = signal(false);
  error = signal<string | null>(null);
  searched = signal(false);

  search(): void {
    if (!this.query.trim()) return;
    this.loading.set(true);
    this.error.set(null);
    this.api.search(this.query, this.topK).subscribe({
      next: res => {
        this.results.set(res.results);
        this.searched.set(true);
        this.loading.set(false);
      },
      error: err => {
        this.error.set(err.message);
        this.loading.set(false);
      },
    });
  }
}
