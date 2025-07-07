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

def get_latest_results_directory(base_dir: str) -> str:
    """Get the most recent results directory"""
    if not os.path.exists(base_dir):
        return None
    
    dirs = [d for d in os.listdir(base_dir) if os.path.isdir(os.path.join(base_dir, d))]
    date_dirs = []
    
    for d in dirs:
        try:
            datetime.strptime(d, '%Y-%m-%d')
            date_dirs.append(d)
        except ValueError:
            continue
    
    if not date_dirs:
        return None
    
    latest = sorted(date_dirs, reverse=True)[0]
    return os.path.join(base_dir, latest)

def launch_dashboard(data_dir: str = None):
    """Launch the master dashboard"""
    import subprocess
    import time
    
    logger = logging.getLogger(__name__)
    
    # Get the dashboard directory (relative to llmevaluator)
    dashboard_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), '..', 'dashboard')
    dashboard_script = os.path.join(dashboard_dir, 'dashboard.py')
    
    if not os.path.exists(dashboard_script):
        logger.error(f"Dashboard script not found at {dashboard_script}")
        return
    
    logger.info("Launching master dashboard...")
    logger.info("Dashboard will be available at http://127.0.0.1:8050/")
    
    try:
        # Start the dashboard in a new process
        subprocess.run([sys.executable, dashboard_script], cwd=dashboard_dir)
    except KeyboardInterrupt:
        logger.info("Dashboard stopped by user")
    except Exception as e:
        logger.error(f"Failed to launch dashboard: {e}")

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
        nargs='?',
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
    parser.add_argument(
        '--dashboard',
        action='store_true',
        help='Launch interactive dashboard after evaluation'
    )
    parser.add_argument(
        '--dashboard-only',
        action='store_true',
        help='Launch dashboard with latest results'
    )
    parser.add_argument(
        '--dashboard-date',
        help='Launch dashboard with results from specific date (YYYY-MM-DD)'
    )
    parser.add_argument(
        '--list-results',
        action='store_true',
        help='List available result dates'
    )
    
    args = parser.parse_args()
    
    # Set up logging
    setup_logging(args.log_level)
    logger = logging.getLogger(__name__)
    
    try:
        # Handle listing results
        if args.list_results:
            if os.path.exists(args.output_dir):
                dirs = sorted([d for d in os.listdir(args.output_dir) if os.path.isdir(os.path.join(args.output_dir, d))], reverse=True)
                if dirs:
                    logger.info("Available result dates:")
                    for d in dirs:
                        logger.info(f"  - {d}")
                else:
                    logger.info("No results found")
            else:
                logger.info("Results directory does not exist")
            sys.exit(0)
        
        # Handle dashboard-only mode
        if args.dashboard_only or args.dashboard_date:
            if args.dashboard_date:
                results_dir = os.path.join(args.output_dir, args.dashboard_date)
            else:
                results_dir = get_latest_results_directory(args.output_dir)
            
            if not results_dir or not os.path.exists(results_dir):
                logger.error("No results found to display")
                sys.exit(1)
            
            dashboard_file = os.path.join(results_dir, 'dashboard-data.json')
            if not os.path.exists(dashboard_file):
                logger.error(f"Dashboard data not found at {dashboard_file}")
                sys.exit(1)
            
            logger.info(f"Launching dashboard with data from {results_dir}")
            launch_dashboard(results_dir)
            sys.exit(0)
        
        # Check if config is required
        if not args.config:
            parser.error("Configuration file is required unless using --dashboard-only, --dashboard-date, or --list-results")
        
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
        logger.info(f"Configured LLMs: {', '.join(llm.name for llm in config.llms)}")
        
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
        
        # Execute prompts against all configured LLMs
        logger.info(f"Executing {len(config.prompts)} prompts against {len(config.llms)} LLMs...")
        results = executor.execute_batch(
            config.prompts, 
            config.settings,
            show_progress=True
        )
        
        # Analyze responses for all LLMs
        logger.info("Analyzing responses...")
        analyzer = ResponseAnalyzer(config.brand_info, llm_interface)
        
        # Build analyses dictionary organized by prompt_id and llm_name
        analyses = {}
        for prompt_result in results:
            analyses[prompt_result.prompt_id] = {}
            for llm_name, llm_result in prompt_result.llm_results.items():
                # Create a list with single result for compatibility with batch_analyze
                single_result_list = [llm_result]
                analysis_dict = analyzer.batch_analyze(
                    single_result_list, 
                    use_llm_sentiment=(config.settings.sentiment_method == 'hybrid')
                )
                # Extract the single analysis
                if llm_result.prompt_id in analysis_dict:
                    analyses[prompt_result.prompt_id][llm_name] = analysis_dict[llm_result.prompt_id]
        
        # Calculate multi-LLM metrics
        logger.info("Calculating metrics...")
        calculator = MetricsCalculator()
        multi_metrics = calculator.calculate_multi_llm_metrics(results, analyses)
        
        # Generate insights
        insights = {
            'overall': calculator.generate_insights(multi_metrics.aggregate_metrics),
            'comparative': []
        }
        
        # Add comparative insights if multiple LLMs
        if multi_metrics.comparative_metrics.enabled:
            insights['comparative'].extend([
                f"LLMs agree on brand mentions {multi_metrics.comparative_metrics.consensus_score:.0%} of the time",
                f"Sentiment alignment between LLMs: {multi_metrics.comparative_metrics.sentiment_alignment:.0%}",
                f"Mention rate variance: {multi_metrics.comparative_metrics.mention_rate_variance:.3f}"
            ])
        
        # Generate multi-LLM report
        logger.info("Generating reports...")
        generator = ReportGenerator(args.output_dir)
        dashboard_data = generator.generate_multi_llm_dashboard_data(
            config, results, analyses, multi_metrics, insights
        )
        
        # Save report
        report_dir = generator.save_report(dashboard_data)
        logger.info(f"Reports saved to {report_dir}")
        
        # Print summary
        print("\n" + "=" * 80)
        print("MULTI-LLM EVALUATION SUMMARY")
        print("=" * 80)
        print(f"Brand: {config.brand_info.name}")
        print(f"Total Prompts: {multi_metrics.aggregate_metrics.total_prompts}")
        print(f"LLMs Evaluated: {len(config.llms)}")
        print("\nPer-LLM Results:")
        for llm_name, metrics in multi_metrics.llm_metrics.items():
            print(f"\n  {llm_name}:")
            print(f"    - Brand Mentions: {metrics.total_brand_mentions}")
            print(f"    - Mention Rate: {metrics.mention_rate:.2f}")
            print(f"    - Sentiment: {metrics.average_sentiment:.3f}")
        
        if multi_metrics.comparative_metrics.enabled:
            print("\nComparative Metrics:")
            print(f"  - Consensus Score: {multi_metrics.comparative_metrics.consensus_score:.0%}")
            print(f"  - Sentiment Alignment: {multi_metrics.comparative_metrics.sentiment_alignment:.0%}")
        
        print("\nKey Insights:")
        all_insights = insights.get('overall', [])[:2] + insights.get('comparative', [])[:1]
        for i, insight in enumerate(all_insights, 1):
            print(f"{i}. {insight}")
        print(f"\nFull results saved to: {report_dir}")
        print("=" * 80)
        
        # Cache statistics
        cache_stats = executor.get_cache_stats()
        if cache_stats:
            logger.info(f"Cache statistics: {cache_stats['size']} items, {cache_stats['volume']} bytes")
        
        # Launch dashboard if requested
        if args.dashboard:
            logger.info("Launching interactive dashboard...")
            launch_dashboard(report_dir)
        
    except KeyboardInterrupt:
        logger.warning("Evaluation interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Evaluation failed: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()