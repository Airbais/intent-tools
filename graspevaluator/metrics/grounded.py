"""
Grounded metric evaluator - Content alignment with customer intents
"""

import asyncio
import json
import re
from typing import Dict, List, Optional
import openai


class GroundedEvaluator:
    """Evaluate how well content supports answering customer intents"""
    
    def __init__(self, config):
        self.config = config
        
        # Initialize OpenAI client
        try:
            api_key = config.get_openai_api_key()
            self.openai_client = openai.OpenAI(api_key=api_key)
        except Exception as e:
            raise ValueError(f"Failed to initialize OpenAI client: {e}")
    
    async def evaluate(self, content: str, intents: List[str]) -> float:
        """
        Evaluate how well content supports answering customer intents
        
        Args:
            content: Text content to evaluate
            intents: List of customer intents/questions
            
        Returns:
            float: Grounded score from 0.0 to 10.0
        """
        # Use the detailed analysis and return just the score for compatibility
        detailed_result = await self.get_detailed_analysis(content, intents)
        return detailed_result.get('overall_score', 0.0)
    
    async def _evaluate_intent_batch(self, content: str, intents: List[str]) -> List[float]:
        """Evaluate a batch of intents against content"""
        scores = []
        
        for intent in intents:
            try:
                score = await self._evaluate_single_intent(content, intent)
                scores.append(score)
            except Exception:
                # If individual intent fails, assign neutral score
                scores.append(5.0)
        
        return scores
    
    async def _evaluate_single_intent(self, content: str, intent: str) -> float:
        """Evaluate how well content supports a single intent"""
        # Step 1: Try to answer the intent using the content
        answer_response = await self._generate_answer(content, intent)
        
        # Step 2: Evaluate the quality of the answer
        evaluation_score = await self._evaluate_answer_quality(content, intent, answer_response)
        
        return evaluation_score
    
    async def _generate_answer(self, content: str, intent: str) -> Dict:
        """Generate an answer to the intent using only the provided content"""
        # Truncate content if too long
        max_content_length = 3000
        if len(content) > max_content_length:
            content = content[:max_content_length] + "..."
        
        prompt = f"""You are tasked with answering a customer question using ONLY the information provided in the content below. 

IMPORTANT RULES:
1. Use ONLY information explicitly stated in the provided content
2. Do not use any external knowledge or assumptions
3. If the content doesn't contain enough information to answer, say so clearly
4. Be specific and cite relevant parts of the content when possible

Customer Question: {intent}

Content to use for answering:
{content}

Provide your response in this JSON format:
{{
    "answer": "Your answer here",
    "confidence": "high|medium|low",
    "content_support": "excellent|good|partial|insufficient",
    "citations": ["relevant quote 1", "relevant quote 2"],
    "gaps": ["information gap 1", "information gap 2"]
}}"""

        try:
            response = await asyncio.to_thread(
                self.openai_client.chat.completions.create,
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are an AI assistant that answers questions using only provided content. Always respond with valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=500,
                temperature=0.1
            )
            
            response_text = response.choices[0].message.content
            
            # Try to parse JSON response
            try:
                return json.loads(response_text)
            except json.JSONDecodeError:
                # Fallback if JSON parsing fails
                return {
                    "answer": response_text,
                    "confidence": "medium",
                    "content_support": "partial",
                    "citations": [],
                    "gaps": []
                }
                
        except Exception as e:
            return {
                "answer": f"Error generating answer: {str(e)}",
                "confidence": "low",
                "content_support": "insufficient",
                "citations": [],
                "gaps": ["Unable to process content"]
            }
    
    async def _evaluate_answer_quality(self, content: str, intent: str, answer_response: Dict) -> float:
        """Evaluate the quality of the generated answer"""
        try:
            prompt = f"""Evaluate how well the provided content supported answering the customer question. 

Customer Question: {intent}

Generated Answer: {answer_response.get('answer', 'No answer provided')}

Content Support Level: {answer_response.get('content_support', 'unknown')}
Confidence Level: {answer_response.get('confidence', 'unknown')}
Information Gaps: {answer_response.get('gaps', [])}

Rate on a scale of 1-10 how well the content enabled answering this question:
- 9-10: Content provides comprehensive, specific information to fully answer the question
- 7-8: Content provides good information with minor gaps
- 5-6: Content provides partial information but has noticeable gaps
- 3-4: Content provides limited relevant information
- 1-2: Content provides little to no relevant information

Respond with only a JSON object:
{{
    "score": <number between 1-10>,
    "reasoning": "Brief explanation of the score"
}}"""

            response = await asyncio.to_thread(
                self.openai_client.chat.completions.create,
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are evaluating content quality for answering customer questions. Respond only with valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=200,
                temperature=0.1
            )
            
            response_text = response.choices[0].message.content
            
            try:
                result = json.loads(response_text)
                score = float(result.get('score', 5.0))
                return min(10.0, max(1.0, score))
            except (json.JSONDecodeError, ValueError, TypeError):
                # Fallback scoring based on answer attributes
                return self._fallback_scoring(answer_response)
                
        except Exception:
            return self._fallback_scoring(answer_response)
    
    def _fallback_scoring(self, answer_response: Dict) -> float:
        """Fallback scoring when LLM evaluation fails"""
        score = 5.0  # Start with neutral
        
        # Adjust based on confidence
        confidence = answer_response.get('confidence', 'medium').lower()
        if confidence == 'high':
            score += 2.0
        elif confidence == 'low':
            score -= 2.0
        
        # Adjust based on content support
        support = answer_response.get('content_support', 'partial').lower()
        if support == 'excellent':
            score += 2.0
        elif support == 'good':
            score += 1.0
        elif support == 'insufficient':
            score -= 3.0
        
        # Adjust based on gaps
        gaps = answer_response.get('gaps', [])
        if len(gaps) > 2:
            score -= 1.0
        
        # Adjust based on citations
        citations = answer_response.get('citations', [])
        if len(citations) > 0:
            score += 0.5
        
        return min(10.0, max(1.0, score))
    
    def _fallback_evaluation(self, content: str, intents: List[str]) -> float:
        """Fallback evaluation when LLM is not available"""
        if not content or not intents:
            return 0.0
        
        # Simple keyword matching approach
        content_lower = content.lower()
        total_score = 0
        
        for intent in intents:
            intent_lower = intent.lower()
            
            # Extract key terms from intent
            key_terms = self._extract_key_terms(intent_lower)
            
            # Count matches in content
            matches = 0
            for term in key_terms:
                if term in content_lower:
                    matches += 1
            
            # Calculate score for this intent
            if key_terms:
                intent_score = (matches / len(key_terms)) * 10
                total_score += intent_score
            else:
                total_score += 5.0  # Neutral if no key terms
        
        return total_score / len(intents) if intents else 0.0
    
    def _extract_key_terms(self, intent: str) -> List[str]:
        """Extract key terms from an intent"""
        # Remove common question words
        stop_words = {'how', 'what', 'where', 'when', 'why', 'who', 'can', 'do', 'does', 'is', 'are', 'the', 'a', 'an', 'and', 'or', 'but', 'to', 'for', 'of', 'in', 'on', 'at', 'by', 'with'}
        
        # Extract words
        words = re.findall(r'\b\w+\b', intent.lower())
        
        # Filter out stop words and short words
        key_terms = [word for word in words if word not in stop_words and len(word) > 2]
        
        return key_terms
    
    async def get_detailed_analysis(self, content: str, intents: List[str]) -> Dict:
        """Get detailed analysis of content grounding"""
        if not content or not content.strip():
            return {
                'overall_score': 0.0,
                'intent_scores': [],
                'recommendations': ['No content provided for analysis'],
                'content_gaps': ['No content to analyze']
            }
        
        if not intents:
            return {
                'overall_score': 5.0,
                'intent_scores': [],
                'recommendations': ['No customer intents provided for evaluation'],
                'content_gaps': ['No intents to evaluate against']
            }
        
        try:
            intent_analyses = []
            intent_scores = []
            
            # Analyze each intent individually
            for intent in intents:
                try:
                    answer_response = await self._generate_answer(content, intent)
                    score = await self._evaluate_answer_quality(content, intent, answer_response)
                    
                    intent_analysis = {
                        'intent': intent,
                        'score': round(score, 1),
                        'answer': answer_response.get('answer', ''),
                        'confidence': answer_response.get('confidence', 'unknown'),
                        'content_support': answer_response.get('content_support', 'unknown'),
                        'gaps': answer_response.get('gaps', []),
                        'citations': answer_response.get('citations', [])
                    }
                    
                    intent_analyses.append(intent_analysis)
                    intent_scores.append(score)
                    
                except Exception:
                    # Fallback for failed intent
                    fallback_score = self._fallback_evaluation(content, [intent])
                    intent_analyses.append({
                        'intent': intent,
                        'score': round(fallback_score, 1),
                        'answer': 'Error in analysis',
                        'confidence': 'low',
                        'content_support': 'unknown',
                        'gaps': ['Analysis error'],
                        'citations': []
                    })
                    intent_scores.append(fallback_score)
            
            overall_score = sum(intent_scores) / len(intent_scores) if intent_scores else 0.0
            
            # Generate enhanced recommendations
            recommendations = await self._generate_enhanced_recommendations(intent_analyses, overall_score, content)
            
            # Identify content gaps
            content_gaps = self._identify_content_gaps(intent_analyses)
            
            return {
                'overall_score': round(overall_score, 1),
                'intent_scores': intent_analyses,
                'recommendations': recommendations,
                'content_gaps': content_gaps
            }
            
        except Exception as e:
            # Complete fallback
            fallback_score = self._fallback_evaluation(content, intents)
            
            return {
                'overall_score': round(fallback_score, 1),
                'intent_scores': [],
                'recommendations': ['Error in detailed analysis. Manual review recommended.'],
                'content_gaps': ['Unable to identify specific gaps due to analysis error'],
                'error': str(e)
            }
    
    async def _generate_enhanced_recommendations(self, intent_analyses: List[Dict], overall_score: float, content: str) -> List[Dict]:
        """Generate detailed, actionable recommendations based on analysis"""
        recommendations = []
        
        # Analyze failed intents for specific guidance
        failed_intents = [analysis for analysis in intent_analyses if analysis.get('score', 0) < 5.0]
        moderate_intents = [analysis for analysis in intent_analyses if 5.0 <= analysis.get('score', 0) < 7.0]
        
        # High-level assessment
        if overall_score < 4.0:
            recommendations.append({
                "priority": "critical",
                "category": "content_coverage",
                "issue": f"Content fails to address {len(failed_intents)} of {len(intent_analyses)} customer intents",
                "impact": "40% weight metric - major impact on GRASP score",
                "action": "Comprehensive content audit and expansion needed",
                "specifics": {
                    "failed_intents": [intent['intent'] for intent in failed_intents],
                    "success_rate": f"{((len(intent_analyses) - len(failed_intents)) / len(intent_analyses) * 100):.0f}%"
                },
                "implementation": {
                    "effort": "high",
                    "timeline": "2-4 weeks",
                    "steps": [
                        "Audit existing content against customer journey",
                        "Create content map for missing intents",
                        "Develop FAQ section addressing failed intents",
                        "Add intent-specific CTAs and landing pages"
                    ]
                }
            })
        
        # Intent-specific recommendations
        for analysis in failed_intents[:3]:  # Focus on top 3 failed intents
            intent = analysis.get('intent', '')
            score = analysis.get('score', 0)
            gaps = analysis.get('gaps', [])
            confidence = analysis.get('confidence', 'unknown')
            
            # Generate specific content suggestions using AI
            content_suggestion = await self._generate_content_suggestions(intent, gaps, content)
            
            recommendations.append({
                "priority": "high",
                "category": "intent_gap",
                "issue": f"Intent '{intent}' scores {score}/10 - insufficient content support",
                "impact": f"Customer question not adequately answered",
                "action": f"Create targeted content for '{intent}'",
                "specifics": {
                    "intent": intent,
                    "current_score": score,
                    "target_score": "7.0+",
                    "confidence_level": confidence,
                    "identified_gaps": gaps,
                    "content_length_needed": "200-400 words"
                },
                "implementation": {
                    "effort": "medium",
                    "timeline": "3-5 days",
                    "placement_suggestions": content_suggestion.get("placement", []),
                    "content_examples": content_suggestion.get("examples", []),
                    "format_recommendations": content_suggestion.get("format", [])
                }
            })
        
        # Moderate scoring intents - optimization opportunities
        for analysis in moderate_intents[:2]:  # Top 2 moderate intents
            intent = analysis.get('intent', '')
            score = analysis.get('score', 0)
            
            recommendations.append({
                "priority": "medium",
                "category": "content_optimization",
                "issue": f"Intent '{intent}' scores {score}/10 - room for improvement",
                "impact": "Opportunity to strengthen content alignment",
                "action": "Enhance existing content with more specific details",
                "specifics": {
                    "intent": intent,
                    "current_score": score,
                    "target_score": "8.0+",
                    "improvement_potential": f"+{(8.0 - score):.1f} points"
                },
                "implementation": {
                    "effort": "low",
                    "timeline": "1-2 days",
                    "steps": [
                        "Add specific examples or case studies",
                        "Include more detailed explanations",
                        "Add relevant internal links",
                        "Improve section headings for clarity"
                    ]
                }
            })
        
        # Cross-intent analysis for systematic issues
        common_gaps = self._find_common_gaps(intent_analyses)
        if common_gaps:
            recommendations.append({
                "priority": "high",
                "category": "systematic_gap",
                "issue": f"Common content gaps appearing across multiple intents",
                "impact": "Addressing these gaps will improve multiple intent scores",
                "action": "Create foundational content addressing common gaps",
                "specifics": {
                    "common_gaps": common_gaps,
                    "affected_intents": len([a for a in intent_analyses if any(gap in a.get('gaps', []) for gap in common_gaps)])
                },
                "implementation": {
                    "effort": "medium",
                    "timeline": "1 week",
                    "content_types": ["FAQ section", "Getting Started guide", "Feature comparison table"],
                    "placement": "Main navigation, footer, or dedicated resource section"
                }
            })
        
        return recommendations
    
    async def _generate_content_suggestions(self, intent: str, gaps: List[str], existing_content: str) -> Dict:
        """Generate AI-powered content suggestions for a specific intent"""
        try:
            gap_list = ", ".join(gaps) if gaps else "general information gaps"
            content_sample = existing_content[:500] + "..." if len(existing_content) > 500 else existing_content
            
            prompt = f"""Based on the customer intent "{intent}" and identified content gaps: {gap_list}

Existing content sample: {content_sample}

Provide specific content recommendations in JSON format:
{{
    "placement": ["where to add content - 3 specific suggestions"],
    "examples": ["specific content examples - 2-3 suggestions"],
    "format": ["recommended content format - e.g., FAQ, step-by-step guide, comparison table"]
}}

Be specific and actionable."""

            response = await asyncio.to_thread(
                self.openai_client.chat.completions.create,
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a content strategist providing specific, actionable recommendations. Respond only with valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=300,
                temperature=0.3
            )
            
            import json
            return json.loads(response.choices[0].message.content)
            
        except Exception:
            # Fallback suggestions
            return {
                "placement": ["Homepage hero section", "Dedicated FAQ page", "Main navigation menu"],
                "examples": [f"Add section addressing '{intent}'", "Include step-by-step instructions", "Provide contact information"],
                "format": ["FAQ format", "Step-by-step guide", "Contact form"]
            }
    
    def _find_common_gaps(self, intent_analyses: List[Dict]) -> List[str]:
        """Find gaps that appear across multiple intents"""
        gap_counts = {}
        
        for analysis in intent_analyses:
            for gap in analysis.get('gaps', []):
                gap_counts[gap] = gap_counts.get(gap, 0) + 1
        
        # Return gaps that appear in 2+ intents
        common_gaps = [gap for gap, count in gap_counts.items() if count >= 2]
        return common_gaps[:3]  # Top 3 most common gaps
    
    def _generate_recommendations(self, intent_analyses: List[Dict], overall_score: float) -> List[str]:
        """Legacy method for backward compatibility"""
        recommendations = []
        
        if overall_score < 4.0:
            recommendations.append("Content significantly lacks information to address customer intents. Consider comprehensive content expansion.")
        elif overall_score < 6.0:
            recommendations.append("Content partially addresses customer intents. Add more specific information and examples.")
        elif overall_score < 8.0:
            recommendations.append("Content addresses most customer intents well. Focus on filling identified gaps.")
        else:
            recommendations.append("Content strongly supports customer intents. Continue maintaining comprehensive coverage.")
        
        # Specific recommendations based on low-scoring intents
        low_score_intents = [analysis for analysis in intent_analyses if analysis.get('score', 0) < 5.0]
        if low_score_intents:
            recommendations.append(f"Pay special attention to improving content for: {', '.join([intent['intent'] for intent in low_score_intents[:3]])}")
        
        # Recommendations based on common gaps
        all_gaps = []
        for analysis in intent_analyses:
            all_gaps.extend(analysis.get('gaps', []))
        
        if all_gaps:
            unique_gaps = list(set(all_gaps))[:3]  # Top 3 unique gaps
            recommendations.append(f"Address these content gaps: {', '.join(unique_gaps)}")
        
        return recommendations
    
    def _identify_content_gaps(self, intent_analyses: List[Dict]) -> List[str]:
        """Identify major content gaps from intent analysis"""
        gaps = []
        
        for analysis in intent_analyses:
            if analysis.get('score', 0) < 5.0:
                gaps.append(f"Insufficient information for: {analysis.get('intent', 'Unknown intent')}")
            
            # Add specific gaps mentioned in the analysis
            intent_gaps = analysis.get('gaps', [])
            gaps.extend(intent_gaps)
        
        # Remove duplicates and limit
        unique_gaps = list(set(gaps))
        return unique_gaps[:10]  # Limit to top 10 gaps