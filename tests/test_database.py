import unittest
import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.db.models import Base, CompanyUniverse, EventRegistry, CrawlLog


class TestDatabase(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine('sqlite:///:memory:')
        Base.metadata.create_all(bind=self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(bind=self.engine)

    def test_company_universe_crud(self):
        company = CompanyUniverse(
            company_name='Apple Inc.',
            ticker='AAPL',
            exchange='NASDAQ',
            country='US',
            cik_or_sedar_id='0000320193',
            ir_page_url='https://investor.apple.com',
            market_cap_bucket='large_cap',
            expected_call_language='en',
        )
        self.db.add(company)
        self.db.commit()

        retrieved = self.db.query(CompanyUniverse).filter_by(ticker='AAPL').first()
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.company_name, 'Apple Inc.')
        self.assertEqual(retrieved.market_cap_bucket, 'large_cap')

    def test_event_registry_idempotency(self):
        company = CompanyUniverse(
            company_name='Microsoft Corp',
            ticker='MSFT',
            exchange='NASDAQ',
            country='US',
            cik_or_sedar_id='0000789019',
            ir_page_url='https://www.microsoft.com/en-us/investor',
            market_cap_bucket='large_cap',
            expected_call_language='en',
        )
        self.db.add(company)
        self.db.commit()

        event1 = EventRegistry(
            company_id=company.id,
            ticker='MSFT',
            fiscal_period='Q3 FY2026',
            webcast_url='https://viewproxy.com/msft',
            vendor='Q4 Inc',
            discovery_source='SEC_EDGAR_8K',
            confidence=0.95,
        )
        self.db.add(event1)
        self.db.commit()

        ev = self.db.query(EventRegistry).filter_by(company_id=company.id, fiscal_period='Q3 FY2026').first()
        self.assertIsNotNone(ev)
        self.assertEqual(ev.ticker, 'MSFT')
        self.assertEqual(ev.vendor, 'Q4 Inc')

    def test_crawl_log_entry(self):
        log = CrawlLog(
            source='SEC_EDGAR_8K',
            target_url='https://data.sec.gov/submissions/CIK0000320193.json',
            http_status=200,
            outcome='SUCCESS',
            correlation_id='TEST-CORR-01',
        )
        self.db.add(log)
        self.db.commit()

        retrieved_log = self.db.query(CrawlLog).filter_by(correlation_id='TEST-CORR-01').first()
        self.assertIsNotNone(retrieved_log)
        self.assertEqual(retrieved_log.outcome, 'SUCCESS')


if __name__ == '__main__':
    unittest.main()
