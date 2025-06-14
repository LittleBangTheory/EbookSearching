#!/usr/bin/env python3
"""
Ebook Search Script for Specialized Sites
Uses Google Custom Search API to find books across multiple platforms
"""

import requests
from dotenv import load_dotenv
import re
import json
import time
import pandas as pd
from urllib.parse import quote
import os
from typing import List, Dict, Any

class EbookSearcher:
    def __init__(self, api_key: str, search_engine_id: str):
        """
        Initialize the ebook searcher
        
        Args:
            api_key: Google Custom Search API key
            search_engine_id: Custom Search Engine ID
        """
        self.api_key = api_key
        self.search_engine_id = search_engine_id
        self.base_url = "https://www.googleapis.com/customsearch/v1"
        
        # Popular ebook sites
        self.ebook_sites_file = "ebook_sites.txt"
        self.ebook_sites = self.get_ebook_sites()
    
    def get_ebook_sites(self) -> List[str]:
        """
        Get a list of popular ebook sites from the file, or raise an error if not found
        
        Returns:
            List of ebook sites
        """
        if not os.path.exists(self.ebook_sites_file):
            raise FileNotFoundError(f"Please create a file named '{self.ebook_sites_file}' with ebook sites.")
        
        # Regex matches lines that look like URLs
        url_pattern = re.compile(r'^[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
        with open(self.ebook_sites_file, 'r') as file:
            sites = [line.strip() for line in file if url_pattern.match(line.strip())]
        
        if not sites:
            raise ValueError("No ebook sites found in the file.")
        
        print(f"Found {len(sites)} ebook sites.")

        return sites

    def build_query(self, keywords: List[str], site: str = "", filetypes: list[str] = "") -> str:
        """
        Build the search query
        
        Args:
            keywords: List of keywords to search for
            site: Specific site to target (optional)
        
        Returns:
            Formatted query for Google
        """
        # Join keywords with quotes for exact search
        keyword_query = " ".join([f'"{keyword}"' for keyword in keywords])

        # Initialize query
        query = ""

        # If a specific site is provided, add it to the query
        if site :
            query += f'site:{site} '

        # Add keywords to the query
        query += keyword_query

        # If filetypes are specified, add them to the query
        if filetypes:
            filetypes_query = " OR ".join([f'filetype:{ft}' for ft in filetypes])
            query += f' {filetypes_query}'
        
        return quote(query)  # URL encode the query for safe transmission
    
    def search_books(self, keywords: List[str], sites: List[str] = None, 
                    max_results_per_site: int = 10, filetypes: List[str] = None
                    ) -> List[Dict[str, Any]]:
        """
        Search for books on specified sites
        
        Args:
            keywords: Keywords to search for
            sites: List of sites (uses self.ebook_sites by default)
            max_results_per_site: Maximum number of results per site
        
        Returns:
            List of found results
        """
        if sites is None:
            sites = self.ebook_sites
        
        all_results = []
        
        for site in sites:
            print(f"Searching on {site}...")
            query = self.build_query(keywords, site, filetypes)
            
            try:
                results = self._perform_search(query, max_results_per_site)
                for result in results:
                    result['source_site'] = site
                    result['search_keywords'] = keywords
                all_results.extend(results)
                
                # Pause to avoid API rate limits
                time.sleep(1)
                
            except Exception as e:
                print(f"Error searching on {site}: {e}")
                continue
        
        return all_results
    
    def _perform_search(self, query: str, max_results: int) -> List[Dict[str, Any]]:
        """
        Perform search via Google API
        
        Args:
            query: Search query
            max_results: Maximum number of results
        
        Returns:
            List of results
        """
        results = []
        start_index = 1
        
        while len(results) < max_results and start_index <= 91:  # Google API limit
            params = {
                'key': self.api_key,
                'cx': self.search_engine_id,
                'q': query,
                'start': start_index,
                'num': min(10, max_results - len(results))
            }
            
            response = requests.get(self.base_url, params=params)
            
            if response.status_code != 200:
                print(f"API Error: {response.status_code}")
                break
            
            data = response.json()
            
            if 'items' not in data:
                break
            
            for item in data['items']:
                result = {
                    'title': item.get('title', ''),
                    'link': item.get('link', ''),
                    'snippet': item.get('snippet', ''),
                    'displayLink': item.get('displayLink', ''),
                    'formattedUrl': item.get('formattedUrl', '')
                }
                results.append(result)
            
            start_index += 10
        
        return results[:max_results]
    
    def save_results(self, results: List[Dict[str, Any]], filename: str = "ebook_results.csv"):
        """
        Save results to CSV file
        
        Args:
            results: List of results
            filename: Output filename
        """
        if not results:
            print("No results to save.")
            return
        
        df = pd.DataFrame(results)
        df.to_csv(filename, index=False, encoding='utf-8')
        print(f"Results saved to {filename}")
    
    def display_results(self, results: List[Dict[str, Any]], limit: int = 20):
        """
        Display results in formatted way
        
        Args:
            results: List of results
            limit: Number of results to display
        """
        if not results:
            print("No results found.")
            return
        
        print(f"\n=== {len(results)} results found ===\n")
        
        for i, result in enumerate(results[:limit], 1):
            print(f"{i}. {result['title']}")
            print(f"   Site: {result.get('source_site', 'N/A')}")
            print(f"   URL: {result['link']}")
            print(f"   Description: {result['snippet'][:100]}...")
            print("-" * 80)

def load_environment_variables() -> tuple[str, str, List[str]]:
    """
    Load environment variables from .env file
    """
    try:
        load_dotenv()
        api_key = os.getenv('API_KEY')
        search_engine_id = os.getenv('SEARCH_ENGINE_ID')
        keywords = load_and_clean_env_list('KEYWORDS')
        filetypes = load_and_clean_env_list('FILETYPES')
        max_results_per_site = int(os.getenv('MAX_RESULTS_PER_SITE', 10))

    except ImportError:
        raise ImportError("Please install python-dotenv to load environment variables.")
    except Exception as e:
        raise RuntimeError(f"Error loading environment variables: {e}")
        
    if any(x is None for x in [api_key, search_engine_id, keywords]) :
        raise ValueError("Please set GOOGLE_API_KEY, GOOGLE_CSE_ID, and SEARCH_KEYWORDS in your .env file.")
     
    return api_key, search_engine_id, keywords, filetypes, max_results_per_site

def load_and_clean_env_list(env_var: str) -> List[str]:
    values = os.getenv(env_var, '').split(',')
    values = [value.strip() for value in values if value.strip()]  # Clean up value
    return values

def main():
    """
    Main function - Configuration and execution
    """

    # Import keys from .env file
    API_KEY, SEARCH_ENGINE_ID, keywords, filetypes, max_results_per_site = load_environment_variables()
    
    # Initialize searcher
    searcher = EbookSearcher(API_KEY, SEARCH_ENGINE_ID)
    
    print(f"Searching for books with keywords: {keywords}")
    print("=" * 50)
    
    # Search across all sites
    results = searcher.search_books(
        keywords=keywords,
        max_results_per_site=max_results_per_site,  # Limit for testing
        filetypes=filetypes
    )
    
    # Display results
    searcher.display_results(results)
    
    # Save results
    searcher.save_results(results, "ebook_search_results.csv")
    
    # Statistics
    print(f"\n📊 Statistics:")
    print(f"Total results: {len(results)}")
    
    if results:
        sites_count = {}
        for result in results:
            site = result.get('source_site', 'Unknown')
            sites_count[site] = sites_count.get(site, 0) + 1
        
        print("Distribution by site:")
        for site, count in sorted(sites_count.items(), key=lambda x: x[1], reverse=True):
            print(f"  {site}: {count} results")

# Google Colab configuration
def setup_colab():
    """
    Specific configuration for Google Colab
    """
    try:
        from google.colab import drive, files
        import ipywidgets as widgets
        from IPython.display import display
        
        print("🚀 Google Colab configuration detected")
        
        # Interface for entering API keys
        api_key_widget = widgets.Text(
            description='API Key:',
            placeholder='Enter your Google API key',
            style={'description_width': 'initial'}
        )
        
        cse_id_widget = widgets.Text(
            description='CSE ID:',
            placeholder='Enter your Custom Search Engine ID',
            style={'description_width': 'initial'}
        )
        
        keywords_widget = widgets.Text(
            description='Keywords:',
            placeholder='Ex: Nietzsche, Gay (comma-separated)',
            style={'description_width': 'initial'}
        )
        
        button = widgets.Button(description="Start Search")
        output = widgets.Output()
        
        def on_button_click(b):
            with output:
                output.clear_output()
                if api_key_widget.value and cse_id_widget.value:
                    os.environ['GOOGLE_API_KEY'] = api_key_widget.value
                    os.environ['GOOGLE_CSE_ID'] = cse_id_widget.value
                    
                    # Parse keywords
                    keywords = [kw.strip().strip('"') for kw in keywords_widget.value.split(',')]
                    
                    # Execute search
                    searcher = EbookSearcher(api_key_widget.value, cse_id_widget.value)
                    results = searcher.search_books(keywords, max_results_per_site=5)
                    searcher.display_results(results)
                    searcher.save_results(results)
                    
                    print("\n💾 Downloading CSV file...")
                    files.download('ebook_search_results.csv')
                else:
                    print("⚠️  Please fill in all fields!")
        
        button.on_click(on_button_click)
        
        display(api_key_widget, cse_id_widget, keywords_widget, button, output)
        
    except ImportError:
        print("📝 Standard environment detected")
        main()

if __name__ == "__main__":
    # Automatic environment detection
    try:
        import google.colab
        setup_colab()
    except ImportError:
        main()