Title: Project: Bloggify, an AI research blog
Date: 2026-09-28 10:03
Category: Projects
Tags: bloggify, ai, groq, automation
Slug: project-bloggify
Summary: Bloggify pulls fresh papers and news, digests them with AI and drafts cited blog posts for review. It powers this blog.
Authors: Vicinic

![Bloggify research blog]({static}/images/projects/bloggify.webp)

Keeping a blog going is hard for a small team. Bloggify does the research and first draft, and a person approves every post before it goes live.

## How it works

1. **Fetch.** Crawlers pull new items for each topic from sources like arXiv, Semantic Scholar, NASA, Hacker News, Google News (via SerpAPI), GDELT and RSS feeds.
2. **Rank.** Items we haven't covered yet are scored on relevance, recency and popularity.
3. **Digest.** Groq's models turn each item into structured notes. For deep dives the lead paper is read in full, in chunks.
4. **Write.** A draft post is written with numbered citations, and a sources list is added automatically.
5. **Review.** The draft waits for approval. Approve it and it's published; reject it and it's discarded.

## On this blog

The Vicinic blog runs on the same pipeline. Drafts arrive three times a week, and approved posts go live straight away. Topics include AI, security, space, markets and South African business news.

This is the engine behind the automated blog included with Growth Hub.
