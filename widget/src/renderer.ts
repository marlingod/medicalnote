import type {
  WidgetSummaryData,
  WidgetBrandConfig,
  ThemeVariables,
} from "./types";
import { getTranslation } from "./i18n";
import { generateThemeCSS } from "./theme";
import { WIDGET_STYLES } from "./styles";

/** Escape HTML to prevent XSS */
function escapeHTML(str: string): string {
  const div = document.createElement("div");
  div.appendChild(document.createTextNode(str));
  return div.innerHTML;
}

/** Shared CSP meta tag for all iframe pages */
function cspMetaTag(): string {
  return `<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; img-src https: data:; script-src 'self'; connect-src 'none'; font-src 'none'; frame-src 'none';">`;
}

/** Shared <head> block */
function headBlock(themeVars: ThemeVariables, lang: "en" | "es"): string {
  return `<!DOCTYPE html>
<html lang="${lang}">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  ${cspMetaTag()}
  <style>${generateThemeCSS(themeVars)}\n${WIDGET_STYLES}</style>
</head>`;
}

export function renderSummaryHTML(
  summary: WidgetSummaryData,
  brandConfig: WidgetBrandConfig,
  themeVars: ThemeVariables,
  lang: "en" | "es"
): string {
  const t = getTranslation(lang);
  const summaryText =
    lang === "es" && summary.summary_es
      ? summary.summary_es
      : summary.summary_en;

  const logoHTML = brandConfig.logo_url
    ? `<img class="mn-logo" src="${escapeHTML(brandConfig.logo_url)}" alt="${escapeHTML(brandConfig.practice_name)} logo" />`
    : "";

  const termsHTML =
    summary.medical_terms_explained.length > 0
      ? `<div class="mn-terms">
          <h3 class="mn-terms-heading">${escapeHTML(t.medical_terms_heading)}</h3>
          <dl class="mn-terms-list">
            ${summary.medical_terms_explained
              .map(
                (term) =>
                  `<dt class="mn-term">${escapeHTML(term.term)}</dt>
                   <dd class="mn-term-explanation">${escapeHTML(term.explanation)}</dd>`
              )
              .join("")}
          </dl>
        </div>`
      : "";

  const langToggleHTML = `<div class="mn-lang-toggle">
    <button class="mn-lang-btn ${lang === "en" ? "mn-lang-active" : ""}" data-lang="en">${t.lang_en}</button>
    <button class="mn-lang-btn ${lang === "es" ? "mn-lang-active" : ""}" data-lang="es">${t.lang_es}</button>
  </div>`;

  return `${headBlock(themeVars, lang)}
<body class="mn-body">
  <div class="mn-container">
    <header class="mn-header">
      ${logoHTML}
      <h1 class="mn-practice-name">${escapeHTML(brandConfig.practice_name)}</h1>
      ${langToggleHTML}
    </header>

    <div class="mn-meta">
      <span class="mn-meta-item"><strong>${escapeHTML(t.subtitle_date)}:</strong> ${escapeHTML(summary.encounter_date)}</span>
      <span class="mn-meta-item"><strong>${escapeHTML(t.subtitle_doctor)}:</strong> ${escapeHTML(summary.doctor_name)}</span>
    </div>

    <main class="mn-summary">
      <h2 class="mn-summary-heading">${escapeHTML(t.summary_heading)}</h2>
      <div class="mn-summary-text">${escapeHTML(summaryText)}</div>
    </main>

    ${termsHTML}

    <div class="mn-disclaimer">
      <strong>${escapeHTML(t.disclaimer_label)}:</strong>
      ${escapeHTML(summary.disclaimer_text)}
    </div>

    <footer class="mn-footer">
      <span class="mn-powered-by">${escapeHTML(t.powered_by)}</span>
    </footer>
  </div>

  <script>
    document.querySelectorAll('.mn-lang-btn').forEach(function(btn) {
      btn.addEventListener('click', function() {
        var lang = btn.getAttribute('data-lang');
        window.parent.postMessage({ ns: 'medicalnote-widget', type: 'SET_LANG', lang: lang }, '*');
      });
    });

    // Notify parent of content height for auto-resize
    var height = document.querySelector('.mn-container').scrollHeight;
    window.parent.postMessage({ ns: 'medicalnote-widget', type: 'RESIZE', height: height }, '*');
  </script>
</body>
</html>`;
}

export function renderLoadingHTML(
  themeVars: ThemeVariables,
  lang: "en" | "es"
): string {
  const t = getTranslation(lang);
  return `${headBlock(themeVars, lang)}
<body class="mn-body">
  <div class="mn-container mn-loading">
    <div class="mn-spinner"></div>
    <p class="mn-loading-text">${escapeHTML(t.loading)}</p>
  </div>
</body>
</html>`;
}

export function renderErrorHTML(
  errorCode: string,
  themeVars: ThemeVariables,
  lang: "en" | "es"
): string {
  const t = getTranslation(lang);
  let message: string;
  switch (errorCode) {
    case "TOKEN_EXPIRED":
      message = t.error_expired;
      break;
    case "NOT_FOUND":
      message = t.error_not_found;
      break;
    case "NETWORK_ERROR":
      message = t.error_network;
      break;
    default:
      message = t.error_generic;
      break;
  }
  return `${headBlock(themeVars, lang)}
<body class="mn-body">
  <div class="mn-container mn-error">
    <div class="mn-error-icon">&#9888;</div>
    <p class="mn-error-text">${escapeHTML(message)}</p>
  </div>
</body>
</html>`;
}

export function renderTokenFormHTML(
  brandConfig: WidgetBrandConfig,
  themeVars: ThemeVariables,
  lang: "en" | "es"
): string {
  const t = getTranslation(lang);
  const logoHTML = brandConfig.logo_url
    ? `<img class="mn-logo" src="${escapeHTML(brandConfig.logo_url)}" alt="${escapeHTML(brandConfig.practice_name)} logo" />`
    : "";

  return `${headBlock(themeVars, lang)}
<body class="mn-body">
  <div class="mn-container mn-token-form">
    <header class="mn-header">
      ${logoHTML}
      <h1 class="mn-practice-name">${escapeHTML(brandConfig.practice_name)}</h1>
    </header>
    <form class="mn-form" id="mn-token-form">
      <label class="mn-label" for="mn-token-input">${escapeHTML(t.enter_token_label)}</label>
      <input class="mn-input" id="mn-token-input" type="text" placeholder="${escapeHTML(t.enter_token_placeholder)}" autocomplete="off" required />
      <button class="mn-submit-btn" type="submit">${escapeHTML(t.submit_button)}</button>
    </form>
    <footer class="mn-footer">
      <span class="mn-powered-by">${escapeHTML(t.powered_by)}</span>
    </footer>
  </div>

  <script>
    document.getElementById('mn-token-form').addEventListener('submit', function(e) {
      e.preventDefault();
      var token = document.getElementById('mn-token-input').value.trim();
      if (token) {
        window.parent.postMessage({ ns: 'medicalnote-widget', type: 'SET_TOKEN', token: token }, '*');
      }
    });
  </script>
</body>
</html>`;
}
