import { Component, inject } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { IndexStateService } from '../../core/index-state.service';

@Component({
  selector: 'app-index',
  standalone: true,
  imports: [MatButtonModule, MatCardModule, MatIconModule, MatProgressBarModule],
  templateUrl: './index.component.html',
})
export class IndexComponent {
  state = inject(IndexStateService);

  index(): void {
    this.state.start('/api/index');
  }

  reindexFull(): void {
    this.state.start('/api/index/full');
  }

  cancel(): void {
    this.state.cancel();
  }

  clear(): void {
    this.state.clear();
  }
}