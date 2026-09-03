import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import React from 'react';
import { AuthModal } from '../AuthModal';
import { ProfilePage } from '../ProfilePage';
import { api } from '../../../api/client';
import { authStore } from '../../../store';
import { UserProfile } from '../../../types';

vi.mock('../../../api/client', () => ({
  api: {
    auth: {
      login: vi.fn(),
      register: vi.fn(),
      verify: vi.fn(),
      resendOtp: vi.fn(),
      changePassword: vi.fn(),
    },
  },
}));

describe('Auth & Profile UI/UX Test Suite (Senior QA)', () => {
  const mockUser: UserProfile = {
    id: 101,
    username: 'ai_scholar',
    email: 'scholar@example.com',
    is_authenticated: true,
    stars: 42,
    total_articles_imported: 8,
    total_questions_solved: 50,
    correct_answers_count: 45,
    streak: 5,
    total_tests_completed: 12,
  };

  beforeEach(() => {
    vi.clearAllMocks();
    authStore.setState({
      user: null,
      isLoading: false,
    });
  });

  // ── 1. AuthModal Tab Switching & Form Submissions ───────────────────────────

  it('renders AuthModal in Login mode and allows typing credentials', async () => {
    const handleClose = vi.fn();
    const handleShowToast = vi.fn();

    vi.mocked(api.auth.login).mockResolvedValueOnce({
      status: 'success',
      message: 'Welcome back!',
      user: mockUser,
    });

    render(
      <AuthModal
        isOpen={true}
        onClose={handleClose}
        initialTab="login"
        onShowToast={handleShowToast}
      />
    );

    expect(screen.getByText('Sign in to ReadQues')).toBeInTheDocument();

    const usernameInput = screen.getByPlaceholderText('Enter your username or email');
    const passwordInput = screen.getByPlaceholderText('••••••••');

    fireEvent.change(usernameInput, { target: { value: 'ai_scholar' } });
    fireEvent.change(passwordInput, { target: { value: 'Password123!' } });

    expect(usernameInput).toHaveValue('ai_scholar');
    expect(passwordInput).toHaveValue('Password123!');

    const submitBtn = screen.getByRole('button', { name: /Sign In/i });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(api.auth.login).toHaveBeenCalledWith('ai_scholar', 'Password123!');
      expect(handleShowToast).toHaveBeenCalledWith('Welcome back!', 'success');
      expect(handleClose).toHaveBeenCalled();
    });
  });

  it('switches between Login and Register tabs', () => {
    render(
      <AuthModal
        isOpen={true}
        onClose={vi.fn()}
        initialTab="login"
      />
    );

    expect(screen.getByText('Sign in to ReadQues')).toBeInTheDocument();

    const registerTabBtn = screen.getByRole('button', { name: /^Register$/i });
    fireEvent.click(registerTabBtn);

    expect(screen.getByText('Create a ReadQues Account')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('Choose a username')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('name@example.com')).toBeInTheDocument();
  });

  it('displays error alert when login fails', async () => {
    vi.mocked(api.auth.login).mockRejectedValueOnce(new Error('Invalid username or password'));

    render(
      <AuthModal
        isOpen={true}
        onClose={vi.fn()}
        initialTab="login"
      />
    );

    const usernameInput = screen.getByPlaceholderText('Enter your username or email');
    const passwordInput = screen.getByPlaceholderText('••••••••');

    fireEvent.change(usernameInput, { target: { value: 'wrong_user' } });
    fireEvent.change(passwordInput, { target: { value: 'wrong_pass' } });

    const submitBtn = screen.getByRole('button', { name: /Sign In/i });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(screen.getByText('Invalid username or password')).toBeInTheDocument();
    });
  });

  // ── 2. ProfilePage Progress & Stats UX ─────────────────────────────────────

  it('renders Sign In Required state when unauthenticated', () => {
    const handleOpenAuth = vi.fn();
    render(<ProfilePage onOpenAuth={handleOpenAuth} />);

    expect(screen.getByText('Sign In Required')).toBeInTheDocument();
    expect(
      screen.getByText(/Please log in to view your learning progress/i)
    ).toBeInTheDocument();

    const signInBtn = screen.getByRole('button', { name: /Sign In/i });
    fireEvent.click(signInBtn);
    expect(handleOpenAuth).toHaveBeenCalled();
  });

  it('renders learning stats and star balance when user is logged in, and hides password form initially', () => {
    authStore.setState({ user: mockUser });

    render(<ProfilePage />);

    expect(screen.getByText('ai_scholar')).toBeInTheDocument();
    expect(screen.getByText('scholar@example.com')).toBeInTheDocument();
    expect(screen.getByText(/42 Stars/i)).toBeInTheDocument();
    expect(screen.getByText('8')).toBeInTheDocument();
    expect(screen.getByText('50')).toBeInTheDocument();
    expect(screen.getByText('90%')).toBeInTheDocument();
    expect(screen.getByText(/5 Days/i)).toBeInTheDocument();

    // Settings button is present
    expect(screen.getByRole('button', { name: /Settings/i })).toBeInTheDocument();

    // Password change inputs are NOT exposed openly
    expect(screen.queryByPlaceholderText('Enter current password')).not.toBeInTheDocument();
    expect(screen.queryByPlaceholderText('Enter new password')).not.toBeInTheDocument();
  });

  it('opens Settings view when clicking Settings button, allowing password updates and closing', async () => {
    authStore.setState({ user: mockUser });
    const handleToast = vi.fn();

    vi.mocked(api.auth.changePassword).mockResolvedValueOnce({
      status: 'success',
      message: 'Password updated successfully',
    });

    render(<ProfilePage onShowToast={handleToast} />);

    // Click Settings button
    const settingsBtn = screen.getByRole('button', { name: /Settings/i });
    fireEvent.click(settingsBtn);

    // Settings view is visible
    expect(screen.getByText('Security & Password')).toBeInTheDocument();
    const currentPassInput = screen.getByPlaceholderText('Enter current password');
    const newPassInput = screen.getByPlaceholderText('Enter new password');
    const confirmPassInput = screen.getByPlaceholderText('Confirm new password');

    fireEvent.change(currentPassInput, { target: { value: 'OldPass123!' } });
    fireEvent.change(newPassInput, { target: { value: 'NewPass456!' } });
    fireEvent.change(confirmPassInput, { target: { value: 'NewPass456!' } });

    const submitBtn = screen.getByRole('button', { name: /Update Password/i });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(api.auth.changePassword).toHaveBeenCalledWith('OldPass123!', 'NewPass456!');
      expect(handleToast).toHaveBeenCalledWith('Password updated successfully', 'success');
    });

    // After success, closes settings back to overview
    expect(screen.queryByPlaceholderText('Enter current password')).not.toBeInTheDocument();
  });

  it('allows canceling Settings and returning to Overview', () => {
    authStore.setState({ user: mockUser });

    render(<ProfilePage />);

    // Click Settings
    fireEvent.click(screen.getByRole('button', { name: /Settings/i }));
    expect(screen.getByText('Security & Password')).toBeInTheDocument();

    // Click Cancel
    fireEvent.click(screen.getByRole('button', { name: /Cancel/i }));
    expect(screen.queryByText('Security & Password')).not.toBeInTheDocument();
  });
});
