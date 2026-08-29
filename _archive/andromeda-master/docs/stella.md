# stella

The AI-powered backend service for Refrens. Provides intelligent features — document understanding, smart data extraction (OCR + LLM), conversational interfaces, and automated lead management — using an agentic LangGraph architecture.

**Tech:** Fastify, TypeScript, LangChain/LangGraph, OpenAI, Google Gemini, Neo4j, MongoDB
**Tags:** backend, backend-ai

## What it contains

- `src/freya/` — the core AI agent system ("Freya"): LangGraph state machines, agents, and chains, including `chatbot/` (conversational AI) and `leads/` (lead understanding and scoring).
- Fastify controllers in `src/controllers/` exposing chat, OCR, document-intelligence, and event endpoints.
- Document intelligence (`document-intelligence.controller.ts`) combining OCR with LLM-based parsing to extract structured data from files.
- Knowledge-graph integration in `src/helpers/neo4j/` for context-aware, relationship-driven queries; RAG to supply relevant context to LLMs.
- Prompt and config management in `src/constants/`, Fastify plugins for auth/db/redis, and a CLI for running AI tasks manually.
- Transcription integrations (AssemblyAI, Deepgram) and tool-use that lets agents query Elasticsearch or `serana`.

## When to reach for it

- Building or modifying AI agents, LangGraph workflows, chains, or the chatbot.
- Working on document parsing / OCR + LLM data extraction.
- Adjusting prompts, RAG context, or knowledge-graph (Neo4j) queries.
- Adding a new LLM/model provider or AI-powered endpoint, or feeding AI insights back into `serana` workflows.
