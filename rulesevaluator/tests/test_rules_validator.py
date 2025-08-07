"""Tests for rules validator"""

import pytest
import json
import tempfile
from pathlib import Path

from src.rules_validator import RulesValidator


class TestRulesValidator:
    """Test cases for RulesValidator"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.validator = RulesValidator()
    
    def test_valid_rules_file(self):
        """Test validation of a valid rules file"""
        valid_rules = {
            "prompts": [
                {
                    "prompt": "Test prompt",
                    "rules": [
                        {
                            "ruletype": "critical",
                            "ruledescription": "Must do something"
                        },
                        {
                            "ruletype": "important",
                            "ruledescription": "Should do something"
                        }
                    ]
                }
            ]
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(valid_rules, f)
            temp_path = f.name
        
        try:
            is_valid, data, errors = self.validator.validate_file(temp_path)
            assert is_valid is True
            assert len(errors) == 0
            assert len(data['prompts']) == 1
        finally:
            Path(temp_path).unlink()
    
    def test_missing_prompts_node(self):
        """Test validation fails when prompts node is missing"""
        invalid_rules = {"not_prompts": []}
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(invalid_rules, f)
            temp_path = f.name
        
        try:
            is_valid, data, errors = self.validator.validate_file(temp_path)
            assert is_valid is False
            assert any("Missing required 'prompts' node" in e for e in errors)
        finally:
            Path(temp_path).unlink()
    
    def test_empty_prompts_list(self):
        """Test validation fails when prompts list is empty"""
        invalid_rules = {"prompts": []}
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(invalid_rules, f)
            temp_path = f.name
        
        try:
            is_valid, data, errors = self.validator.validate_file(temp_path)
            assert is_valid is False
            assert any("At least one prompt is required" in e for e in errors)
        finally:
            Path(temp_path).unlink()
    
    def test_invalid_rule_type(self):
        """Test validation fails with invalid rule type"""
        invalid_rules = {
            "prompts": [
                {
                    "prompt": "Test prompt",
                    "rules": [
                        {
                            "ruletype": "invalid_type",
                            "ruledescription": "Test rule"
                        }
                    ]
                }
            ]
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(invalid_rules, f)
            temp_path = f.name
        
        try:
            is_valid, data, errors = self.validator.validate_file(temp_path)
            assert is_valid is False
            assert any("invalid ruletype" in e for e in errors)
        finally:
            Path(temp_path).unlink()
    
    def test_missing_rule_fields(self):
        """Test validation fails when rule fields are missing"""
        invalid_rules = {
            "prompts": [
                {
                    "prompt": "Test prompt",
                    "rules": [
                        {
                            "ruletype": "critical"
                            # Missing ruledescription
                        }
                    ]
                }
            ]
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(invalid_rules, f)
            temp_path = f.name
        
        try:
            is_valid, data, errors = self.validator.validate_file(temp_path)
            assert is_valid is False
            assert any("missing 'ruledescription'" in e for e in errors)
        finally:
            Path(temp_path).unlink()
    
    def test_case_normalization(self):
        """Test rule type case normalization"""
        rules = {
            "prompts": [
                {
                    "prompt": "Test prompt",
                    "rules": [
                        {
                            "ruletype": "CRITICAL",
                            "ruledescription": "Test rule"
                        },
                        {
                            "ruletype": "Important",
                            "ruledescription": "Test rule"
                        }
                    ]
                }
            ]
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(rules, f)
            temp_path = f.name
        
        try:
            validator = RulesValidator(normalize_case=True)
            is_valid, data, errors = validator.validate_file(temp_path)
            assert is_valid is True
            assert data['prompts'][0]['rules'][0]['ruletype'] == 'critical'
            assert data['prompts'][0]['rules'][0]['original_ruletype'] == 'CRITICAL'
            assert data['prompts'][0]['rules'][1]['ruletype'] == 'important'
        finally:
            Path(temp_path).unlink()
    
    def test_file_not_found(self):
        """Test validation fails when file doesn't exist"""
        is_valid, data, errors = self.validator.validate_file("nonexistent.json")
        assert is_valid is False
        assert any("Rules file not found" in e for e in errors)
    
    def test_invalid_json(self):
        """Test validation fails with invalid JSON"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write("{ invalid json }")
            temp_path = f.name
        
        try:
            is_valid, data, errors = self.validator.validate_file(temp_path)
            assert is_valid is False
            assert any("Invalid JSON format" in e for e in errors)
        finally:
            Path(temp_path).unlink()