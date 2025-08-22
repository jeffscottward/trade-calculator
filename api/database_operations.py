"""
Database operations for earnings data management
"""
import os
import psycopg2
from datetime import datetime, date
from dotenv import load_dotenv
import logging
import time
import asyncio
import json
from typing import List, Dict, Optional

load_dotenv()
logger = logging.getLogger(__name__)

def get_db_connection():
    """Get database connection"""
    try:
        conn = psycopg2.connect(os.getenv("DATABASE_URL"))
        return conn
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        return None

def clear_august_data():
    """Clear specific August dates from database"""
    conn = get_db_connection()
    if not conn:
        return False
    
    try:
        with conn.cursor() as cursor:
            # Delete August 21, 22, and 25 data
            sql = """
                DELETE FROM earnings_calendar 
                WHERE report_date IN ('2024-08-21', '2024-08-22', '2024-08-25')
            """
            cursor.execute(sql)
            deleted_count = cursor.rowcount
            conn.commit()
            logger.info(f"Deleted {deleted_count} records from August 21, 22, and 25")
            return True
    except Exception as e:
        logger.error(f"Error clearing August data: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def check_date_has_data(check_date: date) -> bool:
    """Check if a specific date has earnings data in the database"""
    conn = get_db_connection()
    if not conn:
        return False
    
    try:
        with conn.cursor() as cursor:
            sql = """
                SELECT COUNT(*) FROM earnings_calendar 
                WHERE report_date = %s
            """
            cursor.execute(sql, (check_date,))
            count = cursor.fetchone()[0]
            return count > 0
    except Exception as e:
        logger.error(f"Error checking date data: {e}")
        return False
    finally:
        conn.close()

def store_earnings_data(earnings_data: List[Dict], report_date: date) -> bool:
    """Store earnings data in the database"""
    conn = get_db_connection()
    if not conn:
        return False
    
    try:
        with conn.cursor() as cursor:
            # First, clear any existing data for this date
            cursor.execute("DELETE FROM earnings_calendar WHERE report_date = %s", (report_date,))
            
            # Commit after deletion to start fresh
            conn.commit()
            
            # Insert new data
            stored_count = 0
            for i, earning in enumerate(earnings_data):
                try:
                    sql = """
                        INSERT INTO earnings_calendar (
                            ticker, company_name, report_date, report_time,
                            market_cap, market_cap_numeric, eps_forecast,
                            fiscal_quarter_ending, recommendation, risk_level,
                            expected_move, position_size, iv_rank,
                            avg_volume_pass, iv_rv_ratio_pass, term_structure_pass,
                            created_at, updated_at
                        ) VALUES (
                            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                        )
                    """
                    
                    # Extract analysis results
                    criteria = earning.get('criteria_met', {})
                    
                    # Convert expected_move to numeric, handling 'N/A' and percentage strings
                    expected_move_raw = earning.get('expected_move')
                    expected_move_numeric = None
                    if expected_move_raw and expected_move_raw != 'N/A':
                        # Remove ± and % symbols and convert to float
                        try:
                            expected_move_numeric = float(expected_move_raw.replace('±', '').replace('%', ''))
                        except:
                            expected_move_numeric = None
                    
                    values = (
                        earning.get('ticker'),
                        earning.get('companyName'),
                        report_date,
                        earning.get('reportTime', 'TBD'),
                        earning.get('marketCap'),
                        earning.get('market_cap_numeric'),
                        earning.get('estimate'),
                        earning.get('fiscalQuarterEnding'),
                        earning.get('recommendation', 'AVOID'),
                        earning.get('riskLevel', 'HIGH'),
                        expected_move_numeric,
                        earning.get('position_size', '0%'),
                        earning.get('iv_rank'),
                        criteria.get('volume_check', False),
                        criteria.get('iv_rv_ratio', False),
                        criteria.get('term_structure', False),
                        datetime.now(),
                        datetime.now()
                    )
                    
                    cursor.execute(sql, values)
                    stored_count += 1
                except Exception as e:
                    logger.error(f"Error storing record {i} for {earning.get('ticker', 'UNKNOWN')}: {e}")
                    logger.error(f"Record data: {earning}")
                    continue
            
            conn.commit()
            logger.info(f"Stored {stored_count}/{len(earnings_data)} earnings records for {report_date}")
            return stored_count > 0
            
    except Exception as e:
        logger.error(f"Error storing earnings data: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

async def fetch_and_store_earnings_for_date(date_str: str, force_refresh: bool = False):
    """
    Fetch earnings data for a specific date and store in database
    
    Args:
        date_str: Date in YYYY-MM-DD format
        force_refresh: If True, refresh even if data exists
    """
    logger.info(f"=== FETCH AND STORE for {date_str} ===")
    target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    
    # Check if we already have data (unless force refresh)
    if not force_refresh and check_date_has_data(target_date):
        logger.info(f"Data already exists for {date_str}, skipping fetch")
        return True
    
    logger.info(f"Starting earnings data fetch for {date_str}")
    
    try:
        # Import here to avoid circular imports
        from main import fetch_earnings_from_api, analyze_earnings_list
        
        # Fetch from API
        logger.info(f"Calling fetch_earnings_from_api for {date_str}")
        earnings_data = await fetch_earnings_from_api(date_str)
        
        if not earnings_data:
            logger.warning(f"No earnings data returned from API for {date_str}")
            return False
        
        logger.info(f"Got {len(earnings_data)} earnings from API for {date_str}")
        
        # Analyze each stock
        logger.info(f"Starting analysis for {len(earnings_data)} stocks...")
        analyzed_data = await analyze_earnings_list(earnings_data, date_str)
        logger.info(f"Analysis complete for {date_str}")
        
        # Store in database
        logger.info(f"Storing {len(analyzed_data)} analyzed records in database...")
        success = store_earnings_data(analyzed_data, target_date)
        
        if success:
            logger.info(f"Successfully stored data for {date_str}")
        
        return success
        
    except Exception as e:
        logger.error(f"Error fetching/storing data for {date_str}: {e}")
        return False

async def fetch_remaining_august_days():
    """Fetch and store data for all remaining August days"""
    from datetime import timedelta
    
    # Start from today
    today = date.today()
    
    # If we're in August 2024, process remaining days
    if today.year == 2024 and today.month == 8:
        current_date = today
        august_end = date(2024, 8, 31)
        
        dates_to_fetch = []
        while current_date <= august_end:
            dates_to_fetch.append(current_date.strftime("%Y-%m-%d"))
            current_date += timedelta(days=1)
        
        logger.info(f"Fetching data for {len(dates_to_fetch)} remaining August days")
        
        for date_str in dates_to_fetch:
            # Check if data already exists
            if not check_date_has_data(datetime.strptime(date_str, "%Y-%m-%d").date()):
                logger.info(f"Fetching data for {date_str}")
                await fetch_and_store_earnings_for_date(date_str)
                
                # Rest for 10 seconds between requests
                logger.info("Waiting 10 seconds before next request...")
                await asyncio.sleep(10)
            else:
                logger.info(f"Data already exists for {date_str}, skipping")
    else:
        logger.info("Not in August 2024, skipping bulk fetch")

def get_cached_earnings_for_date(date_str: str) -> Optional[List[Dict]]:
    """Get cached earnings data from database for a specific date"""
    conn = get_db_connection()
    if not conn:
        return None
    
    try:
        with conn.cursor() as cursor:
            sql = """
                SELECT 
                    ticker,
                    company_name as "companyName",
                    report_date as "reportDate",
                    report_time as "reportTime",
                    market_cap as "marketCap",
                    market_cap_numeric,
                    eps_forecast as estimate,
                    fiscal_quarter_ending as "fiscalQuarterEnding",
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
                ORDER BY recommendation ASC, ticker ASC
            """
            
            cursor.execute(sql, (date_str,))
            columns = [desc[0] for desc in cursor.description]
            results = []
            
            for row in cursor.fetchall():
                earning = dict(zip(columns, row))
                
                # Convert date to string
                if earning.get('reportDate'):
                    earning['reportDate'] = earning['reportDate'].strftime("%Y-%m-%d")
                
                # Convert numeric fields to proper types
                for field in ['expected_move', 'position_size', 'iv_rank', 'market_cap_numeric']:
                    if field in earning and earning[field] is not None:
                        try:
                            # Handle percentage strings and convert to float
                            value = earning[field]
                            if isinstance(value, str):
                                # Remove percentage sign if present
                                value = value.replace('%', '').strip()
                            float_val = float(value) if value else None
                            # Handle NaN and infinite values
                            if float_val is not None:
                                import math
                                if math.isnan(float_val) or math.isinf(float_val):
                                    earning[field] = None
                                else:
                                    earning[field] = float_val
                            else:
                                earning[field] = None
                        except (ValueError, TypeError):
                            earning[field] = None
                
                # Add criteria_met for compatibility
                earning['criteria_met'] = {
                    'volume_check': earning.pop('avg_volume_pass', False),
                    'iv_rv_ratio': earning.pop('iv_rv_ratio_pass', False),
                    'term_structure': earning.pop('term_structure_pass', False)
                }
                
                results.append(earning)
            
            return results if results else None
            
    except Exception as e:
        logger.error(f"Error getting cached earnings: {e}")
        return None
    finally:
        conn.close()

async def store_earnings_with_analysis(date_str: str, analyzed_earnings: List[Dict]) -> bool:
    """Store earnings data with analysis results in the database"""
    conn = get_db_connection()
    if not conn:
        return False
    
    try:
        with conn.cursor() as cursor:
            # First, clear existing data for this date
            delete_sql = "DELETE FROM earnings_calendar WHERE report_date = %s"
            cursor.execute(delete_sql, (date_str,))
            
            # Insert new analyzed data
            for earning in analyzed_earnings:
                insert_sql = """
                    INSERT INTO earnings_calendar (
                        ticker, company_name, report_date, report_time,
                        market_cap, eps_forecast, recommendation, risk_level,
                        expected_move, position_size, iv_rank, criteria_met,
                        priority_score, analysis_timestamp, created_at
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                    )
                """
                
                # Convert eps_estimate to float if it's a string
                eps_estimate = earning.get('estimate', earning.get('eps_estimate'))
                if eps_estimate and isinstance(eps_estimate, str):
                    try:
                        # Remove any non-numeric characters except . and -
                        eps_estimate = eps_estimate.replace('$', '').replace(',', '').strip()
                        if eps_estimate == '-' or eps_estimate.lower() == 'n/a':
                            eps_estimate = None
                        else:
                            eps_estimate = float(eps_estimate)
                    except (ValueError, TypeError):
                        eps_estimate = None
                
                # Handle criteria_met - convert dict to JSON string
                criteria_met = earning.get('criteria_met', {})
                if isinstance(criteria_met, dict):
                    criteria_met = json.dumps(criteria_met)
                
                # Handle numeric fields
                def safe_float(value):
                    if value is None:
                        return None
                    if isinstance(value, str):
                        value = value.replace('%', '').strip()
                        if value == '' or value == '-' or value.lower() == 'n/a':
                            return None
                    try:
                        return float(value)
                    except (ValueError, TypeError):
                        return None
                
                values = (
                    earning.get('ticker', ''),
                    earning.get('companyName', ''),
                    date_str,
                    earning.get('reportTime', 'TBD'),
                    earning.get('marketCap', ''),
                    eps_estimate,
                    earning.get('recommendation', 'AVOID'),
                    earning.get('riskLevel', 'HIGH'),
                    safe_float(earning.get('expected_move')),
                    earning.get('position_size', '0%'),
                    safe_float(earning.get('iv_rank')),
                    criteria_met,
                    safe_float(earning.get('priority_score', 0.0)),
                    datetime.now(),
                    datetime.now()
                )
                
                cursor.execute(insert_sql, values)
            
            conn.commit()
            logger.info(f"Successfully stored {len(analyzed_earnings)} analyzed earnings for {date_str}")
            return True
            
    except Exception as e:
        logger.error(f"Error storing analyzed earnings: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

if __name__ == "__main__":
    # Clear August data when run directly
    print("Clearing August 21, 22, and 25 data...")
    if clear_august_data():
        print("Successfully cleared August data")
    else:
        print("Failed to clear August data")