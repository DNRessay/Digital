Title: Project: the Vicinic Site Editor
Date: 2026-09-28 10:06
Category: Projects
Tags: vicinic, website builder, django, react
Slug: project-vicinic-site-editor
Summary: How we built a self-service website editor for small businesses: live editing, a menu editor, extra pages, a free .co.za and email forwarding.
Authors: Vicinic

![The Vicinic Site Editor]({static}/images/projects/editor.webp)

Most small businesses don't need a web designer. They need a good-looking site that they can change themselves when prices, photos or opening hours change. That's what the Vicinic Site Editor is for.

## What it does

- **Pick a template, then edit it live.** Tap any heading, paragraph, image, logo or button on your page and change it right there, then publish in one tap.
- **An easy menu editor.** Rename, reorder, add or remove menu links, and link to pages, sections or any web address. On phones, templates without their own menu button get one automatically.
- **Add your own pages.** New pages are built from the template's own styling, with ready-made sections to drop in: 3 extra pages on Starter, 10 on Growth Hub and unlimited on Business OS.
- **Your own domain.** Every paid plan includes one free .co.za domain, and you can connect a domain you already own from the Deploy tab.
- **Email forwarding.** Forward hello@yourbusiness.co.za to the Gmail or Outlook inbox you already use.

## How it's built

The backend is Django running on AWS Lambda, with a Neon Postgres database. Templates are stored in S3 and rendered per request. The customer editor and our admin console are React apps on Cloudflare Pages, and domains and email routing go through Cloudflare. Hosting a site costs us almost nothing, which is why a Starter site can be a R250 once-off payment.

## Try it

[Sign up free](https://console.vicinic.co.za/?signup), pick a template and start editing. You only pay when you're ready to go live.
