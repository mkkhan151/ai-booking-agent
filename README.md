# AI Booking Agent

A complete, containerized AI-powered booking system that allows users to book time slots between 9 AM and 5 PM through a conversational interface. The system uses Google Gemini as an intelligent agent that can check availability and book appointments.

## Features

- 🤖 **AI-Powered Conversations**: Natural language booking using Google Gemini
- 🔄 **Real-Time Communication**: WebSocket-based chat interface
- 💾 **Persistent Storage**: PostgreSQL for bookings, Redis for chat history
- 🎯 **Smart Agent**: Automatically calls tools to check availability and book slots
- 🚀 **Fully Containerized**: Easy deployment with Docker Compose
- 📱 **Responsive UI**: Modern Next.js frontend with Tailwind CSS

## Tech Stack

### Backend
- **FastAPI** - Modern Python web framework
- **PostgreSQL** - Reliable database for bookings
- **Redis** - Fast cache for chat history
- **Google Gemini Pro** - AI agent with function calling
- **SQL Model** - ORM for database operations
- **WebSockets** - Real-time bidirectional communication

### Frontend
- **Next.js 15** - React framework with App Router
- **TypeScript** - Type-safe development
- **Tailwind CSS** - Utility-first styling
- **WebSocket Client** - Real-time chat connection

## Prerequisites

- Docker and Docker Compose installed
- Google Gemini API key ([Get one here](https://makersuite.google.com/app/apikey))

## Quick Start

### 1. Clone and Setup

```bash
# Clone the repository
git clone https://github.com/mkkhan151/ai-booking-agent.git
cd ai-booking-agent

# Create .env file
cp .env.example .env
```

### 2. Configure Environment

Edit `.env` and add your Gemini API key:

```bash
GEMINI_API_KEY=your_actual_api_key_here
```

### 3. Launch the Application

```bash
# Build and start all services
docker-compose up --build

# Or run in detached mode
docker-compose up -d --build
```

### 4. Access the Application

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Health Check**: http://localhost:8000/health

## How It Works

### The Booking Flow

1. **User Initiates**: User starts a conversation through the web interface
2. **Agent Greets**: AI agent welcomes the user and asks for details
3. **Check Availability**: Agent uses `check_availability` tool to query free slots
4. **User Selects**: User chooses preferred time and duration
5. **Confirmation**: Agent confirms details before booking
6. **Book Slot**: Agent uses `book_slot` tool to create the reservation
7. **Confirmation**: User receives booking ID and details

### Agent Tools

The AI agent has access to two functions:

**`check_availability(date_str: str)`**
- Queries database for a specific date
- Returns available 1-hour slots between 9 AM - 5 PM
- Accounts for existing bookings

**`book_slot(user_name, date_str, hour)`**
- Validates the time slot
- Checks for conflicts with existing bookings
- Creates new booking in PostgreSQL
- Returns confirmation with booking ID

### Architecture

```
┌─────────────┐         ┌─────────────┐
│   Browser   │◄───────►│   Next.js   │
│   (User)    │ WebSocket│  Frontend   │
└─────────────┘         └──────┬──────┘
                               │
                               │ WS
                               ▼
                        ┌─────────────┐
                        │   FastAPI   │
                        │   Backend   │
                        └──────┬──────┘
                               │
                    ┌──────────┼──────────┐
                    ▼          ▼          ▼
              ┌─────────┐ ┌────────┐ ┌────────┐
              │ Gemini  │ │ Postgres│ │ Redis  │
              │   API   │ │   DB    │ │ Cache  │
              └─────────┘ └────────┘ └────────┘
```

## Development

### Backend Development

```bash
# Enter backend container
docker-compose exec backend sh

# View logs
docker-compose logs -f backend
```

### Frontend Development

```bash
# Enter frontend container
docker-compose exec frontend sh

# View logs
docker-compose logs -f frontend
```

### Database Management

```bash
# Connect to PostgreSQL
docker-compose exec db psql -U postgres -d booking_db

# View bookings
SELECT * FROM bookings;
```

### Redis Management

```bash
# Connect to Redis
docker-compose exec redis redis-cli

# View all chat sessions
KEYS chat:*

# View specific session
GET chat:client_123
```

## API Endpoints

### WebSocket
- `ws://localhost:8000/ws/{session_id}` - Chat connection

### HTTP
- `GET /health` - Health check endpoint

## Project Structure

```
project-root/
├── docker-compose.yml        # Container orchestration
├── .env                      # Environment variables
├── .env.example              # Environment template
├── backend/
│   ├── Dockerfile            # Backend container config
│   ├── pyproject.toml        # Python dependencies
│   ├── main.py               # FastAPI app & WebSocket
│   ├── agent.py              # Gemini agent logic
│   ├── tools.py              # Database functions
│   └── database.py           # SQLAlchemy models
└── frontend/
    ├── Dockerfile            # Frontend container config
    ├── package.json          # Node dependencies
    ├── next.config.js        # Next.js configuration
    ├── tailwind.config.ts    # Tailwind setup
    └── app/
        ├── page.tsx          # Main chat UI
        ├── layout.tsx        # Root layout
        ├── globals.css       # Global styles
        └── hooks/
            └── useChatSocket.ts # WebSocket hook
```

## Troubleshooting

### Connection Issues

If the frontend can't connect to the backend:

1. Check that all containers are running:
   ```bash
   docker-compose ps
   ```

2. Verify backend is accessible:
   ```bash
   curl http://localhost:8000/health
   ```

3. Check backend logs:
   ```bash
   docker-compose logs backend
   ```

### Database Issues

If you see database connection errors:

```bash
# Restart database
docker-compose restart db

# Check database health
docker-compose exec db pg_isready -U postgres
```

### Gemini API Issues

If the agent isn't responding:

1. Verify your API key is set in `.env`
2. Check backend logs for API errors
3. Ensure you have quota available on your Gemini API account

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `GEMINI_API_KEY` | Google Gemini API key | Required |
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://postgres:postgres@db:5432/booking_db` |
| `REDIS_URL` | Redis connection string | `redis://redis:6379` |
| `NEXT_PUBLIC_WS_URL` | WebSocket URL for frontend | `ws://localhost:8000` |

## Production Deployment

For production deployment:

1. Use environment-specific `.env` files
2. Set strong database passwords
3. Configure proper CORS origins in `main.py`
4. Use production-grade Redis (e.g., Redis Cloud)
5. Set up SSL/TLS for WebSocket connections
6. Consider using a process manager like PM2 or Supervisor
7. Implement rate limiting and authentication
8. Set up monitoring and logging

## License

MIT License - feel free to use this project for your own purposes.

## Support

For issues or questions:
1. Check the troubleshooting section
2. Review Docker Compose logs
3. Ensure all environment variables are set correctly