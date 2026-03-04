# Accelerator Reporting Manager - Backend

Production-ready FastAPI backend with MySQL database and OpenAI-powered analytics.

---

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- MySQL Server (XAMPP or standalone)
- OpenAI API Key

### Installation

1. **Install Dependencies**
```bash
cd backend
pip install -r requirements.txt
```

2. **Configure Environment**

Create a `.env` file in the backend directory:
```env
# MySQL Database
DATABASE_URL=mysql+aiomysql://root@localhost:3306/reporting_manager

# OpenAI API
OPENAI_API_KEY=your_openai_api_key_here
```

3. **Start the Server**
```bash
python server.py
```

The API will be available at `http://localhost:8000`

---

## 📊 Database

### MySQL Configuration
- **Database:** reporting_manager
- **Connection:** Async via aiomysql
- **ORM:** SQLAlchemy 2.0

### Tables
- `users` - User/investor information
- `properties` - Real estate properties
- `auctions` - Property auctions
- `bids` - Bidding history
- `chat_messages` - AI chat history

### Initial Setup

The database tables will be created automatically on first run. You can also manually create the database:

```sql
CREATE DATABASE reporting_manager;
```

---

## 🔌 API Endpoints

### Base URL
All endpoints are prefixed with `/api`

### Data Endpoints
- `GET /api/users` - Get all users
- `GET /api/properties` - Get all properties
- `GET /api/auctions` - Get all auctions
- `GET /api/bids` - Get all bids

### Chat Endpoint
- `POST /api/chat` - AI-powered analytics chat
  ```json
  {
    "message": "Show me top properties by bid count",
    "user_id": "demo_user"
  }
  ```

### Authentication
- `POST /api/auth/login` - Demo login (accepts any credentials)
  ```json
  {
    "email": "user@example.com",
    "password": "password"
  }
  ```

---

## 🧪 Testing

### API Testing
```bash
# Test health
curl http://localhost:8000/

# Test users endpoint
curl http://localhost:8000/api/users

# Test chat
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"How many properties do we have?","user_id":"demo_user"}'
```

### Database Verification
Access phpMyAdmin at `http://localhost/phpmyadmin` to verify data.

---

## 📁 Project Structure

```
backend/
├── server.py           # Main FastAPI application
├── database.py         # SQLAlchemy models and database connection
├── requirements.txt    # Python dependencies
├── .env               # Environment variables (not in git)
└── README.md          # This file
```

---

## 🔧 Configuration

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `DATABASE_URL` | MySQL connection string | Yes |
| `OPENAI_API_KEY` | OpenAI API key for chat | Yes |

### Database URL Format
```
mysql+aiomysql://username:password@host:port/database
```

Example:
```
mysql+aiomysql://root@localhost:3306/reporting_manager
```

---

## 📦 Dependencies

Key dependencies:
- **FastAPI** - Modern web framework
- **SQLAlchemy** - ORM and database toolkit
- **aiomysql** - Async MySQL driver
- **OpenAI** - AI-powered analytics
- **Pydantic** - Data validation
- **Uvicorn** - ASGI server

See `requirements.txt` for complete list.

---

## 🚀 Deployment

### Production Checklist
- [ ] Set strong database credentials
- [ ] Configure proper CORS origins
- [ ] Use environment variables for secrets
- [ ] Enable HTTPS
- [ ] Set up database backups
- [ ] Configure logging
- [ ] Use production ASGI server (Gunicorn + Uvicorn)

### Production Server
```bash
# Using Gunicorn with Uvicorn workers
gunicorn server:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000
```

---

## 🐛 Troubleshooting

### Server Won't Start
1. Check MySQL is running (XAMPP Control Panel)
2. Verify `.env` file exists with correct credentials
3. Ensure port 8000 is not in use
4. Check database exists: `reporting_manager`

### Database Connection Error
1. Verify MySQL server is running
2. Check DATABASE_URL format
3. Ensure database `reporting_manager` exists
4. Test credentials in phpMyAdmin

### OpenAI API Error
1. Verify OPENAI_API_KEY is set correctly
2. Check API key has sufficient credits
3. Verify internet connection

---

## 📞 Support

For issues or questions:
1. Check error logs in console
2. Verify all prerequisites are met
3. Review environment configuration
4. Check database connection in phpMyAdmin

---

## 📄 License

Proprietary - All rights reserved

---

**Status:** ✅ Production Ready  
**Database:** MySQL  
**API Version:** 1.0


