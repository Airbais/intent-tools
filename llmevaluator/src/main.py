"""
LLM Evaluator - Main Entry Point
Evaluates brand presence and sentiment in LLM responses
"""

import os
import sys
import argparse
import logging
from pathlib import Path
from datetime import datetime
import colorlog

from .config import ConfigurationManager
from .llm_interface import LLMInterface
from .prompt_executor import PromptExecutor
from .analyzer import ResponseAnalyzer
from .metrics import MetricsCalculator
from .report_generator import ReportGenerator

def setup_logging(log_level: str = "INFO") -> None:
    """Set up colored logging"""
    handler = colorlog.StreamHandler()
    handler.setFormatter(
        colorlog.ColoredFormatter(
            '%(log_color)s%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S',
            log_colors={
                'DEBUG': 'cyan',
                'INFO': 'green',
                'WARNING': 'yellow',
                'ERROR': 'red',
                'CRITICAL': 'red,bg_white',
            }
        )
    )
    
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, log_level.upper()))
    logger.addHandler(handler)

def main():
    """Main entry point for LLM Evaluator"""
    parser = argparse.ArgumentParser(
        description="Evaluate brand presence and sentiment in LLM responses"
    )
    parser.add_argument(
        'config',
        help='Path to markdown configuration file'
    )
    parser.add_argument(
        '--output-dir',
        default='./results',
        help='Directory to save results (default: ./results)'
    )
    parser.add_argument(
        '--no-cache',
        action='store_true',
        help='Disable response caching'
    )
    parser.add_argument(
        '--clear-cache',
        action='store_true',
        help='Clear cache before running'
    )
    parser.add_argument(
        '--log-level',
        default='INFO',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        help='Set logging level'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Validate configuration without running evaluation'
    )
    
    args = parser.parse_args()
    
    # Set up logging
    setup_logging(args.log_level)
    logger = logging.getLogger(__name__)
    
    try:
        # Load configuration
        logger.info(f"Loading configuration from {args.config}")
        config = ConfigurationManager(args.config)
        
        # Validate configuration
        issues = config.validate_configuration()
        if issues:
            logger.error("Configuration validation failed:")
            for issue in issues:
                logger.error(f"  - {issue}")
            sys.exit(1)
        
        logger.info(f"Loaded configuration for brand: {config.brand_info.name}")
        logger.info(f"Found {len(config.prompts)} prompts in {len(set(p.category for p in config.prompts))} categories")
        
        if args.dry_run:
            logger.info("Dry run complete - configuration is valid")
            sys.exit(0)
        
        # Create LLM interface
        logger.info("Initializing LLM interface...")
        llm_interface = LLMInterface.create_from_config(config)
        
        available_providers = llm_interface.get_available_providers()
        if not available_providers:
            logger.error("No LLM providers available. Please check your API keys.")
            sys.exit(1)
        
        logger.info(f"Available providers: {', '.join(available_providers)}")
        
        # Create prompt executor
        cache_dir = os.getenv('CACHE_DIR', './cache')
        cache_expire_hours = int(os.getenv('CACHE_EXPIRE_HOURS', '24'))
        executor = PromptExecutor(llm_interface, cache_dir, cache_expire_hours)
        
        if args.clear_cache:
            logger.info("Clearing cache...")
            executor.clear_cache()
        
        # Execute prompts
        logger.info(f"Executing {len(config.prompts)} prompts...")
        results = executor.execute_batch(
            config.prompts, 
            config.settings,
            show_progress=True
        )
        
        # Analyze responses
        logger.info("Analyzing responses...")
        analyzer = ResponseAnalyzer(config.brand_info, llm_interface)
        analyses = analyzer.batch_analyze(
            results, 
            use_llm_sentiment=(config.settings.sentiment_method == 'hybrid')
        )
        
        # Calculate metrics
        logger.info("Calculating metrics...")
        calculator = MetricsCalculator()
        metrics = calculator.calculate_metrics(results, analyses)
        insights = calculator.generate_insights(metrics)
        
        # Generate report
        logger.info("Generating reports...")
        generator = ReportGenerator(args.output_dir)
        dashboard_data = generator.generate_dashboard_data(
            config, results, analyses, metrics, insights
        )
        
        # Save report
        report_dir = generator.save_report(dashboard_data)
        logger.info(f"Reports saved to {report_dir}")
        
        # Print summary
        print("\n" + "=" * 60)
        print("EVALUATION SUMMARY")
        print("=" * 60)
        print(f"Brand: {config.brand_info.name}")
        print(f"Total Prompts: {metrics.total_prompts}")
        print(f"Brand Mentions: {metrics.total_brand_mentions}")
        print(f"Average Sentiment: {metrics.average_sentiment:.3f}")
        print(f"Mention Rate: {metrics.mention_rate:.2f} per prompt")
        print("\nKey Insights:")
        for i, insight in enumerate(insights[:3], 1):
            print(f"{i}. {insight}")
        print(f"\nFull results saved to: {report_dir}")
        print("=" * 60)
        
        # Cache statistics
        cache_stats = executor.get_cache_stats()
        if cache_stats:
            logger.info(f"Cache statistics: {cache_stats['size']} items, {cache_stats['volume']} bytes")
        
    except KeyboardInterrupt:
        logger.warning("Evaluation interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Evaluation failed: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()