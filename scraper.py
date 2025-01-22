import ssl
import urllib.request
import certifi
import requests
from bs4 import BeautifulSoup
import os
import sys
import re
import markdown
import json
from pathlib import Path

def print_debug_info():
    """Print debug information about the Python environment"""
    print(f"Python version: {sys.version}")
    print(f"Certifi version: {certifi.__version__}")
    print(f"Certifi location: {certifi.where()}")
    print(f"SSL default verify paths: {ssl.get_default_verify_paths()}")

def create_session():
    """Create a requests session with proper SSL verification"""
    session = requests.Session()
    session.verify = certifi.where()
    return session

def clean_html(html_content):
    """Clean HTML content and convert to markdown-friendly format"""
    # Remove script and style elements
    soup = BeautifulSoup(html_content, 'html.parser', from_encoding='utf-8')
    for script in soup(["script", "style"]):
        script.decompose()
    
    # Convert HTML to text while preserving UTF-8 encoding
    text = soup.get_text()
    
    # Clean up whitespace while maintaining UTF-8
    lines = (line.strip() for line in text.splitlines())
    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
    text = '\n'.join(chunk for chunk in chunks if chunk)
    
    # Ensure proper UTF-8 encoding
    return text.encode('utf-8', errors='ignore').decode('utf-8')

def scrape_class_doc(session, class_url):
    """Scrape documentation for a specific class"""
    try:
        response = session.get(class_url)
        response.raise_for_status()
        response.encoding = 'utf-8'  # Explicitly set response encoding
        soup = BeautifulSoup(response.text, 'html.parser', from_encoding='utf-8')
        
        # Extract class metadata
        class_doc = {
            'description': '',
            'inheritance': '',
            'constructors': [],
            'methods': [],
            'package': ''
        }
        
        # Get package info
        package_div = soup.find('div', class_='sub-title')
        if package_div:
            package_link = package_div.find('a')
            if package_link:
                class_doc['package'] = clean_html(str(package_link.text))
        
        # Get inheritance info
        inheritance_div = soup.find('div', class_='inheritance')
        if inheritance_div:
            class_doc['inheritance'] = clean_html(str(inheritance_div))
        
        # Extract class description
        description = soup.find('div', class_='block')
        if description:
            class_doc['description'] = clean_html(str(description))
        
        # Extract constructors
        constructor_section = soup.find('section', class_='constructor-details')
        if constructor_section:
            for constructor in constructor_section.find_all('section', class_='detail'):
                constructor_info = {
                    'signature': '',
                    'description': '',
                    'parameters': []
                }
                
                # Get constructor signature
                signature = constructor.find('div', class_='member-signature')
                if signature:
                    constructor_info['signature'] = clean_html(str(signature))
                
                # Get constructor description
                desc = constructor.find('div', class_='block')
                if desc:
                    constructor_info['description'] = clean_html(str(desc))
                
                # Get parameters
                params = constructor.find_all('dd')
                for param in params:
                    param_text = clean_html(str(param))
                    if param_text:
                        constructor_info['parameters'].append(param_text)
                
                class_doc['constructors'].append(constructor_info)
        
        # Extract methods
        method_section = soup.find('section', class_='method-details')
        if method_section:
            for method in method_section.find_all('section', class_='detail'):
                method_info = {
                    'name': '',
                    'signature': '',
                    'description': '',
                    'parameters': [],
                    'returns': '',
                    'overrides': ''
                }
                
                # Get method name and signature
                signature = method.find('div', class_='member-signature')
                if signature:
                    method_info['signature'] = clean_html(str(signature))
                    name = method.find('h3')
                    if name:
                        method_info['name'] = clean_html(str(name))
                
                # Get method description
                desc = method.find('div', class_='block')
                if desc:
                    method_info['description'] = clean_html(str(desc))
                
                # Get parameters
                params = method.find_all('dd')
                for param in params:
                    param_text = clean_html(str(param))
                    if param_text:
                        method_info['parameters'].append(param_text)
                
                # Get return info
                returns = method.find('span', string='Returns:')
                if returns and returns.find_next('dd'):
                    method_info['returns'] = clean_html(str(returns.find_next('dd')))
                
                # Get override info
                overrides = method.find('span', string='Overrides:')
                if overrides and overrides.find_next('dd'):
                    method_info['overrides'] = clean_html(str(overrides.find_next('dd')))
                
                class_doc['methods'].append(method_info)
        
        return class_doc
        
    except requests.exceptions.RequestException as e:
        print(f"Error accessing class {class_url}: {e}")
        return None

def scrape_package_doc(session, package_url):
    """Scrape documentation for a package"""
    try:
        print(f"  Accessing package URL: {package_url}")
        response = session.get(package_url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        classes = []
        # Try different possible class table selectors
        def get_javadoc_format(soup):
            """Determine the Javadoc format based on HTML structure"""
            if soup.find('div', class_='table-tabs'):
                return 'modern'  # Java 11+ style
            elif soup.find('table', class_='summary-table'):
                return 'legacy'  # Older style
            return 'unknown'

        javadoc_format = get_javadoc_format(soup)
        print(f"  Detected Javadoc format: {javadoc_format}")

        if javadoc_format == 'modern':
            # Handle Java 11+ style
            tabs_div = soup.find('div', class_='table-tabs')
            summary_div = soup.find('div', id='class-summary')
            if summary_div:
                class_table = summary_div
        else:
            # Handle legacy style
            class_table = soup.find('table', class_='summary-table')
            if not class_table:
                # Try alternative class names
                class_table = (
                    soup.find('table', class_='summary') or
                    next((t for t in soup.find_all('table')
                         if 'summary' in str(t.get('class', ''))), None)
                )

        # Debug table structure
        if class_table:
            print("  Table structure:")
            print(class_table.prettify()[:500] + "...")
            print(f"  Found class table in {package_url}")

            # Extract class links based on format
            if javadoc_format == 'modern':
                links = class_table.find_all('a')
            else:
                # In legacy format, links are usually in the first column
                links = []
                for row in class_table.find_all('tr'):
                    first_col = row.find('th', class_='col-first')
                    if first_col:
                        link = first_col.find('a')
                        if link:
                            links.append(link)

            # Process found links
            for class_link in links:
                if 'href' in class_link.attrs:
                    class_url = urllib.parse.urljoin(package_url, class_link['href'])
                    print(f"    Found class: {class_link.text}")
                    class_doc = scrape_class_doc(session, class_url)
                    if class_doc:
                        classes.append({
                            'name': class_link.text,
                            'documentation': class_doc
                        })
        else:
            print(f"  No class table found in {package_url}")
            # Debug output
            print("  Available tables:")
            for table in soup.find_all('table'):
                print(f"    Table classes: {table.get('class', 'no-class')}")
        
        return classes if classes else None
        
    except requests.exceptions.RequestException as e:
        print(f"Error accessing package {package_url}: {e}")
        return None

def scrape_javadoc(base_url):
    """Scrape Javadoc content with proper SSL handling"""
    session = create_session()
    documentation = {}
    
    try:
        print(f"Accessing base URL: {base_url}")
        response = session.get(base_url)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extract package links
        packages_found = False
        print("\nDebug: HTML Structure")
        print("==================")
        print("Links found:")
        for link in soup.find_all('a'):
            print(f"  Link: {link.get('href', 'no-href')} -> {link.text}")
        
        print("\nTables found:")
        for table in soup.find_all('table'):
            print(f"  Table classes: {table.get('class', 'no-class')}")
            print("  Table content:")
            print(table.prettify()[:500] + "...")  # First 500 chars
        
        # Find all package summary links
        package_links = [link for link in soup.find_all('a')
                        if 'package-summary.html' in link.get('href', '')]
        
        if not package_links:
            print("No package summaries found!")
            return None
            
        print(f"\nFound {len(package_links)} packages to process")
        
        for package_link in package_links:
            if package_link and 'href' in package_link.attrs:
                packages_found = True
                package_name = package_link.text
                package_url = urllib.parse.urljoin(base_url, package_link['href'])
                print(f"\nScraping package: {package_name}")
                
                classes = scrape_package_doc(session, package_url)
                if classes:
                    documentation[package_name] = classes
                    print(f"Added {len(classes)} classes for {package_name}")
        
        if not packages_found:
            print("No package links found in the main page")
            print("Available links:")
            for link in soup.find_all('a'):
                print(f"  {link.get('href', 'no-href')} -> {link.text}")
        
        return documentation if documentation else None
        
    except requests.exceptions.RequestException as e:
        print(f"Error accessing {base_url}: {e}")
        return None

def save_markdown(documentation, output_file=None):
    """Save documentation to a markdown file named after the source URL"""
    if output_file is None:
        output_file = 'javadoc.md'
    """Save all documentation to a single markdown file"""
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("# ELO Javadoc Documentation\n\n")
        f.write("## Table of Contents\n\n")
        
        # Create table of contents
        for package_name in documentation:
            f.write(f"- [{package_name}](#{package_name.lower().replace('.', '')})\n")
            for class_info in documentation[package_name]:
                anchor = f"{package_name.lower().replace('.', '')}-{class_info['name'].lower()}"
                f.write(f"  - [{class_info['name']}](#{anchor})\n")
        
        f.write("\n---\n\n")
        
        # Write detailed documentation
        for package_name, classes in documentation.items():
            f.write(f"# Package {package_name}\n\n")
            
            for class_info in classes:
                anchor = f"{package_name.lower().replace('.', '')}-{class_info['name'].lower()}"
                f.write(f"## Class {class_info['name']}\n\n")
                
                # Package info
                if class_info['documentation'].get('package'):
                    f.write(f"**Package:** {class_info['documentation']['package']}\n\n")
                
                # Inheritance
                if class_info['documentation'].get('inheritance'):
                    f.write("**Inheritance:**\n\n")
                    f.write(f"{class_info['documentation']['inheritance']}\n\n")
                
                # Class description
                if class_info['documentation'].get('description'):
                    f.write("### Description\n\n")
                    f.write(f"{class_info['documentation']['description']}\n\n")
                
                # Constructors
                if class_info['documentation'].get('constructors'):
                    f.write("### Constructors\n\n")
                    for constructor in class_info['documentation']['constructors']:
                        f.write("```java\n")
                        f.write(f"{constructor['signature']}\n")
                        f.write("```\n\n")
                        
                        if constructor['description']:
                            f.write(f"{constructor['description']}\n\n")
                        
                        if constructor['parameters']:
                            f.write("**Parameters:**\n\n")
                            for param in constructor['parameters']:
                                f.write(f"- {param}\n")
                            f.write("\n")
                
                # Methods
                if class_info['documentation'].get('methods'):
                    f.write("### Methods\n\n")
                    for method in class_info['documentation']['methods']:
                        f.write(f"#### {method['name']}\n\n")
                        
                        f.write("```java\n")
                        f.write(f"{method['signature']}\n")
                        f.write("```\n\n")
                        
                        if method['description']:
                            f.write(f"{method['description']}\n\n")
                        
                        if method['parameters']:
                            f.write("**Parameters:**\n\n")
                            for param in method['parameters']:
                                f.write(f"- {param}\n")
                            f.write("\n")
                        
                        if method['returns']:
                            f.write(f"**Returns:** {method['returns']}\n\n")
                        
                        if method['overrides']:
                            f.write(f"**Overrides:** {method['overrides']}\n\n")
                
                f.write("---\n\n")

if __name__ == "__main__":
    print("Starting Javadoc scraper...")
    print_debug_info()
    
    if len(sys.argv) < 2:
        print("\nUsage: python3 scraper.py <javadoc_url>")
        print("\nExample URLs:")
        print("  https://forum.elo.com/javadoc/ix/23/")
        print("  https://forum.elo.com/javadoc/jc/23/")
        print("  https://forum.elo.com/javadoc/as/23/")
        sys.exit(1)
    
    base_url = sys.argv[1].rstrip('/')
    if not base_url.startswith('http'):
        base_url = f"https://forum.elo.com/javadoc/{base_url}"
    if not base_url.endswith('/'):
        base_url += '/'
        
    print(f"\nAttempting to scrape: {base_url}")
    
    # Generate filename from URL
    url_parts = base_url.rstrip('/').split('/')
    output_file = f"javadoc.{'.'.join(p for p in url_parts[4:] if p)}.md"
    
    documentation = scrape_javadoc(base_url)
    
    if documentation:
        print("\nSaving documentation as Markdown...")
        save_markdown(documentation, output_file)
        print(f"\nDocumentation has been saved to '{output_file}'")
    else:
        print("\nNo documentation found or error occurred")
