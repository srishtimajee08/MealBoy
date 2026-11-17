/* Small page-specific enhancements. The server remains the source of truth. */
const csrfToken = document.querySelector('meta[name="csrf-token"]').content;

function applyTheme(theme) {
  document.documentElement.dataset.theme = theme;
  try {
    localStorage.setItem('mealboy-theme', theme);
  } catch {
    /* Storage may be disabled. */ }
}
try {
  applyTheme(localStorage.getItem('mealboy-theme') || 'light');
} catch {
  applyTheme('light');
}
document.querySelectorAll('.theme-toggle').forEach((button) => {
  button.addEventListener('click', () => {
    applyTheme(document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark');
  });
});

async function apiRequest(url, options) {
  const response = await fetch(url, {
    ...options,
    headers: {
      'X-CSRF-Token': csrfToken,
      ...options.headers
    },
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || 'The request could not be completed.');
  return data;
}

const foodSelect = document.querySelector('#food-select');
const gramsInput = document.querySelector('#grams');

function updateNutritionPreview() {
  const food = foodSelect?.selectedOptions[0];
  const grams = Number(gramsInput?.value);
  const source = document.querySelector('#nutrition-source');
  if (source) source.textContent = food?.dataset.source || '';
  for (const nutrient of ['calories', 'protein', 'carbs', 'fat']) {
    const output = document.querySelector(`#preview-${nutrient}`);
    if (output) output.textContent = food?.value && grams > 0 && grams <= 5000 ?
      (Number(food.dataset[nutrient]) * grams / 100).toFixed(1) : '—';
  }
}
foodSelect?.addEventListener('change', updateNutritionPreview);
gramsInput?.addEventListener('input', updateNutritionPreview);

const imageInput = document.querySelector('#food-image');
let previewUrl;
imageInput?.addEventListener('change', () => {
  const preview = document.querySelector('#image-preview');
  document.querySelector('#predictions').replaceChildren();
  document.querySelector('#prediction-status').textContent = '';
  if (previewUrl) URL.revokeObjectURL(previewUrl);
  const file = imageInput.files[0];
  preview.hidden = !file;
  if (file) {
    previewUrl = URL.createObjectURL(file);
    preview.src = previewUrl;
  }
});
document.querySelector('#image-form')?.addEventListener('submit', async (event) => {
  event.preventDefault();
  const button = event.currentTarget.querySelector('button');
  const status = document.querySelector('#prediction-status');
  const results = document.querySelector('#predictions');
  const file = imageInput.files[0];
  results.replaceChildren();
  if (!file || file.size > 8 * 1024 * 1024) {
    status.textContent = 'Choose an image under 8 MB.';
    return;
  }
  button.disabled = true;
  status.textContent = 'Looking at your photo… The first prediction may take a little longer.';
  try {
    const data = await apiRequest('/api/predict', {
      method: 'POST',
      body: new FormData(event.currentTarget)
    });
    status.textContent = data.uncertain ?
      'The model is uncertain. Check the suggestions or choose the food manually, then enter its weight.' :
      'Suggestions only. Confirm the food and enter its weight before saving.';
    for (const prediction of data.predictions) {
      const item = document.createElement('button');
      item.type = 'button';
      item.className = 'prediction';
      item.disabled = !prediction.supported;
      const confidence = (prediction.confidence * 100).toFixed(1);
      item.textContent = `${prediction.label.replaceAll('_', ' ')} · ${confidence}% model score${prediction.supported ? ' →' : ' · no nutrition entry'}`;
      item.addEventListener('click', () => {
        foodSelect.value = prediction.label;
        updateNutritionPreview();
        status.textContent = 'Food selected. Check the label and portion weight before saving.';
      });
      results.append(item);
    }
  } catch (error) {
    status.textContent = error.message;
  } finally {
    button.disabled = false;
  }
});

function appendMessage(role, text, sources = [], mode = '') {
  document.querySelector('.chat-welcome')?.remove();
  const article = document.createElement('article');
  article.className = `chat-message ${role}-message`;
  const label = document.createElement('small');
  label.textContent = role === 'user' ? 'YOU' : `MEALBOY · ${mode.toUpperCase()}`;
  const paragraph = document.createElement('p');
  paragraph.textContent = text; // Never interpret model output or personal notes as HTML.
  article.append(label, paragraph);
  if (sources.length) {
    const list = document.createElement('div');
    list.className = 'source-list';
    sources.forEach((source, index) => {
      const link = document.createElement('a');
      link.href = source.url;
      link.textContent = `[${index + 1}] ${source.title}`;
      list.append(link);
    });
    article.append(list);
  }
  const messages = document.querySelector('#chat-messages');
  messages.append(article);
  messages.scrollTop = messages.scrollHeight;
}

const chatForm = document.querySelector('#chat-form');
const chatInput = document.querySelector('#chat-input');
let chatPending = false;
chatForm?.addEventListener('submit', async (event) => {
  event.preventDefault();
  if (chatPending) return;
  const question = chatInput.value.trim();
  if (question.length < 3) return;
  const button = chatForm.querySelector('button');
  const status = document.querySelector('#chat-status');
  chatPending = true;
  button.disabled = true;
  chatInput.disabled = true;
  appendMessage('user', question);
  status.textContent = 'Finding relevant records in your workspace…';
  try {
    const data = await apiRequest('/api/chat', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        question
      }),
    });
    appendMessage('assistant', data.answer, data.sources, data.mode);
    status.textContent = data.notice;
    chatInput.value = '';
  } catch (error) {
    status.textContent = `${error.message} Your question is kept below so you can retry.`;
  } finally {
    chatPending = false;
    button.disabled = false;
    chatInput.disabled = false;
    chatInput.focus();
  }
});
document.querySelectorAll('[data-question]').forEach((button) => {
  button.addEventListener('click', () => {
    if (!chatPending) {
      chatInput.value = button.dataset.question;
      chatForm.requestSubmit();
    }
  });
});
document.querySelectorAll('.confirm-delete').forEach((form) => {
  form.addEventListener('submit', (event) => {
    if (!confirm('Remove this meal? Saved chat history will also be cleared to remove outdated answers.')) {
      event.preventDefault();
    }
  });
});
document.querySelector('.print-button')?.addEventListener('click', () => window.print());
