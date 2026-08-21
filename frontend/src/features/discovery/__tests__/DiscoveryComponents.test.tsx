import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import React from 'react';
import { DailyVocabCard } from '../DailyVocabCard';
import { ParaphraseCard } from '../ParaphraseCard';
import { ArticleCard } from '../ArticleCard';

describe('Discovery Components', () => {
  it('renders DailyVocabCard with word, phonetic, definition, and speak button', () => {
    const vocab = {
      word: 'Ephemeral',
      phonetic: '/ɪˈfem.ər.əl/',
      part_of_speech: 'adjective',
      definition: 'Lasting for a very short time.',
      example: 'Fashions are ephemeral.',
    };

    render(<DailyVocabCard vocab={vocab} />);

    expect(screen.getByText('Ephemeral')).toBeInTheDocument();
    expect(screen.getByText('/ɪˈfem.ər.əl/')).toBeInTheDocument();
    expect(screen.getByText('Lasting for a very short time.')).toBeInTheDocument();
    expect(screen.getByText('"Fashions are ephemeral."')).toBeInTheDocument();
  });

  it('renders ParaphraseCard with original and paraphrased academic sentences', () => {
    const demo = {
      original: 'The city grew quickly.',
      paraphrased: 'The municipality experienced exponential urban expansion.',
    };

    render(<ParaphraseCard demo={demo} />);

    expect(screen.getByText('The city grew quickly.')).toBeInTheDocument();
    expect(
      screen.getByText('The municipality experienced exponential urban expansion.')
    ).toBeInTheDocument();
  });

  it('renders ArticleCard and triggers onSelect callback', () => {
    const article = {
      id: 'art_demo_1',
      article_id: 'art_demo_1',
      title: 'Renewable Energy Progress in 2026',
      source_name: 'Tech Daily',
      theme: 'Technology',
      genre: 'general',
      summary: 'An overview of solar and wind breakthroughs.',
      word_count: 520,
      stage: 'gold',
      status: 'completed',
    };

    const handleSelect = vi.fn();
    render(<ArticleCard article={article} onSelect={handleSelect} />);

    expect(screen.getByText('Renewable Energy Progress in 2026')).toBeInTheDocument();
    expect(screen.getByText('Tech Daily')).toBeInTheDocument();
    expect(screen.getByText('520 words')).toBeInTheDocument();

    const startBtn = screen.getByText('Start Practice');
    fireEvent.click(startBtn);

    expect(handleSelect).toHaveBeenCalledWith('art_demo_1');
  });
});
