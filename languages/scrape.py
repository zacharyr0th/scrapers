"""
Language-specific Blockchain Repository Scraper
============================================

Usage:
python3 scrape.py rust --min-stars 100
python3 scrape.py solidity --min-forks 50
python3 scrape.py go --contributors

Features:
- Scrapes repositories in specific languages related to blockchain
- Filters by minimum stars and forks
- Optional contributor information
- Saves results in multiple formats
"""

import requests
import json
import os
from datetime import datetime
from typing import List, Dict
from dataclasses import dataclass
import time
from dotenv import load_dotenv

@dataclass
class LanguageRepo:
    name: str
    stars: int
    forks: int
    last_updated: str
    description: str
    topics: List[str]
    url: str
    language: str
    contributors: List[Dict] = None
    all_contributors_fetched: bool = False

def get_blockchain_keywords() -> List[str]:
    """Common blockchain-related keywords for search."""
    return [
        "blockchain",
        "cryptocurrency",
        "web3",
        "crypto",
        "defi",
        "smart-contracts",
        "consensus",
        "distributed-ledger",
        "nft",
        "dao"
    ]

def get_search_queries(language: str) -> List[str]:
    """Generate search queries combining language and blockchain terms."""
    keywords = get_blockchain_keywords()
    queries = []
    
    for keyword in keywords:
        queries.append(f"language:{language} {keyword}")
        
    # Add specific blockchain platform searches
    blockchain_platforms = [
        "ethereum", "solana", "polkadot", "cosmos", "near",
        "cardano", "avalanche", "polygon", "substrate"
    ]
    
    for platform in blockchain_platforms:
        queries.append(f"language:{language} {platform}")
        
    return queries

def get_all_contributors(repo_name: str, headers: Dict) -> tuple[List[Dict], bool]:
    """Fetch all contributors for a repository."""
    contributors = []
    page = 1
    all_fetched = True
    
    while True:
        url = f"https://api.github.com/repos/{repo_name}/contributors?page={page}&per_page=100"
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()
            
            if not data:
                break
                
            contributors.extend([{
                'username': c.get('login', 'anonymous'),
                'contributions': c['contributions'],
                'profile': c.get('html_url', ''),
                'type': c.get('type', 'Anonymous')
            } for c in data])
            
            if 'Link' not in response.headers:
                break
                
            page += 1
            time.sleep(1)  # Rate limiting
            
        except requests.RequestException as e:
            print(f"Error fetching contributors for {repo_name}: {e}")
            all_fetched = False
            break
    
    return contributors, all_fetched

def search_language_repos(language: str, min_stars: int = 0, min_forks: int = 0, 
                        fetch_contributors: bool = False) -> List[LanguageRepo]:
    """Search for blockchain-related repositories in specified language."""
    
    load_dotenv()
    token = os.getenv('GITHUB_TOKEN')
    
    headers = {
        "Accept": "application/vnd.github.v3+json"
    }
    
    if token:
        headers["Authorization"] = f"token {token}"

    queries = get_search_queries(language)
    all_repos = {}
    
    for query in queries:
        url = f"https://api.github.com/search/repositories?q={query}&sort=stars&order=desc"
        
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()
            
            for repo in data.get("items", []):
                if (repo["stargazers_count"] >= min_stars and 
                    repo["forks_count"] >= min_forks and
                    repo["id"] not in all_repos):
                    
                    contributors = None
                    all_contributors_fetched = False
                    
                    if fetch_contributors:
                        contributors, all_contributors_fetched = get_all_contributors(
                            repo["full_name"], headers
                        )
                    
                    all_repos[repo["id"]] = LanguageRepo(
                        name=repo["full_name"],
                        stars=repo["stargazers_count"],
                        forks=repo["forks_count"],
                        last_updated=repo["updated_at"],
                        description=repo["description"] or "",
                        topics=repo["topics"],
                        url=repo["html_url"],
                        language=repo["language"],
                        contributors=contributors,
                        all_contributors_fetched=all_contributors_fetched
                    )
            
            time.sleep(2)  # Rate limiting
            
        except requests.RequestException as e:
            print(f"Error fetching results for query '{query}': {e}")
    
    return sorted(all_repos.values(), key=lambda x: x.stars, reverse=True)

def save_results(language: str, repos: List[LanguageRepo]):
    """Save results to markdown and JSON files."""
    
    # Get the absolute path of the script's directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Go up one directory to reach project root
    project_root = os.path.dirname(script_dir)
    
    # Create output directory in project root
    output_dir = os.path.join(project_root, "output", f"{language}-repos")
    os.makedirs(output_dir, exist_ok=True)
    
    date_str = datetime.now().strftime("%Y-%m-%d")
    
    # Save as markdown
    md_file = os.path.join(output_dir, f"{language}_repos_{date_str}.md")
    with open(md_file, "w", encoding="utf-8") as f:
        f.write(f"# {language.title()} Blockchain Repositories\n\n")
        f.write(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        for repo in repos:
            f.write(f"## [{repo.name}]({repo.url})\n")
            f.write(f"⭐ Stars: {repo.stars} | 🔄 Forks: {repo.forks}\n\n")
            f.write(f"{repo.description}\n\n")
            if repo.topics:
                f.write("**Topics:** " + ", ".join(repo.topics) + "\n\n")
            if repo.contributors:
                f.write("### Top Contributors:\n")
                for contrib in sorted(repo.contributors, 
                                   key=lambda x: x['contributions'], 
                                   reverse=True)[:10]:
                    f.write(f"- [{contrib['username']}]({contrib['profile']}): "
                           f"{contrib['contributions']} contributions\n")
            f.write("---\n\n")
    
    # Save as JSON
    json_file = os.path.join(output_dir, f"{language}_repos_{date_str}.json")
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump([{
            "name": repo.name,
            "stars": repo.stars,
            "forks": repo.forks,
            "last_updated": repo.last_updated,
            "description": repo.description,
            "topics": repo.topics,
            "url": repo.url,
            "language": repo.language,
            "contributors": repo.contributors
        } for repo in repos], f, indent=2)

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Search for blockchain repositories in a specific language')
    parser.add_argument('language', help='Programming language (e.g., rust, solidity)')
    parser.add_argument('--min-stars', type=int, default=0, help='Minimum number of stars')
    parser.add_argument('--min-forks', type=int, default=0, help='Minimum number of forks')
    parser.add_argument('--contributors', action='store_true', help='Fetch contributor information')
    
    args = parser.parse_args()
    
    print(f"Searching for {args.language} blockchain repositories...")
    repos = search_language_repos(
        args.language,
        min_stars=args.min_stars,
        min_forks=args.min_forks,
        fetch_contributors=args.contributors
    )
    
    print(f"\nFound {len(repos)} repositories")
    save_results(args.language, repos)
    print(f"\nResults saved in output/{args.language}-repos/")

if __name__ == "__main__":
    main()