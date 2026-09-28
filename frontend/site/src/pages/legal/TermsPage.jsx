import { Link } from 'react-router-dom'
import LegalPage, { COMPANY } from './LegalPage.jsx'

export default function TermsPage() {
  return (
    <LegalPage
      title="Terms of Service"
      intro={`These terms are an agreement between you and ${COMPANY.name} ("Vicinic", "we", "us") for the use of vicinic.co.za, the Vicinic customer portal and editor, and every site and service we host for you. You must accept them, together with our Privacy Policy, before you can create an account.`}
    >
      <h2>1. Your account</h2>
      <ul>
        <li>You must be 18 or older, or have authority to act for the business you sign up for.</li>
        <li>
          If your business is not registered with the CIPC, we treat you as a <strong>sole trader</strong> — or, where
          two or more people run it together, as <strong>partners</strong> — and the person or people who sign up are
          personally our client and responsible under these terms. You can move the account to a registered company
          later by contacting us.
        </li>
        <li>Give us accurate details and keep them up to date — domain registries require the real owner's details.</li>
        <li>Keep your password safe. You're responsible for what happens under your account.</li>
      </ul>

      <h2>2. Free accounts</h2>
      <p>
        You can sign up, pick a template and build your site for free. Free sites show a "Powered by Vicinic" credit
        and don't include paid features such as extra pages, image editing, the AI assistant or an included domain.
      </p>

      <h2>3. Paid plans and payment</h2>
      <ul>
        <li>
          Plans, prices and what each includes are shown on our <Link to="/pricing">Pricing</Link> page. Starter Site is a
          once-off payment. Growth Hub and Business OS have a once-off setup fee plus a monthly fee.
        </li>
        <li>Payments are processed by PayFast. We never see or store your card details.</li>
        <li>Monthly plans renew automatically each month until you cancel.</li>
        <li>
          We may change prices for new purchases at any time. For an existing monthly plan we'll give you at least 30
          days' notice before a price change applies to you.
        </li>
        <li>
          Once-off payments and setup fees are non-refundable once your site or setup has been delivered, except where
          the Consumer Protection Act requires otherwise.
        </li>
      </ul>

      <h2>4. Your included .co.za domain</h2>
      <ul>
        <li>
          Each new purchase of a paid plan includes <strong>one (1) free .co.za domain</strong>, provided the name you
          want is <strong>available</strong> when you claim it and the registry accepts the registration.
        </li>
        <li>
          If the name you want is taken or can't be registered, choose another available name — we can't guarantee any
          particular name.
        </li>
        <li>
          <strong>Renewing</strong> your plan (for example, your next monthly payment) does <strong>not</strong> give
          you another free domain.
        </li>
        <li>
          If you cancel your plan and later buy a plan again, that new purchase includes one free .co.za again, on the
          same conditions (only while the name is available).
        </li>
        <li>
          The included domain covers its first registration period. It has no cash value, can't be exchanged for other
          domain endings, and doesn't carry over if unclaimed when your plan ends.
        </li>
        <li>
          Domains are registered in your name as the owner. Renewal of the domain after its first registration period
          is charged at the price shown in your portal at the time.
        </li>
      </ul>

      <h2>5. Cancelling</h2>
      <ul>
        <li>You can cancel a monthly plan at any time from your portal. It stays active until the end of the period you've paid for.</li>
        <li>After cancelling, your site returns to the free tier. Ask us if you need an export of your content.</li>
        <li>You can delete your site or account at any time; deletion is permanent.</li>
      </ul>

      <h2>6. Your content and acceptable use</h2>
      <ul>
        <li>You own the text, images and other content you add. You give us permission to host and display it so we can run your site.</li>
        <li>
          Don't use Vicinic for anything unlawful, misleading, hateful or infringing, for spam, or to collect other
          people's personal information without a lawful basis. We may suspend sites that do.
        </li>
        <li>
          Where your site collects visitors' personal information (for example, contact forms or chat), you are the
          responsible party under POPIA and we process it on your behalf as your operator.
        </li>
      </ul>

      <h2>7. AI features</h2>
      <p>
        The AI chat assistant, WhatsApp bot and automated blog use third-party AI models. Their answers can be wrong or
        incomplete. Review what they say about your business, and don't rely on them for legal, financial or medical
        advice.
      </p>

      <h2>8. Third-party services</h2>
      <p>
        We rely on trusted providers including Amazon Web Services, Cloudflare, Neon, PayFast, domain registrars, Meta
        (WhatsApp) and Groq (AI). Their availability and policies can affect your service, and some features (such as
        WhatsApp) are also subject to their own terms.
      </p>

      <h2>9. Availability and liability</h2>
      <ul>
        <li>We work to keep sites online at all times but can't guarantee uninterrupted service; maintenance and provider outages happen.</li>
        <li>
          To the extent the law allows, our total liability to you is limited to the amount you paid us in the 3 months
          before the claim, and we're not liable for indirect losses such as lost profits.
        </li>
      </ul>

      <h2>10. Schools</h2>
      <p>
        School packages are provided under a separate service agreement approved by the School Governing Body. Where it
        differs from these terms, the school's agreement applies.
      </p>

      <h2>11. Changes and law</h2>
      <p>
        We may update these terms and will change the date above when we do; material changes will be communicated by
        email or in your portal. These terms are governed by the laws of the Republic of South Africa.
      </p>

      <h2>12. Contact</h2>
      <p>
        {COMPANY.name}, Reg. No. {COMPANY.reg}, {COMPANY.address}. Email{' '}
        <a href={`mailto:${COMPANY.email}`}>{COMPANY.email}</a>.
      </p>
    </LegalPage>
  )
}
