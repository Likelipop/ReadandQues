import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import React from 'react';
import { HomePage } from '../HomePage';
import { DailyVocabCard } from '../DailyVocabCard';
import { ArticleGrid } from '../ArticleGrid';
import { ArticleCard } from '../ArticleCard';
import { AllTestsPage } from '../AllTestsPage';
import { getDeterministicDailyVocab, formatVocabDateBanner, DAILY_VOCAB_POOL } from '../../../utils/dailyVocab';
import { isWithinDateFilter, formatPublishDate } from '../../../utils/dateFilter';
import { api } from '../../../api/client';
import { HomepageData, ArticleCard as ArticleCardType } from '../../../types';

vi.mock('../../../api/client', () => ({
  api: {
    homepage: {
      get: vi.fn(),
    },
    articles: {
      list: vi.fn(),
      search: vi.fn(),
      import: vi.fn(),
    },
    search: {
      keyword: vi.fn(),
      semantic: vi.fn(),
    },
  },
}));

describe('Client Requests Verification Suite - QA & DevOps', () => {
  const mockArticles: ArticleCardType[] = [
    {
      id: 'art-101',
      article_id: 'art-101',
      title: 'Solar and Hydrogen Microgrids',
      source_name: 'CleanTech Daily',
      theme: 'Environment',
      genre: 'scientific',
      summary: 'Exploring zero-emission energy grids in 2026.',
      word_count: 650,
      published_at: new Date().toISOString(),
      stage: 'gold',
      status: 'completed',
      has_attempted: false,
    },
    {
      id: 'art-102',
      article_id: 'art-102',
      title: 'Quantum Key Distribution Networks',
      source_name: 'Nature Quantum',
      theme: 'Technology',
      genre: 'academic',
      summary: 'Quantum-safe communication protocols.',
      word_count: 820,
      published_at: '2026-08-01T12:00:00Z',
      stage: 'gold',
      status: 'completed',
      has_attempted: true,
    },
  ];

  const mockHomepageData: HomepageData = {
    status: 'success',
    hero_articles: [mockArticles[0]],
    hero_article: mockArticles[0],
    daily_vocab: {
      word: 'Neuroplasticity',
      phonetic: '/ˌnjʊərəʊplæˈstɪsɪti/',
      part_of_speech: 'noun',
      band_score: 'IELTS Band 9.0',
      definition: 'The ability of the brain to reorganize itself by forming new neural connections throughout life.',
      example: 'Intensive language immersion stimulates adult neuroplasticity and synaptic reorganization.',
    },
    recommended_articles: [mockArticles[1]],
    articles: mockArticles,
    themes: ['All', 'Environment', 'Technology'],
    genres: ['All', 'scientific', 'academic'],
    total_count: 2,
  };

  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.articles.list).mockResolvedValue({
      status: 'success',
      articles: mockArticles,
      total_count: 2,
      page: 1,
      limit: 12,
      has_next: false,
      has_prev: false,
    });
  });

  // ── Request 1: Removal of ParaphraseCard & Full-Width DailyVocabCard ──────

  describe('Request 1: Paraphrase Card Removal & DailyVocab Spotlight', () => {
    it('verifies HomePage renders DailyVocabCard spotlight and does NOT render ParaphraseCard', async () => {
      vi.mocked(api.homepage.get).mockResolvedValueOnce(mockHomepageData);

      const handleSelectArticle = vi.fn();
      render(<HomePage onSelectArticle={handleSelectArticle} selectedTheme="All" />);

      await waitFor(() => {
        expect(screen.getByText('Solar and Hydrogen Microgrids')).toBeInTheDocument();
      });

      // 1. DailyVocab spotlight is present
      expect(screen.getByText('Neuroplasticity')).toBeInTheDocument();
      expect(screen.getByText('Word of the Day')).toBeInTheDocument();
      expect(screen.getByText('/ˌnjʊərəʊplæˈstɪsɪti/')).toBeInTheDocument();

      // 2. Paraphrase card / AI Smart Paraphrase Engine is NOT rendered
      expect(screen.queryByText(/AI Smart Paraphrase/i)).not.toBeInTheDocument();
      expect(screen.queryByText(/Paraphrase Engine/i)).not.toBeInTheDocument();
      expect(screen.queryByText(/Paraphrased Academic Style/i)).not.toBeInTheDocument();
    });
  });

  // ── Request 2: Deterministic Word of the Day ──────────────────────────────

  describe('Request 2: Deterministic Word of the Day Functionality', () => {
    it('verifies getDeterministicDailyVocab is deterministic and consistent for the same date', () => {
      const fixedDate = new Date('2026-08-19T00:00:00Z');
      const vocab1 = getDeterministicDailyVocab(fixedDate);
      const vocab2 = getDeterministicDailyVocab(fixedDate);

      expect(vocab1).toBeDefined();
      expect(vocab1.word).toEqual(vocab2.word);
      expect(vocab1.phonetic).toEqual(vocab2.phonetic);
      expect(vocab1.definition).toEqual(vocab2.definition);
      expect(DAILY_VOCAB_POOL).toContainEqual(vocab1);

      // Verify date banner formatting
      const banner = formatVocabDateBanner(fixedDate);
      expect(banner).toContain('2026');
      expect(banner).toContain('August');
    });

    it('verifies DailyVocabCard audio TTS speak button triggers SpeechSynthesis', () => {
      const mockSpeak = vi.fn();
      const mockCancel = vi.fn();
      window.speechSynthesis = {
        speak: mockSpeak,
        cancel: mockCancel,
      } as any;

      class MockSpeechSynthesisUtterance {
        text: string;
        lang: string = '';
        rate: number = 1;
        onstart: any = null;
        onend: any = null;
        onerror: any = null;
        constructor(text: string) {
          this.text = text;
        }
      }
      (globalThis as any).SpeechSynthesisUtterance = MockSpeechSynthesisUtterance;
      (window as any).SpeechSynthesisUtterance = MockSpeechSynthesisUtterance;

      render(<DailyVocabCard vocab={mockHomepageData.daily_vocab} />);

      const speakBtn = screen.getByLabelText('Listen to pronunciation');
      expect(speakBtn).toBeInTheDocument();

      fireEvent.click(speakBtn);

      expect(mockCancel).toHaveBeenCalled();
      expect(mockSpeak).toHaveBeenCalledTimes(1);
    });

    it('verifies DailyVocabCard copy button copies text and displays copied state', async () => {
      const writeTextMock = vi.fn().mockResolvedValue(undefined);
      Object.assign(navigator, {
        clipboard: {
          writeText: writeTextMock,
        },
      });

      render(<DailyVocabCard vocab={mockHomepageData.daily_vocab} />);

      const copyBtn = screen.getByLabelText('Copy vocabulary card');
      expect(copyBtn).toBeInTheDocument();

      fireEvent.click(copyBtn);

      await waitFor(() => {
        expect(writeTextMock).toHaveBeenCalledWith(
          expect.stringContaining('Neuroplasticity')
        );
      });
    });

    it('verifies DailyVocabCard practice button triggers onExploreTopic callback', () => {
      const handleExplore = vi.fn();
      render(
        <DailyVocabCard
          vocab={mockHomepageData.daily_vocab}
          onExploreTopic={handleExplore}
        />
      );

      const practiceBtn = screen.getByRole('button', {
        name: /Practice Reading Tests with "Neuroplasticity"/i,
      });
      fireEvent.click(practiceBtn);

      expect(handleExplore).toHaveBeenCalledWith('Neuroplasticity');
    });
  });

  // ── Request 3: Date Filter for Articles Catalog ───────────────────────────

  describe('Request 3: Date Filter for News & Articles Catalog', () => {
    it('verifies isWithinDateFilter logic correctly filters date ranges', () => {
      const now = new Date();
      const todayISO = now.toISOString();

      const fourDaysAgo = new Date(now.getTime() - 4 * 86400 * 1000).toISOString();
      const twentyDaysAgo = new Date(now.getTime() - 20 * 86400 * 1000).toISOString();
      const twoMonthsAgo = new Date(now.getTime() - 60 * 86400 * 1000).toISOString();

      // All filter
      expect(isWithinDateFilter(todayISO, 'all')).toBe(true);
      expect(isWithinDateFilter(twoMonthsAgo, 'all')).toBe(true);

      // Today filter (within 24h)
      expect(isWithinDateFilter(todayISO, 'today')).toBe(true);
      expect(isWithinDateFilter(fourDaysAgo, 'today')).toBe(false);

      // Week filter (within 7d)
      expect(isWithinDateFilter(fourDaysAgo, 'week')).toBe(true);
      expect(isWithinDateFilter(twentyDaysAgo, 'week')).toBe(false);

      // Month filter (within 30d)
      expect(isWithinDateFilter(twentyDaysAgo, 'month')).toBe(true);
      expect(isWithinDateFilter(twoMonthsAgo, 'month')).toBe(false);

      // Missing or null date
      expect(isWithinDateFilter(null, 'today')).toBe(false);
      expect(isWithinDateFilter(undefined, 'all')).toBe(true);
    });

    it('verifies formatPublishDate formats ISO dates properly', () => {
      const formatted = formatPublishDate('2026-08-19T08:00:00Z');
      expect(formatted).toBe('Aug 19, 2026');
      expect(formatPublishDate(undefined)).toBe('');
      expect(formatPublishDate('invalid-date')).toBe('');
    });

    it('verifies ArticleGrid renders all date filter options and triggers onSelectDateFilter', () => {
      const handleDateFilter = vi.fn();
      const handleSelectArticle = vi.fn();

      render(
        <ArticleGrid
          articles={mockArticles}
          dateFilter="all"
          onSelectDateFilter={handleDateFilter}
          onSelectArticle={handleSelectArticle}
        />
      );

      // Check all 4 filter buttons
      expect(screen.getByRole('button', { name: 'All' })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: 'Today' })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: 'Week' })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: 'Month' })).toBeInTheDocument();

      // Click 'Today' filter
      fireEvent.click(screen.getByRole('button', { name: 'Today' }));
      expect(handleDateFilter).toHaveBeenCalledWith('today');

      // Click 'Week' filter
      fireEvent.click(screen.getByRole('button', { name: 'Week' }));
      expect(handleDateFilter).toHaveBeenCalledWith('week');
    });

    it('verifies ArticleCard renders formatted date with calendar icon', () => {
      const handleSelect = vi.fn();
      render(<ArticleCard article={mockArticles[1]} onSelect={handleSelect} />);

      expect(screen.getByText('Aug 1, 2026')).toBeInTheDocument();
      expect(screen.getByText('Nature Quantum')).toBeInTheDocument();
    });

    it('verifies AllTestsPage renders date filter pills and re-fetches articles on change', async () => {
      vi.mocked(api.homepage.get).mockResolvedValueOnce(mockHomepageData);
      vi.mocked(api.articles.list).mockResolvedValueOnce({
        status: 'success',
        articles: mockArticles,
        total_count: 2,
        page: 1,
        limit: 12,
        has_next: false,
        has_prev: false,
      });

      const handleSelect = vi.fn();
      render(<AllTestsPage onSelectArticle={handleSelect} />);

      await waitFor(() => {
        expect(screen.getByText('Solar and Hydrogen Microgrids')).toBeInTheDocument();
      });

      // Verify date filter options in AllTestsPage
      expect(screen.getByRole('button', { name: 'All Time' })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: 'Today (24h)' })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: 'Past Week (7d)' })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: 'Past Month (30d)' })).toBeInTheDocument();

      // Select 'Past Month (30d)'
      fireEvent.click(screen.getByRole('button', { name: 'Past Month (30d)' }));

      await waitFor(() => {
        expect(api.articles.list).toHaveBeenCalledWith(
          expect.objectContaining({
            date_filter: 'month',
          })
        );
      });
    });
  });
});
