Title: Project: BHKA Bot, a WhatsApp AI assistant
Date: 2026-09-28 10:02
Category: Projects
Tags: whatsapp, ai, groq, case study
Slug: project-bhka-bot
Summary: A WhatsApp AI chatbot for a South African credit rehabilitation company, answering and qualifying enquiries around the clock.
Authors: Vicinic

![BHKA Bot on WhatsApp]({static}/images/projects/bhka.webp)

BHK Invest helps South Africans rehabilitate their credit. Most of their enquiries arrive on WhatsApp, often after hours, and many are the same first questions. BHKA Bot answers them immediately.

## What it does

- Replies to customers on WhatsApp in plain language, any time of day.
- Asks the right first questions (for example, whether someone is behind on accounts or blacklisted) so the team starts every conversation already knowing the situation.
- Points interested customers to a free consultation with the team.

## How it's built

The bot is written in Python on the Meta WhatsApp Cloud API, with Groq's Llama models for replies. It rotates between several API keys so rate limits don't stall conversations, and it's hosted on Render.

The same idea now powers the WhatsApp bot available on Vicinic's Growth Hub and Business OS plans.
