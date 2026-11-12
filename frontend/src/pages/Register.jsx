
import { useState } from 'react';
import { registerUser } from '../services/authService';
import './Register.css';

const initialForm = {
  fullName: '',
  email: '',
  password: '',
  confirmPassword: '',
  acceptTerms: false,
};

export default function Register() {
  const [form, setForm] = useState(initialForm);
  const [errors, setErrors] = useState({});
  const [message, setMessage] = useState('');
  const [messageType, setMessageType] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const rules = [
    { label: '8+ characters', valid: form.password.length >= 8 },
    { label: 'One uppercase letter', valid: /[A-Z]/.test(form.password) },
    { label: 'One number', valid: /\d/.test(form.password) },
    { label: '12+ characters (optional)', valid: form.password.length >= 12 },
  ];

  const strength = rules.filter(rule => rule.valid).length;

  const matches =
    form.confirmPassword.length > 0 &&
    form.password === form.confirmPassword;

  function updateField(event) {
    const { name, type, checked, value } = event.target;

    setForm(previous => ({
      ...previous,
      [name]: type === 'checkbox' ? checked : value,
    }));

    setErrors(previous => ({
      ...previous,
      [name]: '',
    }));

    setMessage('');
    setMessageType('');
  }

  async function handleSubmit(event) {
    event.preventDefault();

    if (isSubmitting) return;

    const next = {};

    if (!form.fullName.trim()) {
      next.fullName = 'Enter your full name.';
    }

    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email.trim())) {
      next.email = 'Enter a valid email address.';
    }

    if (!rules.slice(0, 3).every(rule => rule.valid)) {
      next.password = 'Meet the required password rules.';
    }

    if (form.password.length > 128) {
      next.password = 'Password must not exceed 128 characters.';
    }

    if (!matches) {
      next.confirmPassword = 'Passwords must match.';
    }

    if (!form.acceptTerms) {
      next.acceptTerms = 'Please agree to the Terms of Use and acknowledge the Privacy Policy.';
    }

    setErrors(next);

    if (Object.keys(next).length > 0) {
      setMessage('');
      return;
    }

    setIsSubmitting(true);
    setMessage('');
    setMessageType('');

    try {
      await registerUser(form);

      setMessage('Account created successfully! You can now log in.');
      setMessageType('success');

      setForm(initialForm);
      setErrors({});
    } catch (error) {
      setMessage(error.message || 'Registration failed. Please try again.');
      setMessageType('error');
    } finally {
      setIsSubmitting(false);
    }
  }

  function field(name, label, placeholder, type = 'text', autoComplete = name) {
    return (
      <div className="register-field">
        <label htmlFor={name}>{label}</label>

        <input
          id={name}
          name={name}
          type={type}
          autoComplete={autoComplete}
          placeholder={placeholder}
          value={form[name]}
          onChange={updateField}
          disabled={isSubmitting}
          required
          aria-invalid={Boolean(errors[name])}
          aria-describedby={errors[name] ? `${name}-error` : undefined}
        />

        {errors[name] && (
          <p className="field-error" id={`${name}-error`}>
            {errors[name]}
          </p>
        )}
      </div>
    );
  }

  return (
    <main className="register-page">
      <section className="register-intro" aria-labelledby="onboarding-title">
        <a className="register-brand" href="/" aria-label="NexaSense home">
          <span className="brand-icon" aria-hidden="true">
            <svg viewBox="0 0 24 24" fill="none">
              <path
                d="M4 12h4l2-6 4 12 2-6h4"
                stroke="currentColor"
                strokeWidth="1.8"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </span>

          <span>
            <strong>NexaSense</strong>
            <small>Inspection &amp; Monitoring</small>
          </span>
        </a>

        <p className="eyebrow onboarding-eyebrow">
          ONBOARDING · 3 STEPS
        </p>

        <h1 id="onboarding-title">
          Set up your<br />
          workspace in<br />
          <span>three</span> steps.
        </h1>

        <p className="intro-description">
          Create your account, register your equipment and run your first
          inspection — all from one place.
        </p>

        <ol className="onboarding-steps">
          <li className="current-step" aria-current="step">
            <span className="step-number">01</span>
            <div>
              <strong>Create your account</strong>
              <p>You are here — takes under a minute</p>
            </div>
          </li>

          <li>
            <span className="step-number">02</span>
            <div>
              <strong>Register your equipment</strong>
              <p>AC units, electrical panels, pumps, ventilation</p>
            </div>
          </li>

          <li>
            <span className="step-number">03</span>
            <div>
              <strong>Run your first inspection</strong>
              <p>Watch readings live and get a health result</p>
            </div>
          </li>
        </ol>

        <footer>© 2026 NexaSense Technologies</footer>
      </section>

      <section className="register-card" aria-labelledby="register-title">
        <p className="eyebrow">STEP 1 OF 3</p>

        <header className="register-heading">
          <h2 id="register-title">Create your account</h2>
          <p>All fields are required.</p>
        </header>

        <form onSubmit={handleSubmit} noValidate>
          {field('fullName', 'Full name', 'Enter your full name', 'text', 'name')}

          {field('email', 'Email', 'you@example.com', 'email', 'email')}

          <div className="password-fields">
            <div className="register-field">
              <label htmlFor="password">
                Password{' '}
                <span
                  className={`password-strength ${
                    strength >= 3 ? 'valid' : ''
                  }`}
                >
                  {form.password
                    ? ['Weak', 'Weak', 'Fair', 'Strong', 'Strong'][strength]
                    : ''}
                </span>
              </label>

              <input
                id="password"
                name="password"
                type="password"
                autoComplete="new-password"
                placeholder="Create a password"
                value={form.password}
                onChange={updateField}
                disabled={isSubmitting}
                required
                aria-invalid={Boolean(errors.password)}
                aria-describedby="password-requirements password-error"
              />

              <div className="strength-meter" aria-hidden="true">
                {rules.map((rule, index) => (
                  <span
                    key={rule.label}
                    className={index < strength ? 'filled' : ''}
                  />
                ))}
              </div>

              <p className="field-error" id="password-error">
                {errors.password}
              </p>
            </div>

            <div className="register-field">
              <label htmlFor="confirmPassword">
                Confirm password{' '}
                <span className="valid">
                  {matches ? '✓ Matches' : ''}
                </span>
              </label>

              <input
                id="confirmPassword"
                name="confirmPassword"
                type="password"
                autoComplete="new-password"
                placeholder="Repeat password"
                value={form.confirmPassword}
                onChange={updateField}
                disabled={isSubmitting}
                required
                aria-invalid={Boolean(errors.confirmPassword)}
                aria-describedby="confirm-error"
              />

              <p className="field-error" id="confirm-error">
                {errors.confirmPassword}
              </p>
            </div>
          </div>

          <ul
            className="password-requirements"
            id="password-requirements"
          >
            {rules.map(rule => (
              <li
                key={rule.label}
                className={rule.valid ? 'valid' : ''}
              >
                <span aria-hidden="true">
                  {rule.valid ? '✓' : '○'}
                </span>
                {rule.label}
              </li>
            ))}
          </ul>

          <div className="terms-label">
            <input id="acceptTerms" name="acceptTerms" type="checkbox"
              checked={form.acceptTerms} onChange={updateField} disabled={isSubmitting}
              required aria-invalid={Boolean(errors.acceptTerms)}
              aria-describedby={errors.acceptTerms ? 'terms-error' : undefined} />
            <label htmlFor="acceptTerms">
              I agree to the{' '}
              <a href="/terms" target="_blank" rel="noopener noreferrer" aria-label="Terms of Use (opens in a new tab)">Terms of Use</a>
              {' '}and acknowledge the{' '}
              <a href="/privacy" target="_blank" rel="noopener noreferrer" aria-label="Privacy Policy (opens in a new tab)">Privacy Policy</a>.
            </label>
          </div>
          {errors.acceptTerms && <p className="field-error terms-error" id="terms-error">{errors.acceptTerms}</p>}

          <button
            className="register-submit"
            type="submit"
            disabled={isSubmitting}
          >
            {isSubmitting ? 'Creating account...' : 'Create account'}
            <span aria-hidden="true">→</span>
          </button>

          <div className="form-feedback" aria-live="polite">
            {Object.values(errors).some(Boolean) && (
              <p className="submit-error">
                Fix the highlighted fields to continue.
              </p>
            )}

            {message && (
              <div
                className={
                  messageType === 'error'
                    ? 'submit-error'
                    : 'form-message'
                }
                role={messageType === 'error' ? 'alert' : 'status'}
              >
                {messageType === 'success' ? (
                  <>
                    <span className="success-icon" aria-hidden="true">✓</span>
                    <div>
                      <strong>Account created successfully!</strong>
                      <p>You can now log in to your account.</p>
                    </div>
                  </>
                ) : message}
              </div>
            )}
          </div>
        </form>

        <p className="login-prompt">
          Already have an account? <a href="/login">Log in</a>
        </p>
      </section>
    </main>
  );
}
