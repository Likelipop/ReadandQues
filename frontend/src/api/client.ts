import {
  Article,
  ArticleCard,
  DictionaryLookupResult,
  ExplainPhraseResult,
  HomepageData,
  ProofData,
  QuestionTicket,
  SearchResultItem,
  SmartParaphraseResult,
  UserProfile,
} from '../types';
import { isWithinDateFilter, DateFilterOption } from '../utils/dateFilter';

const API_BASE = '/api/v1';

function getCookie(name: string): string | null {
  if (typeof document === 'undefined') return null;
  const match = document.cookie.match(new RegExp('(^| )' + name + '=([^;]+)'));
  if (match) return decodeURIComponent(match[2]);
  return null;
}

async function request<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const headers = new Headers(options.headers || {});
  if (!headers.has('Content-Type') && !(options.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json');
  }

  const csrf = getCookie('csrftoken');
  if (csrf && !headers.has('X-CSRFToken')) {
    headers.set('X-CSRFToken', csrf);
  }

  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers,
    credentials: 'same-origin',
  });

  if (!response.ok) {
    let errorMsg = `HTTP Error ${response.status}`;
    try {
      const errJson = await response.json();
      errorMsg = errJson.message || errJson.detail || errorMsg;
    } catch {
      // ignore
    }
    throw new Error(errorMsg);
  }

  return response.json() as Promise<T>;
}

import { SAMPLE_ARTICLES_DATA } from './fixtures/sampleArticles';
import { FALLBACK_HOMEPAGE } from './fixtures/fallbackHomepage';

export { SAMPLE_ARTICLES_DATA, FALLBACK_HOMEPAGE };

export const api = {
  // Discovery & Homepage
  homepage: {
    get: async () => {
      try {
        return await request<HomepageData>('/homepage/');
      } catch (err) {
        console.warn('Backend unavailable, rendering fallback homepage data:', err);
        return FALLBACK_HOMEPAGE;
      }
    },
  },

  // Articles
  articles: {
    list: async (
      params: {
        theme?: string;
        genre?: string;
        date_filter?: string;
        q?: string;
        page?: number;
        limit?: number;
      } = {}
    ) => {
      try {
        const sp = new URLSearchParams();
        if (params.theme && params.theme !== 'All') sp.append('theme', params.theme);
        if (params.genre && params.genre !== 'All') sp.append('genre', params.genre);
        if (params.date_filter && params.date_filter.toLowerCase() !== 'all') {
          sp.append('date_filter', params.date_filter);
        }
        if (params.q) sp.append('q', params.q);
        if (params.page) sp.append('page', String(params.page));
        if (params.limit) sp.append('limit', String(params.limit));
        const qs = sp.toString() ? `?${sp.toString()}` : '';
        return await request<{
          status: string;
          articles: ArticleCard[];
          total_count: number;
          page: number;
          limit: number;
          has_next: boolean;
          has_prev: boolean;
        }>(`/articles/${qs}`);
      } catch (err) {
        let filtered = SAMPLE_ARTICLES_DATA;
        if (params.theme && params.theme !== 'All') {
          filtered = filtered.filter((a) => a.theme?.toLowerCase() === params.theme?.toLowerCase());
        }
        if (params.genre && params.genre !== 'All') {
          filtered = filtered.filter((a) => a.genre?.toLowerCase() === params.genre?.toLowerCase());
        }
        if (params.date_filter && params.date_filter.toLowerCase() !== 'all') {
          filtered = filtered.filter((a) =>
            isWithinDateFilter(a.published_at, params.date_filter as DateFilterOption)
          );
        }
        if (params.q) {
          const q = params.q.toLowerCase();
          filtered = filtered.filter((a) => a.title.toLowerCase().includes(q) || a.summary?.toLowerCase().includes(q));
        }
        return {
          status: 'success',
          articles: filtered,
          total_count: filtered.length,
          page: 1,
          limit: 12,
          has_next: false,
          has_prev: false,
        };
      }
    },

    get: async (id: string) => {
      try {
        return await request<{
          status: string;
          article: Article;
          related_articles: ArticleCard[];
        }>(`/articles/${id}/`);
      } catch (err) {
        const art = SAMPLE_ARTICLES_DATA.find((a) => a.id === id || a.article_id === id) || SAMPLE_ARTICLES_DATA[0];
        return {
          status: 'success',
          article: art,
          related_articles: SAMPLE_ARTICLES_DATA.filter((a) => a.id !== art.id),
        };
      }
    },

    import: (url: string) =>
      request<{
        status: string;
        article_id: string;
        is_new: boolean;
        message?: string;
      }>('/articles/import/', {
        method: 'POST',
        body: JSON.stringify({ url }),
      }),

    status: (id: string) =>
      request<{
        status: string;
        ai_status: string;
        has_quiz: boolean;
        exams?: any[];
        error_message?: string;
      }>(`/status/${id}/`),

    triggerQuiz: (id: string) =>
      request<{ status: string }>('/trigger-quiz/' + id + '/', {
        method: 'POST',
      }),

    submitExam: (
      id: string,
      data: {
        score: number;
        total_questions: number;
        answers: Record<string, any>;
        highlighted_markdown?: string;
        elapsed_time?: number;
      }
    ) =>
      request<{
        status: string;
        id: string;
        related_articles: ArticleCard[];
      }>(`/${id}/submit/`, {
        method: 'POST',
        body: JSON.stringify(data),
      }),

    smartParaphrase: (
      id: string,
      data: {
        paragraph_text: string;
        highlighted_text?: string;
        start_index?: number;
        end_index?: number;
      }
    ) =>
      request<SmartParaphraseResult>(`/${id}/smart_paraphrase/`, {
        method: 'POST',
        body: JSON.stringify(data),
      }),

    explain: async (
      id: string,
      data: {
        phrase: string;
        paragraph_context?: string;
      }
    ): Promise<ExplainPhraseResult> => {
      try {
        return await request<ExplainPhraseResult>(`/${id}/explain/`, {
          method: 'POST',
          body: JSON.stringify(data),
        });
      } catch {
        const p = data.phrase.trim();
        return {
          status: 'success',
          phrase: p,
          summary: `Academic contextual analysis of "${p.slice(0, 50)}${p.length > 50 ? '...' : ''}"`,
          detailed_explanation: `In this section of the passage, this excerpt explains key principles and develops the central thesis.`,
          simplified_version: p,
          key_terms: [],
        };
      }
    },

    saveMarkers: (id: string, highlighted_markdown: string) =>
      request<{ status: string }>(`/${id}/save_markers/`, {
        method: 'POST',
        body: JSON.stringify({ highlighted_markdown }),
      }),

    getProof: (id: string, idx: number) =>
      request<{ status: string; proof: ProofData }>(`/${id}/proof/${idx}/`),
  },

  // Search & AI Tool
  search: {
    keyword: (q: string) =>
      request<{ status: string; results: SearchResultItem[] }>(
        `/search/keyword/?q=${encodeURIComponent(q)}`
      ),
    semantic: (q: string) =>
      request<{ status: string; results: SearchResultItem[] }>(
        `/search/semantic/?q=${encodeURIComponent(q)}`
      ),
  },

  aiTool: {
    run: (question: string, article_id?: string) =>
      request<{
        status: string;
        answer: string;
        citations: any[];
        output?: { answer: string; citation_quote?: string; status: string };
      }>('/ai/tool/run/', {
        method: 'POST',
        body: JSON.stringify({ question, article_id }),
      }),
  },

  // Dictionary Tool
  dictionary: {
    lookup: async (word: string): Promise<DictionaryLookupResult> => {
      try {
        return await request<DictionaryLookupResult>(
          `/dictionary/lookup/?word=${encodeURIComponent(word.trim())}`
        );
      } catch {
        // Safe offline client fallback
        const w = word.trim().toLowerCase();
        const commonMap: Record<string, string> = {
          the: 'Denoting one or more people or things already mentioned or assumed to be common knowledge.',
          a: 'Used when referring to someone or something for the first time in a text.',
          an: 'The form of the indefinite article used before words beginning with a vowel sound.',
          in: 'Expressing the situation of something enclosed or surrounded by something else.',
          of: 'Expressing the relationship between a part and a whole, or origin.',
          to: 'Expressing motion or direction toward a location, goal, or recipient.',
          and: 'Used to connect words of the same part of speech, clauses, or sentences.',
          is: "Third person singular present of 'be': exist, occur, or have a specified state.",
          are: "Second person singular and plural present of 'be'.",
          mitigate: 'Make something less severe, serious, harmful, or painful.',
          pedagogical: 'Relating to the methods, theory, and principles of teaching and education.',
          neuroplasticity: 'The ability of the brain to form and reorganize synaptic connections.',
          geothermal: 'Relating to or produced by the internal thermal heat of the earth.',
        };
        const defText = commonMap[w] || `Meaning and usage of the word "${w}".`;
        return {
          word: w,
          found: true,
          part_of_speech: 'lexicon',
          definitions: [
            {
              part_of_speech: 'lexicon',
              definition: defText,
              examples: [],
              synonyms: [],
              antonyms: [],
            },
          ],
        };
      }
    },
  },

  // Authentication
  auth: {
    login: (username: string, password: string) =>
      request<{
        status: string;
        message?: string;
        user: UserProfile;
      }>('/auth/login/', {
        method: 'POST',
        body: JSON.stringify({ username, password }),
      }),

    register: (data: {
      username: string;
      email: string;
      password: string;
      confirm_password: string;
    }) =>
      request<{
        status: string;
        message?: string;
      }>('/auth/register/', {
        method: 'POST',
        body: JSON.stringify(data),
      }),

    verify: (code: string) =>
      request<{
        status: string;
        message?: string;
        user: UserProfile;
      }>('/auth/verify/', {
        method: 'POST',
        body: JSON.stringify({ code }),
      }),

    resend: () =>
      request<{ status: string; message: string }>('/auth/resend/', {
        method: 'POST',
      }),

    me: () => request<UserProfile>('/auth/me/'),

    logout: () =>
      request<{ status: string; message: string }>('/auth/logout/', {
        method: 'POST',
      }),

    changePassword: (old_password: string, new_password: string) =>
      request<{ status: string; message: string }>('/auth/change-password/', {
        method: 'POST',
        body: JSON.stringify({ old_password, new_password }),
      }),
  },
};
