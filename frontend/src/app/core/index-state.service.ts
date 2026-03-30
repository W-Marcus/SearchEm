import { Injectable, signal } from '@angular/core';

export interface ProgressEntry {
    type: string;
    message: string;
    file?: string;
    file_index?: number;
    file_total?: number;
    chunk_index?: number;
    chunk_total?: number;
}

@Injectable({ providedIn: 'root' })
export class IndexStateService {
    running = signal(false);
    progress = signal<ProgressEntry[]>([]);
    fileIndex = signal(0);
    fileTotal = signal(0);
    chunkIndex = signal(0);
    chunkTotal = signal(0);
    lastStatus = signal<'idle' | 'done' | 'cancelled' | 'error'>('idle');

    private eventSource: EventSource | null = null;
    start(url: string): void {
        if (this.running()) return;
        this.running.set(true);
        this.progress.set([]);
        this.lastStatus.set('idle');

        this.eventSource = new EventSource(url); 

        this.eventSource.onmessage = (event) => {
            const data: ProgressEntry = JSON.parse(event.data);
            this.progress.update(p => [...p, data]);

            if (data.file_total != null) this.fileTotal.set(data.file_total);
            if (data.file_index != null) this.fileIndex.set(data.file_index);
            if (data.chunk_total != null) this.chunkTotal.set(data.chunk_total);
            if (data.chunk_index != null) this.chunkIndex.set(data.chunk_index);

            if (data.type === 'done' || data.type === 'cancelled' || data.type === 'error') {
                this.lastStatus.set(data.type as any);
                this.running.set(false);
                this.eventSource?.close();
                this.eventSource = null;
            }
        };

        this.eventSource.onerror = () => {
            this.progress.update(p => [...p, { type: 'error', message: 'Connection lost.' }]);
            this.lastStatus.set('error');
            this.running.set(false);
            this.eventSource?.close();
            this.eventSource = null;
        };
    }

    cancel(): void {
        fetch('/api/index', { method: 'DELETE' });
    }

    clear(): void {
        if (!this.running()) {
            this.progress.set([]);
            this.lastStatus.set('idle');
            this.fileIndex.set(0);
            this.fileTotal.set(0);
        }
    }
}