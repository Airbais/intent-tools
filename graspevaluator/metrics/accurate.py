"""
Accurate metric evaluator - Content freshness assessment
"""

import re
from datetime import datetime, timedelta
from typing import Optional, Dict, List
from bs4 import BeautifulSoup
import requests


class AccurateEvaluator:
    """Evaluate content accuracy through freshness assessment"""
    
    def __init__(self, config):
        self.config = config
        self.freshness_thresholds = config.get_freshness_thresholds()
    
    def evaluate(self, html: str, url: str) -> str:
        """
        Evaluate content accuracy through freshness
        
        Args:
            html: HTML content to analyze
            url: URL of the content
            
        Returns:
            str: Accuracy rating ('High', 'Medium', 'Low')
        """
        last_modified = self._find_last_modified_date(html, url)
        
        if not last_modified:
            return "Low"  # No date found
        
        # Calculate age in days
        age_days = (datetime.now() - last_modified).days
        
        # Determine rating based on thresholds
        if age_days <= self.freshness_thresholds['high']:
            return "High"
        elif age_days <= self.freshness_thresholds['medium']:
            return "Medium"
        else:
            return "Low"
    
    def _find_last_modified_date(self, html: str, url: str) -> Optional[datetime]:
        """Find the last modified date from multiple sources"""
        # Try different methods in order of reliability
        
        # 1. Check meta tags
        date = self._check_meta_tags(html)
        if date:
            return date
        
        # 2. Check schema.org markup
        date = self._check_schema_org(html)
        if date:
            return date
        
        # 3. Check time elements
        date = self._check_time_elements(html)
        if date:
            return date
        
        # 4. Check for date patterns in content
        date = self._check_content_dates(html)
        if date:
            return date
        
        # 5. Check HTTP headers (if possible)
        date = self._check_http_headers(url)
        if date:
            return date
        
        return None
    
    def _check_meta_tags(self, html: str) -> Optional[datetime]:
        """Check meta tags for last modified date"""
        try:
            soup = BeautifulSoup(html, 'lxml')
            
            # Common meta tag patterns
            meta_patterns = [
                {'name': 'last-modified'},
                {'name': 'date'},
                {'name': 'revised'},
                {'name': 'updated'},
                {'property': 'article:modified_time'},
                {'property': 'article:published_time'},
                {'name': 'article:modified_time'},
                {'name': 'article:published_time'},
                {'name': 'DC.Date.Modified'},
                {'name': 'dc.date.modified'},
                {'name': 'dcterms.modified'},
                {'name': 'pubdate'}
            ]
            
            for pattern in meta_patterns:
                meta_tag = soup.find('meta', attrs=pattern)
                if meta_tag and meta_tag.get('content'):
                    date = self._parse_date_string(meta_tag['content'])
                    if date:
                        return date
            
            return None
            
        except Exception:
            return None
    
    def _check_schema_org(self, html: str) -> Optional[datetime]:
        """Check schema.org markup for dates"""
        try:
            soup = BeautifulSoup(html, 'lxml')
            
            # Look for schema.org date properties
            schema_patterns = [
                {'itemprop': 'dateModified'},
                {'itemprop': 'datePublished'},
                {'itemprop': 'dateCreated'},
                {'itemprop': 'lastReviewed'},
                {'property': 'dateModified'},
                {'property': 'datePublished'}
            ]
            
            for pattern in schema_patterns:
                elements = soup.find_all(attrs=pattern)
                for element in elements:
                    # Check content attribute first
                    if element.get('content'):
                        date = self._parse_date_string(element['content'])
                        if date:
                            return date
                    
                    # Check datetime attribute
                    if element.get('datetime'):
                        date = self._parse_date_string(element['datetime'])
                        if date:
                            return date
                    
                    # Check element text
                    if element.get_text(strip=True):
                        date = self._parse_date_string(element.get_text(strip=True))
                        if date:
                            return date
            
            return None
            
        except Exception:
            return None
    
    def _check_time_elements(self, html: str) -> Optional[datetime]:
        """Check HTML time elements"""
        try:
            soup = BeautifulSoup(html, 'lxml')
            
            # Find all time elements
            time_elements = soup.find_all('time')
            
            latest_date = None
            
            for time_elem in time_elements:
                # Check datetime attribute
                if time_elem.get('datetime'):
                    date = self._parse_date_string(time_elem['datetime'])
                    if date and (not latest_date or date > latest_date):
                        latest_date = date
                
                # Check element text
                text = time_elem.get_text(strip=True)
                if text:
                    date = self._parse_date_string(text)
                    if date and (not latest_date or date > latest_date):
                        latest_date = date
            
            return latest_date
            
        except Exception:
            return None
    
    def _check_content_dates(self, html: str) -> Optional[datetime]:
        """Check for date patterns in content"""
        try:
            soup = BeautifulSoup(html, 'lxml')
            text = soup.get_text()
            
            # Look for common date patterns
            date_patterns = [
                r'Updated:?\s*([A-Za-z]+ \d{1,2},?\s*\d{4})',
                r'Last updated:?\s*([A-Za-z]+ \d{1,2},?\s*\d{4})',
                r'Modified:?\s*([A-Za-z]+ \d{1,2},?\s*\d{4})',
                r'Published:?\s*([A-Za-z]+ \d{1,2},?\s*\d{4})',
                r'(\d{1,2}/\d{1,2}/\d{4})',
                r'(\d{4}-\d{2}-\d{2})',
                r'([A-Za-z]+ \d{1,2},? \d{4})'
            ]
            
            latest_date = None
            
            for pattern in date_patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                for match in matches:
                    date = self._parse_date_string(match)
                    if date and (not latest_date or date > latest_date):
                        latest_date = date
            
            return latest_date
            
        except Exception:
            return None
    
    def _check_http_headers(self, url: str) -> Optional[datetime]:
        """Check HTTP headers for last modified date"""
        try:
            response = requests.head(url, timeout=10)
            
            # Check Last-Modified header
            last_modified = response.headers.get('Last-Modified')
            if last_modified:
                return self._parse_date_string(last_modified)
            
            # Check Date header as fallback
            date_header = response.headers.get('Date')
            if date_header:
                return self._parse_date_string(date_header)
            
            return None
            
        except Exception:
            return None
    
    def _parse_date_string(self, date_str: str) -> Optional[datetime]:
        """Parse various date string formats"""
        if not date_str:
            return None
        
        date_str = date_str.strip()
        
        # Common date formats to try
        formats = [
            '%Y-%m-%d',
            '%Y-%m-%dT%H:%M:%S',
            '%Y-%m-%dT%H:%M:%SZ',
            '%Y-%m-%dT%H:%M:%S.%fZ',
            '%Y-%m-%d %H:%M:%S',
            '%d/%m/%Y',
            '%m/%d/%Y',
            '%B %d, %Y',
            '%b %d, %Y',
            '%d %B %Y',
            '%d %b %Y',
            '%a, %d %b %Y %H:%M:%S GMT',
            '%a, %d %b %Y %H:%M:%S %Z'
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        
        # Try parsing with dateutil if available
        try:
            from dateutil import parser
            return parser.parse(date_str)
        except (ImportError, ValueError):
            pass
        
        return None
    
    def get_detailed_analysis(self, html: str, url: str) -> Dict:
        """Get detailed freshness analysis"""
        last_modified = self._find_last_modified_date(html, url)
        rating = self.evaluate(html, url)
        
        analysis = {
            'rating': rating,
            'last_modified': last_modified.isoformat() if last_modified else None,
            'age_days': None,
            'sources_found': [],
            'recommendations': []
        }
        
        if last_modified:
            age_days = (datetime.now() - last_modified).days
            analysis['age_days'] = age_days
            
            # Check which sources we found dates in
            sources = []
            if self._check_meta_tags(html):
                sources.append('meta_tags')
            if self._check_schema_org(html):
                sources.append('schema_org')
            if self._check_time_elements(html):
                sources.append('time_elements')
            if self._check_content_dates(html):
                sources.append('content_patterns')
            
            analysis['sources_found'] = sources
            
            # Generate recommendations
            if rating == 'Low':
                analysis['recommendations'].append(
                    "Content is outdated. Consider updating with recent information and refreshing publication dates."
                )
            elif rating == 'Medium':
                analysis['recommendations'].append(
                    "Content is moderately fresh but could benefit from regular updates."
                )
            else:
                analysis['recommendations'].append(
                    "Content freshness is good. Continue maintaining regular updates."
                )
        else:
            analysis['recommendations'].append(
                "No publication or modification date found. Add proper date metadata to improve content freshness signals."
            )
        
        return analysis
    
    async def generate_enhanced_recommendations(self, html: str, url: str, rating: str) -> List[Dict]:
        """Generate detailed, actionable recommendations for content accuracy improvements"""
        recommendations = []
        
        detailed_analysis = self.get_detailed_analysis(html, url)
        last_modified = detailed_analysis.get('last_modified')
        age_days = detailed_analysis.get('age_days')
        sources_found = detailed_analysis.get('sources_found', [])
        
        if rating == "Low":
            if age_days is not None and age_days > 365:
                # Very old content
                recommendations.append({
                    "priority": "critical",
                    "category": "content_freshness",
                    "issue": f"Content is {age_days} days old ({age_days/365:.1f} years) - significantly outdated",
                    "impact": "30% weight metric - major SEO and user trust impact",
                    "action": "Comprehensive content audit and update required",
                    "specifics": {
                        "last_modified": last_modified,
                        "age_days": age_days,
                        "freshness_rating": rating,
                        "threshold_exceeded": f"Exceeds medium threshold by {age_days - self.freshness_thresholds['medium']} days"
                    },
                    "implementation": {
                        "effort": "high",
                        "timeline": "1-2 weeks",
                        "steps": [
                            "Review all content for accuracy and relevance",
                            "Update statistics, dates, and references",
                            "Add new information and remove outdated content",
                            "Update meta tags with current modification date",
                            "Add schema.org dateModified markup"
                        ],
                        "specific_targets": [
                            "Update last-modified date to current",
                            "Review and update all factual claims",
                            "Add recent examples and case studies",
                            "Verify all external links still work"
                        ]
                    }
                })
            elif last_modified is None:
                # No date found
                recommendations.append({
                    "priority": "high",
                    "category": "date_metadata",
                    "issue": "No publication or modification date found - cannot assess content freshness",
                    "impact": "Search engines and users cannot determine content recency",
                    "action": "Add proper date metadata and markup",
                    "specifics": {
                        "sources_checked": ["meta_tags", "schema_org", "time_elements", "content_patterns", "http_headers"],
                        "sources_found": sources_found,
                        "missing_elements": "All date sources missing"
                    },
                    "implementation": {
                        "effort": "low",
                        "timeline": "1-2 days",
                        "steps": [
                            "Add meta tag: <meta name=\"last-modified\" content=\"YYYY-MM-DD\">",
                            "Add schema.org markup: <meta property=\"article:modified_time\" content=\"ISO-date\">",
                            "Include <time> elements with datetime attributes",
                            "Add \"Last updated\" text in content with clear date",
                            "Configure server to send Last-Modified headers"
                        ],
                        "priority_order": [
                            "Meta tags (highest impact)",
                            "Schema.org markup",
                            "Time elements",
                            "Visible date in content"
                        ]
                    }
                })
        
        elif rating == "Medium":
            if age_days is not None:
                recommendations.append({
                    "priority": "medium",
                    "category": "content_refresh",
                    "issue": f"Content is {age_days} days old - approaching staleness threshold",
                    "impact": "Opportunity to improve freshness before it becomes a significant issue",
                    "action": "Schedule regular content updates and add freshness indicators",
                    "specifics": {
                        "current_age": f"{age_days} days",
                        "days_until_low": self.freshness_thresholds['medium'] - age_days if age_days < self.freshness_thresholds['medium'] else 0,
                        "recommended_refresh_frequency": "Every 3-6 months"
                    },
                    "implementation": {
                        "effort": "medium",
                        "timeline": "3-5 days",
                        "steps": [
                            "Review content for any outdated information",
                            "Add recent statistics or examples",
                            "Update modification date after changes",
                            "Set up calendar reminder for next review",
                            "Consider adding \"updated\" badges or timestamps"
                        ]
                    }
                })
        
        else:  # High rating
            recommendations.append({
                "priority": "low",
                "category": "freshness_maintenance",
                "issue": "Content freshness is good but requires ongoing maintenance",
                "impact": "Maintain competitive advantage and user trust",
                "action": "Establish content freshness monitoring and update schedule",
                "implementation": {
                    "effort": "low",
                    "timeline": "Ongoing",
                    "steps": [
                        "Set quarterly content review schedule",
                        "Monitor for industry changes that require updates",
                        "Track content performance metrics",
                        "Update dates when making any content changes"
                    ]
                }
            })
        
        # Metadata enhancement recommendations
        if len(sources_found) < 2:
            recommendations.append({
                "priority": "medium",
                "category": "metadata_enhancement",
                "issue": f"Only {len(sources_found)} date source(s) found - limited freshness signals",
                "impact": "Improved date metadata helps search engines and tools assess content freshness",
                "action": "Add multiple date indicators for better freshness detection",
                "specifics": {
                    "current_sources": sources_found,
                    "missing_sources": [source for source in ["meta_tags", "schema_org", "time_elements"] if source not in sources_found],
                    "recommended_minimum": "2-3 date sources"
                },
                "implementation": {
                    "effort": "low",
                    "timeline": "1 day",
                    "steps": [
                        "Add missing meta tags for last-modified date",
                        "Include schema.org dateModified property",
                        "Add visible time element with datetime attribute",
                        "Ensure consistency across all date sources"
                    ]
                }
            })
        
        # Content update strategy based on age and rating
        if rating in ["Low", "Medium"] and age_days is not None:
            update_frequency = "monthly" if age_days > 180 else "quarterly"
            recommendations.append({
                "priority": "medium",
                "category": "update_strategy",
                "issue": "Content needs regular update schedule to maintain freshness",
                "impact": "Consistent updates improve search rankings and user engagement",
                "action": f"Implement {update_frequency} content review and update process",
                "implementation": {
                    "effort": "medium",
                    "timeline": "Ongoing",
                    "content_areas_to_monitor": [
                        "Statistics and data points",
                        "Industry trends and best practices",
                        "Product features and pricing",
                        "External links and references",
                        "Contact information and team details"
                    ],
                    "automation_suggestions": [
                        "Set up Google Alerts for industry changes",
                        "Create content calendar with review dates",
                        "Use tools to monitor broken links",
                        "Track competitor content updates"
                    ]
                }
            })
        
        return recommendations