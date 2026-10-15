import { Link } from 'react-router-dom'
import { SIGNUP_URL, SIGNUP_ENABLED } from '../lib/signup.js'
import '../styles/legal.css'
import FAQ from '../newCompanyFaq.json'

export default function NewCompanyPage() {
  const cta = SIGNUP_ENABLED
    ? <a href={SIGNUP_URL} className="nc-btn">Sign up free</a>
    : <Link to="/contact" className="nc-btn">Get in touch</Link>

  return (
    <section className="legal section">
      <div className="container legal-body">
        <h1>Just registered your company with CIPC? Here's what to do next</h1>
        <p className="legal-intro">
          Getting your registration certificate is the start, not the finish. This is a plain-language checklist for a
          new South African company — officers, SARS, banking and compliance — and then how to get your business online
          with a website and a professional email address.
        </p>
        <p className="legal-updated">Guidance only, not legal or tax advice. Rules and fees change — always confirm on cipc.co.za and sars.gov.za.</p>

        <h2>1. Officers and company records</h2>
        <ul>
          <li><strong>Appoint a public officer.</strong> Every company needs one for SARS — a person in South Africa who answers for the company on tax matters.</li>
          <li><strong>Keep your directors and officers up to date at CIPC.</strong> When a director is appointed, resigns or their details change, you notify CIPC (the CoR39 notice) — don't leave it until the annual return.</li>
          <li><strong>Check your Memorandum of Incorporation (MOI)</strong> and keep your share register and company records somewhere safe.</li>
        </ul>

        <h2>2. SARS and tax</h2>
        <ul>
          <li><strong>Link the company to your SARS eFiling profile</strong> as its registered representative so you can file and see what's due.</li>
          <li><strong>VAT:</strong> registration is compulsory once taxable turnover passes R1 million in 12 months, and optional from R50,000.</li>
          <li><strong>If you hire anyone:</strong> register for PAYE, UIF and SDL with SARS, and for COIDA with the Compensation Fund.</li>
          <li><strong>Company tax return and provisional tax</strong> are due every year — put the dates in your calendar early.</li>
        </ul>

        <h2>3. Banking and ongoing compliance</h2>
        <ul>
          <li><strong>Open a business bank account</strong> in the company's name — keep company and personal money separate from day one.</li>
          <li><strong>Beneficial ownership:</strong> companies must declare who ultimately owns and controls them to CIPC, and keep it current.</li>
          <li><strong>Annual return:</strong> file it with CIPC every year on or after the registration anniversary.</li>
          <li><strong>Selling to corporates or government?</strong> You'll usually need a B-BBEE affidavit, a tax compliance status, and a Central Supplier Database (CSD) registration.</li>
        </ul>

        <h2>4. Get your business online</h2>
        <p>
          Customers, banks and suppliers will look you up before they trust you. A real website and an email address on
          your own domain — <em>you@yourcompany.co.za</em>, not a Gmail address — make a new company look established.
        </p>
        <ul>
          <li><strong>Register your .co.za</strong> to match your company name before someone else does — it's included free with every Vicinic paid plan, while the name is available.</li>
          <li><strong>Get your site live in an afternoon:</strong> pick a template, edit the text, images and logo live — no developer needed.</li>
          <li><strong>Show your company details.</strong> If you sell online, South African law (the ECTA) expects your company name, registration number and physical address on your site.</li>
        </ul>

        <div className="nc-box">
          <h3>Starter Site — R250 once-off</h3>
          <p>
            One website template of your choice, up to 3 extra pages, email forwarding for up to 5 addresses, a free
            .co.za domain and no "Powered by" credit. No monthly bill. Need AI chat, WhatsApp, bookings or a blog? Growth
            Hub adds them.
          </p>
          <p>
            {cta} <Link to="/pricing" className="nc-link">See all plans</Link>
          </p>
          <p className="legal-updated">
            Vicinic builds and hosts your website. We don't register companies — for that use CIPC's BizPortal or your accountant.
          </p>
        </div>

        <h2>Frequently asked questions</h2>
        {FAQ.map((item) => (
          <details key={item.q} className="nc-faq">
            <summary>{item.q}</summary>
            <p>{item.a}</p>
          </details>
        ))}
      </div>
    </section>
  )
}
