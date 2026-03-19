// ── Scroll reveal
const revEls = document.querySelectorAll('.reveal');
if (revEls.length) {
  const obs = new IntersectionObserver((entries) => {
    entries.forEach((e, i) => {
      if (e.isIntersecting) {
        setTimeout(() => e.target.classList.add('in'), i * 70);
        obs.unobserve(e.target);
      }
    });
  }, { threshold: 0.08, rootMargin: '0px 0px -30px 0px' });
  revEls.forEach(el => obs.observe(el));
}

// ── Sticky shadow
const nav = document.querySelector('.navbar');
if (nav) {
  window.addEventListener('scroll', () => {
    nav.style.boxShadow = window.scrollY > 10
      ? '0 4px 20px rgba(0,0,0,.15)'
      : '0 2px 8px rgba(0,0,0,.08)';
  }, { passive: true });
}

// ── Mobile menu toggle
const hamburger = document.querySelector('.hamburger');
const mobileMenu = document.querySelector('.mobile-menu');
if (hamburger && mobileMenu) {
  hamburger.addEventListener('click', () => {
    mobileMenu.classList.toggle('open');
    hamburger.textContent = mobileMenu.classList.contains('open') ? '✕' : '☰';
  });
}

// ── Phone input filter
document.querySelectorAll('.phone-input').forEach(el => {
  el.addEventListener('input', function () {
    this.value = this.value.replace(/[^0-9+\s]/g, '');
  });
});
