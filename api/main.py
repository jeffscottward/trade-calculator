from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from datetime import datetime, date, timedelta
from typing import List, Optional, Dict, AsyncGenerator, Any
import os
from dotenv import load_dotenv
import requests
import json
from decimal import Decimal
# CSV imports removed - using JSON API from NASDAQ
from collections import defaultdict
import psycopg2
from psycopg2.extras import RealDictCursor
import logging
import asyncio

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Earnings Calendar API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Alpha Vantage configuration
# Using NASDAQ API - free, no key required
# Removed Alpha Vantage dependency

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL")

# Cache for earnings data to avoid hitting API limits
earnings_cache = {}
cache_timestamp = None
CACHE_DURATION = timedelta(minutes=5)  # Cache for 5 minutes

# WebSocket removed in favor of SSE

def json_serial(obj: Any) -> Any:
    """JSON serializer for objects not serializable by default json code"""
    if isinstance(obj, Decimal):
        result = float(obj)
        # Handle NaN and Infinity
        import math
        if math.isnan(result) or math.isinf(result):
            return None
        return result
    elif isinstance(obj, (datetime, date)):
        return obj.isoformat()
    elif isinstance(obj, float):
        import math
        if math.isnan(obj) or math.isinf(obj):
            return None
        return obj
    raise TypeError(f"Type {type(obj)} not serializable")

def safe_json_dumps(data: Any) -> str:
    """Safely dump data to JSON, handling Decimal and datetime types"""
    return json.dumps(data, default=json_serial)

def get_db_connection():
    """Get database connection"""
    if not DATABASE_URL:
        logger.warning("DATABASE_URL not configured")
        return None
    try:
        return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    except Exception as e:
        logger.error(f"Failed to connect to database: {str(e)}")
        return None

@app.get("/")
async def root():
    return {"message": "Earnings Calendar API"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

# WebSocket endpoint removed in favor of SSE

async def fetch_earnings_from_api(date_str: str) -> List[Dict]:
    """Fetch earnings data from NASDAQ for a specific date (free, no API key)"""
    logger.info(f"fetch_earnings_from_api called for {date_str}")
    try:
        logger.info("Fetching earnings from NASDAQ...")
        
        # NASDAQ earnings calendar URL
        url = f"https://api.nasdaq.com/api/calendar/earnings"
        
        # Headers to mimic browser request
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Origin': 'https://www.nasdaq.com',
            'Referer': 'https://www.nasdaq.com/'
        }
        
        params = {'date': date_str}
        response = requests.get(url, headers=headers, params=params)
        
        if response.status_code != 200:
            logger.error(f"Failed to fetch from NASDAQ: {response.status_code}")
            return []
            
        data = response.json()
        
        # Extract earnings data
        earnings_list = []
        if 'data' in data and 'rows' in data['data']:
            for idx, row in enumerate(data['data']['rows']):
                ticker = row.get('symbol', '')
                
                # Filter out OTC/foreign stocks
                if ticker and not ticker.endswith('F') and not ticker.endswith('Y'):
                    # Convert NASDAQ time format
                    time_map = {
                        'time-pre-market': 'BMO',
                        'time-after-hours': 'AMC',
                        'time-not-supplied': 'TBD'
                    }
                    report_time = time_map.get(row.get('time', ''), 'TBD')
                    
                    earnings_list.append({
                        "id": str(idx + 1),
                        "ticker": ticker,
                        "companyName": row.get('name', ''),
                        "reportTime": report_time,
                        "marketCap": row.get('marketCap', ''),
                        "fiscalQuarterEnding": row.get('fiscalQuarterEnding', ''),
                        "estimate": row.get('epsForecast', ''),
                        "fiscalDateEnding": row.get('fiscalQuarterEnding', ''),
                        "currency": 'USD'
                    })
        
        logger.info(f"Found {len(earnings_list)} earnings for {date_str} from NASDAQ")
        return earnings_list
    except Exception as e:
        logger.error(f"Error fetching earnings from NASDAQ: {e}")
        return []

async def analyze_earnings_list(earnings_list: List[Dict], date_str: str = None) -> List[Dict]:
    """Analyze a list of earnings with trading recommendations"""
    analyzed = []
    total_stocks = len(earnings_list)
    
    for idx, earning in enumerate(earnings_list):
        ticker = earning.get('ticker', '')
        if ticker:
            # Progress is now sent via SSE in the streaming endpoint
            
            # Get analysis
            analysis = await get_quick_analysis(ticker)
            
            # Merge analysis with earnings data
            earning['recommendation'] = analysis.get('recommendation', 'AVOID')
            earning['riskLevel'] = analysis.get('riskLevel', 'HIGH')
            
            # Get full analysis for more details
            try:
                full_analysis = await analyze_trade(ticker)
                if full_analysis and 'data' in full_analysis:
                    earning['expected_move'] = full_analysis['data'].get('expected_move')
                    earning['position_size'] = full_analysis['data'].get('position_size', '0%')
                    earning['iv_rank'] = full_analysis['data'].get('iv_rank')
                    earning['criteria_met'] = full_analysis['data'].get('criteria_met', {})
                    
                    # Extract market cap if available
                    if 'market_cap' in full_analysis['data']:
                        earning['market_cap_numeric'] = full_analysis['data']['market_cap']
            except Exception as e:
                logger.error(f"Error getting full analysis for {ticker}: {e}")
                earning['criteria_met'] = {}
        
        analyzed.append(earning)
    
    # Completion is now handled via SSE in the streaming endpoint
    
    return analyzed

async def get_quick_analysis(ticker: str):
    """
    Get quick recommendation and risk level for a ticker
    Returns simplified analysis for table display
    """
    try:
        from analysis_engine import compute_recommendation, yang_zhang
        import yfinance as yf
        
        # Get real data from compute_recommendation
        result = compute_recommendation(ticker)
        
        # Handle errors from the analysis
        if "error" in result:
            return {
                "recommendation": "AVOID",
                "riskLevel": "HIGH"
            }
        
        # Get additional data
        stock = yf.Ticker(ticker)
        price_history = stock.history(period='3mo')
        historical_vol = yang_zhang(price_history) if not price_history.empty else 0.30
        
        # Get IV data
        front_iv = result.get('front_iv', 0.35)
        current_iv = front_iv if front_iv else 0.35
        
        # Determine recommendation based on criteria
        avg_volume_pass = result.get('avg_volume', False)
        iv30_rv30_pass = result.get('iv30_rv30', False)
        ts_slope_pass = result.get('ts_slope_0_45', False)
        
        # Match original calculator logic
        if avg_volume_pass and iv30_rv30_pass and ts_slope_pass:
            recommendation = "RECOMMENDED"
            risk_level = "LOW"
        elif ts_slope_pass and (avg_volume_pass or iv30_rv30_pass):
            recommendation = "CONSIDER"
            risk_level = "MODERATE"
        else:
            recommendation = "AVOID"
            risk_level = "HIGH"
        
        return {
            "recommendation": recommendation,
            "riskLevel": risk_level
        }
        
    except Exception as e:
        logger.error(f"Quick analysis failed for {ticker}: {str(e)}")
        return {
            "recommendation": "AVOID",
            "riskLevel": "HIGH"
        }

async def fetch_earnings_calendar():
    """
    Fetch earnings calendar from NASDAQ (free, no API key required)
    Note: NASDAQ requires individual date queries, so this is now deprecated.
    Use fetch_earnings_from_api directly with a specific date.
    """
    global earnings_cache, cache_timestamp
    
    # Check if cache is still valid
    if cache_timestamp and datetime.now() - cache_timestamp < CACHE_DURATION:
        return earnings_cache
    
    # For NASDAQ, we'll just return empty dict and fetch per-date as needed
    # This maintains compatibility but encourages per-date fetching
    logger.info("fetch_earnings_calendar called - NASDAQ requires per-date fetching")
    return {}

@app.get("/api/earnings/{date_str}")
async def get_earnings_by_date(date_str: str, include_analysis: bool = False, force_fetch: bool = False):
    """
    Get earnings for a specific date
    Format: YYYY-MM-DD
    Priority: 1) Database cache (unless force_fetch), 2) Fetch and store if no data exists
    
    Args:
        date_str: Date in YYYY-MM-DD format
        include_analysis: Include trading analysis for each stock
        force_fetch: Force refresh from API even if cached (for cron jobs)
    """
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from database_operations import get_cached_earnings_for_date, fetch_and_store_earnings_for_date, check_date_has_data, store_earnings_with_analysis
    
    logger.info(f"=== EARNINGS REQUEST for {date_str} ===")
    logger.info(f"Include analysis: {include_analysis}, Force fetch: {force_fetch}")
    
    try:
        # Parse the date
        earnings_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        
        # If not forcing refresh, try to get cached data first
        if not force_fetch:
            logger.info(f"Checking for cached data for {date_str}...")
            cached_data = get_cached_earnings_for_date(date_str)
            if cached_data:
                logger.info(f"✅ Found cached data for {date_str}: {len(cached_data)} records")
                return {
                    "date": date_str,
                    "earnings": cached_data,
                    "source": "database_cache",
                    "count": len(cached_data)
                }
            else:
                logger.info(f"❌ No cached data found for {date_str}")
        
        # Check if we need to fetch new data
        has_data = check_date_has_data(earnings_date)
        logger.info(f"Database has data for {date_str}: {has_data}")
        
        if not has_data or force_fetch:
            logger.info(f"📥 Initiating fresh fetch for {date_str}")
            success = await fetch_and_store_earnings_for_date(date_str, force_refresh=force_fetch)
            
            if success:
                logger.info(f"✅ Successfully fetched and stored data for {date_str}")
                # Get the newly stored data
                cached_data = get_cached_earnings_for_date(date_str)
                if cached_data:
                    logger.info(f"Returning {len(cached_data)} fresh records for {date_str}")
                    return {
                        "date": date_str,
                        "earnings": cached_data,
                        "source": "fresh_fetch",
                        "count": len(cached_data)
                    }
            else:
                logger.warning(f"⚠️ Failed to fetch data for {date_str}")
        
        # Try existing database logic as fallback
        conn = get_db_connection()
        if conn:
            try:
                with conn.cursor() as cursor:
                    sql = """
                        SELECT 
                            ticker,
                            company_name as "companyName",
                            report_date as "reportDate",
                            CASE 
                                WHEN report_time = 'time-pre-market' THEN 'BMO'
                                WHEN report_time = 'time-after-hours' THEN 'AMC'
                                WHEN report_time = 'time-not-supplied' THEN 'TBD'
                                ELSE 'TBD'
                            END as "reportTime",
                            market_cap as "marketCap",
                            fiscal_quarter_ending as "fiscalQuarterEnding",
                            eps_forecast as estimate,
                            num_estimates as "numEstimates",
                            last_year_eps as "lastYearEPS",
                            market_cap_numeric as "marketCapNumeric",
                            eps_forecast_numeric as "epsForecastNumeric"
                        FROM earnings_calendar
                        WHERE report_date = %s
                        ORDER BY market_cap_numeric DESC NULLS LAST
                    """
                    cursor.execute(sql, (earnings_date,))
                    earnings_list = cursor.fetchall()
                    
                    # Format the response
                    formatted_earnings = []
                    for idx, earning in enumerate(earnings_list):
                        earning_data = {
                            "id": str(idx + 1),
                            "ticker": earning["ticker"],
                            "companyName": earning["companyName"],
                            "reportTime": earning["reportTime"],
                            "marketCap": earning["marketCap"],
                            "fiscalQuarterEnding": earning["fiscalQuarterEnding"],
                            "estimate": earning["estimate"],
                            "numEstimates": earning["numEstimates"],
                            "lastYearEPS": earning["lastYearEPS"]
                        }
                        
                        # Optionally include quick analysis
                        if include_analysis:
                            analysis = await get_quick_analysis(earning["ticker"])
                            earning_data["recommendation"] = analysis.get("recommendation", "AVOID")
                            earning_data["riskLevel"] = analysis.get("riskLevel", "UNKNOWN")
                        
                        formatted_earnings.append(earning_data)
                    
                    logger.info(f"Found {len(formatted_earnings)} earnings from database for {date_str}")
                    
                    return {
                        "date": date_str,
                        "earnings": formatted_earnings,
                        "count": len(formatted_earnings),
                        "source": "database"
                    }
                    
            except Exception as e:
                logger.error(f"Database query failed: {str(e)}")
            finally:
                conn.close()
        
        # Fall back to API if database not available
        logger.info("Falling back to Alpha Vantage API")
        all_earnings = await fetch_earnings_calendar()
        earnings_list = all_earnings.get(date_str, [])
        
        # Optionally add analysis to API results
        if include_analysis and earnings_list:
            for earning in earnings_list:
                analysis = await get_quick_analysis(earning.get("ticker", ""))
                earning["recommendation"] = analysis.get("recommendation", "AVOID")
                earning["riskLevel"] = analysis.get("riskLevel", "UNKNOWN")
        
        return {
            "date": date_str,
            "earnings": earnings_list,
            "count": len(earnings_list),
            "source": "alpha_vantage"
        }
        
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

@app.get("/api/earnings/calendar/month")
async def get_monthly_earnings(year: int, month: int):
    """
    Get all earnings dates for a specific month
    Priority: 1) Database, 2) Alpha Vantage API
    """
    # First try database
    conn = get_db_connection()
    if conn:
        try:
            with conn.cursor() as cursor:
                sql = """
                    SELECT DISTINCT report_date
                    FROM earnings_calendar
                    WHERE EXTRACT(YEAR FROM report_date) = %s
                    AND EXTRACT(MONTH FROM report_date) = %s
                    ORDER BY report_date
                """
                cursor.execute(sql, (year, month))
                results = cursor.fetchall()
                
                filtered_dates = [row["report_date"].strftime("%Y-%m-%d") for row in results]
                
                logger.info(f"Found {len(filtered_dates)} earnings dates from database for {year}-{month:02d}")
                
                return {
                    "year": year,
                    "month": month,
                    "earnings_dates": filtered_dates,
                    "count": len(filtered_dates),
                    "source": "database"
                }
                
        except Exception as e:
            logger.error(f"Database query failed: {str(e)}")
        finally:
            conn.close()
    
    # Fall back to API
    logger.info("Falling back to Alpha Vantage API for monthly earnings")
    all_earnings = await fetch_earnings_calendar()
    
    # Filter for requested month
    filtered_dates = []
    for date_str in all_earnings.keys():
        try:
            d = datetime.strptime(date_str, "%Y-%m-%d").date()
            if d.year == year and d.month == month:
                filtered_dates.append(date_str)
        except:
            continue
    
    return {
        "year": year,
        "month": month,
        "earnings_dates": sorted(filtered_dates),
        "count": len(filtered_dates),
        "source": "alpha_vantage"
    }

@app.get("/api/earnings/alpha-vantage/{date_str}")
async def get_earnings_from_alpha_vantage(date_str: str):
    """
    Get real earnings data from Alpha Vantage API
    """
    if not ALPHA_VANTAGE_API_KEY:
        raise HTTPException(status_code=500, detail="Alpha Vantage API key not configured")
    
    try:
        # Alpha Vantage earnings calendar endpoint
        params = {
            "function": "EARNINGS_CALENDAR",
            "horizon": "3month",  # Can be "3month" or "12month"
            "apikey": ALPHA_VANTAGE_API_KEY
        }
        
        response = requests.get(AV_BASE_URL, params=params)
        
        if response.status_code != 200:
            raise HTTPException(status_code=502, detail="Failed to fetch data from Alpha Vantage")
        
        # Parse CSV response
        # Note: Alpha Vantage returns CSV format for earnings calendar
        import csv
        from io import StringIO
        
        csv_data = StringIO(response.text)
        reader = csv.DictReader(csv_data)
        
        earnings_list = []
        target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        
        for row in reader:
            report_date = datetime.strptime(row['reportDate'], "%Y-%m-%d").date()
            if report_date == target_date:
                earnings_list.append({
                    "ticker": row['symbol'],
                    "companyName": row['name'] if 'name' in row else row['symbol'],
                    "reportTime": row.get('time', 'TBD'),
                    "estimate": row.get('estimate', 'N/A'),
                    "currency": row.get('currency', 'USD')
                })
        
        return {
            "date": date_str,
            "earnings": earnings_list,
            "source": "alpha_vantage"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching earnings data: {str(e)}")

@app.post("/api/analyze/batch")
async def analyze_batch(tickers: List[str]):
    """
    Batch analyze multiple tickers for performance
    """
    results = {}
    for ticker in tickers[:10]:  # Limit to 10 tickers to avoid timeout
        analysis = await get_quick_analysis(ticker)
        results[ticker] = analysis
    
    return results

@app.get("/api/stock/{ticker}/complete")
async def get_stock_complete(ticker: str):
    """Get both stock details and analysis in a single call for faster loading"""
    logger.info(f"Getting complete data for {ticker}")
    
    # Get stock details from database
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")
    
    stock_data = None
    try:
        with conn.cursor() as cursor:
            # Look for the stock in any recent date
            sql = """
                SELECT DISTINCT ON (ticker)
                    ticker,
                    company_name as companyName,
                    report_date as reportDate,
                    report_time as reportTime,
                    market_cap as marketCap,
                    eps_forecast as estimate,
                    fiscal_quarter_ending as fiscalQuarterEnding,
                    recommendation,
                    position_size,
                    expected_move,
                    iv_rank
                FROM earnings_calendar
                WHERE ticker = %s
                ORDER BY ticker, report_date DESC
                LIMIT 1
            """
            
            cursor.execute(sql, (ticker.upper(),))
            result = cursor.fetchone()
            
            if result:
                # Convert RealDictRow to a regular dict
                # PostgreSQL lowercases column names, so we need to map them correctly
                row_dict = dict(result) if hasattr(result, 'items') else dict(zip([desc[0] for desc in cursor.description], result))
                
                stock_data = {
                    "ticker": row_dict.get('ticker'),
                    "companyName": row_dict.get('companyname'),
                    "reportDate": row_dict.get('reportdate'),
                    "reportTime": row_dict.get('reporttime'),
                    "marketCap": row_dict.get('marketcap'),
                    "estimate": row_dict.get('estimate'),
                    "fiscalQuarterEnding": row_dict.get('fiscalquarterending'),
                    "recommendation": row_dict.get('recommendation'),
                    "position_size": row_dict.get('position_size'),
                    "expected_move": row_dict.get('expected_move'),
                    "iv_rank": row_dict.get('iv_rank')
                }
                
                # Convert date to string
                if stock_data.get('reportDate'):
                    stock_data['reportDate'] = stock_data['reportDate'].strftime("%Y-%m-%d")
                
                # Convert numeric fields
                for field in ['position_size', 'expected_move', 'iv_rank']:
                    if field in stock_data and stock_data[field] is not None:
                        try:
                            value = stock_data[field]
                            if isinstance(value, str):
                                value = value.replace('%', '').strip()
                            float_val = float(value) if value else None
                            if float_val is not None:
                                import math
                                if math.isnan(float_val) or math.isinf(float_val):
                                    stock_data[field] = None
                                else:
                                    stock_data[field] = float_val
                            else:
                                stock_data[field] = None
                        except (ValueError, TypeError):
                            stock_data[field] = None
            else:
                # If not found in database, return minimal data
                logger.info(f"Stock {ticker} not found in database, returning minimal data")
                stock_data = {
                    "ticker": ticker.upper(),
                    "companyName": ticker.upper(),
                    "reportDate": None,
                    "reportTime": "TBD",
                    "marketCap": "-",
                    "estimate": "-",
                    "fiscalQuarterEnding": "-"
                }
                
    except Exception as e:
        logger.error(f"Error getting stock details: {e}")
    finally:
        conn.close()
    
    # Get analysis data
    analysis_data = None
    try:
        # Import the analysis engine without GUI dependencies
        from analysis_engine import compute_recommendation, yang_zhang
        import yfinance as yf
        
        # Get real data from compute_recommendation
        result = compute_recommendation(ticker)
        
        # Handle errors from the analysis
        if "error" in result:
            analysis_data = {
                "current_iv": "N/A",
                "historical_iv": "N/A",
                "iv_rank": 50,
                "suggested_strategy": "Unable to analyze - " + result['error'],
                "expected_move": "N/A",
                "recommendation": "AVOID",
                "risk_level": "UNKNOWN",
                "position_size": "0%",
                "error": result['error']
            }
        else:
            # Get additional market data
            stock = yf.Ticker(ticker)
            info = stock.info
            current_price = result.get('underlying_price', info.get('currentPrice', info.get('regularMarketPrice', 0)))
            
            # Get historical data for IV calculations
            price_history = stock.history(period='3mo')
            historical_vol = yang_zhang(price_history) if not price_history.empty else 0.30
            
            # Determine recommendation based on criteria
            # The compute_recommendation function returns direct boolean values
            # Convert numpy.bool to Python bool for JSON serialization
            criteria_met = {
                "volume_check": bool(result.get("avg_volume", False)),
                "iv_rv_ratio": bool(result.get("iv30_rv30", False)),
                "term_structure": bool(result.get("ts_slope_0_45", False))
            }
            num_criteria_met = sum([
                criteria_met["volume_check"],
                criteria_met["iv_rv_ratio"],
                criteria_met["term_structure"]
            ])
            
            if num_criteria_met >= 3:
                recommendation = "RECOMMENDED"
                position_size = "6%"
            elif num_criteria_met >= 2:
                recommendation = "CONSIDER"
                position_size = "3%"
            else:
                recommendation = "AVOID"
                position_size = "0%"
            
            # Handle expected_move - it might be a string with % or None
            expected_move = result.get('expected_move')
            if expected_move is None:
                expected_move = f"{current_price * 0.05:.1f}%" if current_price else "N/A"
            
            # Calculate IV rank (simplified - would need historical IV data for accurate calculation)
            # This maps IV from 15% (low) to 60% (high) to a 0-100 scale
            front_iv = result.get('front_iv', 0.35)
            iv_rank = min(100, max(0, int((front_iv - 0.15) / (0.60 - 0.15) * 100)))
            
            analysis_data = {
                "current_iv": f"{front_iv * 100:.1f}%",
                "historical_iv": f"{historical_vol * 100:.1f}%",
                "iv_rank": iv_rank,
                "suggested_strategy": result.get('strategy', 'Calendar Spread'),
                "expected_move": expected_move,
                "recommendation": recommendation,
                "position_size": position_size,
                "criteria_met": criteria_met,
                "trade_details": result.get('trade_details', None)
            }
    except Exception as e:
        logger.error(f"Error during analysis: {e}")
        analysis_data = {
            "current_iv": "N/A",
            "historical_iv": "N/A",
            "iv_rank": 50,
            "suggested_strategy": "Analysis unavailable",
            "expected_move": "N/A",
            "recommendation": "AVOID",
            "position_size": "0%",
            "error": str(e)
        }
    
    # Return combined response
    return {
        "ticker": ticker,
        "details": stock_data,
        "analysis": analysis_data
    }

@app.get("/api/stock/{ticker}/details")
async def get_stock_details(ticker: str):
    """Get stock details from cache quickly"""
    logger.info(f"Getting cached details for {ticker}")
    
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")
    
    try:
        with conn.cursor() as cursor:
            # Look for the stock in any recent date
            sql = """
                SELECT DISTINCT ON (ticker)
                    ticker,
                    company_name as companyName,
                    report_date as reportDate,
                    report_time as reportTime,
                    market_cap as marketCap,
                    eps_forecast as estimate,
                    fiscal_quarter_ending as fiscalQuarterEnding,
                    recommendation,
                    position_size,
                    expected_move,
                    iv_rank
                FROM earnings_calendar
                WHERE ticker = %s
                ORDER BY ticker, report_date DESC
                LIMIT 1
            """
            
            cursor.execute(sql, (ticker.upper(),))
            result = cursor.fetchone()
            
            if result:
                # Convert result to a regular dict with correct casing
                stock_data = {
                    "ticker": result[0],
                    "companyName": result[1],
                    "reportDate": result[2],
                    "reportTime": result[3],
                    "marketCap": result[4],
                    "estimate": result[5],
                    "fiscalQuarterEnding": result[6],
                    "recommendation": result[7],
                    "position_size": result[8],
                    "expected_move": result[9],
                    "iv_rank": result[10]
                }
                
                # Convert date to string
                if stock_data.get('reportDate'):
                    stock_data['reportDate'] = stock_data['reportDate'].strftime("%Y-%m-%d")
                
                # Convert numeric fields
                for field in ['position_size', 'expected_move', 'iv_rank']:
                    if field in stock_data and stock_data[field] is not None:
                        try:
                            value = stock_data[field]
                            if isinstance(value, str):
                                value = value.replace('%', '').strip()
                            float_val = float(value) if value else None
                            if float_val is not None:
                                import math
                                if math.isnan(float_val) or math.isinf(float_val):
                                    stock_data[field] = None
                                else:
                                    stock_data[field] = float_val
                            else:
                                stock_data[field] = None
                        except (ValueError, TypeError):
                            stock_data[field] = None
                
                logger.info(f"Found cached details for {ticker}")
                return stock_data
            else:
                raise HTTPException(status_code=404, detail=f"Stock {ticker} not found")
                
    except Exception as e:
        logger.error(f"Error getting stock details: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@app.post("/api/analyze/{ticker}")
async def analyze_trade(ticker: str):
    """
    Trigger trade analysis for a specific ticker using actual calculator logic
    """
    try:
        logger.info(f"Starting analysis for {ticker}")
        
        # Import the analysis engine without GUI dependencies
        from analysis_engine import compute_recommendation, yang_zhang
        import yfinance as yf
        
        # Get real data from compute_recommendation
        result = compute_recommendation(ticker)
        
        # Handle errors from the analysis
        if "error" in result:
            logger.warning(f"Analysis warning for {ticker}: {result['error']}")
            return {
                "ticker": ticker,
                "status": "partial", 
                "message": f"Limited analysis for {ticker}",
                "data": {
                    "current_iv": "N/A",
                    "historical_iv": "N/A",
                    "iv_rank": 50,
                    "suggested_strategy": "Unable to analyze - " + result['error'],
                    "expected_move": "N/A",
                    "recommendation": "AVOID",
                    "risk_level": "UNKNOWN",
                    "position_size": "0%",
                    "error": result['error']
                }
            }
        
        # Get additional market data
        stock = yf.Ticker(ticker)
        info = stock.info
        current_price = result.get('underlying_price', info.get('currentPrice', info.get('regularMarketPrice', 0)))
        
        # Get historical data for IV calculations
        price_history = stock.history(period='3mo')
        historical_vol = yang_zhang(price_history) if not price_history.empty else 0.30
        
        # Get options data for more details
        if stock.options:
            # Get front month expiry
            front_month = stock.options[0] if stock.options else None
            back_month = stock.options[1] if len(stock.options) > 1 else None
            front_iv = result.get('front_iv', 0.35)
        else:
            front_month = None
            back_month = None
            front_iv = result.get('front_iv', 0.35)
        
        # Calculate IV rank (simplified - would need historical IV data for accurate calculation)
        current_iv = front_iv if front_iv else 0.35
        iv_rank = min(100, max(0, int((current_iv - 0.15) / (0.60 - 0.15) * 100)))
        
        # Determine recommendation based on criteria
        avg_volume_pass = result.get('avg_volume', False)
        iv30_rv30_pass = result.get('iv30_rv30', False)
        ts_slope_pass = result.get('ts_slope_0_45', False)
        
        # Match original calculator logic
        if avg_volume_pass and iv30_rv30_pass and ts_slope_pass:
            suggested_strategy = "Calendar Spread"
            recommendation = "RECOMMENDED"
            risk_level = "LOW"
        elif ts_slope_pass and (avg_volume_pass or iv30_rv30_pass):
            suggested_strategy = "Consider Position"
            recommendation = "CONSIDER"
            risk_level = "MODERATE"
        else:
            suggested_strategy = "Wait for Better Setup"
            recommendation = "AVOID"
            risk_level = "HIGH"
        
        # Calculate position size using simplified Kelly Criterion
        # For calendar spreads with high probability: typically 5-10% of portfolio
        if recommendation == "RECOMMENDED":
            position_size = "6-8%"
        elif recommendation == "CONSIDER":
            position_size = "2-3%"
        else:
            position_size = "0%"
        
        analysis_result = {
            "ticker": ticker,
            "status": "completed",
            "message": f"Analysis for {ticker} completed",
            "data": {
                "current_iv": f"{current_iv*100:.1f}%",
                "historical_iv": f"{historical_vol*100:.1f}%",
                "iv_rank": iv_rank,
                "suggested_strategy": suggested_strategy,
                "expected_move": f"±{result.get('expected_move', 'N/A')}" if result.get('expected_move') else "N/A",
                "recommendation": recommendation,
                "risk_level": risk_level,
                "position_size": position_size,
                "criteria_met": {
                    "volume_check": bool(result.get('avg_volume', False)),
                    "iv_rv_ratio": bool(result.get('iv30_rv30', False)),
                    "term_structure": bool(result.get('ts_slope_0_45', False))
                },
                "front_month_expiry": front_month if front_month else "N/A",
                "back_month_expiry": back_month if back_month else "N/A",
                "current_price": f"${current_price:.2f}" if current_price else "N/A"
            }
        }
        
        return analysis_result
        
    except Exception as e:
        logger.error(f"Analysis failed for {ticker}: {str(e)}")
        # Return a degraded response with limited data
        return {
            "ticker": ticker,
            "status": "partial",
            "message": f"Limited analysis for {ticker}",
            "data": {
                "current_iv": "N/A",
                "historical_iv": "N/A",
                "iv_rank": 50,
                "suggested_strategy": "Unable to analyze",
                "expected_move": "N/A",
                "recommendation": "AVOID",
                "risk_level": "UNKNOWN",
                "position_size": "0%",
                "error": str(e)
            }
        }

@app.get("/api/earnings/{date_str}/stream")
async def earnings_stream_with_analysis(date_str: str):
    """
    Server-Sent Events endpoint for real-time earnings data with analysis progress
    Combines fetching and analysis in a single streaming response
    """
    # Import database function at endpoint level
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from database_operations import store_earnings_with_analysis
    
    async def generate() -> AsyncGenerator[str, None]:
        try:
            # Temporarily disable cache to always fetch fresh data
            # TODO: Re-implement proper cache invalidation logic
            cached_data = None
            
            # No cached data, need to fetch and analyze
            yield f"data: {safe_json_dumps({'type': 'start', 'message': 'Fetching earnings data...'})}\n\n"
            
            # Fetch earnings from NASDAQ
            earnings_list = await fetch_earnings_from_api(date_str)
            
            if not earnings_list:
                yield f"data: {safe_json_dumps({'type': 'complete', 'earnings': [], 'source': 'fresh_fetch'})}\n\n"
                return
            
            total_stocks = len(earnings_list)
            yield f"data: {safe_json_dumps({'type': 'fetched', 'total': total_stocks, 'message': f'Analyzing {total_stocks} stocks...'})}\n\n"
            
            # Analyze each stock and send progress
            analyzed_earnings = []
            
            for idx, earning in enumerate(earnings_list):
                ticker = earning.get('ticker', '')
                
                # Send progress update
                yield f"data: {safe_json_dumps({
                    'type': 'progress',
                    'current': idx + 1,
                    'total': total_stocks,
                    'ticker': ticker,
                    'percentage': int(((idx + 1) / total_stocks) * 100),
                    'message': f'Analyzing {ticker}...'
                })}\n\n"
                
                if ticker:
                    # Get analysis
                    logger.info(f"Starting analysis for {ticker}")
                    analysis = await get_quick_analysis(ticker)
                    
                    # Merge analysis with earnings data
                    earning['recommendation'] = analysis.get('recommendation', 'AVOID')
                    earning['riskLevel'] = analysis.get('riskLevel', 'HIGH')
                    
                    # Get full analysis for more details
                    try:
                        full_analysis = await analyze_trade(ticker)
                        if full_analysis and 'data' in full_analysis:
                            earning['expected_move'] = full_analysis['data'].get('expected_move')
                            earning['position_size'] = full_analysis['data'].get('position_size', '0%')
                            earning['iv_rank'] = full_analysis['data'].get('iv_rank')
                            earning['criteria_met'] = full_analysis['data'].get('criteria_met', {})
                            
                            # Extract market cap if available
                            if 'market_cap' in full_analysis['data']:
                                earning['market_cap_numeric'] = full_analysis['data']['market_cap']
                            
                            # Calculate priority score for RECOMMENDED trades
                            if earning.get('recommendation') == 'RECOMMENDED':
                                try:
                                    from analysis_engine import calculate_priority_score
                                    # Get the raw analysis data for scoring
                                    raw_analysis = await get_quick_analysis(ticker) 
                                    if raw_analysis and not raw_analysis.get('error'):
                                        priority_score = calculate_priority_score(raw_analysis)
                                        earning['priority_score'] = priority_score
                                        logger.info(f"Priority score for {ticker}: {priority_score}")
                                    else:
                                        earning['priority_score'] = 0.0
                                except Exception as score_error:
                                    logger.warning(f"Priority score calculation failed for {ticker}: {score_error}")
                                    earning['priority_score'] = 0.0
                            else:
                                earning['priority_score'] = 0.0
                    except Exception as e:
                        logger.warning(f"Analysis warning for {ticker}: {e}")
                        earning['criteria_met'] = {}
                
                analyzed_earnings.append(earning)
                
                # Small delay to prevent overwhelming
                if idx < total_stocks - 1:  # Don't delay after last item
                    await asyncio.sleep(0.05)
            
            # Store in database
            try:
                from database_operations import store_earnings_with_analysis
                await store_earnings_with_analysis(date_str, analyzed_earnings)
                logger.info(f"Successfully stored {len(analyzed_earnings)} earnings for {date_str}")
            except Exception as store_error:
                logger.error(f"Failed to store earnings data: {store_error}")
                # Continue with response even if storage fails
            
            # Send complete event with all analyzed data
            yield f"data: {safe_json_dumps({
                'type': 'complete',
                'earnings': analyzed_earnings,
                'source': 'fresh_fetch',
                'total': total_stocks
            })}\n\n"
            
        except Exception as e:
            logger.error(f"Error in SSE stream: {e}")
            yield f"data: {safe_json_dumps({'type': 'error', 'message': str(e)})}\n\n"
    
    return StreamingResponse(
        generate(), 
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        }
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)