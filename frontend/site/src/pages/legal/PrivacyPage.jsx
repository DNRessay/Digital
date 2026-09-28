import { Link } from 'react-router-dom'
import LegalPage, { COMPANY } from './LegalPage.jsx'

export default function PrivacyPage() {
  return (
    <LegalPage
      title="Privacy Policy"
      intro={`This policy explains how ${COMPANY.name} ("Vicinic") collects, uses and protects personal information, in line with the Protection of Personal Information Act, 2013 (POPIA). We don't sell your personal information.`}
    >
      <h2>1. Who we are</h2>
      <p>
        The responsible party is {COMPANY.name} (Reg. No. {COMPANY.reg}), {COMPANY.address}. Our Information Officer is{' '}
        {COMPANY.officer}, reachable at <a href={`mailto:${COMPANY.email}`}>{COMPANY.email}</a>.
      </p>

      <h2>2. What we collect</h2>
      <ul>
        <li><strong>Account details:</strong> name, username, email address and password (stored securely hashed).</li>
        <li><strong>Profile details:</strong> legal or business name, phone number and address — needed to register domains in your name.</li>
        <li><strong>Your site content:</strong> text, images, links, menus and settings you add in the editor.</li>
        <li><strong>Payment records:</strong> plan, amounts and payment status from PayFast. We never receive your card details.</li>
        <li><strong>Messages:</strong> what you send through our contact form, email, the AI chat or WhatsApp.</li>
        <li>
          <strong>Usage data (with your consent):</strong> pages you visit, what you click, referring site, browser and
          device type, and approximate location from your IP address, collected with cookies. See our{' '}
          <Link to="/cookies">Cookie Policy</Link>.
        </li>
        <li><strong>Technical logs:</strong> IP address and request details kept briefly for security and troubleshooting.</li>
      </ul>

      <h2>3. Why we use it</h2>
      <ul>
        <li>To create and run your account and site, and to provide the features of your plan (contract).</li>
        <li>To register and manage domains and email forwarding for you (contract).</li>
        <li>To process payments and keep financial records (contract and legal obligation).</li>
        <li>To answer your questions and give support (contract and legitimate interest).</li>
        <li>To understand how our site is used and improve it — only if you accept analytics cookies (consent).</li>
        <li>To keep the platform secure and prevent abuse (legitimate interest).</li>
        <li>To send you marketing only if you've opted in; you can opt out at any time (consent).</li>
      </ul>

      <h2>4. Who we share it with</h2>
      <p>We only share what's needed, with service providers (operators) bound to protect it:</p>
      <ul>
        <li>Amazon Web Services (hosting, Ireland) and Neon (database, United States)</li>
        <li>Cloudflare (network, security, DNS and email routing)</li>
        <li>PayFast (payments)</li>
        <li>Domain registrars and registries such as ZADNA/ZACR for .co.za — registrant details may appear in public domain records as the registry requires</li>
        <li>Meta (WhatsApp) and Groq (AI replies), when you use those features</li>
        <li>Web3Forms (delivering contact-form messages)</li>
      </ul>
      <p>
        Some of these providers store information outside South Africa. We only use providers that are subject to
        adequate data-protection laws or agreements, as POPIA section 72 requires. We may also disclose information
        where the law requires it.
      </p>

      <h2>5. Visitors to our customers' sites</h2>
      <p>
        When a Vicinic customer's site collects information from its visitors (for example, a contact form, chat or
        visit statistics), that customer is the responsible party and Vicinic processes the information on their behalf
        as an operator. Contact the business directly about those records.
      </p>

      <h2>6. How long we keep it</h2>
      <p>
        We keep account and site information while your account is active. When you delete your site or account we
        delete it, except records we must keep by law (such as financial records, kept for 5 years). Technical logs are
        kept for about 7 days, and analytics data for up to 26 months.
      </p>

      <h2>7. Security</h2>
      <p>
        We use encrypted connections, hashed passwords, access controls and reputable providers. If a breach affects
        your personal information, we'll notify you and the Information Regulator as POPIA requires.
      </p>

      <h2>8. Your rights</h2>
      <ul>
        <li>Ask what personal information we hold about you and get a copy</li>
        <li>Ask us to correct or delete it</li>
        <li>Object to processing, or withdraw consent (for example, to analytics cookies) at any time</li>
        <li>Opt out of marketing</li>
      </ul>
      <p>
        Email <a href={`mailto:${COMPANY.email}`}>{COMPANY.email}</a> to use any of these rights. If you're not happy with
        our response, you can complain to the Information Regulator (South Africa) at{' '}
        <a href="https://inforegulator.org.za" target="_blank" rel="noreferrer">inforegulator.org.za</a>.
      </p>

      <h2>9. Children</h2>
      <p>
        Vicinic accounts are for adults. School packages may process learner information on a school's instructions,
        under a separate data-protection agreement with that school.
      </p>

      <h2>10. Changes</h2>
      <p>We'll update the date above when this policy changes and tell you about material changes.</p>
    </LegalPage>
  )
}
