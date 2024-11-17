"""
# Basic usage
python3 popular.py solana

# With minimum stars and forks
python3 popular.py ethereum --min-stars 1000 --min-forks 100

# Include contributor information
python3 popular.py polkadot --contributors

# Combine all options
python3 popular.py solana --min-stars 500 --min-forks 50 --contributors
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
class BlockchainRepo:
    name: str
    stars: int
    forks: int
    last_updated: str
    description: str
    topics: List[str]
    url: str
    contributors: List[Dict] = None
    all_contributors_fetched: bool = False

def get_search_queries(blockchain: str) -> List[str]:
    """Generate search queries based on blockchain name."""
    return [
        f"topic:{blockchain}",
        f"language:rust {blockchain}",
        f"{blockchain} blockchain",
        f"{blockchain} web3"
    ]

def get_all_contributors(repo_name: str, headers: Dict) -> List[Dict]:
    """Fetch ALL contributors for a given repository, handling pagination."""
    contributors = []
    page = 1
    
    while True:
        url = f"https://api.github.com/repos/{repo_name}/contributors?page={page}&per_page=100&anon=true"
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()
            
            if not data:  # No more contributors
                break
                
            contributors.extend([{
                'username': c.get('login', 'anonymous'),
                'contributions': c['contributions'],
                'profile': c.get('html_url', ''),
                'type': c.get('type', 'Anonymous'),
                'repo': repo_name
            } for c in data])
            
            # Check for rate limiting
            if 'Link' not in response.headers:
                break
                
            time.sleep(2)  # Increased rate limiting pause
            
        except requests.RequestException as e:
            print(f"Error fetching contributors for {repo_name}: {e}")
            return contributors, False
    
    return contributors, True

def save_contributor_data(blockchain: str, all_contributors: List[Dict]):
    """Save all contributor data to a separate file."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_base = os.path.join(os.path.dirname(os.path.dirname(script_dir)), "output")
    output_dir = os.path.join(output_base, f"{blockchain}-contributors")
    os.makedirs(output_dir, exist_ok=True)
    
    date_str = datetime.now().strftime("%Y-%m-%d")
    
    # Save as JSON
    json_file = os.path.join(output_dir, f"{blockchain}_contributors_{date_str}.json")
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(all_contributors, f, indent=2)
    
    # Save as CSV
    csv_file = os.path.join(output_dir, f"{blockchain}_contributors_{date_str}.csv")
    import csv
    with open(csv_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=['username', 'contributions', 'profile', 'type', 'repo'])
        writer.writeheader()
        writer.writerows(all_contributors)

def search_blockchain_repos(blockchain: str, min_stars: int = 0, min_forks: int = 0, 
                          fetch_contributors: bool = False, token: str = None) -> List[BlockchainRepo]:
    """Modified to fetch all contributors when requested."""
    
    headers = {
        "Accept": "application/vnd.github.v3+json"
    }
    
    if token:
        headers["Authorization"] = f"token {token}"

    queries = get_search_queries(blockchain)
    all_repos = {}
    
    all_contributors = []
    for query in queries:
        query_with_filters = f"{query}+stars:>={min_stars}+forks:>={min_forks}"
        url = f"https://api.github.com/search/repositories?q={query_with_filters}&sort=stars&order=desc&per_page=100"
        
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()
            
            for repo in data.get("items", []):
                if repo["id"] not in all_repos:
                    contributors = None
                    all_contributors_fetched = False
                    
                    if fetch_contributors:
                        contributors, all_contributors_fetched = get_all_contributors(repo["full_name"], headers)
                        if contributors:
                            all_contributors.extend(contributors)
                            
                    all_repos[repo["id"]] = BlockchainRepo(
                        name=repo["full_name"],
                        stars=repo["stargazers_count"],
                        forks=repo["forks_count"],
                        last_updated=repo["updated_at"],
                        description=repo["description"] or "",
                        topics=repo["topics"],
                        url=repo["html_url"],
                        contributors=contributors,
                        all_contributors_fetched=all_contributors_fetched
                    )
            
            time.sleep(2)
            
        except requests.RequestException as e:
            print(f"Error fetching results for query '{query}': {e}")
    
    if fetch_contributors:
        save_contributor_data(blockchain, all_contributors)
    
    return sorted(all_repos.values(), key=lambda x: x.stars, reverse=True)

def save_results(blockchain: str, repos: List[BlockchainRepo], format: str = "markdown"):
    """Save repository results in the specified format."""
    
    # Get the absolute path of the script's directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # Resolve output path relative to project root
    output_base = os.path.join(os.path.dirname(os.path.dirname(script_dir)), "output")
    output_dir = os.path.join(output_base, f"{blockchain}-repos")
    os.makedirs(output_dir, exist_ok=True)
    
    date_str = datetime.now().strftime("%Y-%m-%d")
    
    if format == "markdown":
        output_file = os.path.join(output_dir, f"{blockchain}_repos_{date_str}.md")
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(f"# Popular {blockchain.title()} Repositories\n\n")
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
                                       reverse=True)[:10]:  # Show top 10
                        f.write(f"- [{contrib['username']}]({contrib['profile']}): "
                               f"{contrib['contributions']} contributions\n")
                    f.write("\n")
                f.write("---\n\n")
    
    elif format == "json":
        output_file = os.path.join(output_dir, f"{blockchain}_repos_{date_str}.json")
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump([vars(repo) for repo in repos], f, indent=2)

def main():
    # Load environment variables from .env file
    load_dotenv()
    
    import argparse
    
    parser = argparse.ArgumentParser(description='Search for blockchain repositories on GitHub')
    parser.add_argument('blockchain', help='Name of the blockchain (e.g., solana, ethereum)')
    parser.add_argument('--min-stars', type=int, default=0, help='Minimum number of stars')
    parser.add_argument('--min-forks', type=int, default=0, help='Minimum number of forks')
    parser.add_argument('--contributors', action='store_true', help='Fetch contributor information')
    
    args = parser.parse_args()
    
    blockchain = args.blockchain.lower()
    
    # Get GitHub token from environment variable
    token = os.getenv("GITHUB_TOKEN")
    
    if not token:
        print("Warning: No GitHub token found. Rate limits will be restricted.")
        print("Set your token with: export GITHUB_TOKEN=your_token_here")
    
    print(f"Searching for popular {blockchain} repositories...")
    print(f"Minimum stars: {args.min_stars}")
    print(f"Minimum forks: {args.min_forks}")
    print(f"Fetching contributors: {args.contributors}")
    
    repos = search_blockchain_repos(
        blockchain, 
        min_stars=args.min_stars, 
        min_forks=args.min_forks,
        fetch_contributors=args.contributors,
        token=token
    )
    
    print(f"\nFound {len(repos)} unique repositories")
    print("\nTop 10 repositories by stars:")
    for repo in repos[:10]:
        print(f"- {repo.name}: ⭐ {repo.stars}")
    
    # Save in both formats
    save_results(blockchain, repos, "markdown")
    save_results(blockchain, repos, "json")
    
    print(f"\nResults have been saved to the output/{blockchain}-repos directory")

if __name__ == "__main__":
    main()