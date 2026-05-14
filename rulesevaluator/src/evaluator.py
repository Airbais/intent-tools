"""Main evaluation orchestrator"""

import logging
from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime
import json
from pathlib import Path

from .config_manager import ConfigManager
from .rules_validator import RulesValidator
from .content_ingestor import ContentIngestor
from .rag_database import RAGDatabase
from .ai_providers import AIProviderFactory
from .output_generator import OutputGenerator

logger = logging.getLogger(__name__)


class RulesEvaluator:
    """Main orchestrator for rules evaluation"""
    
    def __init__(self, config: ConfigManager):
        """Initialize evaluator
        
        Args:
            config: Configuration manager instance
        """
        self.config = config
        self.rules_validator = RulesValidator(
            strict_validation=config.get('rules.strict_validation', True),
            normalize_case=config.get('rules.normalize_case', True)
        )
        
        # Initialize components
        self._init_components()
    
    def _init_components(self):
        """Initialize all components"""
        # Content ingestor
        content_config = self.config.get_content_config()
        self.content_ingestor = ContentIngestor(content_config)
        
        # RAG database
        rag_config = self.config.get('rag', {})
        # Add OpenAI API key if available
        response_provider = self.config.get_ai_provider('response')
        if response_provider.get('name') == 'openai':
            rag_config['openai_api_key'] = response_provider.get('api_key')
        
        self.rag_db = RAGDatabase(rag_config)
        
        # AI providers
        response_config = self.config.get_ai_provider('response')
        self.response_provider = AIProviderFactory.create(response_config)
        
        evaluation_config = self.config.get_ai_provider('evaluation')
        self.evaluation_provider = AIProviderFactory.create(evaluation_config)
        
        # Evaluation prompt
        self.evaluation_prompt = self.config.get('evaluation_prompt', '')
        
        # Output generator
        output_config = self.config.get('output', {})
        self.output_generator = OutputGenerator(output_config)
    
    def run_evaluation(self, rules_file: str) -> Dict[str, Any]:
        """Run complete evaluation process
        
        Args:
            rules_file: Path to rules JSON file
            
        Returns:
            Evaluation results dictionary
        """
        start_time = datetime.now()
        logger.info("Starting rules evaluation process")
        
        # Step 1: Validate rules
        logger.info("Step 1: Validating rules file")
        is_valid, rules_data, errors = self.rules_validator.validate_file(rules_file)
        
        if not is_valid:
            raise ValueError(f"Rules validation failed: {errors}")
        
        # Step 2: Ingest content
        logger.info("Step 2: Ingesting content")
        content_items = self.content_ingestor.ingest()
        
        if not content_items:
            raise ValueError("No content ingested")
        
        logger.info(f"Ingested {len(content_items)} content items")
        
        # Step 3: Build RAG database
        logger.info("Step 3: Building RAG database")
        chunks_added = self.rag_db.add_content(content_items, reset=True)
        logger.info(f"Added {chunks_added} chunks to RAG database")
        
        # Get database statistics
        db_stats = self.rag_db.get_statistics()
        
        # Step 4: Evaluate each prompt
        logger.info("Step 4: Evaluating prompts against rules")
        evaluation_results = []
        
        for i, prompt_data in enumerate(rules_data['prompts']):
            logger.info(f"Evaluating prompt {i+1}/{len(rules_data['prompts'])}")
            
            prompt_result = self._evaluate_prompt(prompt_data)
            evaluation_results.append(prompt_result)
        
        # Step 5: Calculate overall scores
        logger.info("Step 5: Calculating overall scores")
        overall_results = self._calculate_overall_scores(evaluation_results)
        
        # Compile final results
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        results = {
            'evaluation_id': f"eval_{start_time.strftime('%Y%m%d_%H%M%S')}",
            'timestamp': start_time.isoformat(),
            'duration_seconds': duration,
            'rules_file': rules_file,
            'content_source': self.config.get('content.type'),
            'database_stats': db_stats,
            'prompt_evaluations': evaluation_results,
            'overall_results': overall_results,
            'config': {
                'passing_score': self.config.get('scoring.passing_score', 60),
                'weights': self.config.get('scoring.weights'),
                'ai_providers': {
                    'response': self.config.get_ai_provider('response').get('name'),
                    'evaluation': self.config.get_ai_provider('evaluation').get('name')
                }
            }
        }
        
        # Generate all output files
        timestamp_str = start_time.strftime('%Y-%m-%d')
        generated_files = self.output_generator.generate_all_outputs(results, timestamp_str)
        results['generated_files'] = {k: str(v) for k, v in generated_files.items()}
        
        return results
    
    def _evaluate_prompt(self, prompt_data: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate a single prompt
        
        Args:
            prompt_data: Prompt and rules from JSON
            
        Returns:
            Evaluation results for this prompt
        """
        prompt_text = prompt_data['prompt']
        rules = prompt_data['rules']
        
        # Get relevant context from RAG
        context = self.rag_db.get_context_for_prompt(prompt_text)
        
        # Generate AI response
        logger.debug(f"Generating response for: {prompt_text[:50]}...")
        ai_response = self.response_provider.generate_response(prompt_text, context)
        
        # Evaluate response against rules
        logger.debug("Evaluating response against rules")
        evaluation = self.evaluation_provider.evaluate_response(
            ai_response, rules, self.evaluation_prompt
        )
        
        # Calculate prompt score
        prompt_score = self._calculate_prompt_score(evaluation, rules)
        
        # Compile prompt results
        prompt_result = {
            'prompt': prompt_text,
            'ai_response': ai_response,
            'context_used': context[:500] + "..." if len(context) > 500 else context,
            'rules_evaluation': evaluation.get('rules_evaluation', []),
            'score': prompt_score['score'],
            'passed': prompt_score['passed'],
            'critical_failed': prompt_score['critical_failed'],
            'summary': evaluation.get('summary', ''),
            'rules_summary': {
                'total_rules': len(rules),
                'rules_passed': prompt_score['rules_passed'],
                'rules_failed': prompt_score['rules_failed'],
                'by_type': prompt_score['by_type']
            }
        }
        
        return prompt_result
    
    def _calculate_prompt_score(self, evaluation: Dict[str, Any], 
                               original_rules: List[Dict]) -> Dict[str, Any]:
        """Calculate score for a single prompt
        
        Args:
            evaluation: AI evaluation results
            original_rules: Original rules for reference
            
        Returns:
            Score calculation results
        """
        rules_eval = evaluation.get('rules_evaluation', [])
        weights = self.config.get('scoring.weights')
        passing_score = self.config.get('scoring.passing_score', 60)
        
        # Check for critical rule failure
        critical_failed = False
        for rule_eval in rules_eval:
            if rule_eval.get('type', '').lower() == 'critical':
                if not rule_eval.get('satisfied', False):
                    critical_failed = True
                    break
        
        # If critical failed, score is 0
        if critical_failed:
            return {
                'score': 0,
                'passed': False,
                'critical_failed': True,
                'rules_passed': 0,
                'rules_failed': len(original_rules),
                'by_type': {
                    'critical': {'passed': 0, 'total': 0},
                    'important': {'passed': 0, 'total': 0},
                    'expected': {'passed': 0, 'total': 0},
                    'desirable': {'passed': 0, 'total': 0}
                }
            }
        
        # Calculate weighted score
        type_scores = {
            'important': {'score': 0, 'max': 0, 'passed': 0, 'total': 0},
            'expected': {'score': 0, 'max': 0, 'passed': 0, 'total': 0},
            'desirable': {'score': 0, 'max': 0, 'passed': 0, 'total': 0}
        }
        
        rules_passed = 0
        rules_failed = 0
        
        # First pass: count rule types present and count of each type
        rule_types_present = set()
        rule_type_counts = {}
        for rule_eval in rules_eval:
            rule_type = rule_eval.get('type', '').lower()
            if rule_type != 'critical' and rule_type in weights:
                rule_types_present.add(rule_type)
                rule_type_counts[rule_type] = rule_type_counts.get(rule_type, 0) + 1
        
        # Calculate adjusted weights so they sum to 100
        total_weight = sum(weights.get(rt, 0) for rt in rule_types_present)
        adjusted_weights = {}
        per_rule_weights = {}
        if total_weight > 0:
            for rt in rule_types_present:
                adjusted_weights[rt] = (weights.get(rt, 0) / total_weight) * 100
                # Divide the adjusted weight by the number of rules of this type
                per_rule_weights[rt] = adjusted_weights[rt] / rule_type_counts[rt]
        
        # Process each rule evaluation
        for rule_eval in rules_eval:
            rule_type = rule_eval.get('type', '').lower()
            score_percentage = rule_eval.get('score_percentage', 0)
            satisfied = rule_eval.get('satisfied', False)
            
            if rule_type == 'critical':
                # Critical rules already handled above
                if satisfied:
                    rules_passed += 1
                else:
                    rules_failed += 1
                continue
            
            if rule_type in type_scores:
                # Use per-rule weight that distributes the type weight evenly across all rules of this type
                weight = per_rule_weights.get(rule_type, 0)
                type_scores[rule_type]['max'] += weight
                type_scores[rule_type]['score'] += (score_percentage / 100) * weight
                type_scores[rule_type]['total'] += 1
                
                if satisfied:
                    type_scores[rule_type]['passed'] += 1
                    rules_passed += 1
                else:
                    rules_failed += 1
        
        # Calculate total score (now guaranteed to be max 100)
        total_score = sum(ts['score'] for ts in type_scores.values())
        total_score = min(100, total_score)  # Safety cap at 100
        
        # Build by_type summary
        by_type = {
            'critical': {
                'passed': len([r for r in rules_eval if r.get('type', '').lower() == 'critical' and r.get('satisfied', False)]),
                'total': len([r for r in rules_eval if r.get('type', '').lower() == 'critical'])
            }
        }
        
        for rule_type, scores in type_scores.items():
            by_type[rule_type] = {
                'passed': scores['passed'],
                'total': scores['total']
            }
        
        return {
            'score': round(total_score, 2),
            'passed': total_score >= passing_score,
            'critical_failed': False,
            'rules_passed': rules_passed,
            'rules_failed': rules_failed,
            'by_type': by_type
        }
    
    def _calculate_overall_scores(self, evaluation_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate overall scores across all prompts
        
        Args:
            evaluation_results: List of prompt evaluation results
            
        Returns:
            Overall scores and statistics
        """
        total_prompts = len(evaluation_results)
        prompts_passed = sum(1 for r in evaluation_results if r['passed'])
        
        # Calculate average score
        total_score = sum(r['score'] for r in evaluation_results)
        average_score = total_score / total_prompts if total_prompts > 0 else 0
        
        # Aggregate rules by type
        total_by_type = {
            'critical': {'passed': 0, 'total': 0},
            'important': {'passed': 0, 'total': 0},
            'expected': {'passed': 0, 'total': 0},
            'desirable': {'passed': 0, 'total': 0}
        }
        
        for result in evaluation_results:
            for rule_type, counts in result['rules_summary']['by_type'].items():
                total_by_type[rule_type]['passed'] += counts['passed']
                total_by_type[rule_type]['total'] += counts['total']
        
        # Calculate pass rates by type
        pass_rates_by_type = {}
        for rule_type, counts in total_by_type.items():
            if counts['total'] > 0:
                pass_rate = (counts['passed'] / counts['total']) * 100
                pass_rates_by_type[rule_type] = round(pass_rate, 2)
            else:
                pass_rates_by_type[rule_type] = 0
        
        return {
            'total_prompts': total_prompts,
            'prompts_passed': prompts_passed,
            'prompts_failed': total_prompts - prompts_passed,
            'overall_pass_rate': round((prompts_passed / total_prompts * 100) if total_prompts > 0 else 0, 2),
            'average_score': round(average_score, 2),
            'total_rules_by_type': total_by_type,
            'pass_rates_by_type': pass_rates_by_type,
            'critical_failures': sum(1 for r in evaluation_results if r['critical_failed'])
        }