# zing-web

Source code for [zing.tharuk.pro](https://zing.tharuk.pro): the official website for zing tool.

## Structure

```
zing-web/
├── index.html              # Homepage
├── features.html           # Features page
├── downloads.html          # Downloads page
├── 404.html                # Error page
├── style.css               # Global styles
├── _nav.html               # Shared nav template
├── _footer.html            # Shared footer template
├── assets/
│   ├── img/                # Images & Screenshots
│   └── favicon.ico
├── docs/
│   ├── index.html          # Redirects to get-started.html
│   ├── get-started.html    # Static first page (not built)
│   ├── *.html              # Generated from markdown
│   └── content/            # Source markdown (deleted after build)
└── .github/
    ├── workflows/
    │   └── build-docs.yml  # CI: clone markdown → build → commit HTML
    └── scripts/
        └── build-docs.py   # Markdown → HTML converter
```
