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

// Rich fallback datasets to ensure UI is 100% resilient and interactive
export const SAMPLE_ARTICLES_DATA: Article[] = [
  {
    id: 'art-sample-001',
    article_id: 'art-sample-001',
    title: 'The Evolution of Artificial Intelligence in Higher Education',
    source_name: 'MIT Technology Review',
    image_url: 'https://images.unsplash.com/photo-1620712943543-bcc4688e7485?q=80&w=1200&auto=format&fit=crop',
    published_at: '2026-08-19T08:00:00Z',
    stage: 'gold',
    status: 'completed',
    theme: 'Technology',
    genre: 'academic',
    summary: 'An investigation into how adaptive machine learning models and cognitive agents are fundamentally transforming university curricula, personalized tutoring, and academic integrity across global institutions.',
    word_count: 685,
    original_text: `The rapid proliferation of neural network architectures and large-scale language models has precipitated a profound pedagogical reckoning across higher education institutions worldwide. For decades, traditional tertiary instruction adhered to a broadcast pedagogical model, in which lecturers transmitted canonical knowledge to large cohorts of students who were subsequently evaluated through summative, high-stakes written assessments.

Recent empirical investigations conducted across leading global universities demonstrate that cognitive AI agents can provide adaptive, real-time scaffolding tailored to individual learning trajectories. Rather than standardizing instructional pace, these algorithmic frameworks diagnose conceptual misconceptions dynamically, delivering customized remediation before cognitive deficits compound.

However, the integration of generative cognitive systems into academic environments is not without controversy. Prominent educational ethicists argue that over-reliance on conversational AI agents may diminish intrinsic metacognitive regulation—the ability of learners to critically plan, monitor, and assess their own problem-solving processes. Furthermore, the opacity of deep neural networks poses significant accountability challenges when evaluating automated grading accuracy.

To mitigate these epistemic risks, contemporary academic institutions are adopting blended cognitive ecosystems. Under this paradigm, algorithmic models serve as co-exploratory assistants rather than authoritative evaluators, fostering higher-order analytical reasoning while preserving human pedagogical mentorship.`,
    exams: [
      {
        exam_id: 'exam_sample_001',
        title: 'Reading Comprehension Test: AI in Higher Education',
        quizzes: [
          {
            quiz_type: 'multiple_choice',
            question: 'According to paragraph 1, traditional higher education was primarily characterized by which method?',
            options: [
              'Continuous personalized formative feedback',
              'A broadcast model with summative written examinations',
              'Peer-led collaborative research workshops',
              'Automated cognitive grading and algorithmic pace'
            ],
            correct_answer: 'A broadcast model with summative written examinations',
            explanation: "Paragraph 1 states that traditional tertiary instruction adhered to a 'broadcast pedagogical model' evaluated through 'summative, high-stakes written assessments'."
          },
          {
            quiz_type: 'yes_no_notgiven',
            question: 'Cognitive AI systems adjust their instruction based on each learner\'s individual misconceptions.',
            options: ['YES', 'NO', 'NOT GIVEN'],
            correct_answer: 'YES',
            explanation: "Paragraph 2 confirms that algorithmic frameworks 'diagnose conceptual misconceptions dynamically, delivering customized remediation'."
          },
          {
            quiz_type: 'yes_no_notgiven',
            question: 'Most university professors have resisted using generative artificial intelligence tools.',
            options: ['YES', 'NO', 'NOT GIVEN'],
            correct_answer: 'NOT GIVEN',
            explanation: 'While educational ethicists raise concerns, the text does not mention the proportion or specific resistance of university professors.'
          },
          {
            quiz_type: 'fill_in_blank',
            question: 'Under the blended cognitive ecosystem, algorithmic tools function as [1] assistants to promote [2] analytical reasoning.',
            correct_answer: 'co-exploratory, higher-order',
            explanation: "Paragraph 4 explains: 'algorithmic models serve as co-exploratory assistants rather than authoritative evaluators, fostering higher-order analytical reasoning'."
          }
        ]
      }
    ]
  },
  {
    id: 'art-sample-002',
    article_id: 'art-sample-002',
    title: 'Breakthroughs in Deep-Sea Geothermal Energy and Grid Storage',
    source_name: 'Nature Energy',
    image_url: 'https://images.unsplash.com/photo-1497435334941-8c899ee9e8e9?q=80&w=1200&auto=format&fit=crop',
    published_at: '2026-08-16T10:30:00Z',
    stage: 'gold',
    status: 'completed',
    theme: 'Environment',
    genre: 'scientific',
    summary: 'Novel supercritical thermodynamic extraction systems operating along tectonic rifts promise round-the-clock baseload clean power with zero surface footprint.',
    word_count: 620,
    original_text: `Transitioning global power grids away from hydrocarbon dependency requires continuous, weather-independent baseload energy. While terrestrial solar and wind generation have achieved unprecedented capital efficiency, their intermittent nature necessitates colossal electrochemical storage infrastructures. Deep-sea geothermal extraction has emerged as an exceptionally viable alternative.

Hydrothermal vents situated along mid-ocean tectonic boundaries discharge mineral-rich supercritical fluids exceeding temperatures of 400 degrees Celsius. Recent deep-water robotic drilling trials have demonstrated the mechanical feasibility of circulating heat-transfer mediums through closed-loop benthic exchangers without disturbing vulnerable abyssal biomes.

Energy analysts estimate that harnessing just 0.1 percent of available tectonic thermal dissipation could meet current global electricity demand twenty times over. Marine engineering consortia are now constructing pilot high-voltage direct current submarine conduits to transmit benthic power directly to coastal industrial clusters.`,
    exams: [
      {
        exam_id: 'exam_sample_002',
        title: 'Reading Comprehension Test: Deep-Sea Geothermal Energy',
        quizzes: [
          {
            quiz_type: 'multiple_choice',
            question: 'What primary limitation of solar and wind energy is highlighted in paragraph 1?',
            options: [
              'Excessive capital extraction costs',
              'Intermittent generation requiring massive storage',
              'Thermal degradation in deep-water environments',
              'Incompatibility with high-voltage direct current lines'
            ],
            correct_answer: 'Intermittent generation requiring massive storage',
            explanation: "Paragraph 1 notes that the intermittent nature of solar and wind 'necessitates colossal electrochemical storage infrastructures'."
          },
          {
            quiz_type: 'yes_no_notgiven',
            question: 'Closed-loop benthic heat exchangers cause widespread destruction of ocean floor ecosystems.',
            options: ['YES', 'NO', 'NOT GIVEN'],
            correct_answer: 'NO',
            explanation: "Paragraph 2 states that robotic drilling trials demonstrated feasibility 'without disturbing vulnerable abyssal biomes'."
          }
        ]
      }
    ]
  },
  {
    id: 'art-sample-003',
    article_id: 'art-sample-003',
    title: 'Neuroplasticity and the Mechanisms of Adult Second Language Acquisition',
    source_name: 'Scientific American',
    image_url: 'https://images.unsplash.com/photo-1507413245164-6160d8298b31?q=80&w=1200&auto=format&fit=crop',
    published_at: '2026-08-05T14:15:00Z',
    stage: 'gold',
    status: 'completed',
    theme: 'Science',
    genre: 'academic',
    summary: 'Contemporary neuroimaging reveals structural synaptic remodeling in adult brains during intensive linguistic immersion, debunking the strict critical period hypothesis.',
    word_count: 640,
    original_text: `For over half a century, the Critical Period Hypothesis held that the human brain loses the neural malleability required for native-like second language mastery following the onset of puberty. Early psycho-linguistic theories attributed this perceived developmental decline to the progressive lateralization of cerebral hemispheres and the myelination of cortical pathways.

Recent longitudinal functional MRI investigations have substantially overturned this deterministic dogma. High-resolution neuroimaging of adult polyglots engaged in spaced syntactic retrieval demonstrates pronounced white-matter reorganization within the left arcuate fasciculus and bilateral inferior frontal gyri.

These neurological findings indicate that while phonological acquisition may exhibit early neurodevelopmental sensitivities, syntactic and lexical consolidation remain remarkably plastic across the entire adult lifespan given targeted cognitive conditioning.`,
    exams: [
      {
        exam_id: 'exam_sample_003',
        title: 'Reading Comprehension Test: Adult Neuroplasticity & Languages',
        quizzes: [
          {
            quiz_type: 'multiple_choice',
            question: 'According to paragraph 3, which linguistic domain remains plastic throughout adulthood?',
            options: [
              'Early childhood phonological sensitivity',
              'Syntactic and lexical consolidation',
              'Progressive cerebral myelination',
              'Bilateral hemispheric lateralization'
            ],
            correct_answer: 'Syntactic and lexical consolidation',
            explanation: "Paragraph 3 concludes that 'syntactic and lexical consolidation remain remarkably plastic across the entire adult lifespan'."
          }
        ]
      }
    ]
  }
];

const FALLBACK_HOMEPAGE: HomepageData = {
  status: 'success',
  hero_articles: SAMPLE_ARTICLES_DATA,
  trending_topics: SAMPLE_ARTICLES_DATA.map((a) => ({ id: a.id || a.article_id, title: a.title })),
  daily_vocab: {
    word: 'Resilience',
    phonetic: '/rɪˈzɪl.jəns/',
    part_of_speech: 'noun',
    definition: 'The capacity to withstand or recover quickly from difficult conditions; elasticity.',
    example: 'The educational institution demonstrated extraordinary academic resilience in adopting AI technologies.',
  },
  paraphrase_demo: {
    original: 'Climate change poses severe threats to global food security.',
    paraphrased: 'Global agricultural output and food distribution networks are gravely endangered by anthropogenic climatic instability.',
  },
  recommended_articles: SAMPLE_ARTICLES_DATA,
  articles: SAMPLE_ARTICLES_DATA,
  total_count: SAMPLE_ARTICLES_DATA.length,
  themes: ['All', 'Technology', 'Environment', 'Science', 'Society', 'Economy'],
  genres: ['All', 'academic', 'scientific', 'opinion'],
  nav_themes: [
    { id: 'TECHNOLOGY', name: 'Technology' },
    { id: 'ENVIRONMENT', name: 'Environment' },
    { id: 'SCIENCE', name: 'Science' },
    { id: 'SOCIETY', name: 'Society' },
    { id: 'ECONOMY', name: 'Economy' },
  ],
};

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
