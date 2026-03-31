import {
    Component, signal, computed, inject, Input, Output, EventEmitter,
    OnChanges, SimpleChanges, ElementRef, ViewChild, AfterViewInit,
} from '@angular/core';
import { DomSanitizer, SafeResourceUrl } from '@angular/platform-browser';
import { HttpClient } from '@angular/common/http';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatTooltipModule } from '@angular/material/tooltip';
import { QueryResult } from '../../core/api.service';

const TEXT_EXTENSIONS = new Set([
    '.txt', '.md', '.py', '.java', '.js', '.ts', '.c', '.cpp', '.h',
    '.cs', '.go', '.rs', '.rb', '.sh', '.yaml', '.yml', '.json', '.toml',
    '.xml', '.css',
]);
const IMAGE_EXTENSIONS = new Set(['.jpg', '.jpeg', '.png', '.gif', '.webp']);

export type ViewerMode = 'text' | 'pdf' | 'image' | 'docx' | 'epub' | 'unsupported';

@Component({
    selector: 'app-viewer',
    standalone: true,
    imports: [MatButtonModule, MatIconModule, MatProgressSpinnerModule, MatTooltipModule],
    templateUrl: './viewer.component.html',
    styleUrls: ['./viewer.component.scss'],
})
export class ViewerComponent implements OnChanges, AfterViewInit {
    @Input() result: QueryResult | null = null;
    @Input() visible = false;
    @Output() close = new EventEmitter<void>();

    @ViewChild('codeBlock') codeBlockRef?: ElementRef<HTMLElement>;
    @ViewChild('docxFrame') docxFrameRef?: ElementRef<HTMLIFrameElement>;
    @ViewChild('epubFrame') epubFrameRef?: ElementRef<HTMLIFrameElement>;

    private sanitizer = inject(DomSanitizer);
    private http = inject(HttpClient);

    mode = signal<ViewerMode>('unsupported');
    loading = signal(false);
    error = signal<string | null>(null);

    modeIcon = computed(() => {
        switch (this.mode()) {
            case 'text': return 'code';
            case 'pdf': return 'picture_as_pdf';
            case 'image': return 'image';
            case 'docx': return 'article';
            case 'epub': return 'menu_book';
            default: return 'draft';
        }
    });

    textContent = signal<string>('');
    highlightedLines = signal<{ start: number; end: number } | null>(null);

    pdfUrl = signal<SafeResourceUrl | null>(null);
    pdfJumpPage = signal<number>(1);

    imageUrl = signal<string | null>(null);

    frameHtml = signal<string>('');

    ngAfterViewInit(): void {
    }

    ngOnChanges(changes: SimpleChanges): void {
        if ((changes['result'] || changes['visible']) && this.visible && this.result) {
            this._load(this.result);
        }
    }

    private _load(r: QueryResult): void {
        this.loading.set(true);
        this.error.set(null);
        this.textContent.set('');
        this.pdfUrl.set(null);
        this.imageUrl.set(null);
        this.frameHtml.set('');

        const ext = r.extension.toLowerCase();
        const encodedPath = encodeURIComponent(r.relative_path);

        if (TEXT_EXTENSIONS.has(ext)) {
            this.mode.set('text');
            this.http.get(`/api/file/text?path=${encodedPath}`, { responseType: 'text' })
                .subscribe({
                    next: text => {
                        this.textContent.set(text);
                        this.loading.set(false);
                        if (r.line_start != null) {
                            this.highlightedLines.set({ start: r.line_start, end: r.line_end ?? r.line_start });
                            setTimeout(() => this._scrollToLine(r.line_start!));
                        }
                    },
                    error: e => { this.error.set(e.message); this.loading.set(false); },
                });

        } else if (ext === '.pdf') {
            this.mode.set('pdf');
            const fileUrl = `/api/file/raw?path=${encodedPath}`;
            const page = r.page_start ?? 1;
            this.pdfJumpPage.set(page);
            const viewerUrl =
                `https://mozilla.github.io/pdf.js/web/viewer.html` +
                `?file=${encodeURIComponent(window.location.origin + fileUrl)}` +
                `#page=${page}`;
            this.pdfUrl.set(this.sanitizer.bypassSecurityTrustResourceUrl(viewerUrl));
            this.loading.set(false);

        } else if (IMAGE_EXTENSIONS.has(ext)) {
            this.mode.set('image');
            this.imageUrl.set(`/api/file/raw?path=${encodedPath}`);
            this.loading.set(false);

        } else if (ext === '.docx') {
            this.mode.set('docx');
            this.http.get(`/api/file/docx?path=${encodedPath}`, { responseType: 'text' })
                .subscribe({
                    next: html => {
                        this.frameHtml.set(html);
                        this.loading.set(false);
                        if (r.paragraph_start != null) {
                            setTimeout(() => this._highlightDocxParagraphs(r.paragraph_start!, r.paragraph_end ?? r.paragraph_start!));
                        }
                    },
                    error: e => { this.error.set(e.message); this.loading.set(false); },
                });

        } else if (ext === '.epub') {
            this.mode.set('epub');
            const chapter = r.chapter ?? '';
            this.http.get(`/api/file/epub?path=${encodedPath}&chapter=${encodeURIComponent(chapter)}`, { responseType: 'text' })
                .subscribe({
                    next: html => {
                        this.frameHtml.set(html);
                        this.loading.set(false);
                    },
                    error: e => { this.error.set(e.message); this.loading.set(false); },
                });

        } else {
            this.mode.set('unsupported');
            this.loading.set(false);
        }
    }


    get lines(): { text: string; num: number; highlighted: boolean }[] {
        const hl = this.highlightedLines();
        return this.textContent().split('\n').map((text, i) => ({
            text,
            num: i + 1,
            highlighted: hl != null && (i + 1) >= hl.start && (i + 1) <= hl.end,
        }));
    }

    private _scrollToLine(lineNum: number): void {
        const el = this.codeBlockRef?.nativeElement;
        if (!el) return;
        const lineEl = el.querySelector<HTMLElement>(`[data-line="${lineNum}"]`);
        lineEl?.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }


    private _highlightDocxParagraphs(start: number, end: number): void {
        const iframe = this.docxFrameRef?.nativeElement;
        if (!iframe?.contentDocument) return;
        const doc = iframe.contentDocument;
        for (let i = start; i <= end; i++) {
            const el = doc.querySelector<HTMLElement>(`[data-para="${i}"]`);
            if (el) el.classList.add('highlight');
        }
        const first = doc.querySelector<HTMLElement>(`[data-para="${start}"]`);
        first?.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }

    get title(): string {
        return this.result?.relative_path ?? '';
    }

    get locationLabel(): string {
        const r = this.result;
        if (!r) return '';
        if (r.page_start != null)
            return r.page_end && r.page_end !== r.page_start ? `pp. ${r.page_start}–${r.page_end}` : `p. ${r.page_start}`;
        if (r.line_start != null)
            return r.line_end && r.line_end !== r.line_start ? `lines ${r.line_start}–${r.line_end}` : `line ${r.line_start}`;
        if (r.paragraph_start != null)
            return r.paragraph_end && r.paragraph_end !== r.paragraph_start ? `¶ ${r.paragraph_start}–${r.paragraph_end}` : `¶ ${r.paragraph_start}`;
        if (r.chapter) return r.chapter;
        return '';
    }
  }