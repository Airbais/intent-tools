#!/usr/bin/env python3
"""
Intent Extraction Tuning Tool
Run A/B tests on different configurations to optimize intent detection.
"""

import json
import yaml
from src.user_intent_extractor import UserIntentExtractor
from src.intent_tuning_analyzer import IntentTuningAnalyzer

def run_tuning_experiment(processed_contents, experiment_configs):
    """Run multiple configurations and compare results."""
    results = {}
    
    for config_name, config in experiment_configs.items():
        print(f"Running experiment: {config_name}")
        extractor = UserIntentExtractor(config=config)
        intent_data = extractor.extract_intents(processed_contents)
        
        results[config_name] = {
            'intent_count': len(intent_data['discovered_intents']),
            'avg_confidence': sum(i['confidence'] for i in intent_data['discovered_intents']) / len(intent_data['discovered_intents']),
            'intent_types': [i['primary_intent'] for i in intent_data['discovered_intents']],
            'data': intent_data
        }
    
    return results

def compare_configurations():
    """Compare different tuning configurations."""
    
    # Define experiment configurations
    experiments = {
        'conservative': {
            'min_confidence_threshold': 0.3,
            'pain_point_sensitivity': 0.2,
            'action_verb_weight': 0.3
        },
        'aggressive': {
            'min_confidence_threshold': 0.1,
            'pain_point_sensitivity': 0.5,
            'action_verb_weight': 0.6
        },
        'balanced': {
            'min_confidence_threshold': 0.2,
            'pain_point_sensitivity': 0.3,
            'action_verb_weight': 0.4
        },
        'precision_focused': {
            'min_confidence_threshold': 0.4,
            'pain_point_sensitivity': 0.1,
            'action_verb_weight': 0.2
        }
    }
    
    print("🧪 Intent Extraction A/B Testing")
    print("=" * 50)
    
    # You'd load your processed_contents here
    # For now, this is a template
    
    return experiments

if __name__ == "__main__":
    configs = compare_configurations()
    print("\nTo run experiments:")
    print("1. Load your processed content")
    print("2. Call run_tuning_experiment(processed_contents, configs)")
    print("3. Analyze results with IntentTuningAnalyzer")