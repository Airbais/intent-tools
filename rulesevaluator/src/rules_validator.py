"""JSON rules file validation"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Tuple

logger = logging.getLogger(__name__)


class RulesValidator:
    """Validates JSON rules file structure and content"""
    
    VALID_RULE_TYPES = {'critical', 'important', 'expected', 'desirable'}
    
    def __init__(self, strict_validation: bool = True, normalize_case: bool = True):
        """Initialize rules validator
        
        Args:
            strict_validation: Whether to enforce strict validation rules
            normalize_case: Whether to normalize rule types to lowercase
        """
        self.strict_validation = strict_validation
        self.normalize_case = normalize_case
        self.validation_errors: List[str] = []
    
    def validate_file(self, file_path: str) -> Tuple[bool, Dict[str, Any], List[str]]:
        """Validate rules JSON file
        
        Args:
            file_path: Path to rules JSON file
            
        Returns:
            Tuple of (is_valid, normalized_rules, error_messages)
        """
        self.validation_errors = []
        
        # Check file exists
        if not Path(file_path).exists():
            self.validation_errors.append(f"Rules file not found: {file_path}")
            return False, {}, self.validation_errors
        
        # Load JSON
        try:
            with open(file_path, 'r') as f:
                rules_data = json.load(f)
        except json.JSONDecodeError as e:
            self.validation_errors.append(f"Invalid JSON format: {e}")
            return False, {}, self.validation_errors
        except Exception as e:
            self.validation_errors.append(f"Error reading file: {e}")
            return False, {}, self.validation_errors
        
        # Validate structure
        is_valid = self._validate_structure(rules_data)
        
        # Normalize if requested
        if is_valid and self.normalize_case:
            rules_data = self._normalize_rules(rules_data)
        
        return is_valid, rules_data, self.validation_errors
    
    def _validate_structure(self, data: Dict[str, Any]) -> bool:
        """Validate JSON structure according to requirements
        
        Returns:
            True if valid, False otherwise
        """
        # Check for prompts node
        if 'prompts' not in data:
            self.validation_errors.append("Missing required 'prompts' node")
            return False
        
        prompts = data['prompts']
        
        # Check prompts is a list
        if not isinstance(prompts, list):
            self.validation_errors.append("'prompts' must be a list")
            return False
        
        # Check minimum one prompt
        if len(prompts) == 0:
            self.validation_errors.append("At least one prompt is required")
            return False
        
        # Validate each prompt
        for i, prompt in enumerate(prompts):
            self._validate_prompt(prompt, i)
        
        return len(self.validation_errors) == 0
    
    def _validate_prompt(self, prompt: Dict[str, Any], index: int) -> None:
        """Validate individual prompt structure
        
        Args:
            prompt: Prompt dictionary
            index: Prompt index for error messages
        """
        # Check prompt is a dict
        if not isinstance(prompt, dict):
            self.validation_errors.append(f"Prompt {index} must be an object")
            return
        
        # Check for prompt text
        if 'prompt' not in prompt:
            self.validation_errors.append(f"Prompt {index} missing 'prompt' field")
        elif not isinstance(prompt['prompt'], str) or not prompt['prompt'].strip():
            self.validation_errors.append(f"Prompt {index} 'prompt' must be a non-empty string")
        
        # Check for rules array
        if 'rules' not in prompt:
            self.validation_errors.append(f"Prompt {index} missing 'rules' array")
            return
        
        rules = prompt['rules']
        
        # Check rules is a list
        if not isinstance(rules, list):
            self.validation_errors.append(f"Prompt {index} 'rules' must be a list")
            return
        
        # Check minimum one rule
        if len(rules) == 0:
            self.validation_errors.append(f"Prompt {index} must have at least one rule")
            return
        
        # Track rule types for this prompt
        rule_types_seen = set()
        has_critical = False
        
        # Validate each rule
        for j, rule in enumerate(rules):
            self._validate_rule(rule, index, j, rule_types_seen)
            if rule.get('ruletype', '').lower() == 'critical':
                has_critical = True
        
        # Additional validation if strict mode
        if self.strict_validation:
            # Warn if no critical rule
            if not has_critical:
                logger.warning(f"Prompt {index} has no critical rule")
    
    def _validate_rule(self, rule: Dict[str, Any], prompt_index: int, 
                      rule_index: int, rule_types_seen: set) -> None:
        """Validate individual rule
        
        Args:
            rule: Rule dictionary
            prompt_index: Parent prompt index
            rule_index: Rule index
            rule_types_seen: Set of rule types already seen
        """
        # Check rule is a dict
        if not isinstance(rule, dict):
            self.validation_errors.append(
                f"Prompt {prompt_index} rule {rule_index} must be an object"
            )
            return
        
        # Check ruletype
        if 'ruletype' not in rule:
            self.validation_errors.append(
                f"Prompt {prompt_index} rule {rule_index} missing 'ruletype'"
            )
        else:
            ruletype = rule['ruletype']
            if not isinstance(ruletype, str):
                self.validation_errors.append(
                    f"Prompt {prompt_index} rule {rule_index} 'ruletype' must be a string"
                )
            else:
                # Validate rule type value
                normalized_type = ruletype.lower()
                if normalized_type not in self.VALID_RULE_TYPES:
                    self.validation_errors.append(
                        f"Prompt {prompt_index} rule {rule_index} invalid ruletype '{ruletype}'. "
                        f"Must be one of: {', '.join(self.VALID_RULE_TYPES)}"
                    )
                
                # Track for duplicate detection
                rule_types_seen.add(normalized_type)
        
        # Check ruledescription
        if 'ruledescription' not in rule:
            self.validation_errors.append(
                f"Prompt {prompt_index} rule {rule_index} missing 'ruledescription'"
            )
        elif not isinstance(rule['ruledescription'], str) or not rule['ruledescription'].strip():
            self.validation_errors.append(
                f"Prompt {prompt_index} rule {rule_index} 'ruledescription' must be a non-empty string"
            )
    
    def _normalize_rules(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize rule types to lowercase while preserving original
        
        Args:
            data: Rules data
            
        Returns:
            Normalized rules data
        """
        normalized = data.copy()
        
        for prompt in normalized['prompts']:
            for rule in prompt['rules']:
                if 'ruletype' in rule:
                    # Store original for reporting
                    rule['original_ruletype'] = rule['ruletype']
                    # Normalize to lowercase
                    rule['ruletype'] = rule['ruletype'].lower()
        
        return normalized