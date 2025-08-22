#!/usr/bin/env python3
"""
Bulk earnings data importer for NASDAQ earnings calendar
Fetches earnings data and stores it in PostgreSQL database
"""

import os
import sys
import re
from datetime import datetime, timedelta
import pandas as pd
import psycopg2
from psycopg2.extras import execute_batch
from dotenv import load_dotenv
from finance_calendars.finance_calendars import get_earnings_by_date, get_earnings_today
import logging

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='🚀 ~ file: earnings_data_importer.py:%(lineno)d → %(funcName)s → %(message)s'
)
logger = logging.getLogger(__name__)

class EarningsDataImporter:
    def __init__(self):
        """Initialize the importer with database connection"""
        self.db_url = os.getenv('DATABASE_URL')
        if not self.db_url:
            raise ValueError("DATABASE_URL not found in environment variables")
        
        self.conn = None
        self.cursor = None
        
    def connect_db(self):
        """Connect to PostgreSQL database"""
        try:
            self.conn = psycopg2.connect(self.db_url)
            self.cursor = self.conn.cursor()
            logger.info("Connected to database successfully")
        except Exception as e:
            logger.error(f"Failed to connect to database: {str(e)}")
            raise
    
    def close_db(self):
        """Close database connection"""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
        logger.info("Database connection closed")
    
    def parse_market_cap(self, market_cap_str):
        """Parse market cap string to numeric value"""
        if not market_cap_str or market_cap_str == 'N/A':
            return None
        
        # Remove $ and commas
        clean_str = market_cap_str.replace('$', '').replace(',', '')
        
        # Handle billions/millions/thousands
        multiplier = 1
        if 'B' in clean_str or 'billion' in clean_str.lower():
            multiplier = 1000000000
            clean_str = re.sub(r'[Bb]illion?', '', clean_str)
        elif 'M' in clean_str or 'million' in clean_str.lower():
            multiplier = 1000000
            clean_str = re.sub(r'[Mm]illion?', '', clean_str)
        elif 'K' in clean_str or 'thousand' in clean_str.lower():
            multiplier = 1000
            clean_str = re.sub(r'[Kk]|thousand', '', clean_str)
        
        try:
            return int(float(clean_str.strip()) * multiplier)
        except:
            return None
    
    def parse_eps(self, eps_str):
        """Parse EPS string to numeric value"""
        if not eps_str or eps_str == 'N/A' or eps_str == '':
            return None
        
        # Remove $ and other characters
        clean_str = eps_str.replace('$', '').replace(',', '').strip()
        
        try:
            return float(clean_str)
        except:
            return None
    
    def parse_date(self, date_str):
        """Parse date string to date object"""
        if not date_str or date_str == 'N/A':
            return None
        
        # Try different date formats
        formats = ['%m/%d/%Y', '%Y-%m-%d', '%d/%m/%Y']
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt).date()
            except:
                continue
        return None
    
    def fetch_earnings_data(self, start_date, end_date):
        """Fetch earnings data for date range"""
        logger.info(f"Fetching earnings from {start_date} to {end_date}")
        
        all_earnings = []
        current_date = start_date
        
        while current_date <= end_date:
            try:
                logger.info(f"Fetching {current_date.strftime('%Y-%m-%d')}...")
                
                # Fetch earnings for current date
                earnings_df = get_earnings_by_date(current_date)
                
                if isinstance(earnings_df, pd.DataFrame) and not earnings_df.empty:
                    # Convert to list of dicts
                    earnings_list = earnings_df.to_dict('records')
                    
                    # Add report date and ticker from index
                    for i, (ticker, earning) in enumerate(zip(earnings_df.index, earnings_list)):
                        earning['ticker'] = ticker
                        earning['report_date'] = current_date
                    
                    all_earnings.extend(earnings_list)
                    logger.info(f"   Found {len(earnings_list)} companies")
                
            except Exception as e:
                logger.warning(f"   Error fetching {current_date}: {str(e)}")
            
            current_date += timedelta(days=1)
        
        logger.info(f"Total earnings fetched: {len(all_earnings)}")
        return all_earnings
    
    def prepare_earnings_record(self, earning):
        """Prepare earnings record for database insertion"""
        return {
            'ticker': earning.get('ticker', ''),
            'company_name': earning.get('name', ''),
            'report_date': earning.get('report_date'),
            'report_time': earning.get('time', 'time-not-supplied'),
            'market_cap': earning.get('marketCap', ''),
            'market_cap_numeric': self.parse_market_cap(earning.get('marketCap')),
            'fiscal_quarter_ending': earning.get('fiscalQuarterEnding', ''),
            'eps_forecast': earning.get('epsForecast', ''),
            'eps_forecast_numeric': self.parse_eps(earning.get('epsForecast')),
            'num_estimates': int(earning.get('noOfEsts', 0)) if earning.get('noOfEsts') and earning.get('noOfEsts') != 'N/A' else None,
            'last_year_report_date': self.parse_date(earning.get('lastYearRptDt')),
            'last_year_eps': earning.get('lastYearEPS', ''),
            'last_year_eps_numeric': self.parse_eps(earning.get('lastYearEPS'))
        }
    
    def import_earnings(self, earnings_data):
        """Import earnings data into database"""
        if not earnings_data:
            logger.warning("No earnings data to import")
            return 0
        
        # Prepare records
        records = [self.prepare_earnings_record(e) for e in earnings_data]
        
        # SQL for upsert (insert or update on conflict)
        sql = """
            INSERT INTO earnings_calendar (
                ticker, company_name, report_date, report_time,
                market_cap, market_cap_numeric, fiscal_quarter_ending,
                eps_forecast, eps_forecast_numeric, num_estimates,
                last_year_report_date, last_year_eps, last_year_eps_numeric
            ) VALUES (
                %(ticker)s, %(company_name)s, %(report_date)s, %(report_time)s,
                %(market_cap)s, %(market_cap_numeric)s, %(fiscal_quarter_ending)s,
                %(eps_forecast)s, %(eps_forecast_numeric)s, %(num_estimates)s,
                %(last_year_report_date)s, %(last_year_eps)s, %(last_year_eps_numeric)s
            )
            ON CONFLICT (ticker, report_date) 
            DO UPDATE SET
                company_name = EXCLUDED.company_name,
                report_time = EXCLUDED.report_time,
                market_cap = EXCLUDED.market_cap,
                market_cap_numeric = EXCLUDED.market_cap_numeric,
                fiscal_quarter_ending = EXCLUDED.fiscal_quarter_ending,
                eps_forecast = EXCLUDED.eps_forecast,
                eps_forecast_numeric = EXCLUDED.eps_forecast_numeric,
                num_estimates = EXCLUDED.num_estimates,
                last_year_report_date = EXCLUDED.last_year_report_date,
                last_year_eps = EXCLUDED.last_year_eps,
                last_year_eps_numeric = EXCLUDED.last_year_eps_numeric,
                updated_at = CURRENT_TIMESTAMP
        """
        
        try:
            execute_batch(self.cursor, sql, records, page_size=100)
            self.conn.commit()
            logger.info(f"Successfully imported {len(records)} earnings records")
            return len(records)
        except Exception as e:
            self.conn.rollback()
            logger.error(f"Failed to import earnings: {str(e)}")
            raise
    
    def record_import_history(self, start_date, end_date, records_imported, status='completed', error_message=None):
        """Record import history"""
        sql = """
            INSERT INTO earnings_import_history 
            (start_date, end_date, records_imported, source, status, error_message)
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        
        try:
            self.cursor.execute(sql, (start_date, end_date, records_imported, 'NASDAQ', status, error_message))
            self.conn.commit()
            logger.info("Import history recorded")
        except Exception as e:
            logger.error(f"Failed to record import history: {str(e)}")
    
    def import_date_range(self, start_date, end_date):
        """Import earnings for a date range"""
        try:
            self.connect_db()
            
            # Fetch earnings data
            earnings_data = self.fetch_earnings_data(start_date, end_date)
            
            # Import to database
            records_imported = self.import_earnings(earnings_data)
            
            # Record import history
            self.record_import_history(start_date, end_date, records_imported)
            
            logger.info(f"✅ Import completed: {records_imported} records")
            return records_imported
            
        except Exception as e:
            logger.error(f"Import failed: {str(e)}")
            self.record_import_history(start_date, end_date, 0, 'failed', str(e))
            raise
        finally:
            self.close_db()
    
    def import_upcoming_month(self):
        """Import earnings for the upcoming month"""
        today = datetime.now().date()
        end_date = today + timedelta(days=30)
        return self.import_date_range(today, end_date)
    
    def import_current_week(self):
        """Import earnings for the current week"""
        today = datetime.now().date()
        end_date = today + timedelta(days=7)
        return self.import_date_range(today, end_date)

def main():
    """Main function for command line usage"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Import NASDAQ earnings calendar data')
    parser.add_argument('--days', type=int, default=30, 
                       help='Number of days to import (default: 30)')
    parser.add_argument('--start-date', type=str, 
                       help='Start date (YYYY-MM-DD)')
    parser.add_argument('--end-date', type=str, 
                       help='End date (YYYY-MM-DD)')
    parser.add_argument('--week', action='store_true', 
                       help='Import current week only')
    
    args = parser.parse_args()
    
    importer = EarningsDataImporter()
    
    try:
        if args.start_date and args.end_date:
            start = datetime.strptime(args.start_date, '%Y-%m-%d').date()
            end = datetime.strptime(args.end_date, '%Y-%m-%d').date()
            records = importer.import_date_range(start, end)
        elif args.week:
            records = importer.import_current_week()
        else:
            # Default: import upcoming days
            start = datetime.now().date()
            end = start + timedelta(days=args.days)
            records = importer.import_date_range(start, end)
        
        print(f"\n✅ Successfully imported {records} earnings records")
        
    except Exception as e:
        print(f"\n❌ Import failed: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()