import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import React from 'react';
import { HomePage } from '../HomePage';
import { AllTestsPage } from '../AllTestsPage';
import { OmniSearch } from '../../../components/common/OmniSearch';
import { api } from '../../../api/client';
import { HomepageData } from '../../../types';

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

describe('Discovery & Exploration UI/UX Test Suite (Senior QA)', () => {
  const mockHomepageBundle: HomepageData = {
    status: 'success',
    hero_article: {
      article_id: 'art-hero-1',
      id: 'art-hero-1',
      title: 'Global Renewable Energy Summit 2026',
      source_name: 'Reuters',
      theme: 'Environment',
      genre: 'news',
      summary: 'World leaders announce massive investments in clean energy storage.',
      word_count: 720,
      status: 'completed',
      has_attempted: false,
    },
    hero_articles: [
      {
        article_id: 'art-hero-1',
        id: 'art-hero-1',
        title: 'Global Renewable Energy Summit 2026',
        source_name: 'Reuters',
        theme: 'Environment',
        genre: 'news',
        summary: 'World leaders announce massive investments in clean energy storage.',
        word_count: 720,
        status: 'completed',
        has_attempted: false,
      },
    ],
    daily_vocab: {
      word: 'Resilience',
      phonetic: '/rɪˈzɪliəns/',
      part_of_speech: 'noun',
      definition: 'The capacity to withstand or recover quickly from difficult conditions.',
      example: 'The economy demonstrated unexpected resilience.',
    },
    paraphrase_demo: {
      original: 'The city grew quickly.',
      paraphrased: 'The municipality experienced exponential urban expansion.',
    },
    recommendations: [
      {
        article_id: 'art-rec-1',
        id: 'art-rec-1',
        title: 'Deep-Sea Geothermal Extraction',
        source_name: 'Nature Energy',
        theme: 'Environment',
        genre: 'scientific',
        summary: 'Supercritical thermodynamic power.',
        word_count: 600,
        status: 'completed',
        has_attempted: false,
      },
    ],
    recommended_articles: [
      {
        article_id: 'art-rec-1',
        id: 'art-rec-1',
        title: 'Deep-Sea Geothermal Extraction',
        source_name: 'Nature Energy',
        theme: 'Environment',
        genre: 'scientific',
        summary: 'Supercritical thermodynamic power.',
        word_count: 600,
        status: 'completed',
        has_attempted: false,
      },
    ],
    articles: [
      {
        article_id: 'art-grid-1',
        id: 'art-grid-1',
        title: 'Quantum Computing and Cryptography',
        source_name: 'Tech Review',
        theme: 'Technology',
        genre: 'academic',
        summary: 'Qubits and post-quantum encryption algorithms.',
        word_count: 540,
        status: 'completed',
        has_attempted: false,
      },
    ],
    themes: ['All', 'Technology', 'Environment', 'Science'],
    genres: ['All', 'academic', 'scientific', 'news'],
    total_count: 1,
  };

  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.articles.list).mockResolvedValue({
      status: 'success',
      articles: mockHomepageBundle.articles,
      total_count: 1,
      page: 1,
      limit: 12,
      has_next: false,
      has_prev: false,
    });
  });

  // ── 1. HomePage Complete Bundle Rendering ──────────────────────────────────

  it('renders HomePage with hero hot news, recommendations, and article grid', async () => {
    vi.mocked(api.homepage.get).mockResolvedValueOnce(mockHomepageBundle);

    const handleSelectArticle = vi.fn();

    render(
      <HomePage
        onSelectArticle={handleSelectArticle}
        selectedTheme="All"
      />
    );

    expect(screen.getByText(/Loading latest reading materials/i)).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText('Global Renewable Energy Summit 2026')).toBeInTheDocument();
    });

    expect(screen.getByText('Deep-Sea Geothermal Extraction')).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText('Quantum Computing and Cryptography')).toBeInTheDocument();
    });
  });

  it('triggers onSelectArticle when clicking Start Practice CTA on hero article', async () => {
    vi.mocked(api.homepage.get).mockResolvedValueOnce(mockHomepageBundle);

    const handleSelectArticle = vi.fn();

    render(
      <HomePage
        onSelectArticle={handleSelectArticle}
        selectedTheme="All"
      />
    );

    await waitFor(() => {
      expect(screen.getByText('Global Renewable Energy Summit 2026')).toBeInTheDocument();
    });

    const startBtn = screen.getByRole('button', { name: /Start Reading & AI Quiz/i });
    fireEvent.click(startBtn);
    expect(handleSelectArticle).toHaveBeenCalledWith('art-hero-1');
  });

  // ── 2. AllTestsPage Catalog & Filtering UX ─────────────────────────────────

  it('renders AllTestsPage with theme filters and paginated articles', async () => {
    vi.mocked(api.homepage.get).mockResolvedValueOnce(mockHomepageBundle);
    vi.mocked(api.articles.list).mockResolvedValueOnce({
      status: 'success',
      articles: mockHomepageBundle.articles,
      total_count: 1,
      page: 1,
      limit: 12,
      has_next: false,
      has_prev: false,
    });

    const handleSelect = vi.fn();

    render(
      <AllTestsPage
        initialQuery=""
        initialTheme="All"
        onSelectArticle={handleSelect}
      />
    );

    await waitFor(() => {
      expect(screen.getByText('Quantum Computing and Cryptography')).toBeInTheDocument();
    });

    expect(screen.getByText('Explore All Reading Tests')).toBeInTheDocument();
    expect(screen.getByText('Theme:')).toBeInTheDocument();
    expect(screen.getByText('Published:')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Today (24h)' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Past Week (7d)' })).toBeInTheDocument();

    // Click Date Filter button
    fireEvent.click(screen.getByRole('button', { name: 'Today (24h)' }));

    await waitFor(() => {
      expect(api.articles.list).toHaveBeenCalledWith(
        expect.objectContaining({
          date_filter: 'today',
        })
      );
    });
  });

  // ── 3. OmniSearch Autocomplete UX ──────────────────────────────────────────

  it('renders OmniSearch and triggers selection callback', async () => {
    vi.mocked(api.search.keyword).mockResolvedValueOnce({
      status: 'success',
      results: [
        {
          article_id: 'art-search-99',
          id: 'art-search-99',
          title: 'Artificial Intelligence Ethics',
          source_name: 'MIT Review',
          theme: 'Technology',
          word_count: 450,
        },
      ],
    });

    const handleSelect = vi.fn();
    render(<OmniSearch onSelectArticle={handleSelect} />);

    const searchInput = screen.getByPlaceholderText(/Search articles/i);
    expect(searchInput).toBeInTheDocument();

    fireEvent.change(searchInput, { target: { value: 'Intelligence' } });

    await waitFor(() => {
      expect(screen.getByText('Artificial Intelligence Ethics')).toBeInTheDocument();
    });

    const resultItem = screen.getByText('Artificial Intelligence Ethics');
    fireEvent.click(resultItem);

    expect(handleSelect).toHaveBeenCalledWith('art-search-99');
  });
});
