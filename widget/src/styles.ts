/**
 * All widget CSS, inlined into the iframe <style> tag.
 * Uses CSS custom properties defined by the theme engine.
 * All classes prefixed with mn- to avoid collisions.
 */
export const WIDGET_STYLES = `
/* Reset */
*, *::before, *::after {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

.mn-body {
  font-family: var(--mn-font-family);
  background-color: var(--mn-bg-color);
  color: var(--mn-text-color);
  line-height: 1.6;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

.mn-container {
  max-width: 640px;
  margin: 0 auto;
  padding: 24px 20px;
}

/* Header */
.mn-header {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
  margin-bottom: 20px;
  padding-bottom: 16px;
  border-bottom: 1px solid var(--mn-border-color);
}

.mn-logo {
  height: 40px;
  width: auto;
  max-width: 120px;
  object-fit: contain;
}

.mn-practice-name {
  font-size: 18px;
  font-weight: 600;
  flex: 1;
  min-width: 0;
}

/* Language toggle */
.mn-lang-toggle {
  display: flex;
  gap: 4px;
  margin-left: auto;
}

.mn-lang-btn {
  background: transparent;
  border: 1px solid var(--mn-border-color);
  border-radius: 4px;
  padding: 4px 10px;
  font-size: 13px;
  cursor: pointer;
  color: var(--mn-text-secondary);
  transition: all 0.15s ease;
}

.mn-lang-btn:hover {
  border-color: var(--mn-brand-color);
  color: var(--mn-brand-color);
}

.mn-lang-active {
  background-color: var(--mn-brand-color);
  border-color: var(--mn-brand-color);
  color: #FFFFFF;
}

.mn-lang-active:hover {
  color: #FFFFFF;
}

/* Meta info (date, doctor) */
.mn-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  margin-bottom: 20px;
  font-size: 14px;
  color: var(--mn-text-secondary);
}

.mn-meta-item strong {
  color: var(--mn-text-color);
}

/* Summary */
.mn-summary {
  margin-bottom: 24px;
}

.mn-summary-heading {
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 12px;
  color: var(--mn-brand-color);
}

.mn-summary-text {
  font-size: 15px;
  line-height: 1.7;
  white-space: pre-wrap;
}

/* Medical terms */
.mn-terms {
  background-color: var(--mn-surface-color);
  border: 1px solid var(--mn-border-color);
  border-radius: 8px;
  padding: 16px;
  margin-bottom: 20px;
}

.mn-terms-heading {
  font-size: 14px;
  font-weight: 600;
  margin-bottom: 12px;
  color: var(--mn-brand-color);
}

.mn-terms-list {
  display: grid;
  gap: 8px;
}

.mn-term {
  font-weight: 600;
  font-size: 14px;
  color: var(--mn-text-color);
}

.mn-term-explanation {
  font-size: 13px;
  color: var(--mn-text-secondary);
  margin-left: 0;
  margin-bottom: 8px;
  padding-left: 12px;
  border-left: 2px solid var(--mn-brand-color);
}

/* Disclaimer */
.mn-disclaimer {
  background-color: var(--mn-surface-color);
  border: 1px solid var(--mn-border-color);
  border-radius: 8px;
  padding: 12px 16px;
  font-size: 13px;
  color: var(--mn-text-secondary);
  margin-bottom: 20px;
}

.mn-disclaimer strong {
  color: var(--mn-text-color);
}

/* Footer */
.mn-footer {
  text-align: center;
  padding-top: 16px;
  border-top: 1px solid var(--mn-border-color);
}

.mn-powered-by {
  font-size: 12px;
  color: var(--mn-text-secondary);
}

/* Loading state */
.mn-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 200px;
  gap: 16px;
}

.mn-spinner {
  width: 32px;
  height: 32px;
  border: 3px solid var(--mn-border-color);
  border-top-color: var(--mn-brand-color);
  border-radius: 50%;
  animation: mn-spin 0.8s linear infinite;
}

@keyframes mn-spin {
  to { transform: rotate(360deg); }
}

.mn-loading-text {
  font-size: 14px;
  color: var(--mn-text-secondary);
}

/* Error state */
.mn-error {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 200px;
  gap: 12px;
  text-align: center;
}

.mn-error-icon {
  font-size: 36px;
  color: var(--mn-text-secondary);
}

.mn-error-text {
  font-size: 14px;
  color: var(--mn-text-secondary);
  max-width: 400px;
}

/* Token form */
.mn-token-form .mn-form {
  max-width: 360px;
  margin: 24px auto;
}

.mn-label {
  display: block;
  font-size: 14px;
  font-weight: 600;
  margin-bottom: 8px;
}

.mn-input {
  display: block;
  width: 100%;
  padding: 10px 12px;
  border: 1px solid var(--mn-border-color);
  border-radius: 6px;
  font-size: 15px;
  background-color: var(--mn-bg-color);
  color: var(--mn-text-color);
  margin-bottom: 12px;
  outline: none;
  transition: border-color 0.15s ease;
}

.mn-input:focus {
  border-color: var(--mn-brand-color);
  box-shadow: 0 0 0 2px color-mix(in srgb, var(--mn-brand-color) 20%, transparent);
}

.mn-submit-btn {
  display: block;
  width: 100%;
  padding: 10px 16px;
  background-color: var(--mn-brand-color);
  color: #FFFFFF;
  border: none;
  border-radius: 6px;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  transition: opacity 0.15s ease;
}

.mn-submit-btn:hover {
  opacity: 0.9;
}

/* Responsive */
@media (max-width: 480px) {
  .mn-container {
    padding: 16px 12px;
  }

  .mn-header {
    flex-direction: column;
    align-items: flex-start;
  }

  .mn-lang-toggle {
    margin-left: 0;
  }

  .mn-meta {
    flex-direction: column;
    gap: 4px;
  }
}
`;
