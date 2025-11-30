# Chess Pattern Analyzer

A web application that analyzes your Chess.com games to identify patterns, weaknesses, and provide actionable recommendations to improve your gameplay.

![Chess Pattern Analyzer Screenshot](Screenshot%202025-11-29%20203818.png)

## Live Demo

- **Frontend:** Deploy to Vercel (see [deployment guide](frontend/VERCEL_DEPLOYMENT_GUIDE.md))
- **Backend API:** https://chess-pattern-analyzer.onrender.com
- **API Docs:** https://chess-pattern-analyzer.onrender.com/api/docs
- **Health Check:** https://chess-pattern-analyzer.onrender.com/healthz

## Deployed Services

### Production Environment

**Backend (Render)**
- **Service:** chess-pattern-analyzer-api
- **Platform:** Render (Free Tier)
- **Region:** US East (Ohio)
- **Runtime:** Docker (Python 3.11)
- **Auto-Deploy:** Enabled (main branch)
- **Health Monitoring:** Automated checks every 30s

**Database (Neon)**
- **Type:** PostgreSQL 17
- **Platform:** Neon Serverless
- **Region:** AWS us-east-1
- **Tier:** Free (0.5GB storage, 0.5GB RAM)
- **Features:** Auto-suspend, branch management

**Cache (Upstash)**
- **Type:** Redis
- **Platform:** Upstash Serverless
- **Tier:** Free (10k commands/day, 256MB)
- **Features:** TLS encryption, global replication

**Frontend (Vercel)**
- **Framework:** Next.js 16
- **Platform:** Vercel (Free Tier)
- **Auto-Deploy:** Enabled (main branch)
- **Features:** Edge network, automatic HTTPS, preview deployments

**CI/CD (GitHub Actions)**
- **Workflows:** Backend CI, Frontend CI (planned)
- **Tests:** Route registration, config validation, exception handling
- **Checks:** Docker build, linting, dependency validation
- **Triggers:** Push to main, pull requests

## Features

- **Pattern Detection:** Identifies common errors across your games
  - Tactical errors (missed tactics, blunders)
  - Opening mistakes
  - Time pressure issues
  - Positional errors
  - Endgame mistakes

- **Personalized Recommendations:** Get specific advice on what to improve
- **Historical Analysis:** Analyze your last N games from Chess.com
- **Free to Use:** No authentication required for basic usage
- **Fast & Efficient:** Powered by Stockfish 16.1 chess engine

## Architecture

### Backend (Python/FastAPI)
- **Framework:** FastAPI with async/await
- **Chess Engine:** Stockfish 16.1
- **Database:** PostgreSQL (Neon serverless)
- **Cache:** Redis (Upstash)
- **API Integration:** Chess.com Published-Data API
- **Deployment:** Render (free tier)

### Frontend (Next.js)
- **Framework:** Next.js 16 with App Router
- **Language:** TypeScript
- **Styling:** Tailwind CSS v4
- **Deployment:** Vercel (free tier)

### Infrastructure Cost
**Total: $0/month** (using free tiers)

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL (or use Neon free tier)
- Redis (or use Upstash free tier)

### Local Development

#### Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set environment variables
cp .env.example .env
# Edit .env with your database and Redis URLs

# Run the server
uvicorn app.main:app --reload
```

Backend will be available at http://localhost:8000

#### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Set environment variables
cp .env.example .env.local
# Edit .env.local with your API URL

# Run development server
npm run dev
```

Frontend will be available at http://localhost:3000

## Deployment

### Backend Deployment (Render)
See [backend/RENDER_DEPLOYMENT_GUIDE.md](backend/RENDER_DEPLOYMENT_GUIDE.md)

### Frontend Deployment (Vercel)
See [frontend/VERCEL_DEPLOYMENT_GUIDE.md](frontend/VERCEL_DEPLOYMENT_GUIDE.md)

## API Documentation

Once the backend is running, visit:
- **Swagger UI:** http://localhost:8000/api/docs (or https://chess-pattern-analyzer.onrender.com/api/docs)
- **ReDoc:** http://localhost:8000/api/redoc (or https://chess-pattern-analyzer.onrender.com/api/redoc)

### Main Endpoints

#### Simple Analysis (MVP - Recommended)

```
GET /api/v1/simple-analyze/{username}?games_limit=10
```

Fast analysis using current month's games with simplified pattern detection. Perfect for MVP and testing.

**Parameters:**
- `username` (required): Chess.com username
- `games_limit` (optional): Number of recent games to analyze (default: 10, max: 50)

**Example:**
```bash
curl "https://chess-pattern-analyzer.onrender.com/api/v1/simple-analyze/magnus10?games_limit=5"
```

**Response:**
```json
{
  "username": "magnus10",
  "total_games": 10,
  "patterns": {
    "tactical_errors": 15,
    "opening_mistakes": 10,
    "time_pressure": 5,
    "positional_errors": 20,
    "endgame_mistakes": 10
  },
  "recommendations": [
    "Study opening theory for your most-played openings...",
    "Practice endgame fundamentals...",
    "Analyze your games with an engine after playing..."
  ],
  "analysis_date": "2025-11-29T12:00:00Z"
}
```

#### Full Analysis (Advanced)

```
GET /api/v1/analyze/{username}?games_limit=10
```

Comprehensive analysis with Stockfish engine evaluation (in development).

#### Health Check

```
GET /healthz
```

Returns: `{"status": "healthy"}`

## Project Structure

```
chess-pattern-analyzer/
├── backend/
│   ├── app/
│   │   ├── api/           # API routes
│   │   ├── core/          # Core configuration
│   │   ├── engine/        # Chess analysis engine
│   │   ├── models/        # Data models
│   │   ├── services/      # External services (Chess.com API)
│   │   └── tests/         # Unit tests
│   ├── Dockerfile
│   ├── requirements.txt
│   └── RENDER_DEPLOYMENT_GUIDE.md
│
├── frontend/
│   ├── src/
│   │   └── app/
│   │       ├── page.tsx   # Main analysis page
│   │       └── layout.tsx # App layout
│   ├── package.json
│   └── VERCEL_DEPLOYMENT_GUIDE.md
│
└── README.md
```

## Technologies Used

### Backend
- **FastAPI** - Modern Python web framework
- **Stockfish** - World's strongest chess engine
- **python-chess** - Chess library for move validation and PGN parsing
- **asyncpg** - Async PostgreSQL driver
- **Redis** - Caching layer
- **httpx** - Async HTTP client for Chess.com API
- **Pydantic** - Data validation

### Frontend
- **Next.js** - React framework
- **TypeScript** - Type-safe JavaScript
- **Tailwind CSS** - Utility-first CSS framework
- **React Hooks** - State management

### Infrastructure
- **Render** - Backend hosting
- **Vercel** - Frontend hosting
- **Neon** - Serverless PostgreSQL
- **Upstash** - Serverless Redis
- **GitHub Actions** - CI/CD automation

## Rate Limiting

To ensure fair usage and API compliance:

- **Anonymous Users:** 3 analyses per day (IP-based)
- **Registered Users:** 10 analyses per day (coming in v1.0)
- **Premium Users:** 100 analyses per day (future)

## Contributing

This is a personal project, but feedback and suggestions are welcome!

## License

MIT License - feel free to use this for learning and experimentation.

## Acknowledgments

- **Stockfish** - For the incredible chess engine
- **Chess.com** - For providing the Published-Data API
- **Render & Vercel** - For generous free tiers

## Roadmap

### MVP (Current)
- ✅ Basic pattern detection
- ✅ Chess.com API integration
- ✅ Web interface
- ✅ Free tier deployment

### Release 1.0 (Next)
- [ ] User authentication (OAuth)
- [ ] Save analysis history
- [ ] Compare against past analyses
- [ ] More detailed pattern breakdowns
- [ ] Opening repertoire analysis

### Future
- [ ] Mobile app
- [ ] Multi-platform support (Lichess, Chess24)
- [ ] AI-powered personalized training plans
- [ ] Social features (compare with friends)
- [ ] Premium tier with advanced features

## Support

For issues or questions:
- Create an issue in this repository
- Check the API documentation at `/docs`
- Review the deployment guides

---

Built with Claude Code
