"""Output generation for rules evaluation results"""

import logging
from typing import Dict, Any, List
from pathlib import Path
from datetime import datetime
import json
import html as html_module

logger = logging.getLogger(__name__)


class OutputGenerator:
    """Generate various output formats for evaluation results"""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize output generator
        
        Args:
            config: Output configuration
        """
        self.config = config
        self.results_dir = Path(config.get('results_dir', './results'))
        self.generate_html = config.get('generate_html_report', True)
        self.generate_markdown = config.get('generate_markdown_report', True)
        self.generate_dashboard_json = config.get('generate_dashboard_json', True)
        self.log_responses = config.get('log_responses', True)
    
    def generate_all_outputs(self, results: Dict[str, Any], timestamp: str) -> Dict[str, Path]:
        """Generate all configured output formats
        
        Args:
            results: Evaluation results
            timestamp: Timestamp for directory naming
            
        Returns:
            Dictionary of output type to file path
        """
        # Create timestamped directory
        output_dir = self.results_dir / timestamp
        output_dir.mkdir(parents=True, exist_ok=True)
        
        generated_files = {}
        
        # Generate JSON results
        json_file = output_dir / 'evaluation_results.json'
        with open(json_file, 'w') as f:
            json.dump(results, f, indent=2)
        generated_files['json'] = json_file
        
        # Generate markdown report
        if self.generate_markdown:
            md_file = output_dir / 'evaluation_summary.md'
            with open(md_file, 'w') as f:
                f.write(self._generate_markdown_report(results))
            generated_files['markdown'] = md_file
        
        # Generate HTML report
        if self.generate_html:
            html_file = output_dir / 'evaluation_report.html'
            with open(html_file, 'w') as f:
                f.write(self._generate_html_report(results))
            generated_files['html'] = html_file
        
        # Generate dashboard JSON
        if self.generate_dashboard_json:
            dashboard_file = output_dir / 'dashboard-data.json'
            dashboard_data = self._generate_dashboard_data(results)
            with open(dashboard_file, 'w') as f:
                json.dump(dashboard_data, f, indent=2)
            generated_files['dashboard'] = dashboard_file
        
        # Log AI responses
        if self.log_responses:
            log_file = output_dir / self.config.get('response_log_file', 'ai_responses.log')
            self._log_ai_responses(results, log_file)
            generated_files['responses_log'] = log_file
        
        logger.info(f"Generated {len(generated_files)} output files in {output_dir}")
        return generated_files
    
    def _generate_markdown_report(self, results: Dict[str, Any]) -> str:
        """Generate detailed markdown report"""
        overall = results['overall_results']
        
        report = f"""# Rules Evaluation Report

**Evaluation ID:** {results['evaluation_id']}  
**Date:** {results['timestamp'][:19].replace('T', ' ')}  
**Duration:** {results['duration_seconds']:.1f} seconds  
**Rules File:** {results['rules_file']}  
**Content Source:** {results['content_source']}  

## Executive Summary

The evaluation processed **{overall['total_prompts']} prompts** with an overall pass rate of **{overall['overall_pass_rate']}%**. The average score across all prompts was **{overall['average_score']}/100**.

{'✅ **EVALUATION PASSED**' if overall['overall_pass_rate'] >= results['config']['passing_score'] else '❌ **EVALUATION FAILED**'}

## Key Metrics

| Metric | Value |
|--------|-------|
| Total Prompts | {overall['total_prompts']} |
| Prompts Passed | {overall['prompts_passed']} |
| Prompts Failed | {overall['prompts_failed']} |
| Average Score | {overall['average_score']}/100 |
| Critical Failures | {overall['critical_failures']} |

## Performance by Rule Type

"""
        
        for rule_type, pass_rate in overall['pass_rates_by_type'].items():
            counts = overall['total_rules_by_type'][rule_type]
            if counts['total'] > 0:
                report += f"- **{rule_type.title()}:** {counts['passed']}/{counts['total']} ({pass_rate}%)\n"
        
        report += f"""

## Content Analysis

- **Total Documents Processed:** {results['database_stats']['total_documents']}
- **Total Text Chunks:** {results['database_stats']['total_chunks']}
- **Embedding Model:** {results['database_stats']['embedding_model']}
- **Sources:** {', '.join(results['database_stats']['sources'].keys())}

## Configuration

- **Passing Score Threshold:** {results['config']['passing_score']}%
- **Rule Type Weights:**
  - Important: {results['config']['weights']['important']}%
  - Expected: {results['config']['weights']['expected']}%
  - Desirable: {results['config']['weights']['desirable']}%
- **AI Providers:**
  - Response Generation: {results['config']['ai_providers']['response']}
  - Evaluation: {results['config']['ai_providers']['evaluation']}

## Detailed Results

"""
        
        for i, prompt_result in enumerate(results['prompt_evaluations']):
            status = "✅ PASSED" if prompt_result['passed'] else "❌ FAILED"
            if prompt_result['critical_failed']:
                status += " (Critical Rule Failed)"
            
            report += f"""
### Prompt {i+1}: {status}

**Prompt:** {prompt_result['prompt']}  
**Score:** {prompt_result['score']}/100  
**Rules Passed:** {prompt_result['rules_summary']['rules_passed']}/{prompt_result['rules_summary']['total_rules']}  

**AI Response Summary:** {prompt_result['summary']}

#### Rule-by-Rule Analysis

"""
            
            for rule_eval in prompt_result['rules_evaluation']:
                rule_status = "✅" if rule_eval['satisfied'] else "❌"
                report += f"- {rule_status} **{rule_eval['type'].title()}:** {rule_eval['rule']} ({rule_eval['score_percentage']}%)\n"
                if rule_eval.get('reasoning'):
                    report += f"  - *{rule_eval['reasoning']}*\n"
            
            report += "\n---\n"
        
        report += f"""

## Recommendations

Based on the evaluation results, here are key recommendations for improvement:

"""
        
        # Generate recommendations based on failed rules
        failed_rules_by_type = {}
        for prompt_result in results['prompt_evaluations']:
            for rule_eval in prompt_result['rules_evaluation']:
                if not rule_eval['satisfied']:
                    rule_type = rule_eval['type']
                    if rule_type not in failed_rules_by_type:
                        failed_rules_by_type[rule_type] = []
                    failed_rules_by_type[rule_type].append(rule_eval['rule'])
        
        if failed_rules_by_type:
            for rule_type, failed_rules in failed_rules_by_type.items():
                unique_rules = list(set(failed_rules))
                report += f"### {rule_type.title()} Rules Needing Attention\n\n"
                for rule in unique_rules:
                    report += f"- {rule}\n"
                report += "\n"
        else:
            report += "✅ All rules are being satisfied effectively. Consider reviewing rules for potential updates or additions.\n"
        
        return report
    
    def _generate_html_report(self, results: Dict[str, Any]) -> str:
        """Generate HTML report with styling"""
        overall = results['overall_results']
        
        # Determine overall status
        passed = overall['overall_pass_rate'] >= results['config']['passing_score']
        status_class = "success" if passed else "failure"
        status_text = "PASSED" if passed else "FAILED"
        
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Rules Evaluation Report - {results['evaluation_id']}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f8f9fa;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 30px;
            text-align: center;
        }}
        .header h1 {{
            margin: 0 0 10px 0;
            font-size: 2.5em;
        }}
        .status {{
            font-size: 1.5em;
            font-weight: bold;
            padding: 10px 20px;
            border-radius: 25px;
            display: inline-block;
            margin-top: 15px;
        }}
        .status.success {{
            background-color: #28a745;
            color: white;
        }}
        .status.failure {{
            background-color: #dc3545;
            color: white;
        }}
        .section {{
            background: white;
            padding: 25px;
            margin-bottom: 25px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }}
        .metric-card {{
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
            color: white;
            padding: 20px;
            border-radius: 10px;
            text-align: center;
        }}
        .metric-value {{
            font-size: 2em;
            font-weight: bold;
            margin-bottom: 5px;
        }}
        .metric-label {{
            font-size: 0.9em;
            opacity: 0.9;
        }}
        .prompt-result {{
            border: 1px solid #ddd;
            border-radius: 8px;
            margin-bottom: 20px;
            overflow: hidden;
        }}
        .prompt-header {{
            padding: 15px 20px;
            font-weight: bold;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .prompt-header.passed {{
            background-color: #d4edda;
            color: #155724;
            border-bottom: 1px solid #c3e6cb;
        }}
        .prompt-header.failed {{
            background-color: #f8d7da;
            color: #721c24;
            border-bottom: 1px solid #f5c6cb;
        }}
        .prompt-body {{
            padding: 20px;
        }}
        .rule-item {{
            display: flex;
            align-items: center;
            padding: 8px 0;
            border-bottom: 1px solid #eee;
        }}
        .rule-item:last-child {{
            border-bottom: none;
        }}
        .rule-status {{
            margin-right: 10px;
            font-size: 1.2em;
        }}
        .rule-type {{
            font-weight: bold;
            margin-right: 10px;
            padding: 2px 8px;
            border-radius: 12px;
            font-size: 0.8em;
        }}
        .rule-type.critical {{
            background-color: #dc3545;
            color: white;
        }}
        .rule-type.important {{
            background-color: #fd7e14;
            color: white;
        }}
        .rule-type.expected {{
            background-color: #20c997;
            color: white;
        }}
        .rule-type.desirable {{
            background-color: #6f42c1;
            color: white;
        }}
        .score-badge {{
            background-color: #007bff;
            color: white;
            padding: 5px 10px;
            border-radius: 15px;
            font-weight: bold;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 15px;
        }}
        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }}
        th {{
            background-color: #f8f9fa;
            font-weight: bold;
        }}
        .progress-bar {{
            background-color: #e9ecef;
            border-radius: 10px;
            height: 20px;
            margin: 10px 0;
            overflow: hidden;
        }}
        .progress-fill {{
            height: 100%;
            background: linear-gradient(90deg, #28a745, #20c997);
            transition: width 0.3s ease;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Rules Evaluation Report</h1>
        <div class="meta">
            <strong>{results['evaluation_id']}</strong><br>
            {results['timestamp'][:19].replace('T', ' ')} | Duration: {results['duration_seconds']:.1f}s
        </div>
        <div class="status {status_class}">{status_text}</div>
    </div>

    <div class="section">
        <h2>Overall Results</h2>
        <div class="metrics-grid">
            <div class="metric-card">
                <div class="metric-value">{overall['total_prompts']}</div>
                <div class="metric-label">Total Prompts</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">{overall['prompts_passed']}</div>
                <div class="metric-label">Prompts Passed</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">{overall['overall_pass_rate']}%</div>
                <div class="metric-label">Pass Rate</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">{overall['average_score']}</div>
                <div class="metric-label">Average Score</div>
            </div>
        </div>
        
        <div class="progress-bar">
            <div class="progress-fill" style="width: {overall['overall_pass_rate']}%"></div>
        </div>
    </div>

    <div class="section">
        <h2>Performance by Rule Type</h2>
        <table>
            <thead>
                <tr>
                    <th>Rule Type</th>
                    <th>Passed</th>
                    <th>Total</th>
                    <th>Pass Rate</th>
                </tr>
            </thead>
            <tbody>
"""
        
        for rule_type, pass_rate in overall['pass_rates_by_type'].items():
            counts = overall['total_rules_by_type'][rule_type]
            if counts['total'] > 0:
                html += f"""
                <tr>
                    <td><span class="rule-type {rule_type}">{rule_type.title()}</span></td>
                    <td>{counts['passed']}</td>
                    <td>{counts['total']}</td>
                    <td>{pass_rate}%</td>
                </tr>
"""
        
        html += """
            </tbody>
        </table>
    </div>

    <div class="section">
        <h2>Individual Prompt Results</h2>
"""
        
        for i, prompt_result in enumerate(results['prompt_evaluations']):
            status_class = "passed" if prompt_result['passed'] else "failed"
            status_text = "✅ PASSED" if prompt_result['passed'] else "❌ FAILED"
            
            if prompt_result['critical_failed']:
                status_text += " (Critical)"
            
            html += f"""
        <div class="prompt-result">
            <div class="prompt-header {status_class}">
                <span>Prompt {i+1}: {html_module.escape(prompt_result['prompt'][:100])}{'...' if len(prompt_result['prompt']) > 100 else ''}</span>
                <div>
                    {status_text}
                    <span class="score-badge">{prompt_result['score']}/100</span>
                </div>
            </div>
            <div class="prompt-body">
                <p><strong>Summary:</strong> {html_module.escape(prompt_result['summary'])}</p>
                <h4>Rule Evaluation:</h4>
"""
            
            for rule_eval in prompt_result['rules_evaluation']:
                rule_status = "✅" if rule_eval['satisfied'] else "❌"
                html += f"""
                <div class="rule-item">
                    <span class="rule-status">{rule_status}</span>
                    <span class="rule-type {rule_eval['type']}">{rule_eval['type'].upper()}</span>
                    <span>{html_module.escape(rule_eval['rule'])} ({rule_eval['score_percentage']}%)</span>
                </div>
"""
            
            html += """
            </div>
        </div>
"""
        
        html += f"""
    </div>

    <div class="section">
        <h2>Technical Details</h2>
        <table>
            <tr><td><strong>Content Source</strong></td><td>{results['content_source']}</td></tr>
            <tr><td><strong>Documents Processed</strong></td><td>{results['database_stats']['total_documents']}</td></tr>
            <tr><td><strong>Text Chunks</strong></td><td>{results['database_stats']['total_chunks']}</td></tr>
            <tr><td><strong>Embedding Model</strong></td><td>{results['database_stats']['embedding_model']}</td></tr>
            <tr><td><strong>Response Provider</strong></td><td>{results['config']['ai_providers']['response']}</td></tr>
            <tr><td><strong>Evaluation Provider</strong></td><td>{results['config']['ai_providers']['evaluation']}</td></tr>
        </table>
    </div>

    <script>
        // Add smooth scrolling
        document.querySelectorAll('a[href^="#"]').forEach(anchor => {{
            anchor.addEventListener('click', function (e) {{
                e.preventDefault();
                document.querySelector(this.getAttribute('href')).scrollIntoView({{
                    behavior: 'smooth'
                }});
            }});
        }});
    </script>
</body>
</html>
"""
        
        return html
    
    def _generate_dashboard_data(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate dashboard-compatible data format"""
        overall = results['overall_results']
        
        # Build recommendations
        recommendations = []
        
        # Analyze failed rules
        failed_rules_by_type = {}
        for prompt_result in results['prompt_evaluations']:
            for rule_eval in prompt_result['rules_evaluation']:
                if not rule_eval['satisfied']:
                    rule_type = rule_eval['type']
                    if rule_type not in failed_rules_by_type:
                        failed_rules_by_type[rule_type] = 0
                    failed_rules_by_type[rule_type] += 1
        
        # Generate recommendations based on failures
        if overall['critical_failures'] > 0:
            recommendations.append({
                "priority": "high",
                "title": "Address Critical Rule Failures",
                "description": f"{overall['critical_failures']} prompts failed due to critical rules not being met. These must be addressed immediately.",
                "action": "Review content to ensure critical requirements are consistently met"
            })
        
        for rule_type, pass_rate in overall['pass_rates_by_type'].items():
            if pass_rate < 70 and overall['total_rules_by_type'][rule_type]['total'] > 0:
                priority = "high" if rule_type == "important" else "medium"
                recommendations.append({
                    "priority": priority,
                    "title": f"Improve {rule_type.title()} Rule Performance",
                    "description": f"Only {pass_rate}% of {rule_type} rules are being satisfied.",
                    "action": f"Focus on improving content that addresses {rule_type} requirements"
                })
        
        if overall['average_score'] < results['config']['passing_score']:
            recommendations.append({
                "priority": "medium",
                "title": "Raise Overall Score",
                "description": f"Average score of {overall['average_score']} is below passing threshold of {results['config']['passing_score']}.",
                "action": "Review and improve content quality across all rule types"
            })
        
        if not recommendations:
            recommendations.append({
                "priority": "low",
                "title": "Maintain Quality Standards",
                "description": "All evaluations are performing well. Continue monitoring for consistency.",
                "action": "Regular evaluation runs to ensure continued compliance"
            })
        
        # Build prompt details for dashboard
        prompt_details = []
        for i, prompt_result in enumerate(results['prompt_evaluations']):
            prompt_details.append({
                "prompt_number": i + 1,
                "prompt_text": prompt_result['prompt'],
                "score": prompt_result['score'],
                "passed": prompt_result['passed'],
                "critical_failed": prompt_result['critical_failed'],
                "rules_passed": prompt_result['rules_summary']['rules_passed'],
                "total_rules": prompt_result['rules_summary']['total_rules'],
                "summary": prompt_result['summary']
            })
        
        return {
            "tool": "rulesevaluator",
            "timestamp": results['timestamp'],
            "summary": {
                "total_prompts": overall['total_prompts'],
                "prompts_passed": overall['prompts_passed'],
                "overall_pass_rate": overall['overall_pass_rate'],
                "average_score": overall['average_score'],
                "critical_failures": overall['critical_failures'],
                "evaluation_passed": overall['average_score'] >= results['config']['passing_score']
            },
            "metrics": {
                "pass_rates_by_type": overall['pass_rates_by_type'],
                "total_rules_by_type": overall['total_rules_by_type'],
                "database_stats": results['database_stats'],
                "config": results['config']
            },
            "recommendations": recommendations,
            "data": {
                "prompt_evaluations": prompt_details,
                "evaluation_id": results['evaluation_id'],
                "rules_file": results['rules_file'],
                "content_source": results['content_source'],
                "duration_seconds": results['duration_seconds']
            }
        }
    
    def _log_ai_responses(self, results: Dict[str, Any], log_file: Path) -> None:
        """Log detailed AI responses to file"""
        with open(log_file, 'w', encoding='utf-8') as f:
            f.write(f"AI Responses Log - {results['evaluation_id']}\n")
            f.write(f"Generated: {results['timestamp']}\n")
            f.write("=" * 80 + "\n\n")
            
            for i, prompt_result in enumerate(results['prompt_evaluations']):
                f.write(f"PROMPT {i+1}\n")
                f.write("-" * 40 + "\n")
                f.write(f"Prompt: {prompt_result['prompt']}\n\n")
                
                f.write("CONTEXT USED:\n")
                f.write(prompt_result['context_used'] + "\n\n")
                
                f.write("AI RESPONSE:\n")
                f.write(prompt_result['ai_response'] + "\n\n")
                
                f.write("EVALUATION RESULTS:\n")
                f.write(f"Score: {prompt_result['score']}/100\n")
                f.write(f"Passed: {prompt_result['passed']}\n")
                f.write(f"Critical Failed: {prompt_result['critical_failed']}\n")
                f.write(f"Summary: {prompt_result['summary']}\n\n")
                
                f.write("RULE BREAKDOWN:\n")
                for rule_eval in prompt_result['rules_evaluation']:
                    status = "PASS" if rule_eval['satisfied'] else "FAIL"
                    f.write(f"  [{status}] {rule_eval['type'].upper()}: {rule_eval['rule']}\n")
                    f.write(f"         Score: {rule_eval['score_percentage']}%\n")
                    if rule_eval.get('reasoning'):
                        f.write(f"         Reason: {rule_eval['reasoning']}\n")
                    f.write("\n")
                
                f.write("=" * 80 + "\n\n")