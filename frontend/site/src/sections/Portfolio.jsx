const BLOG_URL = 'https://blog.vicinic.co.za'

const PROJECTS = [
  {
    image: '/assets/img/portfolio/editor.webp',
    category: 'Website Builder',
    title: 'Vicinic Site Editor',
    link: `${BLOG_URL}/project-vicinic-site-editor/`,
    text: 'Pick a template and edit it live: text, images, logo, links and the menu. Add your own pages, connect a free .co.za domain and email forwarding, then publish in one tap.',
    tags: ['Live editing', 'Free .co.za', 'No code'],
    delay: 100,
    featured: true,
  },
  {
    image: '/assets/img/portfolio/assistant.webp',
    category: 'AI Assistant',
    title: 'Website AI Chat & WhatsApp Bot',
    link: `${BLOG_URL}/project-website-ai-chat-whatsapp-bot/`,
    text: 'An AI assistant on every paid Vicinic site that answers visitors from your own content, plus a WhatsApp bot on your business number for Growth Hub and Business OS.',
    tags: ['AI', 'WhatsApp', '24/7 replies'],
    delay: 200,
  },
  {
    image: '/assets/img/portfolio/templify.webp',
    category: 'Developer Tool',
    title: 'Templify',
    link: `${BLOG_URL}/project-templify/`,
    text: 'Turns ready-made website designs into editable sites automatically. It\'s how new templates reach the Vicinic editor.',
    tags: ['Automation', 'Templates'],
    delay: 300,
  },
  {
    image: '/assets/img/portfolio/bloggify.webp',
    category: 'AI Content',
    title: 'Bloggify',
    link: `${BLOG_URL}/project-bloggify/`,
    text: 'An AI research blog that pulls fresh papers and news (arXiv, NASA, Google News and more), digests them with AI and drafts cited posts three times a week for review.',
    tags: ['AI', 'Research', 'Content'],
    delay: 400,
  },
  {
    image: '/assets/img/portfolio/bhka.webp',
    category: 'WhatsApp AI',
    title: 'BHKA Bot',
    link: `${BLOG_URL}/project-bhka-bot/`,
    text: 'WhatsApp AI chatbot for a South African credit rehabilitation company, answering and qualifying enquiries around the clock.',
    tags: ['AI', 'WhatsApp', 'Lead capture'],
    delay: 500,
  },
  {
    image: '/assets/img/portfolio/semblance.webp',
    category: 'AI Assistant',
    title: 'Semblance',
    link: `${BLOG_URL}/project-semblance/`,
    text: 'A Jarvis-inspired multi-agent personal AI assistant with long-term memory and an animated interface that evolves as it learns.',
    tags: ['AI', 'Memory', 'Agents'],
    delay: 600,
  },
]

export default function Portfolio({ standalone = false }) {
  return (
    <section id="portfolio" className="portfolio section">

      <div className="container section-title" data-aos="fade-up">
        {standalone && <h1 className="visually-hidden">Portfolio</h1>}
        <h2>Portfolio</h2>
        <p>Systems we've designed and shipped — including the tools behind Vicinic</p>
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
                      <a href={project.link} className="action-btn" aria-label={`Read about ${project.title}`}>
                        <i className="bi bi-arrow-up-right"></i>
                      </a>
                    </div>
                  </div>
                  <span className="category-badge">{project.category}</span>
                </div>
                <div className="project-info">
                  <h3><a href={project.link}>{project.title}</a></h3>
                  <p>{project.text}</p>
                  <div className="project-meta">
                    <a href={project.link} className="project-link">Read the story <i className="bi bi-arrow-right"></i></a>
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
