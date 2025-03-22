import smtplib
import logging
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
from typing import List, Dict, Any
from collections import defaultdict
from database import PaperDatabase
from config import (
    SMTP_SERVER, SMTP_PORT, SMTP_USERNAME, 
    SMTP_PASSWORD, SENDER_EMAIL, RECIPIENT_EMAILS,
    EMAIL_SUBJECT_PREFIX, MIN_RELEVANCE_SCORE
)

class EmailDigest:
    """Generates and sends weekly email digests of recent papers."""
    
    def __init__(self, smtp_server=None, smtp_port=None, username=None, 
                 password=None, sender_email=None, recipient_emails=None):
        self.smtp_server = smtp_server or SMTP_SERVER or os.environ.get('SMTP_SERVER')
        self.smtp_port = smtp_port or SMTP_PORT or int(os.environ.get('SMTP_PORT', 587))
        self.username = username or SMTP_USERNAME or os.environ.get('SMTP_USERNAME')
        self.password = password or SMTP_PASSWORD or os.environ.get('SMTP_PASSWORD')
        self.sender_email = sender_email or SENDER_EMAIL or os.environ.get('SENDER_EMAIL')
        
        recipients = recipient_emails or RECIPIENT_EMAILS or os.environ.get('RECIPIENT_EMAILS', '')
        self.recipient_emails = recipients.split(',') if isinstance(recipients, str) else recipients
        
        self.logger = logging.getLogger(__name__)
        
        # Validate required config
        required = [self.smtp_server, self.username, self.password, self.sender_email, self.recipient_emails]
        if not all(required):
            missing = [
                param for param, value in {
                    'SMTP_SERVER': self.smtp_server,
                    'SMTP_USERNAME': self.username,
                    'SMTP_PASSWORD': self.password,
                    'SENDER_EMAIL': self.sender_email,
                    'RECIPIENT_EMAILS': self.recipient_emails
                }.items() if not value
            ]
            self.logger.warning(f"Email configuration incomplete. Missing: {', '.join(missing)}")
    
    def generate_digest(self, days=7, min_relevance=None):
        """Generate HTML content for email digest based on recent papers."""
        min_relevance = min_relevance or MIN_RELEVANCE_SCORE
        
        db = PaperDatabase()
        papers = db.get_recent_papers(days=days, min_relevance=min_relevance)
        
        if not papers:
            self.logger.info(f"No recent papers found in the last {days} days with relevance >= {min_relevance}")
            return None
        
        # Group papers by category
        papers_by_category = defaultdict(list)
        for paper in papers:
            if not paper.get('attack_categories'):
                papers_by_category['Uncategorized'].append(paper)
                continue
                
            for category in paper['attack_categories']:
                papers_by_category[category].append(paper)
        
        # Sort categories by number of papers (descending)
        sorted_categories = sorted(
            papers_by_category.keys(), 
            key=lambda x: len(papers_by_category[x]), 
            reverse=True
        )
        
        # Generate HTML content
        html = f'''
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>AI Red Teaming Research Digest</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 800px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                h1 {{
                    color: #2c3e50;
                    border-bottom: 2px solid #3498db;
                    padding-bottom: 10px;
                }}
                h2 {{
                    color: #2980b9;
                    margin-top: 30px;
                }}
                .paper {{
                    margin-bottom: 25px;
                    border-left: 4px solid #3498db;
                    padding-left: 15px;
                }}
                .paper-title {{
                    font-weight: bold;
                    font-size: 18px;
                    margin-bottom: 5px;
                }}
                .paper-meta {{
                    font-size: 14px;
                    color: #7f8c8d;
                    margin-bottom: 8px;
                }}
                .paper-overview {{
                    margin-bottom: 10px;
                }}
                .relevance {{
                    display: inline-block;
                    padding: 3px 6px;
                    border-radius: 3px;
                    font-size: 12px;
                    font-weight: bold;
                }}
                .relevance-high {{
                    background-color: #e74c3c;
                    color: white;
                }}
                .relevance-medium {{
                    background-color: #f39c12;
                    color: white;
                }}
                .relevance-low {{
                    background-color: #3498db;
                    color: white;
                }}
                .links {{
                    font-size: 14px;
                }}
                .links a {{
                    color: #2980b9;
                    text-decoration: none;
                    margin-right: 15px;
                }}
                .links a:hover {{
                    text-decoration: underline;
                }}
                .footer {{
                    margin-top: 40px;
                    padding-top: 20px;
                    border-top: 1px solid #eee;
                    font-size: 14px;
                    color: #7f8c8d;
                }}
            </style>
        </head>
        <body>
            <h1>AI Red Teaming Research Digest</h1>
            <p>Here are the latest AI red teaming research papers from the past {days} days:</p>
        '''
        
        # Add summary counts
        html += '<p><strong>Summary:</strong></p><ul>'
        html += f'<li>Total papers: {len(papers)}</li>'
        html += f'<li>Categories covered: {len(sorted_categories)}</li>'
        html += '</ul>'
        
        # Add papers by category
        for category in sorted_categories:
            category_papers = papers_by_category[category]
            html += f'<h2>{category} ({len(category_papers)} papers)</h2>'
            
            for paper in category_papers:
                # Determine relevance class
                if paper.get('relevance_score', 0) >= 8:
                    relevance_class = 'relevance-high'
                elif paper.get('relevance_score', 0) >= 5:
                    relevance_class = 'relevance-medium'
                else:
                    relevance_class = 'relevance-low'
                
                html += f'''
                <div class="paper">
                    <div class="paper-title">{paper['title']}</div>
                    <div class="paper-meta">
                        <span>Authors: {', '.join(paper['authors'][:3])}{" et al." if len(paper['authors']) > 3 else ""}</span>
                        <span> • </span>
                        <span>Published: {paper['published']}</span>
                        <span> • </span>
                        <span class="relevance {relevance_class}">Relevance: {paper.get('relevance_score', 'N/A')}/10</span>
                    </div>
                    <div class="paper-overview">{paper.get('brief_overview', 'No overview available')}</div>
                    <div class="links">
                        <a href="{paper['abstract_url']}" target="_blank">Abstract</a>
                        <a href="{paper['pdf_url']}" target="_blank">PDF</a>
                    </div>
                </div>
                '''
        
        # Add footer
        html += f'''
            <div class="footer">
                <p>This digest was generated on {datetime.now().strftime('%Y-%m-%d')}.</p>
                <p>For more details and filtering options, please visit our web interface.</p>
            </div>
        </body>
        </html>
        '''
        
        return html
    
    def send_digest(self, html_content=None, days=7, min_relevance=None):
        """Generate and send weekly digest email."""
        if not html_content:
            html_content = self.generate_digest(days, min_relevance)
            
        if not html_content:
            self.logger.info("No content to send in digest")
            return False
            
        if not all([self.smtp_server, self.username, self.password, self.sender_email, self.recipient_emails]):
            self.logger.error("Email configuration incomplete, cannot send digest")
            return False
        
        try:
            # Create message
            msg = MIMEMultipart()
            msg['From'] = self.sender_email
            msg['To'] = ', '.join(self.recipient_emails)
            
            # Add date to subject
            subject = f"{EMAIL_SUBJECT_PREFIX} {datetime.now().strftime('%Y-%m-%d')}"
            msg['Subject'] = subject
            
            # Attach HTML content
            msg.attach(MIMEText(html_content, 'html'))
            
            # Connect to SMTP server
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.username, self.password)
            
            # Send email
            server.send_message(msg)
            server.quit()
            
            self.logger.info(f"Email digest sent to {len(self.recipient_emails)} recipients")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to send email digest: {str(e)}")
            return False
