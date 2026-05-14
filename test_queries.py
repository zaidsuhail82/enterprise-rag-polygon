#!/usr/bin/env python3
"""
Test Query Script - Verify Phase 1 Retrieval
Uses the project's native BM25Retriever to ensure compatibility.
"""

import sys
from pathlib import Path

# Ensure project root is on the path so we can import our src
sys.path.insert(0, str(Path(__file__).parent))

from src.retrieval.bm25_retriever import BM25Retriever

class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    END = '\033[0m'
    BOLD = '\033[1m'

def run_test_queries():
    """Run test queries using the native BM25Retriever class"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*70}{Colors.END}")
    print(f"{Colors.BOLD}Phase 1 Verification - Native BM25 Test{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*70}{Colors.END}\n")
    
    # Initialize the actual class from your project
    # This automatically handles the pickle loading and bm25s initialization
    try:
        retriever = BM25Retriever()
        
        if retriever._retriever is None:
            print(f"{Colors.RED}✗ BM25 index not found or failed to load.{Colors.END}")
            print("  Check if data/bm25_index.pkl exists.")
            return

        print(f"{Colors.GREEN}✓ BM25 index loaded successfully{Colors.END}")
        print(f"  Total Chunks available: {len(retriever._chunk_ids)}")
        print(f"  Payloads indexed: {len(retriever._payloads)}\n")

    except Exception as e:
        print(f"{Colors.RED}✗ Initialization failed: {e}{Colors.END}")
        return

    # Test queries mapping to your Pattern A/B logic
    test_cases = [
        {
            'pattern': 'A',
            'name': 'Activity Monitoring',
            'query': 'recent proposal technical document',
            'description': 'Testing recency + document type search'
        },
        {
            'pattern': 'B',
            'name': 'Institutional Memory',
            'query': 'bKash eKYC merchant onboarding',
            'description': 'Testing project-specific search'
        },
        {
            'pattern': 'B',
            'name': 'Institutional Memory',
            'query': 'Polygon Technology company profile',
            'description': 'Testing company-specific search'
        },
        {
            'pattern': 'A',
            'name': 'Activity Monitoring',
            'query': 'agreement contract proposal',
            'description': 'Testing document type search'
        },
        {
            'pattern': 'B',
            'name': 'Institutional Memory',
            'query': 'financial services banking solution',
            'description': 'Testing sector-based search'
        }
    ]
    
    print(f"{Colors.BOLD}Running {len(test_cases)} test queries...{Colors.END}\n")
    
    for i, test in enumerate(test_cases, 1):
        print(f"{Colors.BOLD}{Colors.CYAN}Test {i}: Pattern {test['pattern']} - {test['name']}{Colors.END}")
        print(f"  Query: \"{test['query']}\"")
        
        # Using your actual retriever.search method
        results = retriever.search(test['query'], top_k=3)
        
        if results:
            print(f"  {Colors.GREEN}✓ Found {len(results)} matches{Colors.END}")
            for j, res in enumerate(results, 1):
                payload = res.get('payload', {})
                
                # Use the exact key from your diagnostic logs
                file_name = payload.get('document_name', 'Unknown File')
                folder = payload.get('folder_path', 'Root')
                
                score = res['score']
                print(f"    {j}. {Colors.BOLD}{file_name}{Colors.END}")
                print(f"       Path: {folder}")
                print(f"       Score: {score:.2f}")

if __name__ == '__main__':
    run_test_queries()