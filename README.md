# nenquen.is-a.dev

My personal website. A Windows 7 desktop in the browser, built with
[7.css](https://khang-nd.github.io/7.css/) and plain HTML/CSS/JS.

## Live site

<https://nenquen.is-a.dev>

## Features

- Windows 7 styled windows with Aero glass frames, Gentoo-purple theme
- Hash routing (`#about`, `#discord`) so views are linkable
- SmartScreen-style "Windows Security" dialog before leaving the site
  (a joke, obviously — it blocks nothing and can be closed with Cancel,
  the overlay, or `Escape`)
- Live Discord server stats fetched from the public invite API
- Click/warning sound effects
- No build step, no framework, no JavaScript dependencies

## Local preview

`file://` blocks fonts, audio and `fetch`, so use a local server:

```bash
npx serve .
# or: python -m http.server 8000
```

Then open <http://localhost:8000>.

## Project structure

```
index.html          single page, all four windows
404.html            themed 404
CNAME               custom domain for GitHub Pages
assets/css/style.css
assets/js/script.js
assets/images/
assets/sounds/
```

## Deploying

Pushes to `main` are served automatically by GitHub Pages.

After changing `assets/css/style.css` or `assets/js/script.js`, bump the
`?v=` query string in `index.html` so browsers pick up the new files.

## Credits

- [7.css](https://github.com/khang-nd/7.css) by KhangND — MIT licensed
- Fonts are system fonts (Segoe UI / Tahoma); nothing is bundled