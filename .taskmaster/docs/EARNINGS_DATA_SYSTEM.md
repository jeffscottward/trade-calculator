# Earnings Data System Documentation

## Overview

The earnings data system provides a robust solution for fetching, storing, and serving earnings calendar data without hammering external APIs. It uses NASDAQ's public data via the `finance_calendars` library and stores it in PostgreSQL for fast, reliable access.

## Architecture

```
NASDAQ API (via finance_calendars)
    ↓
Bulk Import Script (earnings_data_importer.py)
    ↓
PostgreSQL Database
    ↓
FastAPI Backend
    ↓
React Frontend
```

## Components

### 1. Data Source: NASDAQ via finance_calendars

- **Library**: `finance_calendars` Python package
- **Data Available**: All US stocks earnings dates, times, estimates, market cap
- **Free Access**: No API key required
- **Limitations**: Rate limiting may apply for bulk requests

### 2. Database Schema (`automation/database/schema_earnings.sql`)

**Main Table: `earnings_calendar`**
- Stores all earnings data with parsed numeric values
- Unique constraint on (ticker, report_date) for upserts
- Indexes on commonly queried fields

**Fields**:
- `ticker`: Stock symbol
- `company_name`: Full company name
- `report_date`: Date of earnings report
- `report_time`: BMO (Before Market Open), AMC (After Market Close), TBD
- `market_cap`: Formatted string and numeric value
- `eps_forecast`: EPS estimate with numeric value
- `num_estimates`: Number of analyst estimates
- `last_year_*`: Previous year's data for comparison

**Import History Table: `earnings_import_history`**
- Tracks all bulk imports for auditing
- Records success/failure status

### 3. Data Import Script (`automation/earnings_data_importer.py`)

**Features**:
- Fetches earnings data from NASDAQ
- Bulk imports with upsert logic (updates existing, inserts new)
- Parses string values to numeric for queries
- Handles various date formats
- Records import history

**Usage**:
```bash
# Import next 30 days (default)
python automation/earnings_data_importer.py

# Import specific date range
python automation/earnings_data_importer.py --start-date 2025-01-01 --end-date 2025-01-31

# Import current week only
python automation/earnings_data_importer.py --week

# Import custom number of days
python automation/earnings_data_importer.py --days 60
```

### 4. API Backend (`api/main.py`)

**Endpoints**:
- `GET /api/earnings/{date}`: Get earnings for specific date
- `GET /api/earnings/calendar/month`: Get all earnings dates in a month

**Priority System**:
1. First tries to fetch from database (fast, no API calls)
2. Falls back to Alpha Vantage API if database unavailable
3. Returns data source in response for transparency

### 5. Periodic Updates

**Cron Script** (`scripts/update_earnings_data.sh`):
- Runs daily to fetch new earnings data
- Logs all operations
- Can be scheduled via crontab

**Crontab Setup**:
```bash
# Edit crontab
crontab -e

# Add daily update at 6 AM
0 6 * * * /path/to/update_earnings_data.sh

# Verify setup
crontab -l
```

## Setup Instructions

### 1. Install Dependencies

```bash
pip install finance-calendars pandas psycopg2-binary
```

### 2. Create Database Schema

```bash
# Connect to your database and run:
psql $DATABASE_URL < automation/database/schema_earnings.sql
```

### 3. Initial Data Import

```bash
# Import next 30 days of earnings
python automation/earnings_data_importer.py
```

### 4. Set Up Periodic Updates

```bash
# Make script executable
chmod +x scripts/update_earnings_data.sh

# Add to crontab (see scripts/crontab.example)
crontab -e
```

### 5. Configure Environment Variables

Add to `.env`:
```env
DATABASE_URL=postgresql://user:password@host:port/dbname
ALPHA_VANTAGE_KEY=your_key_here  # Optional fallback
```

## Data Flow

1. **Daily Update (Cron)**:
   - Runs at 6 AM Eastern
   - Fetches next 30 days of earnings
   - Updates existing records, adds new ones

2. **User Request**:
   - Frontend requests earnings for date
   - API checks database first
   - Returns data immediately (no external API call)
   - Falls back to Alpha Vantage only if DB unavailable

3. **Benefits**:
   - ✅ No API rate limiting issues
   - ✅ Fast response times (<50ms)
   - ✅ Reliable data availability
   - ✅ Historical data preservation
   - ✅ Works offline after initial import

## Monitoring

Check import logs:
```bash
tail -f logs/earnings_update.log
```

Check database status:
```sql
-- Recent imports
SELECT * FROM earnings_import_history 
ORDER BY import_date DESC 
LIMIT 10;

-- Data coverage
SELECT 
    MIN(report_date) as earliest,
    MAX(report_date) as latest,
    COUNT(DISTINCT report_date) as days_covered,
    COUNT(*) as total_earnings
FROM earnings_calendar;

-- Today's earnings
SELECT * FROM earnings_calendar_view 
WHERE report_date = CURRENT_DATE
ORDER BY market_cap_numeric DESC;
```

## Troubleshooting

### No data showing
1. Check database connection: `echo $DATABASE_URL`
2. Verify data imported: `SELECT COUNT(*) FROM earnings_calendar;`
3. Check API logs: `tail -f logs/earnings_update.log`

### Import failures
1. Check network connectivity
2. Verify finance_calendars is installed: `pip list | grep finance`
3. Test manual import: `python -c "from finance_calendars.finance_calendars import get_earnings_today; print(get_earnings_today())"`

### Stale data
1. Check cron is running: `crontab -l`
2. Check last import: `SELECT MAX(created_at) FROM earnings_calendar;`
3. Run manual update: `./scripts/update_earnings_data.sh`

## Future Enhancements

- [ ] Add WebSocket for real-time updates
- [ ] Cache frequently accessed dates in Redis
- [ ] Add data quality checks
- [ ] Implement data archival for old earnings
- [ ] Add email alerts for import failures
- [ ] Create admin dashboard for monitoring