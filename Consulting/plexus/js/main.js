/**
 * PLEXUS TECH - JAVASCRIPT PRINCIPAL
 */

(function () {
  'use strict';

  /* ============================================
     ANIMACIÓN DE NÚMEROS (CONTADOR)
     ============================================ */
  function animateCounter(el, target, duration) {
    let start = 0;
    const step = Math.ceil(target / (duration / 16));
    const timer = setInterval(() => {
      start += step;
      if (start >= target) {
        el.textContent = target;
        clearInterval(timer);
      } else {
        el.textContent = start;
      }
    }, 16);
  }

  /* ============================================
     HEADER: SCROLL EFFECT
     ============================================ */
  const header = document.querySelector('.site-header');
  if (header) {
    window.addEventListener('scroll', () => {
      header.classList.toggle('scrolled', window.scrollY > 40);
    }, { passive: true });
  }

  /* ============================================
     HAMBURGER MENU (MÓVIL)
     ============================================ */
  const hamburger = document.querySelector('.hamburger');
  const mainNav = document.querySelector('.main-nav');

  if (hamburger && mainNav) {
    hamburger.addEventListener('click', () => {
      const isOpen = mainNav.classList.toggle('open');
      hamburger.setAttribute('aria-expanded', isOpen);
      hamburger.classList.toggle('active', isOpen);
    });

    // Cerrar al hacer click en un enlace
    mainNav.querySelectorAll('a').forEach(link => {
      link.addEventListener('click', () => {
        mainNav.classList.remove('open');
        hamburger.classList.remove('active');
      });
    });
  }

  /* ============================================
     ROTACIÓN DE PALABRAS EN EL HERO
     ============================================ */
  const words = ['INNOVACIÓN', 'TECNOLOGÍA', 'TALENTO', 'PLEXUS'];
  const wordColors = ['#00aeef', '#4db8ff', '#7dd3fc', '#ffffff'];
  let currentWordIndex = 0;
  const rotatingEl = document.querySelector('.rotating-word');

  if (rotatingEl) {
    function rotateWord() {
      rotatingEl.style.opacity = '0';
      rotatingEl.style.transform = 'translateY(-15px)';
      
      setTimeout(() => {
        currentWordIndex = (currentWordIndex + 1) % words.length;
        rotatingEl.textContent = 'Somos ' + words[currentWordIndex];
        rotatingEl.style.color = wordColors[currentWordIndex];
        rotatingEl.style.opacity = '1';
        rotatingEl.style.transform = 'translateY(0)';
      }, 300);
    }

    rotatingEl.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
    setInterval(rotateWord, 2800);
  }

  /* ============================================
     INTERSECTION OBSERVER: ANIMACIONES DE ENTRADA
     ============================================ */
  const fadeEls = document.querySelectorAll('.fade-in');
  if (fadeEls.length) {
    const observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.classList.add('visible');
          observer.unobserve(entry.target);
        }
      });
    }, { threshold: 0.15 });

    fadeEls.forEach(el => observer.observe(el));
  }

  /* ============================================
     INTERSECTION OBSERVER: CONTADORES
     ============================================ */
  const counters = document.querySelectorAll('[data-count]');
  if (counters.length) {
    const counterObserver = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          const target = parseInt(entry.target.getAttribute('data-count'), 10);
          animateCounter(entry.target, target, 1500);
          counterObserver.unobserve(entry.target);
        }
      });
    }, { threshold: 0.5 });

    counters.forEach(el => counterObserver.observe(el));
  }

  /* ============================================
     SMOOTH SCROLL PARA ANCLAS
     ============================================ */
  document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
      const href = this.getAttribute('href');
      if (href === '#') return;
      const target = document.querySelector(href);
      if (target) {
        e.preventDefault();
        const offset = 80;
        const top = target.getBoundingClientRect().top + window.scrollY - offset;
        window.scrollTo({ top, behavior: 'smooth' });
      }
    });
  });

  /* ============================================
     HAMBURGER ANIMACIÓN CSS (via JS)
     ============================================ */
  const style = document.createElement('style');
  style.textContent = `
    .hamburger.active span:nth-child(1) {
      transform: translateY(7px) rotate(45deg);
    }
    .hamburger.active span:nth-child(2) {
      opacity: 0;
      transform: scaleX(0);
    }
    .hamburger.active span:nth-child(3) {
      transform: translateY(-7px) rotate(-45deg);
    }
  `;
  document.head.appendChild(style);

})();
