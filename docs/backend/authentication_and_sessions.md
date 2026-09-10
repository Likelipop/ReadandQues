# Authentication, Security & Session Management

The **Authentication Subsystem** is housed in the `ReadAndQues/accounts/` app. It provides secure user registration, multi-factor anti-bot defenses, dual-identifier login (username or email), 6-digit email OTP verification, session lifecycle handling, and gamified user profile initialization.

---

## 1. What It Does (Business & Security Overview)

* **Dual-Identifier Authentication:** Users can log in using either their username or email address seamlessly.
* **Anti-Bot Defense:** Protects registration and login endpoints from brute-force bots and automated scrapers using temporal and spatial traps.
* **Email Verification (2FA / OTP):** Inactive accounts must verify a 6-digit one-time passcode sent to their email before gaining access.
* **Gamified Profile Initialization:** Automatically provisions a `UserProfile` with starting star balances, streak counters, and reading analytics.
* **Secure Session Handling:** Manages standard Django HTTP-only session cookies and maintains session state across password updates.

---

## 2. Codebase Organization

| File Path | Role & Technical Responsibility |
| :--- | :--- |
| `ReadAndQues/accounts/backends.py` | `UsernameOrEmailBackend`: Custom authentication backend with timing-attack prevention. |
| `ReadAndQues/accounts/views.py` | Controllers for registration, OTP verification, login, logout, and password change. |
| `ReadAndQues/accounts/models.py` | `UserProfile` (relational gamification profile) and `EmailVerification` (OTP storage). |
| `ReadAndQues/accounts/emails.py` | Email delivery adapter using the Resend API with local console fallback. |
| `ReadAndQues/accounts/urls.py` | Route mapping for auth endpoints (`/login/`, `/register/`, `/register/verify/`, `/profile/`). |

---

## 3. How It Works (Architectural & Technical Deep Dive)

### A. The Registration & 2FA Flow

```mermaid
sequenceDiagram
    participant User as User / Client
    participant View as accounts.views.register_view
    participant DB as PostgreSQL (User & Verification)
    participant Resend as Resend Email Service

    User->>View: POST /register/ (username, email, password)
    Note over View: 1. Anti-Bot Checks (Rate limit < 3s, Honeypot)<br/>2. Field validations (regex, length, existence)
    
    View->>DB: User.objects.create_user(is_active=False)
    View->>DB: EmailVerification.objects.create(code, expires_at=now + 5m)
    View->>Resend: send_verification_email(email, code)
    View-->>User: Redirect to /register/verify/ (Session: verification_user_id)
    
    User->>View: POST /register/verify/ (code)
    Note over View: Verify OTP & check expiration (expires_at > now)
    View->>DB: user.is_active = True; user.save()
    View->>DB: verification.delete()
    Note over View: login(request, user)
    View-->>User: Redirect to / (Home) with active session
```

---

### B. Anti-Bot Defense Mechanisms

The registration and login views implement two proactive defense traps:

#### 1. The Temporal Trap (Rate Limiting)
Automated bot scripts submit forms in milliseconds. The view enforces a 3-second human delay:
```python
last_submit = request.session.get("last_submit_at")
now = time.time()
if last_submit and now - last_submit < 3:
    errors["general"] = "Request processed too fast. Please try again in a moment."
else:
    request.session["last_submit_at"] = now
```

#### 2. The Spatial Trap (Honeypot)
The HTML form contains a hidden input field: `<input type="text" name="website" style="display:none">`. 
Human users never see or fill this field. If a bot parses the DOM and populates `request.POST["website"]`, the request is silently rejected immediately.

---

### C. Custom Authentication Backend (`UsernameOrEmailBackend`)

Defined in `accounts/backends.py`, this backend replaces Django's default `ModelBackend`:

```python
class UsernameOrEmailBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None:
            username = kwargs.get(User.USERNAME_FIELD)
        try:
            # Case-insensitive match on either username or email
            user = User.objects.get(
                Q(username__iexact=username) | Q(email__iexact=username)
            )
        except User.DoesNotExist:
            # Mitigation against Timing Attacks:
            # Execute a dummy password hash so response time matches a valid user lookup
            User().set_password(password)
            return None
```

> [!TIP]
> **Timing Attack Mitigation:**
> If a user does not exist, standard databases return immediately, whereas checking a password for a valid user takes ~100ms due to PBKDF2/Argon2 hashing. By invoking `User().set_password(password)` on non-existent accounts, attackers cannot determine whether an email is registered by timing the server's HTTP response.

---

### D. Email OTP Verification Engine (`EmailVerification`)

The `EmailVerification` model is linked One-to-One with `User`:
```python
class EmailVerification(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="verification")
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    def is_expired(self):
        return timezone.now() > self.expires_at
```

* **TTL:** Passcodes expire after exactly **5 minutes**.
* **Resend Cooldown:** Users cannot spam the resend endpoint. `resend_verification_view` checks:
  ```python
  if (timezone.now() - verification.created_at).total_seconds() < 60:
      # Block request until 60 seconds have elapsed
  ```
* **Email Delivery:** Handled via `accounts/emails.py`. If `RESEND_API_KEY` is not set in environment variables, it gracefully logs the 6-digit code to the terminal console during local development.

---

### E. Session Management & UserProfile Lifecycle

1. **Session Cookies:** Standard Django session middleware stores session keys in signed, HTTP-only cookies (`sessionid`).
2. **Password Changes:** `profile_view` handles password modifications using `PasswordChangeForm`. To prevent the user from being logged out immediately upon password hash mutation, it executes:
   ```python
   update_session_auth_hash(request, user)
   ```
3. **Automated UserProfile Creation:** Handled via Django Signals in `accounts/models.py`:
   ```python
   @receiver(post_save, sender=User)
   def create_user_profile(sender, instance, created, **kwargs):
       if created:
           default_stars = 100 if settings.DEBUG else 10
           UserProfile.objects.create(user=instance, stars=default_stars)
   ```
4. **Streak & Login Tracking:** When a user logs in, the `user_logged_in` signal fires:
   * If `last_login_date == yesterday`, `streak` increments by 1.
   * If `last_login_date < yesterday`, `streak` resets to 1.
   * `login_days_count` increments.
