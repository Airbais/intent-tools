# How IntentCrawler Discovers What Your Website Tells AI Agents

In the age of AI assistants and LLMs, your website isn't just serving human visitors anymore. AI agents crawl, read, and interpret your content to answer user queries. But what exactly are these agents understanding about your site? What user intents are they extracting? IntentCrawler is a Python tool designed to answer these questions by analyzing websites through the lens of user intent discovery.

## The Problem: Understanding AI's Understanding

When ChatGPT, Claude, or other AI assistants reference your website, they're making decisions about what your users want to accomplish. They're identifying pain points, extracting action sequences, and categorizing user goals. Traditional analytics tell you what pages users visit, but they don't reveal what AI agents think those users are trying to achieve.

IntentCrawler bridges this gap by:
- Crawling your website respectfully and comprehensively
- Processing content to extract meaningful signals
- Discovering user intents dynamically from actual content
- Generating structured data that shows how AI might interpret your site

## Architecture Overview

IntentCrawler follows a modular pipeline architecture that processes websites in distinct stages:

```
Website URL → Crawler → Content Processor → Intent Extractor → Report Generator → Dashboard
```

Each component is designed to solve a specific challenge in understanding web content from an AI perspective.

## Stage 1: Intelligent Web Crawling

The journey begins with the `WebCrawler` class, which implements a sophisticated crawling strategy:

### Sitemap-First Approach

```python
def crawl(self, start_url: Optional[str] = None, use_sitemap: bool = True) -> List[CrawledPage]:
    if use_sitemap:
        sitemap_urls = self._discover_urls()
        if sitemap_urls:
            urls_to_visit.extend(sitemap_urls)
```

The crawler prioritizes sitemap discovery because:
1. **Efficiency**: Sitemaps provide a complete URL list without recursive crawling
2. **Respect**: Following sitemaps shows respect for the site's intended structure
3. **Completeness**: Important pages might not be linked but are listed in sitemaps

### Robots.txt Compliance

```python
def _can_fetch(self, url: str) -> bool:
    if not self.robots_parser:
        return True
    return self.robots_parser.can_fetch(self.session.headers['User-Agent'], url)
```

The crawler respects robots.txt rules, checking both crawl permissions and discovering additional sitemaps listed in the robots file.

### Smart Content Storage

Each crawled page stores both raw HTML and extracted content:

```python
@dataclass
class CrawledPage:
    url: str
    title: str
    content: str
    links: List[str]
    section: Optional[str] = None
    metadata: Dict = None
    raw_html: Optional[str] = None
```

This dual storage allows different processing strategies downstream without re-crawling.

## Stage 2: Content Processing and Extraction

The `ContentProcessor` employs multiple extraction strategies to handle diverse website structures:

### Multi-Library Approach

```python
def process_content(self, html_content: str, url: str) -> Optional[ProcessedContent]:
    result = self.process_with_trafilatura(html_content, url)
    if not result:
        result = self.process_with_newspaper(html_content)
    if not result:
        result = self.process_with_beautifulsoup(html_content, url)
```

This fallback strategy ensures content extraction even from challenging pages:
- **Trafilatura**: Excellent for articles and blog posts
- **Newspaper3k**: Strong with news-style content
- **BeautifulSoup**: Fallback for custom structures

### Intelligent Summarization

Rather than using the first N characters, the processor creates contextual summaries:

```python
def _create_summary(self, content: str, title: str) -> str:
    sentences = re.split(r'[.!?]+', content)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 20]
    
    summary = sentences[0]
    for sentence in sentences[1:]:
        if len(summary + ' ' + sentence) <= self.max_summary_length:
            summary += ' ' + sentence
```

This preserves complete thoughts and provides meaningful context for intent analysis.

## Stage 3: User Intent Discovery

The heart of IntentCrawler is its intent extraction system. The `UserIntentExtractor` focuses on understanding what users are trying to accomplish:

### Intent Pattern Recognition

```python
self.intent_patterns = {
    'learn_and_understand': {
        'signals': [
            r'\b(?:how to|tutorial|guide|step by step)\b',
            r'\b(?:learn|understand|explain|what is)\b'
        ],
        'user_goals': ['acquire new skills', 'understand concepts'],
        'pain_points': ['lack of knowledge', 'confusion']
    },
    'solve_problem': {
        'signals': [
            r'\b(?:troubleshoot|fix|solve|error|issue)\b',
            r'\b(?:not working|broken|failed|help)\b'
        ],
        'user_goals': ['fix issues', 'get unblocked'],
        'pain_points': ['system not working', 'stuck on task']
    }
}
```

These patterns capture different user motivations:
- **Research & Compare**: Users evaluating options
- **Learn & Understand**: Users seeking knowledge
- **Solve Problems**: Users facing challenges
- **Implement & Integrate**: Users building solutions

### Multi-Signal Analysis

The extractor doesn't rely on keywords alone. It analyzes multiple signal types:

```python
def _analyze_page_intent(self, content: ProcessedContent) -> Dict[str, any]:
    user_signals = self._extract_user_signals(full_text)
    action_sequences = self._extract_action_sequences(full_text)
    pain_indicators = self._extract_pain_indicators(full_text)
    outcome_indicators = self._extract_outcome_indicators(full_text)
```

#### Action Sequence Extraction

Using spaCy's NLP capabilities, the tool identifies what users want to do:

```python
def _extract_action_sequences(self, text: str) -> List[str]:
    doc = self.nlp(text[:1000000])
    action_sequences = []
    
    for sent in doc.sents:
        if sent[0].pos_ == "VERB" and sent[0].dep_ == "ROOT":
            action_sequences.append(sent.text.strip())
```

This catches imperative sentences like "Configure your API key" or "Download the installer".

#### Pain Point Detection

Understanding user frustrations helps identify problem-solving intents:

```python
pain_patterns = [
    r'\b(?:difficult|hard|challenging|complex|confusing)\b',
    r'\b(?:can\'t|cannot|unable to|doesn\'t work)\b',
    r'\b(?:slow|expensive|time-consuming|inefficient)\b'
]
```

### Intent Clustering and Confidence

Pages are grouped by dominant intent with confidence scoring:

```python
def _calculate_intent_confidence(self, analyses: List[Dict], intent_type: str) -> float:
    strong_signals = sum(1 for analysis in analyses 
                       if analysis['intent_scores'].get(intent_type, 0) > 0.2)
    
    consistency_ratio = strong_signals / len(analyses)
    avg_signal_strength = np.mean([...])
    
    return min(consistency_ratio * avg_signal_strength, 1.0)
```

This ensures discovered intents are statistically significant, not just random keyword matches.

## Stage 4: Dynamic Intent Discovery Methods

Beyond pattern matching, IntentCrawler offers advanced ML-based discovery:

### Topic Modeling with LDA

```python
def _apply_lda_clustering(self, tfidf_matrix, feature_names: List[str]) -> List[Dict]:
    lda = LatentDirichletAllocation(
        n_components=self.config.get('lda_topics', 10),
        random_state=42
    )
    lda_matrix = lda.fit_transform(tfidf_matrix)
```

LDA discovers latent topics across all content, revealing intent patterns that might not match predefined categories.

### Semantic Clustering with Embeddings

```python
if self.embeddings_model:
    embeddings = self.embeddings_model.encode(texts)
    clustering = DBSCAN(eps=0.5, min_samples=2, metric='cosine')
    clusters = clustering.fit_predict(embeddings)
```

Sentence transformers create semantic embeddings, allowing the tool to group conceptually similar pages even with different vocabulary.

## Stage 5: Structured Output Generation

IntentCrawler generates multiple output formats for different use cases:

### LLMS.txt Format

Following the llmstxt specification, the tool creates AI-readable summaries:

```python
def format_as_llmstxt(self, pages: List[CrawledPage], 
                      processed_contents: Dict[str, ProcessedContent]) -> str:
    output.append(f"# {self.site_name}")
    output.append(f"\n> {self._generate_site_description(pages)}")
    
    for section, section_pages in sections.items():
        output.append(f"\n## {section.title()}")
        for page in section_pages[:5]:
            output.append(f"- {content.title}: {content.summary}")
```

This format is optimized for LLM consumption with clear hierarchy and concise summaries.

### Interactive Dashboard

The Dash-based dashboard provides visual intent analysis:

```python
def create_intent_distribution_chart(self, intent_data: List[Dict]) -> go.Figure:
    fig = go.Figure(data=[
        go.Bar(
            x=intent_names,
            y=page_counts,
            marker_color=confidence_scores,
            text=[f"{conf:.0%}" for conf in confidence_scores]
        )
    ])
```

Features include:
- Intent distribution visualization
- Section-by-section analysis
- Confidence score indicators
- Export capabilities

## Technical Optimizations

### Performance Considerations

1. **Rate Limiting**: Configurable delays prevent overwhelming servers
2. **Concurrent Processing**: Multiple analysis methods run in parallel
3. **Memory Management**: Large texts are truncated for NLP processing
4. **Caching**: Results are date-organized for easy retrieval

### Scalability Design

```python
def manage_results_directory(config: Dict[str, Any]) -> str:
    # Automatic cleanup of old results
    if keep_past_results >= 0:
        cleanup_old_results(base_dir, keep_past_results, date_format)
```

The tool automatically manages disk space by cleaning up old results while preserving recent analyses.

## Real-World Impact

IntentCrawler reveals insights that traditional analytics miss:

1. **Content Gaps**: Discover intents users seek but your content doesn't address
2. **AI Readiness**: Understand how well your content serves AI agents
3. **User Journey Mapping**: See the problems users are trying to solve
4. **Content Strategy**: Align content creation with discovered user needs

## Conclusion

IntentCrawler solves a critical problem in the AI era: understanding how machines interpret your website's purpose. By combining respectful crawling, intelligent content processing, and sophisticated intent discovery, it provides a window into your site's AI-perceived value.

The tool's modular architecture makes it extensible - new intent patterns, ML models, or output formats can be added without restructuring the core pipeline. As AI agents become increasingly important traffic sources, tools like IntentCrawler help ensure your content effectively communicates user value to both human and artificial visitors.

Whether you're optimizing for ChatGPT citations, improving content strategy, or simply curious about your site's AI interpretation, IntentCrawler provides the insights needed to thrive in an AI-augmented web.