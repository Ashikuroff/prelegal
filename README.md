# Prelegal

A SaaS application for drafting legal agreements using AI chat. Users can interact with an AI assistant to create various types of legal documents based on predefined templates.

## Features

- AI-powered chat interface for document creation
- Support for 11 different document types (NDA, Cloud Service Agreement, Pilot Agreement, etc.)
- User authentication with JWT
- Document persistence and management
- Live preview and PDF download
- Responsive web interface

## Supported Document Types

- Mutual NDA
- Cloud Service Agreement
- Pilot Agreement
- Design Partner Agreement
- Service Level Agreement (SLA)
- Professional Services Agreement
- Partnership Agreement
- Software License Agreement
- Data Processing Agreement (DPA)
- Business Associate Agreement (BAA)
- AI Addendum

## Setup

### Prerequisites

- Docker
- OpenRouter API key (free tier available)

### Installation

1. Clone the repository
2. Set your OpenRouter API key in `.env`:
   ```
   OPENROUTER_API_KEY=your_api_key_here
   ```
3. Run the application:
   - Mac: `./scripts/start-mac.sh`
   - Linux: `./scripts/start-linux.sh`
   - Windows: `.\scripts\start-windows.ps1`

The application will be available at http://localhost:8000

### Stopping

- Mac: `./scripts/stop-mac.sh`
- Linux: `./scripts/stop-linux.sh`
- Windows: `.\scripts\stop-windows.ps1`

## Development

### Backend

- Built with FastAPI and SQLAlchemy
- Uses uv for dependency management
- SQLite database (fresh start on container launch)

### Frontend

- Built with Next.js and TypeScript
- Static export served by FastAPI

### AI Integration

- Uses LiteLLM with OpenRouter
- Free Llama 3.2 3B model for cost-effective operation
- Structured outputs for reliable field extraction

## API Endpoints

- `POST /api/auth/signup` - User registration
- `POST /api/auth/signin` - User login
- `GET /api/auth/me` - Get current user
- `GET /api/documents` - List user documents
- `POST /api/documents` - Save document
- `GET /api/documents/{id}` - Get document
- `PUT /api/documents/{id}` - Update document
- `DELETE /api/documents/{id}` - Delete document
- `GET /api/chat/greeting` - AI greeting
- `POST /api/chat/message` - Chat with AI
- `GET /api/health` - Health check

## Color Scheme

- Accent Yellow: `#ecad0a`
- Blue Primary: `#209dd7`
- Purple Secondary: `#753991`
- Dark Navy: `#032147`
- Gray Text: `#888888`
