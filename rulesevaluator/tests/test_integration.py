"""Integration tests for complete Rules Evaluator workflow"""

import pytest
import tempfile
import os
from pathlib import Path
import json

from src.config_manager import ConfigManager
from src.evaluator import RulesEvaluator


class TestIntegrationWorkflow:
    """Test complete evaluation workflow"""
    
    def setup_method(self):
        """Set up test fixtures"""
        # Skip if required API keys not available
        if not os.getenv('OPENAI_API_KEY'):
            pytest.skip("OpenAI API key required for integration tests")
        
        # Create temporary directories
        self.temp_dir = Path(tempfile.mkdtemp())
        self.content_dir = self.temp_dir / "content"
        self.content_dir.mkdir()
        self.rules_dir = self.temp_dir / "rules"
        self.rules_dir.mkdir()
        self.results_dir = self.temp_dir / "results"
        
        # Create test content
        (self.content_dir / "policy.txt").write_text("""
Our Return Policy

We offer a 30-day return policy for all products. Items must be returned in original condition 
with all tags attached. Refunds are processed within 5-7 business days to your original payment method.

For questions about returns, contact support@example.com or call 1-800-EXAMPLE.

Premium Subscription Benefits

Our premium subscription includes unlimited access to all features, priority customer support 
available 24/7, advanced analytics dashboard, and early access to new features. 

Premium costs $19.99 per month, compared to our free tier which limits usage to 10 items monthly.
We offer a 14-day free trial for new subscribers.
        """)
        
        # Create test rules
        test_rules = {
            "prompts": [
                {
                    "prompt": "Explain our return policy",
                    "rules": [
                        {
                            "ruletype": "critical", 
                            "ruledescription": "Must mention the 30-day return window"
                        },
                        {
                            "ruletype": "important",
                            "ruledescription": "Should explain the refund process and timeline"
                        }
                    ]
                }
            ]
        }
        
        rules_file = self.rules_dir / "test_rules.json"
        with open(rules_file, 'w') as f:
            json.dump(test_rules, f, indent=2)
        
        self.rules_file = str(rules_file)
        
        # Create test configuration
        self.config_data = {
            'content': {
                'type': 'local',
                'local': {
                    'path': str(self.content_dir),
                    'recursive': False,
                    'file_patterns': ['*.txt', '*.md']
                }
            },
            'rag': {
                'persist_directory': str(self.temp_dir / 'chromadb'),
                'collection_name': 'test_collection',
                'embedding_model': 'text-embedding-3-small',
                'chunk_size': 500,
                'chunk_overlap': 50,
                'update_strategy': 'overwrite'
            },
            'ai_providers': {
                'response_provider': [{
                    'name': 'openai',
                    'api_key': os.getenv('OPENAI_API_KEY'),
                    'model': 'gpt-3.5-turbo',
                    'temperature': 0.7,
                    'max_tokens': 1000
                }],
                'evaluation_provider': [{
                    'name': 'openai',
                    'api_key': os.getenv('OPENAI_API_KEY'),
                    'model': 'gpt-3.5-turbo',
                    'temperature': 0.3,
                    'max_tokens': 500
                }]
            },
            'rules': {
                'file_path': self.rules_file,
                'strict_validation': True,
                'normalize_case': True
            },
            'scoring': {
                'passing_score': 60,
                'weights': {
                    'important': 50,
                    'expected': 35,
                    'desirable': 15
                }
            },
            'evaluation_prompt': """
You are an expert evaluator. Analyze the AI response against the given rules.

For each rule, determine if satisfied and assign a score:
- Fully satisfied: 100%
- Partially satisfied: 50%
- Not satisfied: 0%

Return JSON format:
{
  "rules_evaluation": [
    {
      "rule": "rule text",
      "type": "rule type", 
      "satisfied": true/false,
      "score_percentage": 0-100,
      "reasoning": "brief explanation"
    }
  ],
  "total_score": 0-100,
  "passed": true/false,
  "summary": "brief summary"
}
            """,
            'output': {
                'results_dir': str(self.results_dir),
                'log_responses': True,
                'generate_html_report': True,
                'generate_markdown_report': True,
                'generate_dashboard_json': True
            },
            'general': {
                'log_level': 'INFO',
                'enable_cache': False
            }
        }
        
        # Save config to file
        config_file = self.temp_dir / "test_config.yaml"
        import yaml
        with open(config_file, 'w') as f:
            yaml.dump(self.config_data, f)
        
        # Create config manager with test data
        self.config = ConfigManager()
        self.config.config = self.config_data
    
    def teardown_method(self):
        """Clean up test fixtures"""
        import shutil
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
    
    @pytest.mark.integration
    def test_complete_evaluation_workflow(self):
        """Test complete evaluation workflow from start to finish"""
        # Create evaluator
        evaluator = RulesEvaluator(self.config)
        
        # Run evaluation
        results = evaluator.run_evaluation(self.rules_file)
        
        # Verify results structure
        assert 'evaluation_id' in results
        assert 'timestamp' in results
        assert 'duration_seconds' in results
        assert 'prompt_evaluations' in results
        assert 'overall_results' in results
        assert 'database_stats' in results
        assert 'generated_files' in results
        
        # Verify overall results
        overall = results['overall_results']
        assert overall['total_prompts'] == 1
        assert 'overall_pass_rate' in overall
        assert 'average_score' in overall
        
        # Verify prompt evaluation
        prompt_eval = results['prompt_evaluations'][0]
        assert prompt_eval['prompt'] == "Explain our return policy"
        assert 'ai_response' in prompt_eval
        assert 'score' in prompt_eval
        assert 'passed' in prompt_eval
        assert 'rules_evaluation' in prompt_eval
        
        # Verify rules evaluation
        rules_eval = prompt_eval['rules_evaluation']
        assert len(rules_eval) == 2  # Should have 2 rules
        
        # Check that files were generated
        generated_files = results['generated_files']
        assert 'json' in generated_files
        assert 'dashboard' in generated_files
        
        # Verify files exist
        for file_type, file_path in generated_files.items():
            assert Path(file_path).exists(), f"Generated file {file_type} should exist at {file_path}"
        
        # Verify dashboard data structure
        dashboard_file = Path(generated_files['dashboard'])
        with open(dashboard_file) as f:
            dashboard_data = json.load(f)
        
        assert dashboard_data['tool'] == 'rulesevaluator'
        assert 'summary' in dashboard_data
        assert 'metrics' in dashboard_data
        assert 'recommendations' in dashboard_data
        assert 'data' in dashboard_data
        
        # Verify database stats
        db_stats = results['database_stats']
        assert db_stats['total_documents'] > 0
        assert db_stats['total_chunks'] > 0
        assert 'sources' in db_stats
    
    @pytest.mark.integration  
    def test_critical_rule_failure(self):
        """Test behavior when critical rule fails"""
        # Create rules with a critical rule that should fail
        failing_rules = {
            "prompts": [
                {
                    "prompt": "What are our shipping rates?",
                    "rules": [
                        {
                            "ruletype": "critical",
                            "ruledescription": "Must mention free shipping"
                        }
                    ]
                }
            ]
        }
        
        failing_rules_file = self.rules_dir / "failing_rules.json"
        with open(failing_rules_file, 'w') as f:
            json.dump(failing_rules, f, indent=2)
        
        # Run evaluation
        evaluator = RulesEvaluator(self.config)
        results = evaluator.run_evaluation(str(failing_rules_file))
        
        # Should likely fail since content doesn't mention shipping
        prompt_eval = results['prompt_evaluations'][0]
        
        # Check if critical rule was properly evaluated
        critical_rules = [r for r in prompt_eval['rules_evaluation'] if r['type'] == 'critical']
        assert len(critical_rules) == 1
        
        # If critical rule failed, prompt should have score 0
        if not critical_rules[0]['satisfied']:
            assert prompt_eval['score'] == 0
            assert prompt_eval['critical_failed'] is True