"""
Polished metric evaluator - Grammar and language quality assessment
"""

import re
import asyncio
from typing import Dict, List, Optional
import openai
import os


class PolishedEvaluator:
    """Evaluate grammar and language quality"""
    
    def __init__(self, config):
        self.config = config
        self.polished_config = config.get_polished_config()
        
        # Initialize OpenAI client if API key is available
        self.use_llm = self.polished_config.get('use_llm', True)
        if self.use_llm:
            try:
                api_key = config.get_openai_api_key()
                self.openai_client = openai.OpenAI(api_key=api_key)
            except:
                self.use_llm = False
                self.openai_client = None
    
    async def evaluate(self, content: str) -> str:
        """
        Evaluate content grammar and language quality
        
        Args:
            content: Text content to evaluate
            
        Returns:
            str: Quality rating ('Excellent', 'Good', 'Fair', 'Poor', 'Very Poor')
        """
        if not content or not content.strip():
            return "Very Poor"
        
        try:
            if self.use_llm and self.openai_client:
                # Use LLM for comprehensive grammar checking
                error_rate = await self._llm_grammar_check(content)
            else:
                # Use rule-based grammar checking
                error_rate = self._rule_based_grammar_check(content)
            
            # Convert error rate to rating
            return self._error_rate_to_rating(error_rate)
            
        except Exception:
            # Fallback to basic checks
            error_rate = self._basic_grammar_check(content)
            return self._error_rate_to_rating(error_rate)
    
    async def _llm_grammar_check(self, content: str) -> float:
        """Use LLM to check grammar and language quality"""
        try:
            # Split content into chunks if too long
            chunks = self._split_content(content, max_words=800)
            total_errors = 0
            total_words = 0
            
            for chunk in chunks:
                word_count = len(chunk.split())
                if word_count == 0:
                    continue
                
                # Create prompt for grammar checking
                prompt = f"""Please analyze the following text for grammar, spelling, punctuation, and style issues. 
                
Return only a JSON object with this exact format:
{{
    "error_count": <number>,
    "word_count": <number>,
    "error_types": ["type1", "type2", ...],
    "severity": "low|medium|high"
}}

Text to analyze:
{chunk}"""
                
                try:
                    response = await asyncio.to_thread(
                        self.openai_client.chat.completions.create,
                        model="gpt-3.5-turbo",
                        messages=[
                            {"role": "system", "content": "You are a professional editor analyzing text quality. Respond only with valid JSON."},
                            {"role": "user", "content": prompt}
                        ],
                        max_tokens=200,
                        temperature=0.1
                    )
                    
                    import json
                    result = json.loads(response.choices[0].message.content)
                    
                    chunk_errors = result.get('error_count', 0)
                    chunk_words = result.get('word_count', word_count)
                    
                    total_errors += chunk_errors
                    total_words += chunk_words
                    
                except Exception:
                    # Fallback for this chunk
                    fallback_rate = self._basic_grammar_check(chunk)
                    total_errors += fallback_rate * word_count
                    total_words += word_count
            
            if total_words == 0:
                return 0.5  # Default moderate error rate
            
            return total_errors / total_words
            
        except Exception:
            # Fallback to rule-based checking
            return self._rule_based_grammar_check(content)
    
    def _rule_based_grammar_check(self, content: str) -> float:
        """Rule-based grammar and style checking"""
        if not content:
            return 0.5
        
        words = content.split()
        word_count = len(words)
        
        if word_count == 0:
            return 0.5
        
        error_count = 0
        
        # Check for common grammar issues
        error_count += self._check_spelling_patterns(content)
        error_count += self._check_punctuation_issues(content)
        error_count += self._check_capitalization_issues(content)
        error_count += self._check_common_grammar_mistakes(content)
        error_count += self._check_style_issues(content)
        
        return error_count / word_count
    
    def _basic_grammar_check(self, content: str) -> float:
        """Basic grammar checking for fallback"""
        if not content:
            return 0.5
        
        words = content.split()
        word_count = len(words)
        
        if word_count == 0:
            return 0.5
        
        error_count = 0
        
        # Very basic checks
        error_count += self._check_spelling_patterns(content) * 0.5
        error_count += self._check_punctuation_issues(content) * 0.5
        
        return min(0.2, error_count / word_count)  # Cap at 20% error rate for basic check
    
    def _check_spelling_patterns(self, content: str) -> int:
        """Check for common spelling patterns that indicate errors"""
        error_count = 0
        
        # Common misspellings patterns
        misspelling_patterns = [
            r'\bteh\b',           # the
            r'\brecieve\b',       # receive
            r'\boccur\b',         # occur (checking for occured instead of occurred)
            r'\baccommodate\b',   # accommodate
            r'\bdefinate\b',      # definite
            r'\bseperate\b',      # separate
            r'\bexperiance\b',    # experience
            r'\benvironment\b',   # environment
            r'\bpublic\b.*\bpublic\b',  # duplicate words
        ]
        
        for pattern in misspelling_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            error_count += len(matches)
        
        # Check for repeated words
        words = content.split()
        for i in range(len(words) - 1):
            if words[i].lower() == words[i + 1].lower() and len(words[i]) > 2:
                error_count += 1
        
        return error_count
    
    def _check_punctuation_issues(self, content: str) -> int:
        """Check for punctuation issues"""
        error_count = 0
        
        # Multiple spaces
        error_count += len(re.findall(r'  +', content))
        
        # Missing spaces after punctuation
        error_count += len(re.findall(r'[.!?][A-Za-z]', content))
        
        # Incorrect apostrophe usage
        error_count += len(re.findall(r"its'", content))  # it's vs its
        
        # Multiple punctuation
        error_count += len(re.findall(r'[.!?]{2,}', content))
        
        # Space before punctuation
        error_count += len(re.findall(r' [.!?:;,]', content))
        
        return error_count
    
    def _check_capitalization_issues(self, content: str) -> int:
        """Check for capitalization issues"""
        error_count = 0
        
        sentences = re.split(r'[.!?]+', content)
        
        for sentence in sentences:
            sentence = sentence.strip()
            if sentence and len(sentence) > 1:
                # Check if sentence starts with lowercase (excluding quotes, etc.)
                first_word = re.match(r'^["\'\s]*([a-zA-Z])', sentence)
                if first_word and first_word.group(1).islower():
                    # Check if it's not a continuation or special case
                    if not sentence.startswith(('e.g.', 'i.e.', 'etc.')):
                        error_count += 1
        
        return error_count
    
    def _check_common_grammar_mistakes(self, content: str) -> int:
        """Check for common grammatical mistakes"""
        error_count = 0
        
        # Common grammar mistake patterns
        grammar_patterns = [
            r'\byour\s+welcome\b',        # you're welcome
            r'\bits\s+going\b',           # it's going
            r'\bwould\s+of\b',           # would have
            r'\bcould\s+of\b',           # could have
            r'\bshould\s+of\b',          # should have
            r'\bthere\s+going\b',        # they're going
            r'\bto\s+much\b',            # too much
            r'\balot\b',                 # a lot
        ]
        
        for pattern in grammar_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            error_count += len(matches)
        
        return error_count
    
    def _check_style_issues(self, content: str) -> int:
        """Check for style and readability issues"""
        error_count = 0
        
        # Very long sentences (over 40 words)
        sentences = re.split(r'[.!?]+', content)
        for sentence in sentences:
            words = sentence.split()
            if len(words) > 40:
                error_count += 1
        
        # Excessive use of passive voice (basic check)
        passive_patterns = [
            r'\bwas\s+\w+ed\b',
            r'\bwere\s+\w+ed\b',
            r'\bis\s+\w+ed\b',
            r'\bare\s+\w+ed\b',
        ]
        
        for pattern in passive_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            error_count += len(matches) * 0.5  # Half weight for style issues
        
        return int(error_count)
    
    def _error_rate_to_rating(self, error_rate: float) -> str:
        """Convert error rate to quality rating"""
        if error_rate < 0.01:
            return "Excellent"
        elif error_rate < 0.03:
            return "Good"
        elif error_rate < 0.05:
            return "Fair"
        elif error_rate < 0.10:
            return "Poor"
        else:
            return "Very Poor"
    
    def _split_content(self, content: str, max_words: int = 800) -> List[str]:
        """Split content into chunks for processing"""
        words = content.split()
        chunks = []
        
        for i in range(0, len(words), max_words):
            chunk_words = words[i:i + max_words]
            chunks.append(' '.join(chunk_words))
        
        return chunks
    
    async def get_detailed_analysis(self, content: str) -> Dict:
        """Get detailed grammar and style analysis"""
        if not content or not content.strip():
            return {
                'rating': 'Very Poor',
                'error_rate': 1.0,
                'word_count': 0,
                'issues_found': [],
                'recommendations': ['No content to analyze']
            }
        
        try:
            word_count = len(content.split())
            
            if self.use_llm and self.openai_client:
                error_rate = await self._llm_grammar_check(content)
                issues = await self._get_detailed_llm_analysis(content)
            else:
                error_rate = self._rule_based_grammar_check(content)
                issues = self._get_rule_based_issues(content)
            
            rating = self._error_rate_to_rating(error_rate)
            recommendations = self._generate_recommendations(rating, error_rate, issues)
            
            return {
                'rating': rating,
                'error_rate': round(error_rate, 4),
                'word_count': word_count,
                'issues_found': issues,
                'recommendations': recommendations
            }
            
        except Exception as e:
            # Fallback analysis
            error_rate = self._basic_grammar_check(content)
            rating = self._error_rate_to_rating(error_rate)
            
            return {
                'rating': rating,
                'error_rate': round(error_rate, 4),
                'word_count': len(content.split()),
                'issues_found': ['Analysis error occurred'],
                'recommendations': ['Manual review recommended'],
                'error': str(e)
            }
    
    async def _get_detailed_llm_analysis(self, content: str) -> List[str]:
        """Get detailed issues list from LLM"""
        try:
            sample = content[:1000] if len(content) > 1000 else content
            
            prompt = f"""Analyze this text and list the main grammar, spelling, and style issues found. Be specific but concise.

Text: {sample}

List issues as bullet points:"""
            
            response = await asyncio.to_thread(
                self.openai_client.chat.completions.create,
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a professional editor. List specific issues found in the text."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=300,
                temperature=0.1
            )
            
            issues_text = response.choices[0].message.content
            issues = [line.strip().lstrip('•-*') for line in issues_text.split('\n') if line.strip()]
            
            return issues[:10]  # Limit to top 10 issues
            
        except Exception:
            return []
    
    def _get_rule_based_issues(self, content: str) -> List[str]:
        """Get issues from rule-based analysis"""
        issues = []
        
        # Check for various issue types
        if self._check_spelling_patterns(content) > 0:
            issues.append("Potential spelling errors detected")
        
        if self._check_punctuation_issues(content) > 0:
            issues.append("Punctuation issues found")
        
        if self._check_capitalization_issues(content) > 0:
            issues.append("Capitalization errors detected")
        
        if self._check_common_grammar_mistakes(content) > 0:
            issues.append("Common grammar mistakes found")
        
        if self._check_style_issues(content) > 0:
            issues.append("Style and readability issues detected")
        
        return issues
    
    def _generate_recommendations(self, rating: str, error_rate: float, issues: List[str]) -> List[str]:
        """Generate improvement recommendations"""
        recommendations = []
        
        if rating in ['Poor', 'Very Poor']:
            recommendations.append("Consider comprehensive proofreading and editing")
            recommendations.append("Use grammar checking tools or professional editing services")
        
        if rating == 'Fair':
            recommendations.append("Review and correct identified grammar and style issues")
            
        if error_rate > 0.05:
            recommendations.append("Focus on reducing spelling and punctuation errors")
        
        if any('style' in issue.lower() for issue in issues):
            recommendations.append("Improve sentence structure and readability")
        
        if any('spelling' in issue.lower() for issue in issues):
            recommendations.append("Use spell-check tools and review for common misspellings")
        
        if not recommendations:
            recommendations.append("Content quality is good. Continue maintaining high standards.")
        
        return recommendations
    
    async def generate_enhanced_recommendations(self, content: str, rating: str) -> List[Dict]:
        """Generate detailed, actionable recommendations for language quality improvements"""
        recommendations = []
        
        if not content or not content.strip():
            return [{
                "priority": "critical",
                "category": "no_content",
                "issue": "No content provided for language quality analysis",
                "impact": "Cannot assess writing quality",
                "action": "Provide content for evaluation"
            }]
        
        detailed_analysis = await self.get_detailed_analysis(content)
        error_rate = detailed_analysis.get('error_rate', 0)
        word_count = detailed_analysis.get('word_count', 0)
        issues_found = detailed_analysis.get('issues_found', [])
        
        # Critical language quality issues
        if rating in ["Very Poor", "Poor"]:
            severity = "critical" if rating == "Very Poor" else "high"
            recommendations.append({
                "priority": severity,
                "category": "language_quality",
                "issue": f"Language quality rated as {rating} (error rate: {error_rate:.1%})",
                "impact": "10% weight metric - poor user experience and credibility impact",
                "action": "Comprehensive language quality improvement required",
                "specifics": {
                    "current_rating": rating,
                    "error_rate": f"{error_rate:.1%}",
                    "word_count": word_count,
                    "estimated_errors": int(error_rate * word_count),
                    "target_error_rate": "< 3%",
                    "issues_categories": issues_found
                },
                "implementation": {
                    "effort": "high",
                    "timeline": "1-2 weeks",
                    "phases": [
                        "Phase 1: Grammar and spelling corrections (Week 1)",
                        "Phase 2: Style and readability improvements (Week 1-2)",
                        "Phase 3: Professional review and final polish (Week 2)"
                    ],
                    "recommended_tools": [
                        "Grammarly or ProWritingAid for automated checking",
                        "Professional editing service for final review",
                        "Hemingway Editor for readability improvement"
                    ]
                }
            })
        
        # Specific error type recommendations
        if any('spelling' in issue.lower() for issue in issues_found):
            recommendations.append({
                "priority": "high",
                "category": "spelling_errors",
                "issue": "Spelling errors detected in content",
                "impact": "Reduced credibility and professional appearance",
                "action": "Systematic spelling correction and prevention",
                "implementation": {
                    "effort": "low",
                    "timeline": "1-2 days",
                    "immediate_steps": [
                        "Run content through spell-checker",
                        "Manually review flagged words",
                        "Create custom dictionary for technical terms",
                        "Set up automatic spell-check in content management system"
                    ],
                    "prevention_measures": [
                        "Enable spell-check in writing tools",
                        "Create style guide with correct spellings",
                        "Train content creators on common misspellings"
                    ]
                }
            })
        
        if any('punctuation' in issue.lower() for issue in issues_found):
            recommendations.append({
                "priority": "medium",
                "category": "punctuation_issues",
                "issue": "Punctuation errors found in content",
                "impact": "Affects readability and professional appearance",
                "action": "Review and correct punctuation usage",
                "implementation": {
                    "effort": "low",
                    "timeline": "1 day",
                    "focus_areas": [
                        "Spacing after punctuation marks",
                        "Proper apostrophe usage (it's vs its)",
                        "Avoiding multiple punctuation marks",
                        "Correct comma placement in lists",
                        "Proper use of semicolons and colons"
                    ],
                    "tools": [
                        "Grammarly for punctuation checking",
                        "Manual review with style guide reference"
                    ]
                }
            })
        
        if any('grammar' in issue.lower() for issue in issues_found):
            recommendations.append({
                "priority": "high",
                "category": "grammar_mistakes",
                "issue": "Grammar errors identified in content",
                "impact": "Reduces content clarity and professional credibility",
                "action": "Address grammatical errors systematically",
                "implementation": {
                    "effort": "medium",
                    "timeline": "2-3 days",
                    "common_fixes": [
                        "Subject-verb agreement corrections",
                        "Proper pronoun usage",
                        "Correct verb tense consistency",
                        "Fix run-on sentences",
                        "Eliminate dangling modifiers"
                    ],
                    "approach": [
                        "Use grammar checking tools for initial scan",
                        "Manual review for context-specific issues",
                        "Read content aloud to catch errors",
                        "Consider professional editing for complex issues"
                    ]
                }
            })
        
        if any('style' in issue.lower() or 'readability' in issue.lower() for issue in issues_found):
            recommendations.append({
                "priority": "medium",
                "category": "style_improvement",
                "issue": "Style and readability issues detected",
                "impact": "Affects user engagement and content comprehension",
                "action": "Improve writing style and readability",
                "implementation": {
                    "effort": "medium",
                    "timeline": "3-5 days",
                    "style_improvements": [
                        "Break up long sentences (aim for 15-20 words)",
                        "Use active voice instead of passive voice",
                        "Eliminate unnecessary words and phrases",
                        "Improve paragraph structure and flow",
                        "Add transition words for better connectivity"
                    ],
                    "readability_enhancements": [
                        "Use simpler vocabulary where appropriate",
                        "Add subheadings for content organization",
                        "Include bullet points for lists",
                        "Vary sentence length for better flow",
                        "Use concrete examples and analogies"
                    ]
                }
            })
        
        # Error rate specific recommendations
        if error_rate > 0.05:  # > 5% error rate
            recommendations.append({
                "priority": "high",
                "category": "error_density",
                "issue": f"High error density ({error_rate:.1%}) across content",
                "impact": "May indicate systemic writing quality issues",
                "action": "Implement comprehensive quality control process",
                "specifics": {
                    "current_error_rate": f"{error_rate:.1%}",
                    "target_rate": "< 3%",
                    "improvement_needed": f"{((error_rate - 0.03) * 100):.1f} percentage points"
                },
                "implementation": {
                    "effort": "high",
                    "timeline": "1 week",
                    "process_improvements": [
                        "Implement multi-stage review process",
                        "Use automated grammar/spell checking",
                        "Add peer review step for all content",
                        "Create content quality checklist",
                        "Train content creators on common issues"
                    ],
                    "quality_gates": [
                        "Automated tool check (first pass)",
                        "Self-review by author",
                        "Peer review by colleague",
                        "Final review by editor (if available)"
                    ]
                }
            })
        
        # Content length considerations
        if word_count > 1000 and error_rate > 0.03:
            recommendations.append({
                "priority": "medium",
                "category": "content_management",
                "issue": f"Large content piece ({word_count} words) with quality issues",
                "impact": "Errors in long content have compound negative effect",
                "action": "Break content into sections for easier quality management",
                "implementation": {
                    "effort": "medium",
                    "timeline": "2-3 days",
                    "strategies": [
                        "Divide content into smaller, manageable sections",
                        "Review each section independently",
                        "Use consistent style across all sections",
                        "Add section-level quality checks",
                        "Consider multiple authors with final unified review"
                    ]
                }
            })
        
        # Positive reinforcement for good quality
        if rating in ["Good", "Excellent"]:
            recommendations.append({
                "priority": "low",
                "category": "quality_maintenance",
                "issue": "Good language quality with optimization opportunities",
                "impact": "Maintain competitive advantage in content quality",
                "action": "Continue current quality standards with minor enhancements",
                "implementation": {
                    "effort": "low",
                    "timeline": "Ongoing",
                    "maintenance_practices": [
                        "Regular content audits for quality consistency",
                        "Stay updated with style guide changes",
                        "Periodic training on writing best practices",
                        "Monitor reader feedback for language clarity",
                        "Benchmark against industry-leading content"
                    ]
                }
            })
        
        # Tool and process recommendations
        if not self.use_llm or not self.openai_client:
            recommendations.append({
                "priority": "medium",
                "category": "tooling_improvement",
                "issue": "Limited automated language checking capabilities",
                "impact": "May miss subtle language quality issues",
                "action": "Enhance language quality checking tools and processes",
                "implementation": {
                    "effort": "low",
                    "timeline": "1 day",
                    "tool_recommendations": [
                        "Enable AI-powered grammar checking",
                        "Integrate with professional editing tools",
                        "Set up automated quality scoring",
                        "Consider human editorial review for important content"
                    ]
                }
            })
        
        return recommendations