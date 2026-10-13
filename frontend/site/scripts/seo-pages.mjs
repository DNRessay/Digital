// Writes a copy of index.html per route with that page's title, description
// and canonical URL, so crawlers that don't run JavaScript still see them.
import { readFileSync, writeFileSync, copyFileSync } from 'node:fs'

const ORIGIN = 'https://vicinic.co.za'
const pages = JSON.parse(readFileSync('src/seo.json', 'utf8'))
const html = readFileSync('dist/index.html', 'utf8')
const esc = (s) => s.replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/</g, '&lt;')

function render(path, { title, description, jsonld }) {
  const url = `${ORIGIN}${path}`
  return html
    .replace(/<title>[^<]*<\/title>/, `<title>${esc(title)}</title>`)
    .replace(/(<meta name="description" content=")[^"]*/, `$1${esc(description)}`)
    .replace(/(<link rel="canonical" href=")[^"]*/, `$1${url}`)
    .replace(/(<meta property="og:title" content=")[^"]*/, `$1${esc(title)}`)
    .replace(/(<meta property="og:description" content=")[^"]*/, `$1${esc(description)}`)
    .replace(/(<meta property="og:url" content=")[^"]*/, `$1${url}`)
    .replace('</head>', () => (jsonld ? `<script type="application/ld+json">${JSON.stringify(jsonld)}</script>\n</head>` : '</head>'))
}

for (const [path, meta] of Object.entries(pages)) {
  writeFileSync(path === '/' ? 'dist/index.html' : `dist${path}.html`, render(path, meta))
}
copyFileSync('dist/index.html', 'dist/404.html')
