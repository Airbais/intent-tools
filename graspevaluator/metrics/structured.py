"""
Structured metric evaluator - HTML structure assessment
"""

import re
from typing import Dict, List
from bs4 import BeautifulSoup


class StructuredEvaluator:
    """Evaluate semantic HTML structure for LLM consumption"""
    
    def __init__(self, config):
        self.config = config
        self.structured_config = config.get_structured_config()
    
    def evaluate(self, html: str) -> str:
        """
        Evaluate HTML structure quality
        
        Args:
            html: HTML content to analyze
            
        Returns:
            str: Structure rating ('Excellent', 'Good', 'Fair', 'Poor', 'Very Poor')
        """
        if not html:
            return "Very Poor"
        
        try:
            soup = BeautifulSoup(html, 'lxml')
            
            total_score = 0
            max_score = 100
            
            # Heading structure (25 points)
            if self.structured_config.get('check_headings', True):
                total_score += self._evaluate_headings(soup)
            
            # Semantic elements (25 points)
            if self.structured_config.get('check_semantic_elements', True):
                total_score += self._evaluate_semantic_elements(soup)
            
            # Lists and tables (25 points)
            total_score += self._evaluate_data_structures(soup)
            
            # Schema markup (25 points)
            if self.structured_config.get('check_schema_markup', True):
                total_score += self._evaluate_schema_markup(soup)
            
            # Convert to rating
            return self._score_to_rating(total_score)
            
        except Exception:
            return "Poor"
    
    def _evaluate_headings(self, soup: BeautifulSoup) -> float:
        """Evaluate heading structure (max 25 points)"""
        score = 0
        
        # Find all headings
        headings = []
        for level in range(1, 7):
            level_headings = soup.find_all(f'h{level}')
            for heading in level_headings:
                if heading.get_text(strip=True):
                    headings.append({
                        'level': level,
                        'text': heading.get_text(strip=True)
                    })
        
        if not headings:
            return 0
        
        # Check for h1 presence (5 points)
        h1_count = len([h for h in headings if h['level'] == 1])
        if h1_count == 1:
            score += 5
        elif h1_count > 1:
            score += 2  # Multiple h1s are not ideal but better than none
        
        # Check heading hierarchy (10 points)
        hierarchy_score = self._check_heading_hierarchy(headings)
        score += hierarchy_score * 10
        
        # Check heading content quality (10 points)
        content_score = self._check_heading_content(headings)
        score += content_score * 10
        
        return min(25, score)
    
    def _check_heading_hierarchy(self, headings: List[Dict]) -> float:
        """Check if headings follow proper hierarchy"""
        if not headings:
            return 0
        
        violations = 0
        total_checks = 0
        
        for i, heading in enumerate(headings[1:], 1):
            prev_level = headings[i-1]['level']
            curr_level = heading['level']
            
            total_checks += 1
            
            # Check if heading level jumps more than 1
            if curr_level > prev_level + 1:
                violations += 1
        
        if total_checks == 0:
            return 1.0
        
        return max(0, 1 - (violations / total_checks))
    
    def _check_heading_content(self, headings: List[Dict]) -> float:
        """Check heading content quality"""
        if not headings:
            return 0
        
        quality_score = 0
        
        for heading in headings:
            text = heading['text']
            
            # Check length (not too short, not too long)
            if 3 <= len(text.split()) <= 10:
                quality_score += 1
            elif len(text.split()) > 0:
                quality_score += 0.5
            
            # Check for descriptive content (not just numbers or single words)
            if len(text.split()) >= 2 and not text.isdigit():
                quality_score += 0.5
        
        return min(1.0, quality_score / len(headings))
    
    def _evaluate_semantic_elements(self, soup: BeautifulSoup) -> float:
        """Evaluate semantic HTML elements (max 25 points)"""
        score = 0
        
        # Important semantic elements and their points
        semantic_elements = {
            'main': 5,      # Main content area
            'article': 4,   # Article content
            'section': 3,   # Content sections
            'header': 2,    # Page/section headers
            'footer': 2,    # Page/section footers
            'nav': 2,       # Navigation
            'aside': 1,     # Sidebar content
            'figure': 1,    # Figures with captions
            'figcaption': 1 # Figure captions
        }
        
        found_elements = set()
        
        for element, points in semantic_elements.items():
            if soup.find(element):
                score += points
                found_elements.add(element)
        
        # Bonus for using multiple semantic elements
        if len(found_elements) >= 5:
            score += 3
        elif len(found_elements) >= 3:
            score += 2
        elif len(found_elements) >= 2:
            score += 1
        
        return min(25, score)
    
    def _evaluate_data_structures(self, soup: BeautifulSoup) -> float:
        """Evaluate lists and tables (max 25 points)"""
        score = 0
        
        # Check for lists
        lists = soup.find_all(['ul', 'ol', 'dl'])
        if lists:
            score += 5
            
            # Bonus for using definition lists
            if soup.find('dl'):
                score += 2
            
            # Check list quality
            quality_lists = 0
            for lst in lists:
                items = lst.find_all(['li', 'dt', 'dd'])
                if len(items) >= 2:  # At least 2 items
                    quality_lists += 1
            
            if quality_lists > 0:
                score += min(5, quality_lists * 2)
        
        # Check for tables
        tables = soup.find_all('table')
        if tables:
            score += 3
            
            # Check table quality
            for table in tables:
                # Has table headers
                if table.find('th') or table.find('thead'):
                    score += 2
                
                # Has table caption
                if table.find('caption'):
                    score += 1
                
                # Has proper structure
                if table.find('tbody') or table.find('thead'):
                    score += 1
        
        # Check for other structured data elements
        if soup.find_all(['blockquote', 'code', 'pre']):
            score += 2
        
        return min(25, score)
    
    def _evaluate_schema_markup(self, soup: BeautifulSoup) -> float:
        """Evaluate schema.org markup (max 25 points)"""
        score = 0
        
        # Check for JSON-LD structured data
        json_ld_scripts = soup.find_all('script', type='application/ld+json')
        if json_ld_scripts:
            score += 10
            
            # Bonus for multiple schemas
            if len(json_ld_scripts) > 1:
                score += 2
        
        # Check for microdata
        microdata_elements = soup.find_all(attrs={'itemscope': True})
        if microdata_elements:
            score += 5
            
            # Check for itemtype
            typed_elements = soup.find_all(attrs={'itemtype': True})
            if typed_elements:
                score += 3
        
        # Check for RDFa
        rdfa_elements = soup.find_all(attrs={'typeof': True})
        if rdfa_elements:
            score += 3
        
        # Check for meta properties (Open Graph, Twitter Cards)
        og_tags = soup.find_all('meta', attrs={'property': re.compile(r'og:')})
        twitter_tags = soup.find_all('meta', attrs={'name': re.compile(r'twitter:')})
        
        if og_tags:
            score += 3
        if twitter_tags:
            score += 2
        
        return min(25, score)
    
    def _score_to_rating(self, score: float) -> str:
        """Convert numerical score to rating"""
        if score >= 90:
            return "Excellent"
        elif score >= 75:
            return "Good"
        elif score >= 50:
            return "Fair"
        elif score >= 25:
            return "Poor"
        else:
            return "Very Poor"
    
    def get_detailed_analysis(self, html: str) -> Dict:
        """Get detailed structure analysis"""
        if not html:
            return {
                'rating': 'Very Poor',
                'total_score': 0,
                'breakdown': {},
                'recommendations': ['No HTML content to analyze'],
                'elements_found': {}
            }
        
        try:
            soup = BeautifulSoup(html, 'lxml')
            
            # Calculate individual scores
            heading_score = self._evaluate_headings(soup) if self.structured_config.get('check_headings', True) else 0
            semantic_score = self._evaluate_semantic_elements(soup) if self.structured_config.get('check_semantic_elements', True) else 0
            data_score = self._evaluate_data_structures(soup)
            schema_score = self._evaluate_schema_markup(soup) if self.structured_config.get('check_schema_markup', True) else 0
            
            total_score = heading_score + semantic_score + data_score + schema_score
            rating = self._score_to_rating(total_score)
            
            # Find elements
            elements_found = self._catalog_elements(soup)
            
            # Generate recommendations
            recommendations = self._generate_recommendations(soup, {
                'headings': heading_score,
                'semantic': semantic_score,
                'data': data_score,
                'schema': schema_score
            })
            
            return {
                'rating': rating,
                'total_score': round(total_score, 1),
                'breakdown': {
                    'headings': {'score': heading_score, 'max': 25},
                    'semantic_elements': {'score': semantic_score, 'max': 25},
                    'data_structures': {'score': data_score, 'max': 25},
                    'schema_markup': {'score': schema_score, 'max': 25}
                },
                'recommendations': recommendations,
                'elements_found': elements_found
            }
            
        except Exception as e:
            return {
                'rating': 'Poor',
                'total_score': 0,
                'breakdown': {},
                'recommendations': [f'Error analyzing structure: {str(e)}'],
                'elements_found': {}
            }
    
    def _catalog_elements(self, soup: BeautifulSoup) -> Dict:
        """Catalog found structural elements"""
        elements = {
            'headings': {},
            'semantic': [],
            'lists': 0,
            'tables': 0,
            'schema_types': []
        }
        
        # Catalog headings
        for level in range(1, 7):
            count = len(soup.find_all(f'h{level}'))
            if count > 0:
                elements['headings'][f'h{level}'] = count
        
        # Catalog semantic elements
        semantic_tags = ['main', 'article', 'section', 'header', 'footer', 'nav', 'aside', 'figure']
        for tag in semantic_tags:
            if soup.find(tag):
                elements['semantic'].append(tag)
        
        # Count lists and tables
        elements['lists'] = len(soup.find_all(['ul', 'ol', 'dl']))
        elements['tables'] = len(soup.find_all('table'))
        
        # Find schema types
        schema_elements = soup.find_all(attrs={'itemtype': True})
        for elem in schema_elements:
            itemtype = elem.get('itemtype', '')
            if itemtype:
                elements['schema_types'].append(itemtype)
        
        return elements
    
    def _generate_recommendations(self, soup: BeautifulSoup, scores: Dict) -> List[str]:
        """Generate improvement recommendations"""
        recommendations = []
        
        # Heading recommendations
        if scores['headings'] < 15:
            h1_count = len(soup.find_all('h1'))
            if h1_count == 0:
                recommendations.append("Add a single H1 tag for the main page title")
            elif h1_count > 1:
                recommendations.append("Use only one H1 tag per page")
            
            if len(soup.find_all(['h2', 'h3', 'h4', 'h5', 'h6'])) == 0:
                recommendations.append("Add hierarchical headings (H2, H3, etc.) to structure content")
        
        # Semantic element recommendations
        if scores['semantic'] < 15:
            if not soup.find('main'):
                recommendations.append("Add a <main> element to identify the primary content area")
            if not soup.find('article'):
                recommendations.append("Use <article> elements for standalone content pieces")
            if not soup.find('section'):
                recommendations.append("Use <section> elements to group related content")
        
        # Data structure recommendations
        if scores['data'] < 15:
            if not soup.find_all(['ul', 'ol']):
                recommendations.append("Use lists (<ul>, <ol>) to structure related items")
            if soup.find_all('table') and not soup.find('th'):
                recommendations.append("Add table headers (<th>) to improve table accessibility")
        
        # Schema recommendations
        if scores['schema'] < 15:
            recommendations.append("Add structured data markup (JSON-LD) to help search engines understand content")
            if not soup.find_all('meta', attrs={'property': re.compile(r'og:')}):
                recommendations.append("Add Open Graph meta tags for better social media sharing")
        
        return recommendations
    
    async def generate_enhanced_recommendations(self, html: str, rating: str) -> List[Dict]:
        """Generate detailed, actionable recommendations for structural improvements"""
        recommendations = []
        
        if not html:
            return [{
                "priority": "critical",
                "category": "no_content",
                "issue": "No HTML content provided for analysis",
                "impact": "Cannot assess structural quality",
                "action": "Provide valid HTML content for evaluation"
            }]
        
        detailed_analysis = self.get_detailed_analysis(html)
        scores = detailed_analysis.get('breakdown', {})
        elements_found = detailed_analysis.get('elements_found', {})
        
        # Critical issues (Very Poor, Poor ratings)
        if rating in ["Very Poor", "Poor"]:
            recommendations.append({
                "priority": "critical",
                "category": "structural_foundation",
                "issue": f"HTML structure rated as {rating} - fundamental structural issues",
                "impact": "10% weight metric - poor LLM understanding and SEO impact",
                "action": "Implement comprehensive structural improvements",
                "specifics": {
                    "current_rating": rating,
                    "total_score": detailed_analysis.get('total_score', 0),
                    "max_possible": 100,
                    "improvement_needed": f"{100 - detailed_analysis.get('total_score', 0):.0f} points"
                },
                "implementation": {
                    "effort": "high",
                    "timeline": "1-2 weeks",
                    "phases": [
                        "Phase 1: Fix heading structure (Week 1)",
                        "Phase 2: Add semantic elements (Week 1-2)",
                        "Phase 3: Implement schema markup (Week 2)"
                    ]
                }
            })
        
        # Heading structure issues
        heading_score = scores.get('headings', {}).get('score', 0)
        if heading_score < 15:
            soup = BeautifulSoup(html, 'lxml')
            h1_count = len(soup.find_all('h1'))
            total_headings = len(soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6']))
            
            priority = "critical" if heading_score < 5 else "high"
            recommendations.append({
                "priority": priority,
                "category": "heading_structure",
                "issue": f"Poor heading structure (score: {heading_score}/25)",
                "impact": "Reduced content hierarchy understanding for both users and LLMs",
                "action": "Implement proper heading hierarchy",
                "specifics": {
                    "h1_count": h1_count,
                    "total_headings": total_headings,
                    "current_score": heading_score,
                    "target_score": "20+",
                    "heading_distribution": elements_found.get('headings', {})
                },
                "implementation": {
                    "effort": "low",
                    "timeline": "1-2 days",
                    "steps": [
                        "Add exactly one H1 tag for the main page title" if h1_count != 1 else "Maintain single H1 structure",
                        "Create logical heading hierarchy (H1 → H2 → H3)",
                        "Ensure headings describe content sections clearly",
                        "Use 3-10 words per heading for optimal length",
                        "Avoid skipping heading levels (e.g., H1 directly to H3)"
                    ],
                    "specific_fixes": [
                        f"Current H1 count: {h1_count} (should be 1)",
                        f"Add {max(0, 3 - len(soup.find_all(['h2', 'h3'])))} more subheadings",
                        "Review heading content for descriptiveness"
                    ]
                }
            })
        
        # Semantic elements issues
        semantic_score = scores.get('semantic_elements', {}).get('score', 0)
        if semantic_score < 15:
            soup = BeautifulSoup(html, 'lxml')
            missing_elements = []
            critical_missing = []
            
            if not soup.find('main'):
                critical_missing.append('main')
            if not soup.find('header'):
                missing_elements.append('header')
            if not soup.find('nav'):
                missing_elements.append('nav')
            if not soup.find('article'):
                missing_elements.append('article')
            if not soup.find('section'):
                missing_elements.append('section')
            
            recommendations.append({
                "priority": "high" if critical_missing else "medium",
                "category": "semantic_markup",
                "issue": f"Insufficient semantic HTML elements (score: {semantic_score}/25)",
                "impact": "Poor content structure recognition by search engines and screen readers",
                "action": "Add semantic HTML5 elements to improve content structure",
                "specifics": {
                    "current_score": semantic_score,
                    "target_score": "20+",
                    "critical_missing": critical_missing,
                    "missing_elements": missing_elements,
                    "found_elements": elements_found.get('semantic', [])
                },
                "implementation": {
                    "effort": "medium",
                    "timeline": "2-3 days",
                    "priority_order": [
                        "<main> - Wrap primary content (highest priority)",
                        "<header> - Page/section headers",
                        "<nav> - Navigation areas",
                        "<article> - Standalone content pieces",
                        "<section> - Thematic content groups",
                        "<aside> - Sidebar/supplementary content",
                        "<footer> - Page/section footers"
                    ],
                    "implementation_guide": {
                        "main": "Wrap the primary content area with <main>",
                        "header": "Use for page header, logo, and primary navigation",
                        "nav": "Wrap navigation menus and breadcrumbs",
                        "article": "Use for blog posts, news articles, or standalone content",
                        "section": "Group related content with thematic headings"
                    }
                }
            })
        
        # Data structures issues
        data_score = scores.get('data_structures', {}).get('score', 0)
        if data_score < 15:
            soup = BeautifulSoup(html, 'lxml')
            has_lists = len(soup.find_all(['ul', 'ol', 'dl'])) > 0
            has_tables = len(soup.find_all('table')) > 0
            
            recommendations.append({
                "priority": "medium",
                "category": "data_organization",
                "issue": f"Poor data structure organization (score: {data_score}/25)",
                "impact": "Missed opportunities for better content organization and comprehension",
                "action": "Implement appropriate data structures for content organization",
                "specifics": {
                    "current_score": data_score,
                    "target_score": "18+",
                    "has_lists": has_lists,
                    "has_tables": has_tables,
                    "list_count": elements_found.get('lists', 0),
                    "table_count": elements_found.get('tables', 0)
                },
                "implementation": {
                    "effort": "low",
                    "timeline": "1-2 days",
                    "opportunities": [
                        "Convert related items to bulleted lists (<ul>)",
                        "Use numbered lists (<ol>) for sequential steps",
                        "Implement tables for comparative data",
                        "Add table headers (<th>) for accessibility",
                        "Use definition lists (<dl>) for term-definition pairs"
                    ],
                    "specific_actions": [
                        "Identify content that would benefit from list structure",
                        "Add table captions for better accessibility",
                        "Ensure tables have proper header structure",
                        "Consider using <blockquote> for quotations"
                    ]
                }
            })
        
        # Schema markup issues
        schema_score = scores.get('schema_markup', {}).get('score', 0)
        if schema_score < 15:
            soup = BeautifulSoup(html, 'lxml')
            has_json_ld = len(soup.find_all('script', type='application/ld+json')) > 0
            has_og_tags = len(soup.find_all('meta', attrs={'property': re.compile(r'og:')})) > 0
            
            priority = "high" if schema_score < 5 else "medium"
            recommendations.append({
                "priority": priority,
                "category": "structured_data",
                "issue": f"Missing or insufficient structured data markup (score: {schema_score}/25)",
                "impact": "Poor search engine understanding and reduced rich snippet opportunities",
                "action": "Implement comprehensive structured data markup",
                "specifics": {
                    "current_score": schema_score,
                    "target_score": "18+",
                    "has_json_ld": has_json_ld,
                    "has_open_graph": has_og_tags,
                    "schema_types_found": elements_found.get('schema_types', [])
                },
                "implementation": {
                    "effort": "medium",
                    "timeline": "3-5 days",
                    "priority_implementations": [
                        "JSON-LD structured data (highest impact)",
                        "Open Graph meta tags for social sharing",
                        "Twitter Card meta tags",
                        "Basic microdata markup"
                    ],
                    "schema_types_to_implement": [
                        "Organization - Company/business information",
                        "Website - Website metadata",
                        "Article - Content pieces",
                        "BreadcrumbList - Navigation hierarchy",
                        "ContactPoint - Contact information"
                    ],
                    "code_examples": {
                        "basic_organization": "Add JSON-LD script with Organization schema",
                        "open_graph": "Add og:title, og:description, og:image meta tags",
                        "twitter_cards": "Add twitter:card, twitter:title meta tags"
                    }
                }
            })
        
        # Optimization recommendations for good structures
        if rating in ["Good", "Excellent"]:
            recommendations.append({
                "priority": "low",
                "category": "structural_optimization",
                "issue": "Good structural foundation with optimization opportunities",
                "impact": "Fine-tuning can improve LLM understanding and user experience",
                "action": "Optimize existing structure for maximum effectiveness",
                "implementation": {
                    "effort": "low",
                    "timeline": "1-2 days",
                    "optimizations": [
                        "Review heading hierarchy for logical flow",
                        "Add missing alt attributes to images",
                        "Ensure all forms have proper labels",
                        "Add ARIA landmarks where beneficial",
                        "Validate HTML for any syntax errors"
                    ]
                }
            })
        
        return recommendations