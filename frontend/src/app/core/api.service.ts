import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface QueryResult {
  rank: number;
  score: number;
  relative_path: string;
  extension: string;
  chunk_id: string;
  file_size: number;
  timestamp: number;
  content: string;
}

export interface SearchResponse {
  query: string;
  total: number;
  results: QueryResult[];
}

export interface IndexResponse {
  status: string;
  files_processed: number;
  files_unchanged: number;
  message: string;
}

export interface IndexRequest {
  force_reprocess?: boolean;
  extensions?: string[] | null;
}
export interface SettingsResponse {
  model: string;
  extensions: string[];
}

export interface SettingsRequest {
  model?: string;
  extensions?: string[];
}
const BASE = '/api';

@Injectable({ providedIn: 'root' })
export class ApiService {
  private http = inject(HttpClient);

  search(query: string, top_k = 5): Observable<SearchResponse> {
    return this.http.post<SearchResponse>(`${BASE}/search`, { query, top_k });
  }

  index(request: IndexRequest = {}): Observable<IndexResponse> {
    return this.http.post<IndexResponse>(`${BASE}/index`, request);
  }

  reindexFull(): Observable<IndexResponse> {
    return this.http.post<IndexResponse>(`${BASE}/index/full`, {});
  }
  getSettings(): Observable<SettingsResponse> {
    return this.http.get<SettingsResponse>(`${BASE}/settings`);
  }

  patchSettings(request: SettingsRequest): Observable<SettingsResponse> {
    return this.http.patch<SettingsResponse>(`${BASE}/settings`, request);
  }
}
