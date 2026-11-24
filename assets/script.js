const navToggle = document.getElementById("navToggle");
const navMenu = document.getElementById("navMenu");
const navLinks = document.querySelectorAll(".nav-menu a");
const heroTitle = document.getElementById("hero-title");
const navTitle = document.getElementById("navTitle");
const pages = document.querySelectorAll(".hero, .section");
const dotButtons = document.querySelectorAll(".dots button");
const dotIndicator = document.getElementById("dotIndicator");

const NAV_HEIGHT = 65;
const pageOffsets = [];
let heroTitleBottom = 0;
let dotStep = 0;
let maxScroll = 0;

function measure() {
  const y = window.scrollY;
  pageOffsets.length = 0;
  pages.forEach((page) => {
    pageOffsets.push(page.getBoundingClientRect().top + y - NAV_HEIGHT);
  });
  heroTitleBottom = heroTitle.getBoundingClientRect().bottom + y;
  dotStep = dotButtons.length > 1 ? dotButtons[1].offsetTop - dotButtons[0].offsetTop : 0;
  maxScroll = document.documentElement.scrollHeight - window.innerHeight;
  if (dotIndex >= 0) setDot(dotIndex, true);
}

function refresh() {
  measure();
  render();
}

let navTitleVisible = null;

function updateNavTitle() {
  const visible = heroTitleBottom - window.scrollY <= NAV_HEIGHT;
  if (visible === navTitleVisible) return;
  navTitleVisible = visible;
  navTitle.classList.toggle("visible", visible);
}

function currentPageIndex() {
  const y = window.scrollY + 25;
  let index = 0;
  for (let i = 0; i < pageOffsets.length; i++) {
    if (pageOffsets[i] <= y) index = i;
  }
  return index;
}

let activeLinkId = null;

function updateActiveLink() {
  const index = window.scrollY >= maxScroll - 2 ? pageOffsets.length - 1 : currentPageIndex();
  const id = pages[index] ? pages[index].id : "";
  if (id === activeLinkId) return;
  activeLinkId = id;
  navLinks.forEach((link) => {
    link.classList.toggle("active", link.getAttribute("href") === `#${id}`);
  });
}

let dotIndex = -1;

function setDot(index, force) {
  if (!force && index === dotIndex) return;
  dotIndex = index;
  dotIndicator.style.transform = `translate3d(0, ${(index * dotStep).toFixed(2)}px, 0)`;
}

function updateDots() {
  const y = window.scrollY;
  let index = 0;
  while (index < pageOffsets.length - 1 && y >= pageOffsets[index + 1]) index++;
  setDot(index);
}

let renderQueued = false;
let animating = false;
let activeIndex = 0;
let activeProgress = 0;
let goalIndex = 0;
let goalProgress = 0;

function positionOf(y) {
  let index = 0;
  while (index < pageOffsets.length - 1 && y >= pageOffsets[index + 1]) index++;
  const start = pageOffsets[index];
  const end = index < pageOffsets.length - 1 ? pageOffsets[index + 1] : Math.max(start, maxScroll);
  return { index, progress: end > start ? Math.min(Math.max((y - start) / (end - start), 0), 1) : 0 };
}

function trackPosition() {
  const position = positionOf(window.scrollY);
  activeIndex = position.index;
  activeProgress = position.progress;
}

function rememberGoal(target) {
  const position = positionOf(target);
  goalIndex = position.index;
  goalProgress = position.progress;
}

function render() {
  renderQueued = false;
  trackPosition();
  updateNavTitle();
  updateActiveLink();
  if (!animating) updateDots();
}

function scheduleRender() {
  if (renderQueued) return;
  renderQueued = true;
  requestAnimationFrame(render);
}

let animationFrame = 0;
let animationToken = 0;

function animateScrollTo(target) {
  const start = window.scrollY;
  const distance = target - start;
  const token = ++animationToken;
  rememberGoal(target);

  if (animationFrame) {
    cancelAnimationFrame(animationFrame);
    animationFrame = 0;
  }
  if (Math.abs(distance) < 1) {
    animating = false;
    window.scrollTo(0, target);
    render();
    return;
  }

  animating = true;
  const duration = 450;
  const startTime = performance.now();
  const ease = (t) => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2);

  const step = (now) => {
    if (token !== animationToken) return;
    const t = Math.min((now - startTime) / duration, 1);
    window.scrollTo(0, start + distance * ease(t));
    render();
    if (t < 1) {
      animationFrame = requestAnimationFrame(step);
    } else {
      animationFrame = 0;
      animating = false;
      render();
    }
  };

  animationFrame = requestAnimationFrame(step);
}

function goToPage(index) {
  if (index < 0 || index >= pageOffsets.length) return;
  setDot(index);
  animateScrollTo(Math.max(0, pageOffsets[index]));
}

navToggle.addEventListener("click", () => {
  const open = navMenu.classList.toggle("open");
  navToggle.classList.toggle("active", open);
  navToggle.setAttribute("aria-expanded", open);
});

document.addEventListener("click", (event) => {
  const link = event.target.closest('a[href^="#"]');
  if (!link) return;
  const hash = link.getAttribute("href");
  if (hash.length < 2) return;

  const target = hash === "#top" ? pages[0] : document.querySelector(hash);
  const index = [...pages].indexOf(target);
  if (index === -1) return;

  event.preventDefault();
  navMenu.classList.remove("open");
  navToggle.classList.remove("active");
  navToggle.setAttribute("aria-expanded", "false");
  goToPage(index);
});

let wheelLock = false;

window.addEventListener("wheel", (event) => {
  if (event.ctrlKey) return;
  event.preventDefault();
  if (wheelLock || Math.abs(event.deltaY) < 4) return;

  const index = currentPageIndex();
  const pageTop = pageOffsets[index];
  const viewHeight = window.innerHeight - NAV_HEIGHT;
  const pageEnd = index < pageOffsets.length - 1 ? pageOffsets[index + 1] : maxScroll + viewHeight;
  const pageBottom = Math.min(pageEnd - viewHeight, maxScroll);

  if (event.deltaY > 0 && window.scrollY < pageBottom - 8) {
    wheelLock = true;
    animateScrollTo(pageBottom);
    setTimeout(() => { wheelLock = false; }, 700);
    return;
  }
  if (event.deltaY < 0 && window.scrollY > pageTop + 8) {
    wheelLock = true;
    animateScrollTo(pageTop);
    setTimeout(() => { wheelLock = false; }, 700);
    return;
  }

  const next = index + (event.deltaY > 0 ? 1 : -1);
  if (next < 0 || next >= pages.length) return;

  wheelLock = true;
  goToPage(next);
  setTimeout(() => { wheelLock = false; }, 700);
}, { passive: false });

let touchStartY = null;
let touchLock = false;
let touchMode = "jump";

window.addEventListener("touchstart", (event) => {
  if (event.touches.length !== 1) return;
  touchStartY = event.touches[0].clientY;
  const page = pages[currentPageIndex()];
  touchMode = page.getBoundingClientRect().height > window.innerHeight - NAV_HEIGHT + 2 ? "native" : "jump";
}, { passive: true });

window.addEventListener("touchmove", (event) => {
  if (touchStartY === null || touchMode !== "jump") return;
  if (!event.cancelable) return;
  event.preventDefault();
}, { passive: false });

window.addEventListener("touchend", (event) => {
  if (touchStartY === null) return;
  const delta = event.changedTouches[0].clientY - touchStartY;
  touchStartY = null;

  if (touchMode !== "jump" || touchLock) return;

  if (Math.abs(delta) < 40) {
    handleResize();
    return;
  }

  const next = currentPageIndex() + (delta < 0 ? 1 : -1);
  if (next < 0 || next >= pages.length) return;

  touchLock = true;
  goToPage(next);
  setTimeout(() => { touchLock = false; }, 550);
}, { passive: true });

window.addEventListener("touchcancel", () => {
  if (touchStartY === null) return;
  touchStartY = null;
  if (touchMode === "jump" && !touchLock) handleResize();
}, { passive: true });

dotButtons.forEach((button) => {
  button.addEventListener("click", () => goToPage(Number(button.dataset.page)));
});

document.addEventListener("copy", (event) => event.preventDefault());

let resizeQueued = false;
let resizing = false;

window.addEventListener("scroll", () => {
  if (animating || resizing) return;
  scheduleRender();
}, { passive: true });

function handleResize() {
  if (resizeQueued) return;
  resizeQueued = true;
  resizing = true;

  requestAnimationFrame(() => {
    resizeQueued = false;

    if (touchStartY !== null) {
      measure();
      resizing = false;
      return;
    }

    const index = animating ? goalIndex : activeIndex;
    const progress = animating ? goalProgress : activeProgress;

    if (animating) {
      animationToken++;
      if (animationFrame) cancelAnimationFrame(animationFrame);
      animationFrame = 0;
      animating = false;
    }

    measure();

    const start = pageOffsets[index];
    const end = index < pageOffsets.length - 1 ? pageOffsets[index + 1] : Math.max(start, maxScroll);
    const target = Math.max(0, Math.min(start + progress * (end - start), maxScroll));
    window.scrollTo(0, target);
    resizing = false;
    render();
  });
}

window.addEventListener("resize", handleResize);
window.addEventListener("load", refresh);

if (document.fonts && document.fonts.ready) {
  document.fonts.ready.then(refresh);
}

refresh();

const dotsElement = document.getElementById("dots");
setTimeout(() => dotsElement.classList.add("ready"), 0);

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
