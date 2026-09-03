import React from 'react';
import { UnifiedReadingDock, UnifiedReadingDockProps } from './UnifiedReadingDock';

export interface WorkspaceToolbarProps extends UnifiedReadingDockProps {
  isQuizOpen: boolean;
  onToggleQuiz: () => void;
  className?: string;
}

/**
 * WorkspaceToolbar
 * Legacy wrapper that delegates to Bob's "AuraDock" UnifiedReadingDock suite.
 * Maintains full backwards compatibility with all workspace consumers and test suites.
 */
export const WorkspaceToolbar: React.FC<WorkspaceToolbarProps> = ({
  isQuizOpen,
  onToggleQuiz,
  className = '',
}) => {
  return (
    <UnifiedReadingDock
      isQuizOpen={isQuizOpen}
      onToggleQuiz={onToggleQuiz}
      className={className}
    />
  );
};
