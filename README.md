# SF Street Sweeping Reminder API

A FastAPI service that sends automated reminders before San Francisco street sweeping to help you avoid parking tickets.

## Features

- 📍 **Location-based lookup**: Finds your exact street and block side from GPS coordinates
- 📅 **Accurate scheduling**: Calculates next street sweeping date using SF's official data
- 🔔 **Automated reminders**: Sends notifications at 7 AM and 8 PM the day before sweeping
- 🗄️ **Persistent storage**: Tracks parking locations in PostgreSQL database

## How It Works

1. Share your location via the iOS Shortcut
2. The API determines your street, block side, and next sweeping date
3. You'll receive reminders the day before and morning of street sweeping.

## Usage (No Setup Required)

### iOS Shortcut
1. Install the [Street Sweeping Shortcut](https://www.icloud.com/shortcuts/74745470b59f4dc7a68c61ee6952a4d2)
2. update the shortcut so it has your phone number instead of mine
3. Park your car and run the shortcut
4. You'll automatically receive reminders before the next sweep (once i get permission from the US govermnet to send texts - soon!)

That's it! The API is already deployed and running.

---

## For Developers

Want to run this locally or deploy your own instance? Here's how:

### Prerequisites

- Docker
- PostgreSQL database
- SimplePush account (for notifications)

### Local Development

1. **Clone the repository**
```bash
   git clone https://github.com/yourusername/street_sweeping_API.git
   cd street_sweeping_API
```

2. **Create `.env` file**
```bash
   DATABASE_URL=postgresql://user:password@localhost:5432/street_sweeping
   SIMPLEPUSH_KEY=your_simplepush_key
```

3. **Build and run with Docker**
```bash
   docker build -t street-sweep .
   docker run -p 8000:8000 --env-file .env street-sweep
```

4. **Test the API**
```bash
   curl -X POST http://localhost:8000/next_sweep \
     -H "Content-Type: application/json" \
     -d '{
       "latitude": 37.7749,
       "longitude": -122.4194,
       "phone_number": "4155551234"
     }'
```

### API Documentation
### Database Setup

**Important**: You need to create the PostgreSQL database first. The `parking_records` table will be created automatically when the API starts.

#### Option 1: Use existing PostgreSQL
If you already have PostgreSQL installed:
```bash
# Create the database
createdb street_sweeping

# Update your .env with the connection string
DATABASE_URL=postgresql://username:password@localhost:5432/street_sweeping
```

When you start the API, it will automatically create the `parking_records` table.

#### Option 2: Run PostgreSQL in Docker
```bash
# Start PostgreSQL container
docker run -d \
  --name postgres \
  -e POSTGRES_USER=sweepuser \
  -e POSTGRES_PASSWORD=sweeppass \
  -e POSTGRES_DB=street_sweeping \
  -p 5432:5432 \
  postgres:15

# Update your .env
DATABASE_URL=postgresql://sweepuser:sweeppass@localhost:5432/street_sweeping
```

The `-e POSTGRES_DB=street_sweeping` automatically creates the database. The API will create the table on startup.

#### Option 3: Docker Compose (easiest for local dev)
Create `docker-compose.yml`:
```yaml
version: '3.8'

services:
  db:
    image: postgres:15
    environment:
      POSTGRES_USER: sweepuser
      POSTGRES_PASSWORD: sweeppass
      POSTGRES_DB: street_sweeping
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql://sweepuser:sweeppass@db:5432/street_sweeping
      SIMPLEPUSH_KEY: ${SIMPLEPUSH_KEY}
    depends_on:
      - db

volumes:
  postgres_data:
```

Then run:
```bash
docker-compose up
```

**What gets created automatically:**
- ✅ `parking_records` table (created by SQLAlchemy on API startup)

**What you need to create:**
- ❌ PostgreSQL database (must exist before running the API)
- ❌ PostgreSQL server (must be running)
Once running, visit `http://localhost:8000/docs` for interactive API documentation.

### Deployment

**Running the reminder script:**
```bash
docker run --rm --env-file .env --network host street-sweep python send_reminders.py
```

**Schedule automated reminders with cron:**
```bash
# Edit crontab
crontab -e

# Add these lines (adjust timezone as needed)
0 7 * * * cd /path/to/street_sweeping_API && docker run --rm --env-file .env --network host street-sweep python send_reminders.py >> reminder.log 2>&1
0 20 * * * cd /path/to/street_sweeping_API && docker run --rm --env-file .env --network host street-sweep python send_reminders.py >> reminder.log 2>&1
```

### Project Structure
```
street_sweeping_API/
├── main.py              # FastAPI application
├── send_reminders.py    # Notification script
├── Dockerfile           # Container configuration
├── requirements.txt     # Python dependencies
└── README.md
```

### Tech Stack

- **FastAPI**: REST API framework
- **GeoPandas**: Geospatial data processing
- **PostgreSQL**: Database
- **SQLAlchemy**: ORM
- **Docker**: Containerization
- **SimplePush**: Push notifications

### Data Sources

This project uses real-time data from SF OpenData:
- [Street Centerlines](https://data.sfgov.org/resource/3psu-pn9h.csv)
- [Street Sweeping Schedule](https://data.sfgov.org/resource/yhqp-riqs.csv)

## Contributing

Pull requests welcome! Feel free to open an issue if you find bugs or have feature suggestions.

## License

MIT

## Contact

Built by al-gent - 94gent@gmail.com

---

**Note**: This service only works for San Francisco street sweeping schedules.