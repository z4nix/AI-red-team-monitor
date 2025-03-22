import sqlite3
import json
import logging
import os
from typing import List, Dict, Any, Optional
from config import DATABASE_PATH

class PaperDatabase:
    """Handles database operations for storing and retrieving papers."""
    
    def __init__(self, db_path=None):
        self.db_path = db_path or DATABASE_PATH
        self.logger = logging.getLogger(__name__)
        
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        # Initialize database
        self._init_db()
    
    def _init_db(self):
        """Initialize the database schema."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create papers table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS papers (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            authors TEXT NOT NULL,
            summary TEXT NOT NULL,
            published TEXT NOT NULL,
            updated TEXT NOT NULL,
            arxiv_categories TEXT NOT NULL,
            pdf_url TEXT NOT NULL,
            abstract_url TEXT NOT NULL,
            brief_overview TEXT,
            technical_explanation TEXT,
            attack_categories TEXT,
            relevance_score INTEGER,
            processed BOOLEAN DEFAULT 0,
            processed_at TEXT,
            processing_error TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # Create index for faster queries
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_published ON papers(published)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_processed ON papers(processed)')
        
        conn.commit()
        conn.close()
        
        self.logger.info("Database initialized")
    
    def save_papers(self, papers: List[Dict[str, Any]]):
        """Save papers to the database."""
        if not papers:
            return 0
            
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        inserted = 0
        updated = 0
        
        for paper in papers:
            # Convert list and dict fields to JSON strings
            paper_data = paper.copy()
            for field in ['authors', 'arxiv_categories', 'attack_categories']:
                if field in paper_data and isinstance(paper_data[field], (list, dict)):
                    paper_data[field] = json.dumps(paper_data[field])
            
            # Check if paper exists
            cursor.execute('SELECT id FROM papers WHERE id = ?', (paper['id'],))
            exists = cursor.fetchone()
            
            if exists:
                # Update existing paper
                fields = []
                values = []
                
                for key, value in paper_data.items():
                    if key != 'id':  # Skip the ID field
                        fields.append(f"{key} = ?")
                        values.append(value)
                
                values.append(paper['id'])  # Add ID for WHERE clause
                
                update_query = f"UPDATE papers SET {', '.join(fields)} WHERE id = ?"
                cursor.execute(update_query, values)
                updated += 1
            else:
                # Insert new paper
                fields = list(paper_data.keys())
                placeholders = ['?'] * len(fields)
                values = [paper_data[field] for field in fields]
                
                insert_query = f"INSERT INTO papers ({', '.join(fields)}) VALUES ({', '.join(placeholders)})"
                cursor.execute(insert_query, values)
                inserted += 1
        
        conn.commit()
        conn.close()
        
        self.logger.info(f"Saved papers: {inserted} inserted, {updated} updated")
        return inserted + updated
    
    def get_unprocessed_papers(self, limit=None):
        """Get papers that haven't been processed yet."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        query = 'SELECT * FROM papers WHERE processed = 0 ORDER BY published DESC'
        if limit:
            query += f' LIMIT {limit}'
            
        cursor.execute(query)
        rows = cursor.fetchall()
        
        papers = []
        for row in rows:
            paper = dict(row)
            # Convert JSON strings back to Python objects
            for field in ['authors', 'arxiv_categories', 'attack_categories']:
                if paper[field] and isinstance(paper[field], str):
                    try:
                        paper[field] = json.loads(paper[field])
                    except json.JSONDecodeError:
                        self.logger.warning(f"Failed to parse JSON for {field} in paper {paper['id']}")
                        paper[field] = []
            
            papers.append(paper)
        
        conn.close()
        
        self.logger.info(f"Retrieved {len(papers)} unprocessed papers")
        return papers
    
    def get_papers_by_category(self, category, days=None):
        """Get papers by attack category with optional time filter."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        params = [f'%"{category}"%']  # For JSON array search
        
        query = "SELECT * FROM papers WHERE processed = 1 AND attack_categories LIKE ?"
        
        # Add date filter if specified
        if days:
            query += " AND date(published) >= date('now', ?)"
            params.append(f'-{days} days')
        
        query += " ORDER BY published DESC"
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        papers = []
        for row in rows:
            paper = dict(row)
            # Convert JSON strings back to Python objects
            for field in ['authors', 'arxiv_categories', 'attack_categories']:
                if paper[field] and isinstance(paper[field], str):
                    try:
                        paper[field] = json.loads(paper[field])
                    except json.JSONDecodeError:
                        paper[field] = []
            
            papers.append(paper)
        
        conn.close()
        
        self.logger.info(f"Retrieved {len(papers)} papers for category '{category}'")
        return papers
    
    def get_recent_papers(self, days=7, min_relevance=None):
        """Get recent processed papers with optional relevance filter."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        params = [f'-{days} days']
        
        query = '''
        SELECT * FROM papers 
        WHERE processed = 1 
        AND date(published) >= date('now', ?)
        '''
        
        if min_relevance is not None:
            query += " AND relevance_score >= ?"
            params.append(min_relevance)
            
        query += " ORDER BY published DESC"
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        papers = []
        for row in rows:
            paper = dict(row)
            # Convert JSON strings back to Python objects
            for field in ['authors', 'arxiv_categories', 'attack_categories']:
                if paper[field] and isinstance(paper[field], str):
                    try:
                        paper[field] = json.loads(paper[field])
                    except json.JSONDecodeError:
                        paper[field] = []
            
            papers.append(paper)
        
        conn.close()
        
        self.logger.info(f"Retrieved {len(papers)} recent papers from the last {days} days")
        return papers
    
    def get_all_categories(self):
        """Get all unique attack categories."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT attack_categories FROM papers WHERE processed = 1')
        rows = cursor.fetchall()
        
        categories = set()
        for row in rows:
            if row[0]:
                try:
                    cats = json.loads(row[0])
                    if isinstance(cats, list):
                        for cat in cats:
                            categories.add(cat)
                except json.JSONDecodeError:
                    pass
        
        conn.close()
        
        return sorted(list(categories))
    
    def get_stats(self):
        """Get summary statistics about the database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        stats = {}
        
        # Total papers
        cursor.execute('SELECT COUNT(*) FROM papers')
        stats['total_papers'] = cursor.fetchone()[0]
        
        # Processed papers
        cursor.execute('SELECT COUNT(*) FROM papers WHERE processed = 1')
        stats['processed_papers'] = cursor.fetchone()[0]
        
        # Papers by relevance
        cursor.execute('''
        SELECT relevance_score, COUNT(*) 
        FROM papers 
        WHERE processed = 1 
        GROUP BY relevance_score
        ORDER BY relevance_score DESC
        ''')
        stats['papers_by_relevance'] = dict(cursor.fetchall())
        
        # Recent papers (last 7 days)
        cursor.execute('''
        SELECT COUNT(*) FROM papers 
        WHERE date(published) >= date('now', '-7 days')
        ''')
        stats['recent_papers'] = cursor.fetchone()[0]
        
        conn.close()
        
        return stats
