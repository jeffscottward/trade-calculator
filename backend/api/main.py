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
import math

# Import database operations module
from . import database_operations

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Earnings Calendar API")

# Priority Scoring Functions
def parse_market_cap_string(market_cap_str: str) -> float:
    """Parse market cap string like '$1.5B' to numeric value."""
    if not market_cap_str:
        return 0
    
    clean_str = market_cap_str.replace('$', '').replace(',', '').strip()
    
    if not clean_str or clean_str == '-':
        return 0
    
    try:
        if clean_str.endswith('T'):
            return float(clean_str[:-1]) * 1_000_000_000_000
        elif clean_str.endswith('B'):
            return float(clean_str[:-1]) * 1_000_000_000
        elif clean_str.endswith('M'):
            return float(clean_str[:-1]) * 1_000_000
        else:
            return float(clean_str)
    except (ValueError, AttributeError):
        return 0

def calculate_priority_score_components(iv_rv_ratio: float, term_slope: float, 
                                       avg_volume_30d: float, market_cap: float) -> Dict:
    """Calculate priority score with component breakdown."""
    logger.debug(f"Calculating priority score - IV/RV: {iv_rv_ratio}, Slope: {term_slope}, Vol: {avg_volume_30d}, MCap: {market_cap}")
    
    # IV/RV Score (40% weight)
    if iv_rv_ratio <= 1.0:
        iv_rv_score = 0.0
    else:
        iv_rv_score = min(100.0, max(0.0, (iv_rv_ratio - 1.0) * 50))
    
    # Term Slope Score (30% weight)
    if term_slope >= 0:
        term_slope_score = 0.0
    else:
        term_slope_score = min(100.0, max(0.0, abs(term_slope) * 200))
    
    # Liquidity Score (20% weight)
    if avg_volume_30d < 1_000_000:
        liquidity_score = 0.0
    else:
        log_volume = math.log10(avg_volume_30d)
        liquidity_score = min(100.0, max(0.0, (log_volume - 6) * 50))
    
    # Market Cap Score (10% weight)
    if market_cap < 1_000_000_000:
        market_cap_score = 0.0
    else:
        log_cap = math.log10(market_cap)
        market_cap_score = min(100.0, max(0.0, (log_cap - 9) * 33.33))
    
    # Calculate weighted total
    priority_score = (
        iv_rv_score * 0.40 +
        term_slope_score * 0.30 +
        liquidity_score * 0.20 +
        market_cap_score * 0.10
    )
    
    return {
        'priority_score': round(priority_score, 2),
        'iv_rv_score': round(iv_rv_score, 2),
        'term_slope_score': round(term_slope_score, 2),
        'liquidity_score': round(liquidity_score, 2),
        'market_cap_score': round(market_cap_score, 2)
    }

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001", "http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Using NASDAQ API - free, no key required for earnings data

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
        from .analysis_engine import compute_recommendation, yang_zhang
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
        
        # Extract raw values for priority scoring
        iv_rv_ratio_raw = result.get('iv_rv_ratio_raw', 1.0) 
        term_structure_slope_raw = result.get('term_structure_slope_raw', 0.0)
        avg_volume_raw = result.get('avg_volume_raw', 1000000)
        
        return {
            "recommendation": recommendation,
            "riskLevel": risk_level,
            "iv_rv_ratio_raw": iv_rv_ratio_raw,
            "term_structure_slope_raw": term_structure_slope_raw,
            "avg_volume_raw": avg_volume_raw
        }
        
    except Exception as e:
        logger.error(f"Quick analysis failed for {ticker}: {str(e)}")
        return {
            "recommendation": "AVOID",
            "riskLevel": "HIGH"
        }


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
    # Use database operations imported at module level
    
    logger.info(f"=== EARNINGS REQUEST for {date_str} ===")
    logger.info(f"Include analysis: {include_analysis}, Force fetch: {force_fetch}")
    
    try:
        # Parse the date
        earnings_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        
        # If not forcing refresh, try to get cached data first
        if not force_fetch:
            logger.info(f"Checking for cached data for {date_str}...")
            cached_data = database_operations.get_cached_earnings_for_date(date_str)
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
        has_data = database_operations.check_date_has_data(earnings_date)
        logger.info(f"Database has data for {date_str}: {has_data}")
        
        if not has_data or force_fetch:
            logger.info(f"📥 Initiating fresh fetch for {date_str}")
            success = await database_operations.fetch_and_store_earnings_for_date(date_str, force_refresh=force_fetch)
            
            if success:
                logger.info(f"✅ Successfully fetched and stored data for {date_str}")
                # Get the newly stored data
                cached_data = database_operations.get_cached_earnings_for_date(date_str)
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
                            eps_forecast_numeric as "epsForecastNumeric",
                            priority_score,
                            recommendation,
                            risk_level as "riskLevel",
                            expected_move,
                            position_size,
                            iv_rank,
                            avg_volume_pass,
                            iv_rv_ratio_pass,
                            term_structure_pass
                        FROM earnings_calendar
                        WHERE report_date = %s
                        ORDER BY priority_score DESC NULLS LAST, market_cap_numeric DESC NULLS LAST
                    """
                    cursor.execute(sql, (earnings_date,))
                    columns = [desc[0] for desc in cursor.description]
                    earnings_list = []
                    for row in cursor.fetchall():
                        earnings_list.append(dict(zip(columns, row)))
                    
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
                            "lastYearEPS": earning["lastYearEPS"],
                            "priority_score": earning.get("priority_score", 0.0),
                            "recommendation": earning.get("recommendation", "AVOID"),
                            "riskLevel": earning.get("riskLevel", "HIGH"),
                            "expected_move": earning.get("expected_move"),
                            "position_size": earning.get("position_size", "0%"),
                            "iv_rank": earning.get("iv_rank"),
                            "criteria_met": {
                                "volume_check": earning.get("avg_volume_pass", False),
                                "iv_rv_ratio": earning.get("iv_rv_ratio_pass", False),
                                "term_structure": earning.get("term_structure_pass", False)
                            }
                        }
                        
                        # Optionally override with fresh analysis
                        if include_analysis:
                            analysis = await get_quick_analysis(earning["ticker"])
                            if analysis and not analysis.get("error"):
                                earning_data["recommendation"] = analysis.get("recommendation", earning_data["recommendation"])
                                earning_data["riskLevel"] = analysis.get("riskLevel", earning_data["riskLevel"])
                        
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
        
        # Return empty list if database not available
        logger.info("Database not available, returning empty earnings list")
        return {
            "date": date_str,
            "earnings": [],
            "count": 0,
            "source": "none"
        }
        
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

@app.get("/api/earnings/calendar/month")
async def get_monthly_earnings(year: int, month: int):
    """
    Get all earnings dates for a specific month from database
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
    
    # Return empty list if database not available
    logger.info("Database not available for monthly earnings")
    return {
        "year": year,
        "month": month,
        "earnings_dates": [],
        "count": 0,
        "source": "none"
    }


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
                    iv_rank,
                    priority_score
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
                    "iv_rank": row_dict.get('iv_rank'),
                    "priority_score": row_dict.get('priority_score')
                }
                
                # Convert date to string
                if stock_data.get('reportDate'):
                    stock_data['reportDate'] = stock_data['reportDate'].strftime("%Y-%m-%d")
                
                # Convert numeric fields
                for field in ['position_size', 'expected_move', 'iv_rank', 'priority_score']:
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
        from .analysis_engine import compute_recommendation, yang_zhang
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
            
            # Calculate IV rank with improved scaling
            # Historical data shows most earnings IVs range from 20% to 100%+
            # Use a more realistic scale that doesn't cap at 60%
            front_iv = result.get('front_iv', 0.35)
            # Map IV from 20% (low) to 80% (high) for a more realistic distribution
            # Values above 80% will still show high rank but not always 100%
            iv_rank = min(100, max(0, int((front_iv - 0.20) / (0.80 - 0.20) * 100)))
            
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
                for field in ['position_size', 'expected_move', 'iv_rank', 'priority_score']:
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
        from .analysis_engine import compute_recommendation, yang_zhang
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
        
        # Calculate IV rank with improved scaling
        # Map IV from 20% (low) to 80% (high) for a more realistic distribution
        current_iv = front_iv if front_iv else 0.35
        iv_rank = min(100, max(0, int((current_iv - 0.20) / (0.80 - 0.20) * 100)))
        
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
    async def generate() -> AsyncGenerator[str, None]:
        try:
            # Check for cached data first
            logger.info(f"SSE endpoint called for {date_str}, checking cache...")
            cached_data = database_operations.get_cached_earnings_for_date(date_str)
            
            if cached_data:
                # Return cached data immediately
                logger.info(f"✅ Found cached earnings data for {date_str}: {len(cached_data)} records")
                yield f"data: {safe_json_dumps({
                    'type': 'cached',
                    'earnings': cached_data,
                    'source': 'database_cache',
                    'total': len(cached_data)
                })}\n\n"
                return
            
            # No cached data, need to fetch and analyze
            logger.info(f"❌ No cached data found for {date_str}, fetching fresh data...")
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
                            
                            # Calculate priority score for all trades
                            try:
                                # Get the necessary data for scoring
                                raw_analysis = await get_quick_analysis(ticker) 
                                if raw_analysis and not raw_analysis.get('error'):
                                    # Extract values with defaults
                                    iv_rv_ratio = raw_analysis.get('iv_rv_ratio_raw', 1.0)
                                    term_slope = raw_analysis.get('term_structure_slope_raw', 0.0)
                                    avg_volume = raw_analysis.get('avg_volume_raw', 1000000)
                                    
                                    # Parse market cap
                                    market_cap_str = earning.get('marketCap', '0')
                                    market_cap_numeric = parse_market_cap_string(market_cap_str)
                                    
                                    # Calculate scores
                                    scores = calculate_priority_score_components(
                                        iv_rv_ratio=iv_rv_ratio,
                                        term_slope=term_slope,
                                        avg_volume_30d=avg_volume,
                                        market_cap=market_cap_numeric
                                    )
                                    
                                    # Ensure CONSIDER stocks get a minimum priority score
                                    # If recommendation is CONSIDER but score is 0, give it a base score
                                    if earning.get('recommendation') == 'CONSIDER' and scores['priority_score'] == 0:
                                        # Calculate a basic score based on the criteria that passed
                                        base_score = 0
                                        if earning.get('criteria_met', {}).get('iv_rv_ratio', False):
                                            base_score += 3.0  # Base points for IV/RV pass
                                        if earning.get('criteria_met', {}).get('term_structure', False):
                                            base_score += 2.0  # Base points for term structure pass
                                        if earning.get('criteria_met', {}).get('volume_check', False):
                                            base_score += 1.0  # Base points for volume pass
                                        scores['priority_score'] = base_score
                                        logger.info(f"Assigned base priority score {base_score} to CONSIDER stock {ticker}")
                                    
                                    earning['priority_score'] = scores['priority_score']
                                    earning['iv_rv_score'] = scores['iv_rv_score']
                                    earning['term_slope_score'] = scores['term_slope_score']
                                    earning['liquidity_score'] = scores['liquidity_score']
                                    earning['market_cap_score'] = scores['market_cap_score']
                                    earning['market_cap_numeric'] = market_cap_numeric
                                    
                                    logger.info(f"Priority score for {ticker}: {scores['priority_score']} (IV/RV: {iv_rv_ratio}, Slope: {term_slope}, Vol: {avg_volume}, MCap: {market_cap_numeric})")
                                else:
                                    earning['priority_score'] = 0.0
                                    logger.warning(f"No analysis data for {ticker}")
                            except Exception as score_error:
                                logger.warning(f"Priority score calculation failed for {ticker}: {score_error}")
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
                await database_operations.store_earnings_with_analysis(date_str, analyzed_earnings)
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
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET",
            "Access-Control-Allow-Headers": "*",
        }
    )

@app.get("/api/trades/executed")
async def get_executed_trades():
    """
    Get all executed calendar spread trades from the database
    """
    conn = get_db_connection()
    if not conn:
        # Return mock calendar spread data if database not available
        mock_trades = [
            {
                "id": "1",
                "ticker": "AAPL",
                "companyName": "Apple Inc.",
                "tradeType": "Calendar Spread",
                "entryDate": "2024-01-15",
                "exitDate": "2024-01-17",
                "frontStrike": 185.00,
                "frontExpiry": "2024-01-19",
                "frontPremium": 3.45,
                "frontContracts": 10,
                "backStrike": 185.00,
                "backExpiry": "2024-02-16",
                "backPremium": 5.20,
                "backContracts": 10,
                "netDebit": 175.00,
                "pnl": 285.00,
                "ivCrush": 18.5,
                "expectedMove": 4.2,
                "actualMove": 2.8,
                "status": "closed",
                "recommendation": "RECOMMENDED",
                "positionSize": "6%"
            },
            {
                "id": "2", 
                "ticker": "MSFT",
                "companyName": "Microsoft Corporation",
                "tradeType": "Calendar Spread",
                "entryDate": "2024-01-20",
                "exitDate": "2024-01-22",
                "frontStrike": 415.00,
                "frontExpiry": "2024-01-26",
                "frontPremium": 4.85,
                "frontContracts": 5,
                "backStrike": 415.00,
                "backExpiry": "2024-02-23",
                "backPremium": 6.90,
                "backContracts": 5,
                "netDebit": 102.50,
                "pnl": -45.00,
                "ivCrush": 12.3,
                "expectedMove": 3.8,
                "actualMove": 5.2,
                "status": "closed",
                "recommendation": "CONSIDER",
                "positionSize": "3%"
            }
        ]
        return {"trades": mock_trades}
    
    try:
        with conn.cursor() as cursor:
            sql = """
                SELECT 
                    id,
                    symbol as ticker,
                    company_name,
                    trade_type,
                    entry_time as entry_date,
                    exit_time as exit_date,
                    front_strike,
                    front_expiry,
                    front_premium,
                    front_contracts,
                    back_strike,
                    back_expiry,
                    back_premium,
                    back_contracts,
                    net_debit,
                    pnl,
                    iv_crush,
                    expected_move,
                    actual_move,
                    status,
                    recommendation,
                    position_size,
                    created_at,
                    updated_at
                FROM trades 
                WHERE status = 'closed'
                ORDER BY exit_time DESC
            """
            cursor.execute(sql)
            trades = cursor.fetchall()
            
            # Convert to list of dicts and format dates
            formatted_trades = []
            for trade in trades:
                trade_dict = dict(trade)
                # Format dates as strings
                for date_field in ['entry_date', 'exit_date', 'created_at', 'updated_at']:
                    if trade_dict.get(date_field):
                        trade_dict[date_field] = trade_dict[date_field].isoformat()
                formatted_trades.append(trade_dict)
            
            return {"trades": formatted_trades}
            
    except Exception as e:
        logger.error(f"Error fetching executed trades: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    finally:
        conn.close()

@app.get("/api/trades/current")
async def get_current_holdings():
    """
    Get all current open calendar spread positions
    """
    conn = get_db_connection()
    if not conn:
        # Return mock calendar spread data if database not available
        mock_holdings = [
            {
                "id": "4",
                "ticker": "NVDA",
                "companyName": "NVIDIA Corporation",
                "tradeType": "Calendar Spread",
                "entryDate": "2024-08-22",
                "frontStrike": 120.00,
                "frontExpiry": "2024-08-30",
                "frontPremium": 2.85,
                "frontContracts": 8,
                "backStrike": 120.00,
                "backExpiry": "2024-09-27",
                "backPremium": 4.20,
                "backContracts": 8,
                "netDebit": 108.00,
                "currentPrice": 119.85,
                "unrealizedPnl": 42.00,
                "ivCrush": None,
                "expectedMove": 5.2,
                "status": "open",
                "recommendation": "RECOMMENDED",
                "positionSize": "6%",
                "daysHeld": 1,
                "expectedExit": "2024-08-24"
            },
            {
                "id": "5",
                "ticker": "TSLA", 
                "companyName": "Tesla, Inc.",
                "tradeType": "Calendar Spread",
                "entryDate": "2024-08-21",
                "frontStrike": 240.00,
                "frontExpiry": "2024-08-25",
                "frontPremium": 5.15,
                "frontContracts": 6,
                "backStrike": 240.00,
                "backExpiry": "2024-09-20",
                "backPremium": 7.85,
                "backContracts": 6,
                "netDebit": 162.00,
                "currentPrice": 238.50,
                "unrealizedPnl": -28.00,
                "ivCrush": None,
                "expectedMove": 7.8,
                "status": "open",
                "recommendation": "CONSIDER",
                "positionSize": "3%",
                "daysHeld": 2,
                "expectedExit": "2024-08-23"
            }
        ]
        return {"holdings": mock_holdings}
    
    try:
        with conn.cursor() as cursor:
            sql = """
                SELECT 
                    id,
                    symbol as ticker,
                    company_name,
                    trade_type,
                    entry_time as entry_date,
                    front_strike,
                    front_expiry,
                    front_premium,
                    front_contracts,
                    back_strike,
                    back_expiry,
                    back_premium,
                    back_contracts,
                    net_debit,
                    current_price,
                    unrealized_pnl,
                    iv_crush,
                    expected_move,
                    status,
                    recommendation,
                    position_size,
                    expected_exit_date,
                    created_at,
                    updated_at,
                    (CURRENT_DATE - entry_time::date) as days_held
                FROM trades 
                WHERE status = 'open'
                ORDER BY entry_time DESC
            """
            cursor.execute(sql)
            holdings = cursor.fetchall()
            
            # Convert to list of dicts and format dates
            formatted_holdings = []
            for holding in holdings:
                holding_dict = dict(holding)
                # Format dates as strings
                for date_field in ['entry_date', 'expected_exit_date', 'created_at', 'updated_at']:
                    if holding_dict.get(date_field):
                        holding_dict[date_field] = holding_dict[date_field].isoformat()
                formatted_holdings.append(holding_dict)
            
            return {"holdings": formatted_holdings}
            
    except Exception as e:
        logger.error(f"Error fetching current holdings: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    finally:
        conn.close()

@app.get("/api/trades/portfolio-history")
async def get_portfolio_history():
    """
    Get portfolio value history for chart display
    """
    conn = get_db_connection()
    if not conn:
        # Return mock portfolio history if database not available
        from datetime import datetime, timedelta
        mock_history = []
        base_value = 100000
        for i in range(30):
            date = datetime.now() - timedelta(days=29-i)
            # Add some variation to simulate real trading
            variation = (i % 7 - 3) * 150 + (i * 50)
            mock_history.append({
                "date": date.strftime("%Y-%m-%d"),
                "value": base_value + variation,
                "dailyPnl": variation if i > 0 else 0
            })
        return {"history": mock_history}
    
    try:
        with conn.cursor() as cursor:
            sql = """
                SELECT 
                    date,
                    total_value,
                    cash_balance,
                    positions_value,
                    daily_pnl
                FROM portfolio_history 
                ORDER BY date DESC
                LIMIT 90
            """
            cursor.execute(sql)
            history = cursor.fetchall()
            
            # Convert to list of dicts and format dates
            formatted_history = []
            for record in history:
                history_dict = dict(record)
                # Format date as string
                if history_dict.get('date'):
                    history_dict['date'] = history_dict['date'].isoformat()
                # Convert Decimal to float
                for field in ['total_value', 'cash_balance', 'positions_value', 'daily_pnl']:
                    if history_dict.get(field) is not None:
                        history_dict[field] = float(history_dict[field])
                formatted_history.append(history_dict)
            
            # Reverse to get chronological order
            formatted_history.reverse()
            
            return {"history": formatted_history}
            
    except Exception as e:
        logger.error(f"Error fetching portfolio history: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    finally:
        conn.close()

@app.get("/api/trades/summary")
async def get_trades_summary():
    """
    Get trading summary statistics
    """
    conn = get_db_connection()
    if not conn:
        # Return mock data if database not available
        return {
            "totalRealizedPnl": 422.50,
            "totalUnrealizedPnl": -47.00,
            "winRate": 66.7,
            "totalTrades": 3,
            "activeTrades": 2,
            "avgTradeReturn": 7.3
        }
    
    try:
        with conn.cursor() as cursor:
            # Get realized P&L and trade count
            cursor.execute("""
                SELECT 
                    COALESCE(SUM(pnl), 0) as total_realized_pnl,
                    COUNT(*) as total_trades,
                    COUNT(CASE WHEN pnl > 0 THEN 1 END) as winning_trades
                FROM trades 
                WHERE status = 'closed' AND pnl IS NOT NULL
            """)
            realized_stats = cursor.fetchone()
            
            # Get unrealized P&L and active trade count  
            cursor.execute("""
                SELECT 
                    COALESCE(SUM(unrealized_pnl), 0) as total_unrealized_pnl,
                    COUNT(*) as active_trades
                FROM trades 
                WHERE status = 'open' AND unrealized_pnl IS NOT NULL
            """)
            unrealized_stats = cursor.fetchone()
            
            # Calculate win rate
            win_rate = 0
            if realized_stats['total_trades'] > 0:
                win_rate = (realized_stats['winning_trades'] / realized_stats['total_trades']) * 100
            
            # Calculate average trade return (simplified)
            avg_return = 0
            if realized_stats['total_trades'] > 0:
                avg_return = float(realized_stats['total_realized_pnl']) / realized_stats['total_trades']
            
            return {
                "totalRealizedPnl": float(realized_stats['total_realized_pnl']),
                "totalUnrealizedPnl": float(unrealized_stats['total_unrealized_pnl']),
                "winRate": round(win_rate, 1),
                "totalTrades": realized_stats['total_trades'],
                "activeTrades": unrealized_stats['active_trades'],
                "avgTradeReturn": round(avg_return, 2)
            }
            
    except Exception as e:
        logger.error(f"Error fetching trades summary: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    finally:
        conn.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)