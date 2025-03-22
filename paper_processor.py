import time
import json
import logging
from typing import List, Dict, Any
import os
import datetime
from config import LLM_MODEL, LLM_PROVIDER, BATCH_SIZE, PROCESSING_DELAY

# Import appropriate client libraries based on configuration
if LLM_PROVIDER == "anthropic":
    from anthropic import Anthropic, AnthropicError
elif LLM_PROVIDER == "openai":
    import openai
else:
    raise ValueError(f"Unsupported LLM provider: {LLM_PROVIDER}")

class PaperProcessor:
    """Processes papers using cost-effective LLM APIs."""
    
    def __init__(self, api_key=None, model=None, batch_size=None):
        self.api_key = api_key or os.environ.get(f"{LLM_PROVIDER.upper()}_API_KEY")
        if not self.api_key:
            raise ValueError(f"No API key provided for {LLM_PROVIDER}")
            
        self.model = model or LLM_MODEL
        self.batch_size = batch_size or BATCH_SIZE
        self.logger = logging.getLogger(__name__)
        
        # Initialize the appropriate client
        if LLM_PROVIDER == "anthropic":
            self.client = Anthropic(api_key=self.api_key)
        elif LLM_PROVIDER == "openai":
            self.client = openai.OpenAI(api_key=self.api_key)
    
    def process_papers(self, papers: List[Dict[str, Any]]):
        """Process multiple papers in cost-effective batches."""
        if not papers:
            self.logger.info("No papers to process")
            return []
            
        processed_papers = []
        
        # Process papers in batches to reduce API costs
        for i in range(0, len(papers), self.batch_size):
            batch = papers[i:i+self.batch_size]
            self.logger.info(f"Processing batch {i//self.batch_size + 1}/{(len(papers)-1)//self.batch_size + 1} with {len(batch)} papers")
            
            processed_batch = self._process_batch(batch)
            processed_papers.extend(processed_batch)
            
            # Avoid rate limits with delay between batches
            if i + self.batch_size < len(papers):
                self.logger.info(f"Sleeping for {PROCESSING_DELAY} seconds between batches")
                time.sleep(PROCESSING_DELAY)
        
        return processed_papers
    
    def _process_batch(self, batch: List[Dict[str, Any]]):
        """Process a batch of papers."""
        processed_batch = []
        
        for paper in batch:
            # Skip already processed papers
            if paper.get('processed', False):
                self.logger.info(f"Skipping already processed paper: {paper['id']}")
                processed_batch.append(paper)
                continue
            
            try:
                # Create prompt for LLM
                prompt = self._create_prompt(paper)
                
                # Get response from LLM
                llm_response = self._call_llm(prompt)
                
                # Parse the response
                parsed_result = self._parse_response(llm_response)
                
                # Update paper with processed information
                paper.update({
                    'brief_overview': parsed_result.get('brief_overview', 'Not provided'),
                    'technical_explanation': parsed_result.get('technical_explanation', 'Not provided'),
                    'attack_categories': parsed_result.get('categories', ['unclassified']),
                    'relevance_score': parsed_result.get('relevance_score', 0),
                    'processed': True,
                    'processed_at': datetime.datetime.now().isoformat()
                })
                
                self.logger.info(f"Successfully processed paper: {paper['id']}")
            except Exception as e:
                self.logger.error(f"Error processing paper {paper['id']}: {str(e)}")
                # Mark as failed but don't update other fields
                paper['processing_error'] = str(e)
            
            processed_batch.append(paper)
        
        return processed_batch
    
    def _create_prompt(self, paper: Dict[str, Any]) -> str:
        """Create prompt for LLM analysis."""
        prompt = f"""
        You are an expert in AI security and AI red teaming research. Analyze this research paper and provide:
        
        1. A brief overview (2-3 sentences summarizing the paper's main contribution)
        2. A technical explanation (5-7 sentences explaining the key technical details)
        3. Categorization by attack type (choose the most relevant categories from: prompt injection, jailbreaking, adversarial examples, 
           model extraction, data poisoning, model backdoor attacks, privacy attacks, model stealing, 
           reward hacking, social engineering, or any other relevant category). They must be related to AI Red teaming research specifically. 
        4. Relevance score for AI red teaming (1-10, with 10 being most relevant)
        
        Paper Title: {paper['title']}
        Authors: {', '.join(paper['authors'])}
        Abstract: {paper['summary']}
        
        Return ONLY a JSON object with these keys:
        {{
          "brief_overview": "...",
          "technical_explanation": "...",
          "categories": ["category1", "category2"],
          "relevance_score": number
        }}
        """
        return prompt
    
    def _call_llm(self, prompt: str) -> str:
        """Call the LLM API with the prompt."""
        try:
            if LLM_PROVIDER == "anthropic":
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=1024,
                    messages=[
                        {"role": "user", "content": prompt}
                    ]
                )
                return response.content[0].text
                
            elif LLM_PROVIDER == "openai":
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "You are a helpful AI research assistant skilled at analyzing academic papers."},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=1024
                )
                return response.choices[0].message.content
                
        except Exception as e:
            self.logger.error(f"API call failed: {str(e)}")
            raise
    
    def _parse_response(self, response: str) -> Dict[str, Any]:
        """Parse the JSON response from the LLM."""
        try:
            # Find and extract JSON from response
            start_idx = response.find('{')
            end_idx = response.rfind('}') + 1
            
            if start_idx >= 0 and end_idx > 0:
                json_str = response[start_idx:end_idx]
                result = json.loads(json_str)
                
                # Validate required fields
                if not all(k in result for k in ['brief_overview', 'technical_explanation', 'categories', 'relevance_score']):
                    missing = [k for k in ['brief_overview', 'technical_explanation', 'categories', 'relevance_score'] if k not in result]
                    self.logger.warning(f"Missing required fields in LLM response: {missing}")
                
                return result
            else:
                self.logger.error("Could not find JSON in response")
                raise ValueError("No JSON found in response")
                
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse JSON: {str(e)}, Response: {response[:200]}...")
            raise
