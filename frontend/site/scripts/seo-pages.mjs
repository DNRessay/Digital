// Writes a copy of index.html per route with that page's title, description,
// canonical URL, social tags and visible fallback content, so crawlers that
// don't run JavaScript (Bing, DuckDuckGo, link previews) still see real text and
// internal links. Also generates sitemap.xml from src/seo.json. React replaces
// the fallback content when it mounts.
import { readFileSync, writeFileSync, copyFileSync } from 'node:fs'

const ORIGIN = 'https://vicinic.co.za'
const pages = JSON.parse(readFileSync('src/seo.json', 'utf8'))
const html = readFileSync('dist/index.html', 'utf8')
const esc = (s) => s.replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/</g, '&lt;')
const today = new Date().toISOString().slice(0, 10)
const LEGAL = new Set(['/terms', '/privacy', '/cookies'])

const h1Of = (path, { title, h1 }) =>
  h1 || (path === '/' ? 'Websites & WhatsApp Systems for Small Businesses in South Africa' : title.split(/ [|—] /)[0])

const nav = Object.entries(pages)
  .filter(([p]) => !LEGAL.has(p))
  .map(([p, m]) => `<li><a href="${p}">${esc(h1Of(p, m))}</a></li>`)
  .join('')

function fallback(path, meta) {
  return (
    `<main id="seo-static"><h1>${esc(h1Of(path, meta))}</h1><p>${esc(meta.description)}</p>` +
    `<nav aria-label="Main"><ul>${nav}<li><a href="https://blog.vicinic.co.za/">Blog</a></li></ul></nav></main>`
  )
}

function render(path, meta) {
  const { title, description, jsonld } = meta
  const url = `${ORIGIN}${path === '/' ? '/' : path}`
  const extra = [
    `<meta name="robots" content="index,follow,max-image-preview:large,max-snippet:-1">`,
    `<meta property="og:locale" content="en_ZA">`,
    `<meta property="og:site_name" content="Vicinic">`,
    `<meta name="twitter:title" content="${esc(title)}">`,
    `<meta name="twitter:description" content="${esc(description)}">`,
    `<link rel="alternate" hreflang="en-ZA" href="${url}">`,
    `<link rel="alternate" type="application/rss+xml" title="Vicinic Blog" href="https://blog.vicinic.co.za/feeds/all.rss.xml">`,
    jsonld ? `<script type="application/ld+json">${JSON.stringify(jsonld)}</script>` : '',
  ].join('\n')
  return html
    .replace(/<title>[^<]*<\/title>/, `<title>${esc(title)}</title>`)
    .replace(/(<meta name="description" content=")[^"]*/, `$1${esc(description)}`)
    .replace(/(<link rel="canonical" href=")[^"]*/, `$1${url}`)
    .replace(/(<meta property="og:title" content=")[^"]*/, `$1${esc(title)}`)
    .replace(/(<meta property="og:description" content=")[^"]*/, `$1${esc(description)}`)
    .replace(/(<meta property="og:url" content=")[^"]*/, `$1${url}`)
    .replace('<div id="root"></div>', () => `<div id="root">${fallback(path, meta)}</div>`)
    .replace('</head>', () => `${extra}\n</head>`)
}

for (const [path, meta] of Object.entries(pages)) {
  writeFileSync(path === '/' ? 'dist/index.html' : `dist${path}.html`, render(path, meta))
}
copyFileSync('dist/index.html', 'dist/404.html')

const urls = Object.keys(pages)
  .map((p) => {
    const priority = p === '/' ? '1.0' : LEGAL.has(p) ? '0.2' : '0.7'
    return `  <url><loc>${ORIGIN}${p}</loc><lastmod>${today}</lastmod><priority>${priority}</priority></url>`
  })
  .join('\n')
writeFileSync(
  'dist/sitemap.xml',
  `<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n${urls}\n</urlset>\n`,
)
