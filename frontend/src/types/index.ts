export interface QuizOption {
  text: string;
}

export type QuizType = 'yes_no_notgiven' | 'multiple_choice' | 'fill_in_blank';

export interface Quiz {
  quiz_type: QuizType;
  question: string;
  options?: string[];
  correct_answer: string;
  explanation: string;
  supporting_text?: string;
}

export interface Exam {
  exam_id?: string;
  title?: string;
  quizzes: Quiz[];
}

export interface Article {
  article_id: string;
  id: string;
  url?: string;
  title: string;
  source_name: string;
  image_url?: string | null;
  published_at?: string | null;
  stage?: string;
  status: string;
  theme: string;
  genre: string;
  summary: string;
  original_text: string;
  cleaned_text?: string;
  word_count: number;
  has_attempted?: boolean;
  exams?: Exam[];
  created_at?: string;
}

export interface ArticleCard {
  article_id: string;
  id: string;
  url?: string;
  title: string;
  source_name: string;
  image_url?: string | null;
  published_at?: string | null;
  stage?: string;
  status: string;
  theme: string;
  genre: string;
  summary: string;
  word_count: number;
  has_attempted?: boolean;
}

export interface DailyVocab {
  word: string;
  phonetic: string;
  part_of_speech: string;
  definition: string;
  example: string;
  band_score?: string;
}

export interface ParaphraseDemo {
  original: string;
  paraphrased: string;
}

export interface NavTheme {
  id: string;
  name: string;
}

export interface HomepageData {
  status: string;
  hero_article?: ArticleCard;
  hero_articles?: ArticleCard[];
  trending_topics?: Array<{ id: string; title: string }>;
  daily_vocab: DailyVocab;
  paraphrase_demo?: ParaphraseDemo;
  recommended_articles?: ArticleCard[];
  recommendations?: ArticleCard[];
  articles: ArticleCard[];
  total_count: number;
  themes: string[];
  genres: string[];
  nav_themes?: NavTheme[];
}

export interface UserProfile {
  id: number;
  username: string;
  email: string;
  is_authenticated: boolean;
  stars: number;
  total_articles_imported: number;
  total_questions_solved: number;
  correct_answers_count: number;
  avatar_url?: string | null;
  streak: number;
  total_tests_completed: number;
}

export interface QuestionTicket {
  id: string;
  question: string;
  answer: string;
  citation_quote?: string;
  timestamp: number;
  status: 'RESOLVED' | 'PENDING' | 'ERROR';
}

export interface ProofData {
  proof_found: boolean;
  proof_excerpt?: string;
  confidence_score?: number;
  reason?: string;
}

export interface SearchResultItem {
  article_id?: string;
  id: string;
  title: string;
  source?: string;
  source_name?: string;
  theme?: string;
  genre?: string;
  snippet?: string;
  date?: string;
  similarity?: number;
  word_count?: number;
}

export interface KeyTerm {
  term: string;
  meaning: string;
}

export interface ExplainPhraseResult {
  status: string;
  phrase: string;
  summary: string;
  detailed_explanation: string;
  simplified_version: string;
  key_terms: KeyTerm[];
}

export interface SmartExplanationCard {
  id: string;
  selected_text: string;
  summary?: string;
  explanation: string;
  simplified_version?: string;
  paraphrased_text?: string;
  key_terms?: KeyTerm[];
  timestamp: number;
}

export interface DictionaryDefinitionItem {
  part_of_speech: string;
  definition: string;
  examples: string[];
  synonyms: string[];
  antonyms: string[];
}

export interface DictionaryLookupResult {
  word: string;
  found: boolean;
  lemma?: string | null;
  part_of_speech?: string | null;
  phonetic?: string | null;
  definitions: DictionaryDefinitionItem[];
}

export interface ExamSubmissionResult {
  status: string;
  id: string;
  related_articles?: ArticleCard[];
}

