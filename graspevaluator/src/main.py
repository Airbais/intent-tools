"""
Main module for GRASP evaluator
"""

import asyncio
import argparse
import logging
import sys
import os
from pathlib import Path
from datetime import datetime

# Add parent directory to path to import evaluator
parent_dir = Path(__file__).parent.parent
sys.path.append(str(parent_dir))
sys.path.append(str(parent_dir / "src"))
sys.path.append(str(parent_dir / "metrics"))
sys.path.append(str(parent_dir / "utils"))

from evaluator import GRASPEvaluator
from config_manager import ConfigManager


def setup_logging(config: ConfigManager):
    """Setup logging configuration"""
    log_config = config.config.get('logging', {})
    
    level = getattr(logging, log_config.get('level', 'INFO').upper())
    format_str = log_config.get('format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Configure root logger
    logging.basicConfig(level=level, format=format_str, force=True)
    
    # Optional file logging
    if log_config.get('log_to_file', False):
        log_file = log_config.get('log_file', 'grasp_evaluator.log')
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(logging.Formatter(format_str))
        logging.getLogger().addHandler(file_handler)


async def run_evaluation(url: str, config_path: str = None, output_dir: str = None) -> dict:
    """Run GRASP evaluation for a single URL"""
    logger = logging.getLogger(__name__)
    
    try:
        # Initialize evaluator
        evaluator = GRASPEvaluator(config_path)
        
        logger.info(f"Starting GRASP evaluation for: {url}")
        
        # Run evaluation
        results = await evaluator.evaluate_website(url)
        
        # Save results
        saved_path = evaluator.save_results(results, output_dir)
        
        logger.info(f"Evaluation completed. Results saved to: {saved_path}")
        
        return results
        
    except Exception as e:
        logger.error(f"Error during evaluation: {e}")
        raise


async def run_batch_evaluation(config_path: str = None, output_dir: str = None) -> list:
    """Run GRASP evaluation for all URLs in configuration"""
    logger = logging.getLogger(__name__)
    
    try:
        # Load configuration
        config = ConfigManager(config_path)
        target_urls = config.get_target_urls()
        
        if not target_urls:
            logger.warning("No target URLs found in configuration")
            return []
        
        logger.info(f"Running batch evaluation for {len(target_urls)} URLs")
        
        # Run evaluations
        all_results = []
        evaluator = GRASPEvaluator(config_path)
        
        for url in target_urls:
            try:
                logger.info(f"Evaluating: {url}")
                results = await evaluator.evaluate_website(url)
                
                # Save individual results
                saved_path = evaluator.save_results(results, output_dir)
                logger.info(f"Results for {url} saved to: {saved_path}")
                
                all_results.append(results)
                
            except Exception as e:
                logger.error(f"Error evaluating {url}: {e}")
                continue
        
        logger.info(f"Batch evaluation completed. {len(all_results)} URLs processed successfully.")
        
        return all_results
        
    except Exception as e:
        logger.error(f"Error during batch evaluation: {e}")
        raise


def print_results_summary(results: dict):
    """Print a summary of evaluation results"""
    print("\n" + "="*60)
    print("GRASP CONTENT QUALITY EVALUATION RESULTS")
    print("="*60)
    
    print(f"URL: {results['url']}")
    print(f"Timestamp: {results['timestamp']}")
    print(f"Overall Score: {results['overall_score']:.1f}/100 ({get_grade(results['overall_score'])})")
    
    print("\nMetric Breakdown:")
    print("-" * 40)
    
    metrics = results['breakdown']
    for metric, data in metrics.items():
        score = data['normalized']
        weight = data['weight'] * 100
        contribution = data['weighted_contribution']
        
        # Create progress bar
        bar_length = 20
        filled_length = int(bar_length * score / 100)
        bar = "█" * filled_length + "░" * (bar_length - filled_length)
        
        print(f"{metric.upper():>10}: {bar} {score:5.1f}/100 ({weight:2.0f}%) → {contribution:5.1f}")
    
    print("\nRecommendations:")
    print("-" * 40)
    for i, rec in enumerate(results['recommendations'], 1):
        print(f"{i}. {rec}")
    
    print("\n" + "="*60)


def get_grade(score: float) -> str:
    """Convert score to letter grade"""
    if score >= 90:
        return "A"
    elif score >= 80:
        return "B"
    elif score >= 70:
        return "C"
    elif score >= 60:
        return "D"
    else:
        return "F"


def start_dashboard(results_dir: str = None):
    """Start the dashboard to view results"""
    try:
        # Import dashboard runner
        dashboard_path = Path(__file__).parent.parent.parent / "dashboard" / "run_dashboard.py"
        
        if dashboard_path.exists():
            import subprocess
            
            cmd = [sys.executable, str(dashboard_path)]
            if results_dir:
                cmd.extend(["--tools-path", str(Path(results_dir).parent)])
            
            print("Starting dashboard...")
            subprocess.run(cmd)
        else:
            print("Dashboard not found. Please run the dashboard manually from the dashboard directory.")
            
    except Exception as e:
        print(f"Error starting dashboard: {e}")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="GRASP Content Quality Evaluator")
    
    parser.add_argument("--url", type=str, help="URL to evaluate (if not provided, runs batch evaluation from config)")
    parser.add_argument("--config", type=str, help="Path to configuration file")
    parser.add_argument("--output", type=str, help="Output directory for results")
    parser.add_argument("--dashboard", action="store_true", help="Start dashboard after evaluation")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")
    
    args = parser.parse_args()
    
    # Only show help if explicitly requested or if there's a usage error
    # Normal case: no URL = batch evaluation, URL provided = single evaluation
    
    try:
        # Initialize configuration and logging
        config = ConfigManager(args.config)
        
        if args.verbose:
            config.config.setdefault('logging', {})['level'] = 'DEBUG'
        
        setup_logging(config)
        
        logger = logging.getLogger(__name__)
        logger.info("Starting GRASP evaluator")
        
        # Run evaluation - automatically determine mode based on whether URL is provided
        if args.url:
            # Single URL evaluation
            results = asyncio.run(run_evaluation(args.url, args.config, args.output))
            print_results_summary(results)
        else:
            # Batch evaluation (default when no URL provided)
            results_list = asyncio.run(run_batch_evaluation(args.config, args.output))
            
            if results_list:
                print(f"\nBatch evaluation completed successfully!")
                print(f"Evaluated {len(results_list)} URLs")
                
                # Print summary for each URL
                for results in results_list:
                    print_results_summary(results)
            else:
                print("No URLs were successfully evaluated.")
        
        # Start dashboard if requested
        if args.dashboard:
            start_dashboard(args.output)
        
    except KeyboardInterrupt:
        print("\nEvaluation cancelled by user")
    except Exception as e:
        print(f"\nError: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()