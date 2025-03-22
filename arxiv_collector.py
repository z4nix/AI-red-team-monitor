import arxiv
import datetime
import logging
from config import ARXIV_KEYWORDS, MAX_RESULTS

class ArxivCollector:
      # Collect papers from arxiv    
    def __init__(self, keywords=None, max_results=None):
        self.keywords = keywords or ARXIV_KEYWORDS
        self.max_results = max_results or MAX_RESULTS
        self.logger = logging.getLogger(__name__)
    
    def construct_query(self, days=7):
        """Construct arXiv API query string with date filter."""
        # Base query with OR for keywords
        base_query = " OR ".join([f"\"{keyword}\"" for keyword in self.keywords])
        
        # Limit to papers from specified timeframe
        current_date = datetime.datetime.now()
        start_date = current_date - datetime.timedelta(days=days)
        
        # Format for arXiv API date filter (YYYYMMDD)
        date_query = f"submittedDate:[{start_date.strftime('%Y%m%d')}000000 TO {current_date.strftime('%Y%m%d')}235959]"
        
        # Add relevant categories to narrow down results
        categories = "cat:cs.AI OR cat:cs.CL OR cat:cs.CR OR cat:cs.LG"
        
        # Combine queries
        full_query = f"({base_query}) AND ({date_query}) AND ({categories})"
        
        self.logger.info(f"Query: {full_query}")
        return full_query
    
    def fetch_papers(self, days=7):
        """Fetch papers matching criteria from arXiv"""
        query = self.construct_query(days)
        self.logger.info(f"Fetching papers with query: {query}")
        
        # Initialize arXiv client
        client = arxiv.Client(
            page_size=100,
            delay_seconds=3,
            num_retries=3
        )
        
        # Create search
        search = arxiv.Search(
            query=query,
            max_results=self.max_results,
            sort_by=arxiv.SortCriterion.SubmittedDate
        )
        
        # Fetch results
        papers = []
        for result in client.results(search):
            paper = {
                'id': result.entry_id.split('/')[-1],  # Extract ID from URL
                'title': result.title,
                'authors': [author.name for author in result.authors],
                'summary': result.summary,
                'published': result.published.strftime('%Y-%m-%d'),
                'updated': result.updated.strftime('%Y-%m-%d'),
                'arxiv_categories': result.categories,
                'pdf_url': result.pdf_url,
                'abstract_url': f"https://arxiv.org/abs/{result.entry_id.split('/')[-1]}",
                'processed': False,
                'processed_at': None,
            }
            papers.append(paper)
        
        self.logger.info(f"Fetched {len(papers)} papers")
        return papers
