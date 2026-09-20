const PROJECTS = [
  {
    image: '/assets/img/portfolio/portfolio-2.webp',
    category: 'Django',
    title: 'LSuite (Ledger Suite)',
    text: 'Django-based financial management system that parses South African bank statements (Capitec, TymeBank) from PDFs and Gmail, auto-categorizes transactions, and syncs with ERPNext.',
    tags: ['Django', 'MySQL', 'ERPNext'],
    delay: 100,
  },
  {
    image: '/assets/img/portfolio/portfolio-4.webp',
    category: 'WhatsApp AI',
    title: 'BHKA Bot',
    text: 'WhatsApp AI chatbot for a South African credit rehabilitation company, powered by Groq (Llama 3) and the Meta WhatsApp Cloud API.',
    tags: ['Python', 'Groq', 'WhatsApp Cloud API'],
    delay: 200,
    featured: true,
  },
  {
    image: '/assets/img/portfolio/portfolio-8.webp',
    category: 'AI Assistant',
    title: 'Semblance',
    text: 'A Jarvis-inspired personal AI assistant with an animated React interface and a Claude-powered backend.',
    tags: ['React', 'Claude API'],
    delay: 300,
  },
  {
    image: '/assets/img/portfolio/portfolio-1.webp',
    category: 'Data',
    title: 'News-Forex Dataset',
    text: 'A US economic calendar dataset (2001–2026) enriched with technical indicators (RSI, MACD, Bollinger Bands) built for automated market analysis.',
    tags: ['Python', 'GitHub Actions', 'yfinance'],
    delay: 400,
  },
]

export default function Portfolio({ standalone = false }) {
  return (
    <section id="portfolio" className="portfolio section">

      <div className="container section-title" data-aos="fade-up">
        {standalone && <h1 className="visually-hidden">Portfolio</h1>}
        <h2>Portfolio</h2>
        <p>A few of the systems we've designed and shipped</p>
      </div>

      <div className="container" data-aos="fade-up" data-aos-delay="100">

        <div className="row g-4">
          {PROJECTS.map((project) => (
            <div className="col-lg-6 col-md-6" data-aos="fade-up" data-aos-delay={project.delay} key={project.title}>
              <div className={`project-card${project.featured ? ' featured' : ''}`}>
                <div className="image-wrapper">
                  <img src={project.image} alt="Project preview" className="img-fluid" loading="lazy" />
                  <div className="hover-overlay">
                    <div className="overlay-actions">
                      <a href={project.image} className="glightbox action-btn" data-gallery="portfolio">
                        <i className="bi bi-eye"></i>
                      </a>
                    </div>
                  </div>
                  <span className="category-badge">{project.category}</span>
                </div>
                <div className="project-info">
                  <h3>{project.title}</h3>
                  <p>{project.text}</p>
                  <div className="project-meta">
                    <div className="tech-tags">
                      {project.tags.map((tag) => (
                        <span key={tag}>{tag}</span>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>

      </div>

    </section>
  )
}
