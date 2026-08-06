# Frontend Application

The GPT Researcher UI is the **Next.js** app in `frontend/nextjs/`. The Python backend on port **8000** is API-only (`/ws`, `/api/chat`, `/docs`); use port **3000** for the web interface.

## Prerequisites

- Node.js (v18.17.0 recommended)
- npm
- Backend API running (`python main.py` from the repo root)

## Setup and Running

1. Navigate to the Next.js directory:

   ```
   cd frontend/nextjs
   ```

2. Set up Node.js (optional, if using nvm):

   ```
   nvm install 18.17.0
   nvm use v18.17.0
   ```

3. Install dependencies:

   ```
   npm install --legacy-peer-deps
   ```

4. Start the development server:

   ```
   npm run dev
   ```

5. Open [http://localhost:3000](http://localhost:3000)

Set `NEXT_PUBLIC_GPTR_API_URL` in `.env` if the backend is not on `http://localhost:8000`.

## Legacy static frontend

The files `frontend/index.html` and `frontend/scripts.js` are no longer served by the backend. They remain in the repo for reference only; do not use them as the primary UI.

## Features

1. Intuitive research interface with Preferences / Settings
2. Real-time progress via WebSocket
3. Report generation and post-report chat (with web search)
4. Multi Agents and MCP configuration
5. Responsive layout (desktop + mobile)

For production, use the Next.js build (`npm run build` / Docker `gptr-nextjs` service).
