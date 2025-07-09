#!/usr/bin/env python3
"""
GEO Evaluator - Generative Engine Optimization Analysis Tool

Analyzes websites for optimization to improve LLM understanding and brand representation.
Evaluates content structure, readability, token efficiency, and LLM-specific features.
"""

import argparse
import sys
import logging
import os
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from config_manager import ConfigurationManager
from utils import setup_logging, validate_url


def main():
    """Main entry point for the GEO Evaluator CLI."""
    
    parser = argparse.ArgumentParser(
        description="GEO Evaluator - Analyze websites for Generative Engine Optimization",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze Airbais website with default settings
  python geoevaluator.py --url https://airbais.com --name "Airbais"
  
  # Use a configuration file
  python geoevaluator.py config.yaml
  
  # Quick analysis with custom output directory
  python geoevaluator.py --url https://example.com --output ./my-results
  
  # Dashboard integration mode
  python geoevaluator.py config.yaml --dashboard
        """
    )
    
    # Configuration options
    parser.add_argument(
        'config_file',
        nargs='?',
        help='Configuration file path (YAML format)'
    )
    
    parser.add_argument(
        '--url',
        help='Website URL to analyze'
    )
    
    parser.add_argument(
        '--name',
        help='Website/brand name for analysis'
    )
    
    # Analysis options
    parser.add_argument(
        '--max-pages',
        type=int,
        default=50,
        help='Maximum number of pages to analyze (default: 50)'
    )
    
    parser.add_argument(
        '--crawl-depth',
        type=int,
        default=3,
        help='Maximum crawl depth (default: 3)'
    )
    
    # Output options
    parser.add_argument(
        '--output-dir',
        default='./results',
        help='Output directory for results (default: ./results)'
    )
    
    parser.add_argument(
        '--dashboard',
        action='store_true',
        help='Generate dashboard-compatible output'
    )
    
    parser.add_argument(
        '--formats',
        nargs='+',
        choices=['json', 'html', 'dashboard'],
        default=['json', 'dashboard'],
        help='Output formats to generate (default: json, dashboard)'
    )
    
    # Crawling options
    parser.add_argument(
        '--delay',
        type=float,
        default=1.0,
        help='Delay between requests in seconds (default: 1.0)'
    )
    
    parser.add_argument(
        '--timeout',
        type=int,
        default=30,
        help='Request timeout in seconds (default: 30)'
    )
    
    # Utility options
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Validate configuration without running analysis'
    )
    
    parser.add_argument(
        '--version',
        action='version',
        version='GEO Evaluator 1.0.0'
    )
    
    args = parser.parse_args()
    
    # Setup logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    setup_logging(log_level)
    logger = logging.getLogger(__name__)
    
    try:
        # Load configuration
        config_manager = ConfigurationManager()
        
        if args.config_file:
            # Load from file
            if not os.path.exists(args.config_file):
                logger.error(f"Configuration file not found: {args.config_file}")
                sys.exit(1)
            
            config = config_manager.load_from_file(args.config_file)
            logger.info(f"Loaded configuration from {args.config_file}")
        else:
            # Create from command line arguments
            if not args.url:
                logger.error("URL is required when not using a configuration file")
                parser.print_help()
                sys.exit(1)
            
            config = config_manager.create_from_args(args)
            logger.info(f"Created configuration for {args.url}")
        
        # Override config with command line arguments
        config = config_manager.apply_cli_overrides(config, args)
        
        # Validate configuration
        validation_result = config_manager.validate_config(config)
        if not validation_result['valid']:
            logger.error("Configuration validation failed:")
            for error in validation_result['errors']:
                logger.error(f"  - {error}")
            sys.exit(1)
        
        if args.dry_run:
            logger.info("Configuration validation successful!")
            logger.info(f"Would analyze: {config['website']['url']}")
            logger.info(f"Max pages: {config['website']['max_pages']}")
            logger.info(f"Output formats: {config['output']['formats']}")
            return
        
        # Run the analysis
        logger.info("Starting GEO analysis...")
        logger.info(f"Target: {config['website']['url']}")
        logger.info(f"Brand: {config['website']['name']}")
        
        # Import and run the main analysis pipeline
        from main import GEOAnalysisPipeline
        
        pipeline = GEOAnalysisPipeline(config)
        results = pipeline.run()
        
        if results:
            logger.info("Analysis completed successfully!")
            
            # Show key results
            overall_score = results.get('overall_score', {}).get('total_score', 0)
            grade = results.get('overall_score', {}).get('grade', 'Unknown')
            pages_analyzed = results.get('metadata', {}).get('pages_analyzed', 0)
            
            logger.info(f"Overall Score: {overall_score:.1f}/100 ({grade})")
            logger.info(f"Pages Analyzed: {pages_analyzed}")
            
            # Show output locations
            output_dir = results.get('metadata', {}).get('output_directory', '')
            if output_dir:
                logger.info(f"Results saved to: {output_dir}")
                
                # List generated files
                output_path = Path(output_dir)
                if output_path.exists():
                    files = list(output_path.glob('*'))
                    if files:
                        logger.info("Generated files:")
                        for file in sorted(files):
                            logger.info(f"  - {file.name}")
            
            if args.dashboard:
                logger.info("Dashboard data generated - launching master dashboard...")
                try:
                    # Import and launch the master dashboard
                    dashboard_path = Path(__file__).parent.parent / 'dashboard' / 'run_dashboard.py'
                    if dashboard_path.exists():
                        import subprocess
                        subprocess.run([sys.executable, str(dashboard_path)], check=True)
                    else:
                        logger.warning("Master dashboard not found - results available in output directory")
                except Exception as e:
                    logger.error(f"Failed to launch dashboard: {e}")
                    logger.info("Dashboard data is available in the output directory")
        else:
            logger.error("Analysis failed to complete")
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.info("Analysis interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Analysis failed: {str(e)}")
        if args.verbose:
            logger.exception("Full error details:")
        sys.exit(1)


if __name__ == '__main__':
    main()