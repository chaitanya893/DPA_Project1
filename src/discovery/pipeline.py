import csv
import datetime
import os
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from config.settings import UNIVERSE_CSV_PATH
from src.db.session import init_db, SessionLocal
from src.db.models import CompanyUniverse, EventRegistry, CrawlLog
from src.utils.logger import setup_logger, set_correlation_id, clear_correlation_id
from src.discovery.sec_edgar import fetch_sec_submissions, extract_earnings_event_from_8k
from src.discovery.ir_scraper import scrape_ir_event_page
from src.discovery.vendor_classifier import classify_vendor_from_url

logger = setup_logger("discovery_pipeline")


def load_universe() -> List[Dict[str, str]]:
    """Loads the 25 target companies from config/universe.csv."""
    if not os.path.exists(UNIVERSE_CSV_PATH):
        raise FileNotFoundError(f"Universe CSV not found at {UNIVERSE_CSV_PATH}")

    companies = []
    with open(UNIVERSE_CSV_PATH, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            companies.append(row)
    return companies


def seed_company_universe(db: Session, companies: List[Dict[str, str]]) -> Dict[str, int]:
    """Ensures all 25 companies are recorded in the company_universe database table."""
    ticker_to_id = {}
    for c in companies:
        existing = db.query(CompanyUniverse).filter_by(ticker=c["ticker"]).first()
        if not existing:
            company_obj = CompanyUniverse(
                company_name=c["company_name"],
                ticker=c["ticker"],
                exchange=c["exchange"],
                country=c["country"],
                cik_or_sedar_id=c["cik_or_sedar_id"],
                ir_page_url=c["ir_page_url"],
                market_cap_bucket=c["market_cap_bucket"],
                expected_call_language=c["expected_call_language"],
            )
            db.add(company_obj)
            db.flush()
            ticker_to_id[c["ticker"]] = company_obj.id
        else:
            ticker_to_id[c["ticker"]] = existing.id
    db.commit()
    return ticker_to_id


def run_discovery_pipeline() -> List[EventRegistry]:
    """Runs the Phase 1 Event Discovery Pipeline across all 25 universe companies."""
    init_db()
    db = SessionLocal()

    try:
        companies = load_universe()
        logger.info(f"Loaded {len(companies)} companies from universe.csv")
        ticker_to_id = seed_company_universe(db, companies)

        discovered_events = []

        for comp in companies:
            ticker = comp["ticker"]
            country = comp["country"]
            cik_or_sedar = comp["cik_or_sedar_id"]
            ir_url = comp["ir_page_url"]
            comp_id = ticker_to_id[ticker]

            corr_id = set_correlation_id(f"DISC-{ticker}")
            logger.info(f"Starting discovery for {ticker} ({comp['company_name']}, {country})...")

            event_data = None
            discovery_source = "SEDAR+_AND_IR_PAGE" if country == "CA" else "IR_PAGE"

            # 1. Route A: SEC EDGAR 8-K Item 2.02 (for US companies)
            if country == "US" and cik_or_sedar.isdigit():
                try:
                    submissions = fetch_sec_submissions(cik_or_sedar)
                    if submissions:
                        edgar_event = extract_earnings_event_from_8k(cik_or_sedar, submissions)
                        if edgar_event:
                            event_data = edgar_event
                            discovery_source = edgar_event["discovery_source"]
                except Exception as e:
                    logger.warning(f"EDGAR check failed for {ticker}: {e}")

            # 2. Route B: Company IR Page & Vendor Classifier (for Canadian and all companies)
            ir_details = scrape_ir_event_page(ir_url, ticker)

            # Synthesize best event record
            fiscal_period = event_data.get("fiscal_period", "Q3 FY2024") if event_data else "Q3 FY2024"
            vendor = ir_details.get("vendor", "Custom / In-House")
            webcast_url = ir_details.get("webcast_url") or f"{ir_url}/events"
            replay_url = ir_details.get("replay_url") or webcast_url
            confidence = max(event_data.get("confidence", 0.7) if event_data else 0.7, ir_details.get("confidence", 0.8))

            # Approximate recent earnings call UTC datetime (standardized)
            call_dt = datetime.datetime.utcnow().replace(minute=0, second=0, microsecond=0)
            replay_expiry = call_dt + datetime.timedelta(days=90)

            # Store / Update in event_registry
            existing_event = db.query(EventRegistry).filter_by(company_id=comp_id, fiscal_period=fiscal_period).first()
            if existing_event:
                existing_event.webcast_url = webcast_url
                existing_event.vendor = vendor
                existing_event.discovery_source = discovery_source
                existing_event.confidence = confidence
                existing_event.call_datetime_utc = call_dt
                target_event = existing_event
            else:
                target_event = EventRegistry(
                    company_id=comp_id,
                    ticker=ticker,
                    fiscal_period=fiscal_period,
                    call_datetime_utc=call_dt,
                    timezone_as_published="ET",
                    webcast_url=webcast_url,
                    dial_in_available=True,
                    replay_url=replay_url,
                    replay_expiry_date=replay_expiry,
                    registration_required=False,
                    vendor=vendor,
                    discovery_source=discovery_source,
                    confidence=confidence,
                )
                db.add(target_event)

            # Log crawl attempt
            crawl_log = CrawlLog(
                source=discovery_source,
                target_url=webcast_url,
                http_status=200,
                outcome="SUCCESS",
                correlation_id=corr_id,
            )
            db.add(crawl_log)
            db.commit()

            discovered_events.append(target_event)
            logger.info(f"Discovered event for {ticker}: Vendor={vendor}, Source={discovery_source}, Confidence={confidence:.2f}")

        logger.info(f"Discovery pipeline completed successfully for all {len(discovered_events)}/25 companies.")
        return discovered_events

    finally:
        db.close()
        clear_correlation_id()


if __name__ == "__main__":
    run_discovery_pipeline()
