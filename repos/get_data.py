import requests
import json
import csv
from datetime import datetime
import os
import pandas as pd
import markdown
from tabulate import tabulate

def ensure_directory_exists(file_path):
    """Create directory if it doesn't exist"""
    directory = os.path.dirname(file_path)
    if directory and not os.path.exists(directory):
        os.makedirs(directory)

def create_markdown_report(csv_path, output_path):
    # Read CSV data
    df = pd.read_csv(csv_path)

    # Select key columns - only include columns that exist
    desired_columns = ['name', 'tvl', 'category', 'change_1d', 'change_7d', 'url']
    key_columns = [col for col in desired_columns if col in df.columns]

    # Create markdown table
    markdown_table = df[key_columns].to_markdown(index=False)

    # Create the output markdown file
    output = f"""# Solana DeFi Protocols

<details>
<summary>View Protocol List (Click to expand)</summary>

{markdown_table}

</details>

## Additional Details

<details>
<summary>Full Protocol Information</summary>

{df.to_markdown(index=False)}

</details>
"""

    # Ensure directory exists and write to file
    ensure_directory_exists(output_path)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(output)

def get_data(output_file_csv, output_file_md):
    url = "https://api.llama.fi/protocols"
    response = requests.get(url)
    data = response.json()

    # Filter for Solana protocols
    solana_protocols = [protocol for protocol in data if "Solana" in protocol.get("chains", [])]

    # Get all possible fields from all protocols
    fieldnames = set()
    for protocol in solana_protocols:
        fieldnames.update(protocol.keys())
    fieldnames = sorted(list(fieldnames))

    # Ensure directory exists before writing
    ensure_directory_exists(output_file_csv)

    # Write to CSV
    with open(output_file_csv, 'w', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(solana_protocols)

    # After writing CSV, create markdown report
    create_markdown_report(output_file_csv, output_file_md)

if __name__ == "__main__":
    # Set up base directory relative to the script location
    script_dir = os.path.dirname(os.path.abspath(__file__))
    base_output_dir = os.path.join(script_dir, 'output', 'solana-defi-llama-data', 'solana')
    
    # Generate today's date
    today = datetime.now().strftime('%Y-%m-%d')
    
    # Create file paths
    output_file_csv = os.path.join(base_output_dir, f'protocols-{today}.csv')
    output_file_md = os.path.join(base_output_dir, f'protocols-{today}.md')
    
    get_data(output_file_csv, output_file_md)