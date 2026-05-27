# mia_n_eve

A realtime voice-first AI operating assistant built with modern AI orchestration, streaming architecture, and native desktop capabilities.

## Features

- Realtime AI streaming
- Voice interaction
- WebSocket-based communication
- AI orchestration engine
- Memory and context retrieval
- Tool execution system
- Native desktop integration
- Modular architecture

## Tech Stack

- Node.js
- TypeScript
- Express
- WebSockets
- Tauri
- PostgreSQL
- Redis
- Qdrant
- Hugging Face APIs

## Architecture

```text
UI Layer
   ↓
WebSockets + REST
   ↓
Backend Gateway
   ↓
AI Orchestrator
   ↓
Memory + Tools + Voice + LLMs