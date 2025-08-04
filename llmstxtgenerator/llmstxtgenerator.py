#!/usr/bin/env python3
"""
LLMS.txt Generator - Generate LLMS.txt files for websites
Part of the Airbais Tools Suite
"""

import argparse
import sys
from src.main import run_generator


def main():
    parser = argparse.ArgumentParser(
        description="Generate LLMS.txt files for websites to help LLMs understand their content",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s https://example.com
  %(prog)s https://example.com --name "My Project" --description "A cool project"
  %(prog)s https://example.com --max-pages 50 --max-depth 2
  %(prog)s https://example.com --no-ai --output-dir custom_results
  %(prog)s --config custom_config.yaml
  %(prog)s --max-pages 50        # Uses URL from config.yaml
  %(prog)s                       # Uses all defaults from config.yaml
        """
    )
    
    # Main arguments
    parser.add_argument('url', nargs='?', help='Website URL to generate LLMS.txt for')
    parser.add_argument('-c', '--config', default='config.yaml', help='Configuration file path (default: config.yaml)')
    
    # Website information
    parser.add_argument('--name', help='Website/project name (overrides auto-detection)')
    parser.add_argument('--description', help='Website/project description (overrides auto-detection)')
    
    # Crawling options
    parser.add_argument('--max-pages', type=int, help='Maximum number of pages to crawl')
    parser.add_argument('--max-depth', type=int, help='Maximum crawl depth')
    
    # Analysis options
    parser.add_argument('--no-ai', action='store_true', help='Disable AI-generated descriptions')
    
    # Output options
    parser.add_argument('-o', '--output-dir', help='Output directory for results')
    parser.add_argument('--dashboard', action='store_true', help='Launch dashboard after generation')
    
    # Other options
    parser.add_argument('-v', '--verbose', action='store_true', help='Enable verbose logging')
    parser.add_argument('--version', action='version', version='%(prog)s 1.0.0')
    
    args = parser.parse_args()
    
    # Validate arguments - check if config file has URL before requiring command line URL
    if not args.url:
        try:
            from src.config_manager import ConfigManager
            config = ConfigManager(args.config)
            if not config.website_url:
                parser.error("No URL provided. Either provide a URL argument or configure one in the config file.")
        except FileNotFoundError:
            parser.error("Configuration file not found. Either provide a URL argument or create a config.yaml file.")
        except Exception as e:
            parser.error(f"Error reading configuration: {e}")
    
    # Run the generator
    result = run_generator(
        config_path=args.config,
        url=args.url,
        name=args.name,
        description=args.description,
        max_pages=args.max_pages,
        max_depth=args.max_depth,
        no_ai=args.no_ai,
        output_dir=args.output_dir,
        dashboard=args.dashboard,
        verbose=args.verbose
    )
    
    # Exit with appropriate code
    if result['status'] == 'success':
        print(f"\n✅ Successfully generated LLMS.txt files!")
        print(f"📁 Files generated: {result['files_generated']}")
        print(f"📊 Pages crawled: {result['metrics']['pages_crawled']}")
        print(f"📑 Sections found: {result['metrics']['sections_found']}")
        sys.exit(0)
    else:
        print(f"\n❌ Error: {result.get('message', 'Unknown error')}")
        sys.exit(1)


if __name__ == '__main__':
    main()