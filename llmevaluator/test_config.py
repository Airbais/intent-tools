#!/usr/bin/env python3
"""
Test configuration loading and validation
"""

import sys
from src.config import ConfigurationManager

def test_config():
    """Test loading the example configuration"""
    try:
        # Load example config
        config = ConfigurationManager('example_config.md')
        
        print("✓ Configuration loaded successfully")
        print(f"\nBrand Information:")
        print(f"  Name: {config.brand_info.name}")
        print(f"  Website: {config.brand_info.website}")
        print(f"  Aliases: {config.brand_info.aliases}")
        print(f"  Competitors: {config.brand_info.competitors}")
        
        print(f"\nEvaluation Settings:")
        print(f"  Provider: {config.settings.llm_provider}")
        print(f"  Model: {config.settings.model}")
        print(f"  Temperature: {config.settings.temperature}")
        
        print(f"\nPrompts: {len(config.prompts)} total")
        categories = {}
        for prompt in config.prompts:
            if prompt.category not in categories:
                categories[prompt.category] = 0
            categories[prompt.category] += 1
        
        for category, count in categories.items():
            print(f"  {category}: {count} prompts")
        
        # Validate
        issues = config.validate_configuration()
        if issues:
            print("\n⚠ Validation Issues:")
            for issue in issues:
                print(f"  - {issue}")
        else:
            print("\n✓ Configuration validation passed")
        
        return True
        
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

if __name__ == "__main__":
    success = test_config()
    sys.exit(0 if success else 1)