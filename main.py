#!/usr/bin/env python3
import argparse
import logging
import os
import time
from datetime import datetime
import schedule
import sys

# Import project modules
from arxiv_collector import ArxivCollector
from paper_processor import PaperProcessor
from database import PaperDatabase
from email_digest import EmailDigest
from config import (
    LOG_LEVEL, LOG_FILE, LOG_FORMAT,
    COLLECTION_SCHEDULE, PROCESSING_SCHEDULE, DIGEST_SCHEDULE
)

# Setup logging
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format=LOG_FORMAT,
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

def run_collection(days=7):
    """Run the paper collection process."""
    logger.info("Starting paper collection process")
    
    try:
        # Initialize collector
        collector = ArxivCollector()
        
        # Fetch papers
        papers = collector.fetch_papers(days=days)
        
        # Save to database
        db = PaperDatabase()
        count = db.save_papers(papers)
        
        logger.info(f"Collection complete: {count} papers saved")
        return papers
    except Exception as e:
        logger.error(f"Error in collection process: {str(e)}", exc_info=True)
        return []

def run_processing(limit=None):
    """Run the paper processing with LLM."""
    logger.info("Starting paper processing")
    
    try:
        # Check if API key is available
        api_key = os.environ.get('ANTHROPIC_API_KEY') or os.environ.get('OPENAI_API_KEY')
        if not api_key:
            logger.error("No API key found. Set ANTHROPIC_API_KEY or OPENAI_API_KEY environment variable.")
            return False
        
        # Initialize components
        db = PaperDatabase()
        processor = PaperProcessor()
        
        # Get unprocessed papers
        papers = db.get_unprocessed_papers(limit=limit)
        logger.info(f"Found {len(papers)} unprocessed papers")
        
        if not papers:
            logger.info("No papers to process")
            return True
        
        # Process papers
        processed_papers = processor.process_papers(papers)
        
        # Save processed papers
        count = db.save_papers(processed_papers)
        
        logger.info(f"Processing complete: {count} papers processed")
        return True
    except Exception as e:
        logger.error(f"Error in processing: {str(e)}", exc_info=True)
        return False

def send_weekly_digest(days=7, min_relevance=5):
    """Generate and send weekly digest."""
    logger.info("Generating weekly digest")
    
    try:
        # Initialize email digest
        digest = EmailDigest()
        
        # Send digest
        success = digest.send_digest(days=days, min_relevance=min_relevance)
        
        if success:
            logger.info("Weekly digest sent successfully")
        else:
            logger.error("Failed to send weekly digest")
            
        return success
    except Exception as e:
        logger.error(f"Error generating digest: {str(e)}", exc_info=True)
        return False

def run_scheduled_tasks():
    """Run as a scheduled service."""
    logger.info("Starting scheduled service")
    
    # Schedule collection
    schedule.every().day.at(COLLECTION_SCHEDULE).do(run_collection)
    logger.info(f"Scheduled paper collection for {COLLECTION_SCHEDULE} daily")
    
    # Schedule processing
    schedule.every().day.at(PROCESSING_SCHEDULE).do(run_processing)
    logger.info(f"Scheduled paper processing for {PROCESSING_SCHEDULE} daily")
    
    # Schedule weekly digest (default: Monday at 8 AM)
    schedule.every().monday.at(DIGEST_SCHEDULE).do(send_weekly_digest)
    logger.info(f"Scheduled weekly digest for Monday at {DIGEST_SCHEDULE}")
    
    # Run immediately if requested
    if os.environ.get('RUN_IMMEDIATE', 'false').lower() == 'true':
        logger.info("Running tasks immediately per RUN_IMMEDIATE setting")
        run_collection()
        run_processing()
    
    # Keep the scheduler running
    logger.info("Scheduler is now running...")
    try:
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
    except KeyboardInterrupt:
        logger.info("Scheduler stopped by user")
    except Exception as e:
        logger.error(f"Error in scheduler: {str(e)}", exc_info=True)

def main():
    parser = argparse.ArgumentParser(description="arXiv AI Red Teaming Monitor")
    parser.add_argument("--collect", action="store_true", help="Run paper collection")
    parser.add_argument("--process", action="store_true", help="Run paper processing")
    parser.add_argument("--digest", action="store_true", help="Send email digest")
    parser.add_argument("--schedule", action="store_true", help="Run as a scheduled service")
    parser.add_argument("--days", type=int, default=7, help="Number of days to look back for papers")
    parser.add_argument("--limit", type=int, help="Limit number of papers to process")
    
    args = parser.parse_args()
    
    # Check if any action is specified
    if not (args.collect or args.process or args.digest or args.schedule):
        parser.print_help()
        return
    
    # Run requested actions
    if args.collect:
        run_collection(days=args.days)
    
    if args.process:
        run_processing(limit=args.limit)
    
    if args.digest:
        send_weekly_digest(days=args.days)
    
    if args.schedule:
        run_scheduled_tasks()

if __name__ == "__main__":
    main()
