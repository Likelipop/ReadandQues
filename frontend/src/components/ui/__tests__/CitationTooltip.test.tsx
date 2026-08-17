import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { CitationTooltip } from '../CitationTooltip';

describe('CitationTooltip', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('renders trigger button with children content', () => {
    render(
      <CitationTooltip articleId="art-1" questionIdx={0}>
        Show Verbatim Proof
      </CitationTooltip>
    );

    const button = screen.getByRole('button', { name: /view passage grounding proof/i });
    expect(button).toBeInTheDocument();
    expect(screen.getByText('Show Verbatim Proof')).toBeInTheDocument();
  });

  it('fetches proof data and renders excerpt and confidence score on click', async () => {
    const mockResponse = {
      status: 'success',
      proof: {
        proof_found: true,
        proof_excerpt: 'Microplastics severely damage marine ecosystems.',
        confidence_score: 0.95,
      },
    };

    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => mockResponse,
      })
    );

    render(
      <CitationTooltip articleId="art-1" questionIdx={0}>
        Show Verbatim Proof
      </CitationTooltip>
    );

    const button = screen.getByRole('button', { name: /view passage grounding proof/i });
    fireEvent.click(button);

    // Should render tooltip dialog/role
    expect(screen.getByRole('tooltip')).toBeInTheDocument();

    await waitFor(() => {
      expect(
        screen.getByText(/Microplastics severely damage marine ecosystems/i)
      ).toBeInTheDocument();
      expect(screen.getByText(/Grounding Passage Proof/i)).toBeInTheDocument();
      expect(screen.getByText(/Confidence: 95%/i)).toBeInTheDocument();
    });

    expect(fetch).toHaveBeenCalledWith('/readspace/art-1/proof/0/');
  });

  it('handles fetch failure and renders error message', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: false,
        status: 404,
      })
    );

    render(
      <CitationTooltip articleId="art-invalid" questionIdx={0}>
        Show Verbatim Proof
      </CitationTooltip>
    );

    const button = screen.getByRole('button', { name: /view passage grounding proof/i });
    fireEvent.click(button);

    await waitFor(() => {
      expect(screen.getByText(/HTTP error 404/i)).toBeInTheDocument();
    });
  });

  it('toggles tooltip visibility when clicked twice', async () => {
    const mockResponse = {
      status: 'success',
      proof: {
        proof_found: true,
        proof_excerpt: 'Sample proof text.',
      },
    };

    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => mockResponse,
      })
    );

    render(
      <CitationTooltip articleId="art-1" questionIdx={0}>
        Show Verbatim Proof
      </CitationTooltip>
    );

    const button = screen.getByRole('button', { name: /view passage grounding proof/i });

    // Open
    fireEvent.click(button);
    expect(screen.getByRole('tooltip')).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText(/Sample proof text/i)).toBeInTheDocument();
    });

    // Close
    fireEvent.click(button);
    expect(screen.queryByRole('tooltip')).not.toBeInTheDocument();
  });
});
