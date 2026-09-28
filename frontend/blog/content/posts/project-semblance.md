Title: Project: Semblance, a multi-agent personal AI assistant
Date: 2026-09-28 10:01
Category: Projects
Tags: semblance, ai, agents, groq
Slug: project-semblance
Summary: Semblance is a Jarvis-inspired personal assistant with long-term memory, sub-agents and an animated interface that evolves as it learns.
Authors: Vicinic

![Semblance personal AI assistant]({static}/images/projects/semblance.webp)

Semblance started with a simple question: what would a personal assistant look like if it actually remembered who you are?

## What makes it different

- **Permanent memory.** Conversations are stored in Postgres with pgvector, so Semblance can recall what matters instead of starting fresh each time.
- **A team of agents.** A seven-step pipeline assembles context, loads memory, runs tools and hands bigger jobs to sub-agents for planning, scheduling, research and more.
- **Personality and emotion.** It adapts to you using the Big Five personality model and an emotional-context layer, so replies fit the person and the moment.
- **Tools.** Web search (SerpAPI), news, calendar and WhatsApp are all available to it through one flat tool registry.
- **An interface that evolves.** The React interface moves through animated stages as the assistant grows.

## Built to run cheaply

Semblance runs on open-weight models (Qwen and GPT-OSS) through Groq and is deployed on AWS, designed to stay close to zero cost. Many of the lessons from it, such as model fallbacks and memory, went straight into the AI assistant on Vicinic sites.
