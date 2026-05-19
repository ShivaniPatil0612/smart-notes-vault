/* Smart Notes Vault — Main JS */

'use strict';

// Auto-dismiss flash messages after 5 seconds
document.querySelectorAll('.flash').forEach(f => {
  setTimeout(() => {
    f.style.transition = 'opacity .4s, transform .4s';
    f.style.opacity = '0';
    f.style.transform = 'translateX(20px)';
    setTimeout(() => f.remove(), 400);
  }, 5000);
});

// Toggle password visibility
function togglePw(id) {
  const input = document.getElementById(id);
  input.type = input.type === 'password' ? 'text' : 'password';
}

// Prevent double-form submission
document.querySelectorAll('form').forEach(form => {
  form.addEventListener('submit', function () {
    const btn = form.querySelector('[type="submit"]');
    if (btn) {
      setTimeout(() => {
        btn.disabled = true;
        btn.style.opacity = '.6';
      }, 0);
    }
  });
});
