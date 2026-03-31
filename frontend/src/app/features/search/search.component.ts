import { Component, signal, inject, HostListener } from '@angular/core';
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
import { ViewerComponent } from '../viewer/viewer.component';

@Component({
  selector: 'app-search',
  standalone: true,
  imports: [
    FormsModule, DatePipe, DecimalPipe, SlicePipe,
    MatFormFieldModule, MatInputModule, MatButtonModule,
    MatIconModule, MatCardModule, MatProgressSpinnerModule, MatChipsModule,
    ViewerComponent,
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

  viewerResult = signal<QueryResult | null>(null);
  viewerVisible = signal(false);

  @HostListener('document:keydown.escape')
  onEscape(): void { this.closeViewer(); }

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

  openViewer(result: QueryResult): void {
    this.viewerResult.set(result);
    this.viewerVisible.set(true);
  }

  closeViewer(): void {
    this.viewerVisible.set(false);
  }

  locationLabel(result: QueryResult): string | null {
    if (result.page_start != null) {
      return result.page_end != null && result.page_end !== result.page_start
        ? `pp. ${result.page_start}–${result.page_end}`
        : `p. ${result.page_start}`;
    }
    if (result.line_start != null) {
      return result.line_end != null && result.line_end !== result.line_start
        ? `lines ${result.line_start}–${result.line_end}`
        : `line ${result.line_start}`;
    }
    if (result.paragraph_start != null) {
      return result.paragraph_end != null && result.paragraph_end !== result.paragraph_start
        ? `¶ ${result.paragraph_start}–${result.paragraph_end}`
        : `¶ ${result.paragraph_start}`;
    }
    if (result.chapter != null) return result.chapter;
    return null;
  }

  locationIcon(result: QueryResult): string {
    if (result.page_start != null) return 'menu_book';
    if (result.line_start != null) return 'code';
    if (result.paragraph_start != null) return 'article';
    if (result.chapter != null) return 'bookmark';
    return 'place';
  }
}