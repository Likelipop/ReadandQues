import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MarkdownView } from '../MarkdownView';

describe('MarkdownView Component', () => {
  it('renders bold, italics, inline code and headings', () => {
    const sampleMarkdown = `### Key Takeaways
This is **crucial** and *interesting* with \`const test = 1\`.`;

    render(<MarkdownView content={sampleMarkdown} />);

    expect(screen.getByText('Key Takeaways')).toBeInTheDocument();
    expect(screen.getByText('crucial')).toBeInTheDocument();
    expect(screen.getByText('interesting')).toBeInTheDocument();
    expect(screen.getByText('const test = 1')).toBeInTheDocument();
  });

  it('renders markdown tables cleanly', () => {
    const tableMarkdown = `| Metric | Value |
| --- | --- |
| Accuracy | 98% |`;

    render(<MarkdownView content={tableMarkdown} />);

    expect(screen.getByText('Metric')).toBeInTheDocument();
    expect(screen.getByText('Accuracy')).toBeInTheDocument();
    expect(screen.getByText('98%')).toBeInTheDocument();
  });

  it('renders code blocks with language badge and copy button', () => {
    const codeBlockMarkdown = `\`\`\`python
def calculate_accuracy():
    return 100
\`\`\``;

    render(<MarkdownView content={codeBlockMarkdown} />);

    expect(screen.getByText('PYTHON')).toBeInTheDocument();
    expect(screen.getByText('Copy')).toBeInTheDocument();
    expect(screen.getByText(/def calculate_accuracy/)).toBeInTheDocument();
  });

  it('renders markdown links with external icon and rel attributes', () => {
    const linkMarkdown = `Check out [NASA Climate Research](https://climate.nasa.gov).`;

    render(<MarkdownView content={linkMarkdown} />);

    const link = screen.getByRole('link', { name: /NASA Climate Research/i });
    expect(link).toHaveAttribute('href', 'https://climate.nasa.gov');
    expect(link).toHaveAttribute('target', '_blank');
  });
});
