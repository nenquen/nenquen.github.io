const navToggle = document.getElementById("navToggle");
const navMenu = document.getElementById("navMenu");
const sections = document.querySelectorAll("section[id]");
const navLinks = document.querySelectorAll(".nav-menu a");
const heroTitle = document.getElementById("hero-title");
const navTitle = document.getElementById("navTitle");
const pages = document.querySelectorAll(".hero, .section");
const dotButtons = document.querySelectorAll(".dots button");
const dotIndicator = document.getElementById("dotIndicator");

navToggle.addEventListener("click", () => {
  const open = navMenu.classList.toggle("open");
  navToggle.classList.toggle("active", open);
  navToggle.setAttribute("aria-expanded", open);
});

function updateActiveLink() {
  let current = null;
  sections.forEach((section) => {
    if (section.getBoundingClientRect().top <= 90) current = section.id;
  });
  if (window.innerHeight + window.scrollY >= document.documentElement.scrollHeight - 2) {
    current = sections[sections.length - 1].id;
  }
  navLinks.forEach((link) => {
    link.classList.toggle("active", link.getAttribute("href") === `#${current}`);
  });
}

function updateNavTitle() {
  navTitle.classList.toggle("visible", heroTitle.getBoundingClientRect().bottom <= 65);
}

function updateDots() {
  const step = dotButtons.length > 1 ? dotButtons[1].offsetTop - dotButtons[0].offsetTop : 0;
  const tops = [...pages].map((page) => page.getBoundingClientRect().top + window.scrollY - 65);
  const y = window.scrollY;

  let index = 0;
  while (index < tops.length - 1 && y >= tops[index + 1]) index++;

  const start = tops[index];
  const end = index < tops.length - 1 ? tops[index + 1] : start;
  const progress = end > start ? Math.min(Math.max((y - start) / (end - start), 0), 1) : 0;

  dotIndicator.style.transform = `translateY(${(index + progress) * step}px)`;
}

function onScroll() {
  updateNavTitle();
  updateActiveLink();
  updateDots();
}

let animationToken = 0;
let animationTimer = null;

function animateScrollTo(target) {
  const start = window.scrollY;
  const distance = target - start;
  if (Math.abs(distance) < 1) return;

  if (animationTimer) clearInterval(animationTimer);
  const token = ++animationToken;
  const duration = 450;
  const startTime = performance.now();
  const ease = (t) => 1 - Math.pow(1 - t, 3);

  animationTimer = setInterval(() => {
    if (token !== animationToken) return;
    const t = Math.min((performance.now() - startTime) / duration, 1);
    window.scrollTo(0, start + distance * ease(t));
    updateDots();
    if (t >= 1) {
      clearInterval(animationTimer);
      animationTimer = null;
    }
  }, 16);
}

function goToPage(index) {
  const page = pages[index];
  if (!page) return;
  const top = page.getBoundingClientRect().top + window.scrollY - 65;
  animateScrollTo(Math.max(0, top));
  onScroll();
}

function currentPageIndex() {
  let index = 0;
  pages.forEach((page, i) => {
    if (page.getBoundingClientRect().top <= 90) index = i;
  });
  return index;
}

navMenu.querySelectorAll("a").forEach((link) => {
  link.addEventListener("click", (event) => {
    navMenu.classList.remove("open");
    navToggle.classList.remove("active");
    navToggle.setAttribute("aria-expanded", "false");
    const hash = link.getAttribute("href");
    if (hash.startsWith("#") && hash !== "#top") {
      const target = document.querySelector(hash);
      const index = [...pages].indexOf(target);
      if (index !== -1) {
        event.preventDefault();
        goToPage(index);
      }
    }
  });
});

navTitle.addEventListener("click", (event) => {
  event.preventDefault();
  goToPage(0);
});

let wheelLock = false;

window.addEventListener("wheel", (event) => {
  if (event.ctrlKey) return;
  event.preventDefault();
  if (wheelLock || Math.abs(event.deltaY) < 4) return;

  const next = currentPageIndex() + (event.deltaY > 0 ? 1 : -1);
  if (next < 0 || next >= pages.length) return;

  wheelLock = true;
  goToPage(next);
  setTimeout(() => { wheelLock = false; }, 800);
}, { passive: false });

let touchStartY = null;
let touchLock = false;
let touchMode = "jump";

window.addEventListener("touchstart", (event) => {
  if (event.touches.length !== 1) return;
  touchStartY = event.touches[0].clientY;
  const page = pages[currentPageIndex()];
  touchMode = page.getBoundingClientRect().height > window.innerHeight - 65 + 2 ? "native" : "jump";
}, { passive: true });

window.addEventListener("touchmove", (event) => {
  if (touchStartY === null || touchMode !== "jump") return;
  if (!event.cancelable) return;
  if (Math.abs(event.touches[0].clientY - touchStartY) > 8) event.preventDefault();
}, { passive: false });

window.addEventListener("touchend", (event) => {
  if (touchStartY === null) return;
  const delta = event.changedTouches[0].clientY - touchStartY;
  touchStartY = null;
  if (touchMode !== "jump" || touchLock || Math.abs(delta) < 40) return;

  const next = currentPageIndex() + (delta < 0 ? 1 : -1);
  if (next < 0 || next >= pages.length) return;

  touchLock = true;
  goToPage(next);
  setTimeout(() => { touchLock = false; }, 550);
}, { passive: true });

dotButtons.forEach((button) => {
  button.addEventListener("click", () => goToPage(Number(button.dataset.page)));
});

document.addEventListener("copy", (event) => event.preventDefault());

window.addEventListener("scroll", onScroll, { passive: true });
window.addEventListener("resize", onScroll);
onScroll();

const titleText = "welcome to peace";
const width = titleText.length;
const padded = " ".repeat(width) + titleText + " ".repeat(width);
const totalSteps = padded.length - width + 1;
let titleStep = 0;
let titlePause = 0;

setInterval(() => {
  if (titlePause > 0) {
    titlePause--;
    document.title = "\u200b";
    return;
  }
  const frame = padded.slice(titleStep, titleStep + width);
  document.title = frame.trim() ? frame : "\u200b";
  titleStep++;
  if (titleStep >= totalSteps) {
    titleStep = 0;
    titlePause = 7;
  }
}, 140);
