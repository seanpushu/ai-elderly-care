'use strict';

const form        = document.querySelector('#contact-form');
const nameInput   = document.querySelector('#name');
const phoneInput  = document.querySelector('#phone');
const statusText  = document.querySelector('#contact-status');
const callLink    = document.querySelector('#call');
const noContactHint = document.querySelector('#no-contact-hint');

const STORAGE_KEY = 'pausepal.trusted-contact.v1';

// Basic phone validation: allows +, digits, spaces, hyphens, parentheses.
// Must have at least 7 digits total.
function isValidPhone(phone) {
  return (
    /^\+?[\d ()-]{7,30}$/.test(phone) &&
    phone.replace(/\D/g, '').length >= 7
  );
}

function showHint() {
  if (noContactHint) noContactHint.hidden = false;
}

function hideHint() {
  if (noContactHint) noContactHint.hidden = true;
}

// Render a saved contact: update the status line and tel link.
// Returns true if the contact is valid and was displayed, false otherwise.
function displayContact(name, phone) {
  // Reset call link first
  callLink.hidden = true;
  callLink.removeAttribute('href');
  callLink.textContent = '';

  if (!name || !isValidPhone(phone)) {
    return false;
  }

  // Update inputs to reflect stored values
  nameInput.value = name;
  phoneInput.value = phone;

  // Status line — always shows readable name and number
  statusText.textContent = `Saved contact: ${name} — ${phone}`;

  // Tel link — user must click; we never auto-dial
  const digitsOnly = phone.replace(/[ ()-]/g, '');
  callLink.href = 'tel:' + digitsOnly;
  callLink.textContent = `Open dialer for ${name} (${phone})`;
  callLink.hidden = false;

  hideHint();
  return true;
}

// ── On page load: restore from sessionStorage ─────────────────────────────
try {
  const raw = sessionStorage.getItem(STORAGE_KEY);
  const saved = raw ? JSON.parse(raw) : null;
  if (saved && saved.name && saved.phone) {
    const restored = displayContact(String(saved.name), String(saved.phone));
    if (!restored) showHint();
  } else {
    showHint();
  }
} catch {
  // sessionStorage unavailable (e.g. private browsing restriction)
  statusText.textContent =
    'Session storage is unavailable. You can still follow the verification steps above.';
  showHint();
}

// ── Save contact ─────────────────────────────────────────────────────────
form.addEventListener('submit', (event) => {
  event.preventDefault();

  const name  = nameInput.value.trim();
  const phone = phoneInput.value.trim();

  if (!name) {
    statusText.textContent = 'Please enter a contact name.';
    nameInput.focus();
    return;
  }

  if (!isValidPhone(phone)) {
    statusText.textContent =
      'Please enter a valid phone number (at least 7 digits). Use a number you already trust.';
    phoneInput.focus();
    return;
  }

  const displayed = displayContact(name, phone);
  if (!displayed) {
    statusText.textContent = 'Enter a name and a valid phone number you already trust.';
    return;
  }

  try {
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify({ name, phone }));
  } catch {
    statusText.textContent =
      'Contact is shown above, but could not be saved for this session.';
  }
});

// ── Clear contact ─────────────────────────────────────────────────────────
document.querySelector('#clear').addEventListener('click', () => {
  form.reset();
  callLink.hidden = true;
  callLink.removeAttribute('href');
  callLink.textContent = '';

  try {
    sessionStorage.removeItem(STORAGE_KEY);
    statusText.textContent = 'Contact cleared.';
  } catch {
    statusText.textContent =
      'The form was cleared, but stored data could not be removed. Close this tab to end the session.';
  }

  showHint();
});

// ── Copy verification message ─────────────────────────────────────────────
document.querySelector('#copy').addEventListener('click', async () => {
  const copyStatus = document.querySelector('#copy-status');
  const scriptText = document.querySelector('#script').textContent.trim();

  try {
    await navigator.clipboard.writeText(scriptText);
    copyStatus.textContent = 'Copied. Send it yourself using a channel you already trust.';
  } catch {
    copyStatus.textContent =
      'Copy is unavailable in this browser. Please select the message above and copy it manually.';
  }
});
