# Architecture Patterns for Refactoring Monolithic Python Files

**Domain:** Python code refactoring - monolithic files to maintainable modules
**Researched:** 2026-01-23
**Confidence:** HIGH

## Executive Summary

Refactoring large monolithic Python files (600-2000+ lines) into maintainable modules requires a disciplined, incremental approach that prioritizes interface stability, maintains backwards compatibility, and uses automated tooling wherever possible. Based on comprehensive research and analysis of the Airbais Tools codebase, the recommended strategy follows a Test-First, Interface-First, Strangler Fig pattern combined with semantic module extraction techniques.

**Key Finding:** For systems with external integration contracts (like dashboard-data.json), interface-first refactoring with contract testing is critical to prevent breaking changes during module extraction.

**Primary Risk:** Dashboard consumes dashboard-data.json from all tools. Any refactoring that changes JSON schema or file paths breaks tool integration. JSON schema validation must be implemented BEFORE refactoring begins.

**Recommended Pattern:** Incremental strangler fig refactoring with automated extraction tools (Rope), test harnesses, and interface contracts.

## Recommended Architecture

### Three-Phase Refactoring Strategy

#### Phase 1: Establish Safety Net (Foundation)
Create infrastructure that enables safe refactoring without breaking existing functionality.

**Components:**
1. **JSON Schema Contract Definition**
   - Purpose: Formalize dashboard-data.json interface
   - Implementation: Create schema validation using jsonschema library
   - Guards against: Breaking dashboard integration during refactoring

2. **Test Harness Creation**
   - Purpose: Characterization tests for existing behavior
   - Implementation: Pytest-based tests capturing current outputs
   - Guards against: Regression during module extraction

3. **Baseline Metrics Collection**
   - Purpose: Track refactoring progress objectively
   - Implementation: Measure cyclomatic complexity, coupling, cohesion
   - Guards against: Refactoring that doesn't improve maintainability

#### Phase 2: Module Extraction (Transformation)
Systematically extract cohesive modules from monolithic files using strangler fig pattern.

**Components:**
1. **Semantic Boundary Identification**
   - Purpose: Find natural seams for module extraction
   - Implementation: Analyze dependencies, coupling, and cohesion
   - Ensures: Clean module boundaries with minimal coupling

2. **Interface-First Extraction**
   - Purpose: Define module contracts before implementation
   - Implementation: Create interface stubs, import them, test they work
   - Ensures: Backwards compatibility during transition

3. **Incremental Migration**
   - Purpose: Migrate functionality gradually, not all at once
   - Implementation: Extract one module at a time, test, commit
   - Ensures: Rollback points and continuous system functionality

#### Phase 3: Consolidation (Optimization)
Clean up after extraction, optimize interfaces, remove duplication.

**Components:**
1. **Interface Simplification**
   - Purpose: Reduce coupling between newly created modules
   - Implementation: Identify and eliminate circular dependencies
   - Ensures: True modularity with clear dependency graph

2. **Documentation Generation**
   - Purpose: Explain new architecture for maintainers
   - Implementation: Module docstrings, dependency diagrams, import maps
   - Ensures: New developers understand refactored structure

3. **Performance Validation**
   - Purpose: Confirm refactoring didn't degrade performance
   - Implementation: Benchmark tests comparing before/after
   - Ensures: Refactoring improved maintainability without cost

### Module Extraction Patterns

#### Pattern 1: Extract Class (Semantic Grouping)

**What:** Group related functions and data into a class, extract to new module
**When:** Functions share state or operate on common data structures
**Tool Support:** Rope, PyCharm automated refactoring

**Example: Dashboard Callbacks**
```python
# BEFORE: dashboard.py (2002 lines)
def setup_callbacks(self):
    @callback(...)
    def update_tool_dropdown(...):
        # 50 lines

    @callback(...)
    def update_run_dropdown(...):
        # 40 lines

    @callback(...)
    def display_tool_results(...):
        # 200 lines

    # 15 more callbacks...

# AFTER: dashboard/callbacks/tool_selection.py
class ToolSelectionCallbacks:
    """Handles tool and run selection callbacks"""

    def __init__(self, app, data_loader):
        self.app = app
        self.data_loader = data_loader
        self.register_callbacks()

    def register_callbacks(self):
        @self.app.callback(...)
        def update_tool_dropdown(...):
            # 50 lines

        @self.app.callback(...)
        def update_run_dropdown(...):
            # 40 lines

# AFTER: dashboard/callbacks/results_display.py
class ResultsDisplayCallbacks:
    """Handles results visualization callbacks"""
    # Similar pattern

# AFTER: dashboard/dashboard.py (now ~300 lines)
from callbacks.tool_selection import ToolSelectionCallbacks
from callbacks.results_display import ResultsDisplayCallbacks

class MasterDashboard:
    def __init__(self):
        # initialization

    def setup_callbacks(self):
        ToolSelectionCallbacks(self.app, self.data_loader)
        ResultsDisplayCallbacks(self.app, self.data_loader)
        # More callback groups...
```

**Implementation Steps:**
1. Identify callback groups by domain (tool selection, metrics display, export, theme)
2. Create callback class with `__init__(app, data_loader)` constructor
3. Move related callbacks to class, update decorator to `@self.app.callback`
4. Test each callback group independently
5. Import and instantiate in main dashboard file

**Risks:**
- Circular imports if callbacks reference each other
- Shared state between callback groups must be managed
- Testing becomes more complex with distributed callbacks

**Mitigation:**
- Use dependency injection for shared state
- Create callback base class for common functionality
- Provide integration test suite for cross-callback interactions

#### Pattern 2: Extract Function (Utility Separation)

**What:** Move utility functions to dedicated modules
**When:** Functions are pure (no shared state) and reusable
**Tool Support:** Rope extract method, automated import updates

**Example: Metric Evaluators**
```python
# BEFORE: polished.py (670 lines)
class PolishedEvaluator:
    async def evaluate(self, content):
        # evaluation logic

    def _split_content(self, content, max_words):
        # 30 lines of text chunking logic

    def _basic_grammar_check(self, content):
        # 80 lines of regex-based checks

    def _error_rate_to_rating(self, error_rate):
        # 20 lines of scoring logic

    def _llm_grammar_check(self, content):
        # 150 lines of LLM interaction

    # More helper methods...

# AFTER: metrics/utils/text_processing.py
def split_content(content: str, max_words: int = 800) -> List[str]:
    """Split content into chunks for processing"""
    # 30 lines - now reusable across evaluators

def calculate_readability_score(content: str) -> float:
    """Calculate Flesch reading ease score"""
    # Pure function, testable in isolation

# AFTER: metrics/utils/scoring.py
def error_rate_to_rating(error_rate: float) -> str:
    """Convert numeric error rate to quality rating"""
    # 20 lines - scoring logic used by multiple evaluators

def normalize_score(raw_score: float, min_val: float, max_val: float) -> int:
    """Normalize scores to 0-100 scale"""
    # Common scoring function

# AFTER: metrics/checkers/grammar.py
async def llm_grammar_check(content: str, openai_client) -> float:
    """Use LLM to check grammar and return error rate"""
    # 150 lines - complex but isolated

def rule_based_grammar_check(content: str) -> float:
    """Regex-based grammar checking"""
    # 80 lines - no external dependencies

# AFTER: polished.py (now ~250 lines)
from metrics.utils.text_processing import split_content
from metrics.utils.scoring import error_rate_to_rating, normalize_score
from metrics.checkers.grammar import llm_grammar_check, rule_based_grammar_check

class PolishedEvaluator:
    async def evaluate(self, content: str) -> str:
        if not content.strip():
            return "Very Poor"

        chunks = split_content(content)
        error_rate = await llm_grammar_check(chunks[0], self.openai_client)
        return error_rate_to_rating(error_rate)
```

**Implementation Steps:**
1. Identify pure functions (no side effects, no instance state)
2. Group by domain (text processing, scoring, validation)
3. Create utility modules with clear names
4. Extract functions with proper type hints
5. Update imports in original file
6. Write unit tests for extracted utilities

**Benefits:**
- Utilities become reusable across multiple evaluators
- Pure functions are trivial to test
- Reduces cognitive load in main evaluator class

#### Pattern 3: Extract Module (Layer Separation)

**What:** Separate layers of concern into distinct modules
**When:** File mixes UI, business logic, and data access
**Tool Support:** Manual extraction with Rope for imports

**Example: Dashboard Layers**
```python
# BEFORE: dashboard.py (2002 lines)
# - Layout definition (HTML/Dash components)
# - Callback logic (event handlers)
# - Data loading and transformation
# - Visualization generation (charts, tables)
# - Theme management
# - Export functionality

# AFTER: dashboard/layout.py
class DashboardLayout:
    """Defines dashboard UI structure"""

    def create_layout(self, tools_with_display_names):
        return html.Div([
            self._create_header(),
            self._create_tool_selection(tools_with_display_names),
            self._create_overview_section(),
            self._create_metrics_section(),
            # More sections...
        ])

    def _create_header(self):
        # Header HTML

    def _create_tool_selection(self, tools):
        # Tool selection dropdowns

# AFTER: dashboard/callbacks/__init__.py
# Callback registration system

# AFTER: dashboard/data_processor.py
class DataProcessor:
    """Transforms raw tool data for visualization"""

    def process_grasp_data(self, data):
        # GRASP-specific transformations

    def process_llm_data(self, data):
        # LLM-specific transformations

# AFTER: dashboard/visualizations.py
class Visualizations:
    """Creates Plotly charts and tables"""

    def create_metrics_gauge(self, score, title):
        # Gauge chart

    def create_recommendations_table(self, recommendations):
        # Table component

# AFTER: dashboard/theme_manager.py
class ThemeManager:
    """Manages dark/light theme state"""

    def get_current_theme(self):
        # Theme retrieval

    def toggle_theme(self):
        # Theme switching

# AFTER: dashboard/dashboard.py (now ~400 lines)
from layout import DashboardLayout
from data_processor import DataProcessor
from visualizations import Visualizations
from theme_manager import ThemeManager
from callbacks import setup_all_callbacks

class MasterDashboard:
    def __init__(self):
        self.app = dash.Dash(__name__)
        self.layout_builder = DashboardLayout()
        self.data_processor = DataProcessor()
        self.visualizations = Visualizations()
        self.theme_manager = ThemeManager()

        self.setup_layout()
        setup_all_callbacks(self.app, self)
```

**Implementation Steps:**
1. Map current file structure by layer (UI, logic, data, visualization)
2. Create layer modules with clear responsibilities
3. Extract each layer incrementally (start with utilities, then UI, then logic)
4. Use dependency injection to connect layers
5. Test each layer independently

**Benefits:**
- Clear separation of concerns
- Each layer testable in isolation
- New features touch fewer files
- Easier to understand architecture

#### Pattern 4: Facade Pattern (Backwards Compatibility)

**What:** Maintain old interface while refactoring internals
**When:** External code depends on current API
**Tool Support:** Manual implementation with deprecation warnings

**Example: Dashboard Data Contract**
```python
# CRITICAL: dashboard-data.json is consumed by dashboard
# Refactoring tools must NOT change this schema

# BEFORE: Tools write dashboard-data.json directly
def generate_dashboard_data(results):
    dashboard_data = {
        "tool": "graspevaluator",
        "timestamp": datetime.now().isoformat(),
        "overall_score": results['overall_score'],
        "metrics": results['metrics'],
        # ...
    }
    with open("results/dashboard-data.json", "w") as f:
        json.dump(dashboard_data, f)

# AFTER: Create DashboardDataContract class
# File: shared/dashboard_contract.py
from jsonschema import validate
import json

class DashboardDataContract:
    """Enforces dashboard-data.json schema contract"""

    SCHEMA = {
        "type": "object",
        "required": ["tool", "timestamp", "overall_score", "metrics"],
        "properties": {
            "tool": {"type": "string"},
            "timestamp": {"type": "string"},
            "overall_score": {"type": "number"},
            "metrics": {"type": "object"},
            # Full schema definition...
        }
    }

    @classmethod
    def validate(cls, data):
        """Raises ValidationError if data doesn't match schema"""
        validate(instance=data, schema=cls.SCHEMA)

    @classmethod
    def create(cls, tool_name, results):
        """Create valid dashboard data from results"""
        data = {
            "tool": tool_name,
            "timestamp": datetime.now().isoformat(),
            "overall_score": results.overall_score,
            "metrics": results.metrics_dict,
        }
        cls.validate(data)
        return data

    @classmethod
    def write(cls, data, output_path):
        """Write validated data to file"""
        cls.validate(data)
        with open(output_path, "w") as f:
            json.dump(data, f, indent=2)

# AFTER: Tools use contract
from shared.dashboard_contract import DashboardDataContract

def generate_dashboard_data(results, output_path):
    data = DashboardDataContract.create("graspevaluator", results)
    DashboardDataContract.write(data, output_path)
    # Guaranteed to match schema or raises validation error
```

**Implementation Steps:**
1. Extract current JSON schema from examples
2. Formalize schema using JSON Schema specification
3. Create contract class with validation
4. Add contract tests ensuring examples pass
5. Refactor tools to use contract class
6. Dashboard continues consuming same JSON format

**Benefits:**
- Interface stability guaranteed by schema validation
- Refactoring cannot break contract without test failure
- Schema serves as documentation
- Future schema evolution controlled through versioning

### Detailed Refactoring Workflow

#### Step-by-Step Process for Dashboard Refactoring (2002 lines)

**Pre-Refactoring Phase (Week 1)**

1. **Establish Baseline**
   ```bash
   # Measure current complexity
   radon cc dashboard/dashboard.py -a
   radon mi dashboard/dashboard.py

   # Document current behavior
   python dashboard/run_dashboard.py  # Manually test all features
   pytest dashboard/tests/  # Run existing tests
   ```

2. **Create Characterization Tests**
   ```python
   # tests/test_dashboard_characterization.py
   class TestDashboardBehavior:
       """Tests capturing current behavior before refactoring"""

       def test_tool_dropdown_options(self):
           """Verify tool dropdown shows correct tools"""
           dashboard = MasterDashboard()
           tools = dashboard.available_tools
           assert "graspevaluator" in tools
           assert "llmevaluator" in tools

       def test_dashboard_data_loading(self):
           """Verify dashboard loads data correctly"""
           dashboard = MasterDashboard()
           data = dashboard.data_loader.load_tool_data("graspevaluator", "2025-07-19")
           assert data is not None
           assert "overall_score" in data

       # 20+ more tests capturing all current behavior
   ```

3. **Create JSON Schema Contract**
   ```python
   # shared/dashboard_contract.py
   # (Full implementation shown in Pattern 4 above)

   # tests/test_dashboard_contract.py
   class TestDashboardContract:
       def test_schema_validates_grasp_output(self):
           """Verify GRASP output matches schema"""
           with open("graspevaluator/results/2025-07-19/dashboard-data.json") as f:
               data = json.load(f)
           DashboardDataContract.validate(data)  # Should not raise

       def test_schema_validates_llm_output(self):
           # Similar for other tools
   ```

**Refactoring Phase 1: Extract Utilities (Week 2)**

4. **Identify Utility Functions**
   ```bash
   # Find standalone functions that don't use instance state
   grep -n "    def " dashboard/dashboard.py | grep -v "self\." | head -20
   ```

5. **Extract to Utility Modules**
   ```python
   # Create dashboard/utils/formatting.py
   def format_metric_value(value, metric_type):
       """Format metric value for display"""
       # 15 lines extracted from dashboard.py

   def format_timestamp(iso_timestamp):
       """Format ISO timestamp for display"""
       # 10 lines extracted

   # Create dashboard/utils/data_transforms.py
   def normalize_metrics(metrics_dict):
       """Normalize metric scores to 0-100"""
       # 25 lines extracted
   ```

6. **Update Imports and Test**
   ```python
   # dashboard/dashboard.py
   from utils.formatting import format_metric_value, format_timestamp
   from utils.data_transforms import normalize_metrics

   # Update function calls (Rope can automate this)
   # Run tests: pytest dashboard/tests/ --tb=short
   # Verify: All characterization tests still pass
   ```

**Refactoring Phase 2: Extract Layout (Week 3)**

7. **Create Layout Module**
   ```python
   # dashboard/layout.py
   class DashboardLayout:
       def create_layout(self, tool_options, available_tools):
           return html.Div([...])  # 300 lines from setup_layout
   ```

8. **Update Main Dashboard**
   ```python
   # dashboard/dashboard.py
   from layout import DashboardLayout

   def setup_layout(self):
       layout_builder = DashboardLayout()
       self.app.layout = layout_builder.create_layout(
           self.tool_options,
           self.available_tools
       )
   ```

9. **Test Layout Generation**
   ```python
   # tests/test_layout.py
   def test_layout_creates_header():
       layout = DashboardLayout()
       result = layout.create_layout([], [])
       # Verify header exists in result
   ```

**Refactoring Phase 3: Extract Callbacks (Week 4-5)**

10. **Group Callbacks by Domain**
    - Tool selection callbacks (update dropdowns)
    - Results display callbacks (show data)
    - Visualization callbacks (create charts)
    - Export callbacks (download reports)
    - Theme callbacks (toggle theme)

11. **Create Callback Classes**
    ```python
    # dashboard/callbacks/tool_selection.py
    class ToolSelectionCallbacks:
        def __init__(self, app, data_loader):
            self.app = app
            self.data_loader = data_loader
            self.register_callbacks()

        def register_callbacks(self):
            @self.app.callback(...)
            def update_tool_dropdown(...):
                # Moved from setup_callbacks
    ```

12. **Incremental Migration**
    - Extract one callback group at a time
    - Test thoroughly after each extraction
    - Commit after each successful extraction
    - Rollback if tests fail

**Refactoring Phase 4: Extract Visualizations (Week 6)**

13. **Create Visualization Module**
    ```python
    # dashboard/visualizations.py
    class DashboardVisualizations:
        def create_metric_gauge(self, score, title, max_score=100):
            # Plotly gauge creation

        def create_recommendations_table(self, recommendations):
            # Dash table creation
    ```

14. **Update Callbacks to Use Visualizations**
    ```python
    # dashboard/callbacks/results_display.py
    from visualizations import DashboardVisualizations

    class ResultsDisplayCallbacks:
        def __init__(self, app, data_loader):
            self.viz = DashboardVisualizations()
            # ...

        def register_callbacks(self):
            @self.app.callback(...)
            def display_metrics(...):
                gauge = self.viz.create_metric_gauge(score, title)
                return gauge
    ```

**Post-Refactoring Phase (Week 7)**

15. **Verify All Tests Pass**
    ```bash
    pytest dashboard/tests/ -v
    pytest --cov=dashboard tests/
    # Coverage should be maintained or improved
    ```

16. **Measure Improvement**
    ```bash
    radon cc dashboard/dashboard.py -a  # Should show lower complexity
    radon mi dashboard/dashboard.py     # Should show higher maintainability
    wc -l dashboard/dashboard.py        # Should be <500 lines
    ```

17. **Update Documentation**
    ```markdown
    # dashboard/README.md

    ## Architecture

    Dashboard is organized into:
    - `dashboard.py` - Main application and orchestration (400 lines)
    - `layout.py` - UI component definitions (300 lines)
    - `callbacks/` - Event handlers by domain (5 modules, ~150 lines each)
    - `visualizations.py` - Chart and table generation (200 lines)
    - `data_processor.py` - Data transformation logic (250 lines)
    - `utils/` - Shared utilities (100 lines total)

    Total: ~1800 lines across 10+ modules vs 2002 lines in 1 file
    ```

### Order of Operations

**Critical Sequence for Airbais Tools:**

1. **Interface Contracts First** (Cannot skip)
   - JSON schema for dashboard-data.json
   - Contract tests for all existing tools
   - Validation integrated into output generation
   - Rationale: Prevents breaking dashboard during refactoring

2. **Characterization Tests Second** (Cannot skip)
   - Tests capturing current behavior
   - Integration tests for end-to-end flows
   - Baseline metrics collection
   - Rationale: Safety net for refactoring, enables rollback

3. **Utilities Third** (Lowest risk)
   - Extract pure functions first
   - Utilities have no shared state
   - Easy to test in isolation
   - Rationale: Builds confidence, provides early wins

4. **Layer Separation Fourth** (Medium risk)
   - Extract UI, data, visualization layers
   - Layers have clear boundaries
   - Can be tested independently
   - Rationale: Major architectural improvement with manageable risk

5. **Callbacks Last** (Highest risk)
   - Callbacks have complex interactions
   - Shared state across callbacks
   - Most likely to introduce bugs
   - Rationale: Save highest-risk work for when you have most experience

**Never Do:**
- Refactor without tests
- Refactor multiple modules simultaneously
- Change interfaces during extraction
- Skip commit points (commit after each successful extraction)
- Ignore failing tests ("we'll fix it later")

### Backwards Compatibility Strategy

**Principle:** Refactoring should never break external integrations.

#### Compatibility Levels

**Level 1: File System Compatibility**
```python
# MAINTAIN: File paths and directory structure
# tools/{tool}/results/{date}/dashboard-data.json

# If refactoring changes output location, use symlinks
ln -s new_location/dashboard-data.json old_location/dashboard-data.json

# Or update dashboard to check both locations
def find_dashboard_data(tool, date):
    primary = f"{tool}/results/{date}/dashboard-data.json"
    fallback = f"{tool}/output/{date}/dashboard.json"

    if os.path.exists(primary):
        return primary
    elif os.path.exists(fallback):
        return fallback
    else:
        raise FileNotFoundError
```

**Level 2: Schema Compatibility**
```python
# MAINTAIN: JSON schema for dashboard-data.json
# Use JSON Schema versioning for evolution

class DashboardDataContract:
    SCHEMA_V1 = {
        # Original schema
    }

    SCHEMA_V2 = {
        # Updated schema with new fields
        # All V1 fields still present
    }

    @classmethod
    def validate(cls, data):
        # Try V2, fall back to V1
        try:
            validate(data, cls.SCHEMA_V2)
        except ValidationError:
            validate(data, cls.SCHEMA_V1)

    @classmethod
    def upgrade_v1_to_v2(cls, v1_data):
        """Upgrade old format to new format"""
        v2_data = v1_data.copy()
        v2_data['schema_version'] = 2
        v2_data['new_field'] = default_value
        return v2_data
```

**Level 3: Import Compatibility**
```python
# MAINTAIN: Public API imports during refactoring
# Use __init__.py to expose old interface

# Before refactoring: from dashboard.py import MasterDashboard
# After refactoring: dashboard/ directory with multiple modules

# dashboard/__init__.py
from .dashboard import MasterDashboard
from .layout import DashboardLayout  # New module
from .visualizations import DashboardVisualizations  # New module

# This allows old code to still work:
from dashboard import MasterDashboard  # Still works

# While enabling new imports:
from dashboard.visualizations import DashboardVisualizations  # New
```

**Level 4: Deprecation Path**
```python
# When changing function signatures or module locations
import warnings

def old_function_name(*args, **kwargs):
    warnings.warn(
        "old_function_name is deprecated, use new_function_name instead",
        DeprecationWarning,
        stacklevel=2
    )
    return new_function_name(*args, **kwargs)

# In code that might be externally used
class PolishedEvaluator:
    def evaluate_content(self, content):  # Old name
        warnings.warn(
            "evaluate_content is deprecated, use evaluate instead",
            DeprecationWarning,
            stacklevel=2
        )
        return self.evaluate(content)

    def evaluate(self, content):  # New name
        # Implementation
```

### Risk Mitigation Strategies

#### Risk 1: Breaking Dashboard Integration

**Symptoms:**
- Dashboard cannot find tool data
- Dashboard crashes when loading data
- Visualizations fail to render

**Prevention:**
1. Create JSON schema BEFORE refactoring
2. Add schema validation to all tool output generation
3. Test schema with all existing dashboard-data.json files
4. Add integration test: generate data → validate schema → load in dashboard

**Detection:**
```python
# tests/test_integration_dashboard.py
def test_refactored_tool_output_loads_in_dashboard():
    """Ensure refactored tool output still works with dashboard"""
    # Generate output with refactored tool
    run_tool("graspevaluator", url="https://example.com")

    # Load in dashboard
    dashboard = MasterDashboard()
    data = dashboard.data_loader.load_tool_data("graspevaluator", today())

    # Verify dashboard can process it
    assert data is not None
    assert "overall_score" in data

    # Verify visualizations don't crash
    viz = dashboard.create_visualizations(data)
    assert viz is not None
```

**Recovery:**
- Rollback to pre-refactoring commit
- Fix schema validation
- Re-run integration tests
- Only proceed when tests pass

#### Risk 2: Circular Import Dependencies

**Symptoms:**
- ImportError: cannot import name 'X' from partially initialized module
- Module attributes accessed before definition
- Tests fail with confusing import errors

**Prevention:**
1. Design module dependency graph before extraction
2. Ensure dependencies flow in one direction (no cycles)
3. Use dependency injection instead of direct imports
4. Avoid module-level imports that reference each other

**Detection:**
```bash
# Use import analysis tools
pydeps dashboard --show-cycles

# Or custom script
python -c "
import ast
import sys
# Parse all files, build import graph, detect cycles
"
```

**Recovery:**
- Identify cycle: A imports B, B imports A
- Solution 1: Move shared code to third module C
- Solution 2: Use local imports (import inside function)
- Solution 3: Redesign to remove dependency

#### Risk 3: Shared State Corruption

**Symptoms:**
- Test passes in isolation but fails in suite
- Callback behavior differs between first/second invocation
- State leaks between test cases

**Prevention:**
1. Minimize shared mutable state
2. Use dependency injection for state
3. Clear state in setup/teardown
4. Use pytest fixtures with proper scope

**Detection:**
```python
# tests/conftest.py
@pytest.fixture(autouse=True)
def reset_state():
    """Reset global state before each test"""
    # Clear any module-level caches
    # Reset singleton instances
    yield
    # Cleanup after test
```

**Recovery:**
- Identify shared state (class variables, module globals)
- Refactor to instance variables or function parameters
- Add proper teardown logic

#### Risk 4: Performance Degradation

**Symptoms:**
- Dashboard loads slower after refactoring
- Tool execution time increases
- Memory usage increases

**Prevention:**
1. Benchmark before refactoring
2. Profile during refactoring
3. Benchmark after refactoring
4. Automated performance tests

**Detection:**
```python
# tests/test_performance.py
import time

def test_dashboard_load_time():
    """Dashboard should load within 2 seconds"""
    start = time.time()
    dashboard = MasterDashboard()
    dashboard.data_loader.discover_tools()
    elapsed = time.time() - start
    assert elapsed < 2.0, f"Dashboard took {elapsed}s to load"

def test_grasp_evaluation_time():
    """GRASP evaluation should complete within 30 seconds"""
    start = time.time()
    run_grasp_evaluator("https://example.com")
    elapsed = time.time() - start
    assert elapsed < 30.0
```

**Recovery:**
- Profile to find bottleneck
- Common causes: Excessive imports, repeated I/O, deep call stacks
- Solution: Lazy imports, caching, optimization

## Tools and Automation

### Rope: Python Refactoring Library

**Capabilities:**
- Rename variables, functions, classes, modules
- Extract method/function from code block
- Inline method (opposite of extract)
- Move functions/classes between modules
- Organize imports (remove unused, sort)
- Change method signature

**Installation:**
```bash
pip install rope
```

**Usage:**
```python
# Programmatic usage
from rope.base.project import Project
from rope.refactor.rename import Rename
from rope.refactor.extract import ExtractMethod

project = Project('.')
resource = project.root.get_file('dashboard/dashboard.py')

# Rename refactoring
rename = Rename(project, resource, offset)
changes = rename.get_changes('new_name')
project.do(changes)

# Extract method
extract = ExtractMethod(project, resource, start_offset, end_offset)
changes = extract.get_changes('new_method_name')
project.do(changes)
```

**IDE Integration:**
- PyCharm: Built-in refactoring uses Rope-like algorithms
- VS Code: Python extension includes Rope support
- Vim/Neovim: python-rope plugin

**Limitations:**
- Rope supports Python up to 3.10 (as of 2026)
- Complex refactorings may require manual verification
- Cannot understand semantic intent, only syntax

### Automated Testing Tools

**pytest with coverage:**
```bash
# Install
pip install pytest pytest-cov pytest-asyncio

# Run with coverage
pytest --cov=dashboard --cov-report=html tests/

# View coverage report
open htmlcov/index.html
```

**pytest-watch (automatic re-runs):**
```bash
# Install
pip install pytest-watch

# Auto-run tests on file changes
ptw dashboard/ tests/
```

**mutation testing (validates test quality):**
```bash
# Install
pip install mutpy

# Run mutation tests
mut.py --target dashboard.dashboard --unit-test tests/ --runner pytest
```

### Static Analysis Tools

**Radon (complexity metrics):**
```bash
# Install
pip install radon

# Cyclomatic complexity
radon cc dashboard/ -a  # -a for average
radon cc dashboard/dashboard.py -s  # -s for sort by complexity

# Maintainability index
radon mi dashboard/ -s
```

**Pylint (code quality):**
```bash
# Install
pip install pylint

# Run
pylint dashboard/
pylint --disable=C0111 dashboard/  # Disable missing docstring warnings
```

**Prospector (combines multiple tools):**
```bash
# Install
pip install prospector

# Run (combines pylint, pyflakes, mccabe, etc.)
prospector dashboard/
```

### Visualization Tools

**PyDeps (import graph):**
```bash
# Install
pip install pydeps

# Generate import graph
pydeps dashboard --max-bacon=2 -o dashboard_deps.svg
pydeps dashboard --show-cycles  # Find circular imports
```

**Code2flow (call graph):**
```bash
# Install
pip install code2flow

# Generate call graph
code2flow dashboard/dashboard.py -o dashboard_flow.png
```

## File-Specific Refactoring Recommendations

### dashboard/dashboard.py (2002 lines)

**Current Structure:**
- Lines 1-45: Imports and initialization
- Lines 46-107: Layout setup (HTML/Dash components)
- Lines 108-2002: Callback definitions (15+ callbacks)

**Recommended Extraction:**

1. **Week 1: Utilities**
   - Extract `format_*` functions → `utils/formatting.py`
   - Extract data transformations → `utils/data_transforms.py`
   - Target: Reduce to ~1800 lines

2. **Week 2: Layout**
   - Extract `setup_layout()` → `layout.py` class
   - Move theme HTML → `layout.py`
   - Target: Reduce to ~1500 lines

3. **Week 3-4: Callbacks (Phase 1)**
   - Extract tool selection callbacks → `callbacks/tool_selection.py`
   - Extract theme callbacks → `callbacks/theme.py`
   - Target: Reduce to ~1200 lines

4. **Week 5-6: Callbacks (Phase 2)**
   - Extract results display callbacks → `callbacks/results_display.py`
   - Extract visualization callbacks → `callbacks/visualizations.py`
   - Target: Reduce to ~800 lines

5. **Week 7-8: Callbacks (Phase 3)**
   - Extract export callbacks → `callbacks/export.py`
   - Extract metrics callbacks → `callbacks/metrics.py`
   - Target: Reduce to ~400 lines

**Final Structure:**
```
dashboard/
├── __init__.py              # Public API exports
├── dashboard.py             # Main app (400 lines)
├── layout.py                # UI structure (300 lines)
├── data_processor.py        # Data transformations (250 lines)
├── utils/
│   ├── __init__.py
│   ├── formatting.py        # Display formatting (100 lines)
│   └── data_transforms.py   # Data manipulation (100 lines)
├── callbacks/
│   ├── __init__.py          # Callback registration
│   ├── tool_selection.py    # Tool/run dropdowns (150 lines)
│   ├── results_display.py   # Results rendering (200 lines)
│   ├── visualizations.py    # Chart creation (150 lines)
│   ├── metrics.py           # Metrics display (150 lines)
│   ├── export.py            # Export functionality (100 lines)
│   └── theme.py             # Theme toggle (50 lines)
└── visualizations.py        # Plotly chart builders (200 lines)
```

### graspevaluator/metrics/polished.py (670 lines)

**Current Structure:**
- Lines 1-30: Imports and class initialization
- Lines 31-57: Main evaluation logic
- Lines 58-200: LLM grammar checking
- Lines 201-350: Rule-based grammar checking
- Lines 351-500: Scoring and rating logic
- Lines 501-670: Helper functions and utilities

**Recommended Extraction:**

1. **Week 1: Utilities**
   - Extract `_split_content()` → `utils/text_processing.py`
   - Extract `_error_rate_to_rating()` → `utils/scoring.py`
   - Target: Reduce to ~550 lines

2. **Week 2: Checkers**
   - Extract `_llm_grammar_check()` → `checkers/llm_checker.py`
   - Extract `_rule_based_grammar_check()` → `checkers/rule_checker.py`
   - Extract `_basic_grammar_check()` → `checkers/basic_checker.py`
   - Target: Reduce to ~200 lines

3. **Week 3: Integration**
   - Create unified `GrammarChecker` interface
   - Polished evaluator uses interface
   - Target: Final ~150 lines

**Final Structure:**
```
graspevaluator/metrics/
├── polished.py              # Main evaluator (150 lines)
├── utils/
│   ├── text_processing.py   # Text utilities (100 lines)
│   └── scoring.py           # Score calculations (50 lines)
└── checkers/
    ├── __init__.py          # Checker interface
    ├── llm_checker.py       # LLM-based checking (200 lines)
    ├── rule_checker.py      # Regex-based checking (150 lines)
    └── basic_checker.py     # Simple heuristics (50 lines)
```

### rulesevaluator/src/output_generator.py (642 lines)

**Current Structure:**
- Lines 1-50: Imports and initialization
- Lines 51-150: JSON output generation
- Lines 151-300: HTML output generation
- Lines 301-450: Markdown output generation
- Lines 451-550: Dashboard data generation
- Lines 551-642: Utility functions

**Recommended Extraction:**

1. **Week 1: Format Generators**
   - Extract JSON generation → `outputs/json_generator.py`
   - Extract HTML generation → `outputs/html_generator.py`
   - Extract Markdown generation → `outputs/markdown_generator.py`
   - Extract dashboard generation → `outputs/dashboard_generator.py`
   - Target: Reduce to ~150 lines

2. **Week 2: Templates**
   - Extract HTML templates → `templates/report_template.html`
   - Use Jinja2 for templating
   - Target: Separate presentation from logic

**Final Structure:**
```
rulesevaluator/src/
├── output_generator.py      # Orchestrator (150 lines)
├── outputs/
│   ├── __init__.py          # Output interface
│   ├── json_generator.py    # JSON output (100 lines)
│   ├── html_generator.py    # HTML output (150 lines)
│   ├── markdown_generator.py # MD output (100 lines)
│   └── dashboard_generator.py # Dashboard JSON (100 lines)
└── templates/
    └── report_template.html  # HTML template
```

### graspevaluator/metrics/structured.py (640 lines)

**Similar pattern to polished.py:**
- Extract semantic HTML checking to `checkers/html_checker.py`
- Extract schema markup checking to `checkers/schema_checker.py`
- Extract scoring to `utils/scoring.py` (shared with polished)

### geoevaluator/src/main.py (633 lines)

**Recommended Structure:**
```
geoevaluator/src/
├── main.py                  # Entry point (150 lines)
├── crawler.py               # Web crawling (200 lines)
├── analyzer.py              # Location analysis (150 lines)
├── report_generator.py      # Report generation (150 lines)
└── utils/
    └── geo_utils.py         # Location utilities (100 lines)
```

## JSON Schema Contract Specification

### dashboard-data.json Schema

**Purpose:** Formal contract between tools and dashboard ensuring interface stability during refactoring.

**Implementation:**
```python
# shared/dashboard_contract.py
from jsonschema import validate, ValidationError
import json
from datetime import datetime
from typing import Dict, Any, List

class DashboardDataContract:
    """
    Enforces dashboard-data.json schema contract.

    All tools must generate output matching this schema.
    Schema validation prevents breaking dashboard during refactoring.
    """

    SCHEMA_VERSION = "1.0"

    SCHEMA = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "title": "Dashboard Data Schema",
        "description": "Standard format for tool output consumed by master dashboard",
        "type": "object",
        "required": ["tool", "version", "timestamp", "overall_score", "metrics"],
        "properties": {
            "tool": {
                "type": "string",
                "description": "Tool identifier (graspevaluator, llmevaluator, etc.)",
                "pattern": "^[a-z]+evaluator$"
            },
            "version": {
                "type": "string",
                "description": "Tool version (semver)",
                "pattern": "^\\d+\\.\\d+\\.\\d+$"
            },
            "timestamp": {
                "type": "string",
                "description": "ISO 8601 timestamp",
                "format": "date-time"
            },
            "url": {
                "type": "string",
                "description": "Analyzed URL (optional for some tools)",
                "format": "uri"
            },
            "overall_score": {
                "type": "number",
                "description": "Weighted overall score (0-100)",
                "minimum": 0,
                "maximum": 100
            },
            "metrics": {
                "type": "object",
                "description": "Individual metric scores",
                "patternProperties": {
                    "^[a-z_]+$": {
                        "type": "object",
                        "required": ["score", "normalized_score", "weight"],
                        "properties": {
                            "score": {
                                "description": "Raw score (can be number, boolean, or string)",
                                "oneOf": [
                                    {"type": "number"},
                                    {"type": "boolean"},
                                    {"type": "string"}
                                ]
                            },
                            "normalized_score": {
                                "type": "number",
                                "minimum": 0,
                                "maximum": 100
                            },
                            "weight": {
                                "type": "number",
                                "minimum": 0,
                                "maximum": 100
                            },
                            "description": {
                                "type": "string"
                            }
                        }
                    }
                }
            },
            "recommendations": {
                "type": "array",
                "description": "Simple text recommendations",
                "items": {
                    "type": "string"
                }
            },
            "enhanced_recommendations": {
                "type": "array",
                "description": "Structured recommendations with implementation details",
                "items": {
                    "type": "object",
                    "required": ["priority", "category", "issue", "impact", "action"],
                    "properties": {
                        "priority": {
                            "type": "string",
                            "enum": ["critical", "high", "medium", "low"]
                        },
                        "category": {
                            "type": "string"
                        },
                        "issue": {
                            "type": "string"
                        },
                        "impact": {
                            "type": "string"
                        },
                        "action": {
                            "type": "string"
                        },
                        "specifics": {
                            "type": "object"
                        },
                        "implementation": {
                            "type": "object"
                        }
                    }
                }
            },
            "data": {
                "type": "object",
                "description": "Tool-specific additional data"
            }
        }
    }

    @classmethod
    def validate(cls, data: Dict[str, Any]) -> None:
        """
        Validate data against schema.

        Args:
            data: Dashboard data dictionary

        Raises:
            ValidationError: If data doesn't match schema
        """
        validate(instance=data, schema=cls.SCHEMA)

    @classmethod
    def validate_file(cls, file_path: str) -> None:
        """
        Validate JSON file against schema.

        Args:
            file_path: Path to dashboard-data.json file

        Raises:
            ValidationError: If file doesn't match schema
            FileNotFoundError: If file doesn't exist
            json.JSONDecodeError: If file isn't valid JSON
        """
        with open(file_path, 'r') as f:
            data = json.load(f)
        cls.validate(data)

    @classmethod
    def create(cls,
               tool: str,
               version: str,
               overall_score: float,
               metrics: Dict[str, Dict],
               url: str = None,
               recommendations: List[str] = None,
               enhanced_recommendations: List[Dict] = None,
               data: Dict = None) -> Dict[str, Any]:
        """
        Create valid dashboard data dictionary.

        Args:
            tool: Tool identifier
            version: Tool version
            overall_score: Overall score (0-100)
            metrics: Metrics dictionary
            url: Optional analyzed URL
            recommendations: Optional simple recommendations
            enhanced_recommendations: Optional structured recommendations
            data: Optional tool-specific data

        Returns:
            Valid dashboard data dictionary

        Raises:
            ValidationError: If created data doesn't match schema
        """
        dashboard_data = {
            "tool": tool,
            "version": version,
            "timestamp": datetime.now().isoformat(),
            "overall_score": overall_score,
            "metrics": metrics
        }

        if url:
            dashboard_data["url"] = url
        if recommendations:
            dashboard_data["recommendations"] = recommendations
        if enhanced_recommendations:
            dashboard_data["enhanced_recommendations"] = enhanced_recommendations
        if data:
            dashboard_data["data"] = data

        # Validate before returning
        cls.validate(dashboard_data)
        return dashboard_data

    @classmethod
    def write(cls, data: Dict[str, Any], output_path: str) -> None:
        """
        Write validated data to JSON file.

        Args:
            data: Dashboard data dictionary
            output_path: Output file path

        Raises:
            ValidationError: If data doesn't match schema
        """
        cls.validate(data)
        with open(output_path, 'w') as f:
            json.dump(data, f, indent=2)

    @classmethod
    def migrate_v1_to_v2(cls, v1_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Migrate v1 schema to v2 (future compatibility).

        Args:
            v1_data: Data in v1 format

        Returns:
            Data in v2 format
        """
        # Example migration logic for future schema evolution
        v2_data = v1_data.copy()
        v2_data['schema_version'] = '2.0'
        # Add new required fields with defaults
        # Transform changed fields
        return v2_data
```

**Usage in Tools:**
```python
# Example: graspevaluator/src/report_generator.py
from shared.dashboard_contract import DashboardDataContract

class ReportGenerator:
    def generate_dashboard_data(self, results):
        """Generate dashboard-compatible output"""

        # Prepare metrics in required format
        metrics = {
            "grounded": {
                "score": results.grounded_score,
                "normalized_score": results.grounded_normalized,
                "weight": 40,
                "description": "Content alignment with customer intents"
            },
            # More metrics...
        }

        # Create validated dashboard data
        dashboard_data = DashboardDataContract.create(
            tool="graspevaluator",
            version="1.0.0",
            overall_score=results.overall_score,
            metrics=metrics,
            url=results.url,
            recommendations=results.recommendations,
            enhanced_recommendations=results.enhanced_recommendations
        )

        # Write to file (automatically validated)
        output_path = f"results/{date}/dashboard-data.json"
        DashboardDataContract.write(dashboard_data, output_path)
```

**Contract Tests:**
```python
# tests/test_dashboard_contract.py
import pytest
import json
from pathlib import Path
from shared.dashboard_contract import DashboardDataContract
from jsonschema import ValidationError

class TestDashboardContract:
    """Test dashboard-data.json schema contract"""

    def test_schema_validates_grasp_output(self):
        """GRASP output matches schema"""
        data = json.load(open("graspevaluator/results/2025-07-19/dashboard-data.json"))
        DashboardDataContract.validate(data)  # Should not raise

    def test_schema_validates_llm_output(self):
        """LLM output matches schema"""
        data = json.load(open("llmevaluator/results/2025-08-01/dashboard-data.json"))
        DashboardDataContract.validate(data)

    def test_schema_validates_all_existing_outputs(self):
        """All existing dashboard-data.json files match schema"""
        dashboard_files = Path(".").rglob("*/results/*/dashboard-data.json")
        for file_path in dashboard_files:
            DashboardDataContract.validate_file(str(file_path))

    def test_schema_rejects_missing_required_fields(self):
        """Schema rejects data missing required fields"""
        invalid_data = {
            "tool": "graspevaluator",
            # Missing timestamp, overall_score, metrics
        }
        with pytest.raises(ValidationError):
            DashboardDataContract.validate(invalid_data)

    def test_schema_rejects_invalid_score_range(self):
        """Schema rejects scores outside 0-100 range"""
        invalid_data = {
            "tool": "graspevaluator",
            "version": "1.0.0",
            "timestamp": "2025-07-19T12:00:00",
            "overall_score": 150,  # Invalid
            "metrics": {}
        }
        with pytest.raises(ValidationError):
            DashboardDataContract.validate(invalid_data)

    def test_create_method_produces_valid_data(self):
        """Create method produces schema-compliant data"""
        data = DashboardDataContract.create(
            tool="graspevaluator",
            version="1.0.0",
            overall_score=85.5,
            metrics={
                "grounded": {
                    "score": 8.5,
                    "normalized_score": 85,
                    "weight": 40,
                    "description": "Test metric"
                }
            }
        )
        # Should not raise
        DashboardDataContract.validate(data)

    def test_write_method_creates_valid_file(self, tmp_path):
        """Write method creates valid JSON file"""
        data = DashboardDataContract.create(
            tool="test",
            version="1.0.0",
            overall_score=100,
            metrics={}
        )

        output_path = tmp_path / "dashboard-data.json"
        DashboardDataContract.write(data, str(output_path))

        # Validate written file
        DashboardDataContract.validate_file(str(output_path))

    def test_dashboard_can_load_contract_data(self):
        """Dashboard successfully loads contract-validated data"""
        from dashboard.data_loader import ToolDataLoader

        # Create valid data
        data = DashboardDataContract.create(
            tool="testool",
            version="1.0.0",
            overall_score=50,
            metrics={}
        )

        # Write to temp location
        temp_file = "/tmp/dashboard-data.json"
        DashboardDataContract.write(data, temp_file)

        # Verify dashboard can load it
        loader = ToolDataLoader()
        loaded_data = loader.load_data_file(temp_file)
        assert loaded_data is not None
        assert loaded_data['overall_score'] == 50
```

## Anti-Patterns to Avoid

### Anti-Pattern 1: Big Bang Refactoring

**What:** Refactoring everything at once without incremental testing
**Why Bad:** High risk of introducing bugs, difficult to isolate issues, no rollback points
**Example:**
```python
# WRONG: Refactor entire dashboard in one commit
git commit -m "Refactor dashboard.py into 15 modules"
# 2000 lines changed, nothing works, hard to debug
```

**Instead:**
```python
# RIGHT: Incremental refactoring with test points
git commit -m "Extract formatting utilities from dashboard"  # 100 lines changed
# Test, verify, commit
git commit -m "Extract layout module from dashboard"  # 300 lines changed
# Test, verify, commit
git commit -m "Extract tool selection callbacks"  # 150 lines changed
# Continue incrementally...
```

### Anti-Pattern 2: Refactoring Without Tests

**What:** Extracting modules without characterization tests
**Why Bad:** No safety net, can't detect regressions, breaks existing functionality
**Example:**
```python
# WRONG: Extract module without tests
def extract_utilities():
    # Move functions to utils.py
    # Hope nothing breaks

# Tests fail or worse, silent bugs introduced
```

**Instead:**
```python
# RIGHT: Write characterization tests first
def test_format_metric_value_behavior():
    """Document current behavior before extraction"""
    result = format_metric_value(85.5, "percentage")
    assert result == "85.5%"

# Now safe to extract
def extract_utilities():
    # Extract to utils.py
    # Tests verify behavior unchanged
```

### Anti-Pattern 3: Premature Abstraction

**What:** Creating generic interfaces before understanding patterns
**Why Bad:** Over-engineering, unnecessary complexity, harder to change
**Example:**
```python
# WRONG: Create abstract base class prematurely
class AbstractMetricEvaluator(ABC):
    @abstractmethod
    def pre_evaluate(self, content): pass

    @abstractmethod
    def evaluate(self, content): pass

    @abstractmethod
    def post_evaluate(self, result): pass

    @abstractmethod
    def validate_input(self, content): pass

    # 10 more abstract methods...

# Now all evaluators must implement 15 methods they don't need
```

**Instead:**
```python
# RIGHT: Extract common code after patterns emerge
# First, refactor each evaluator independently
# Then, identify actual shared code
# Finally, create minimal interface for real commonality

class MetricEvaluator:
    """Base class with actual shared code only"""

    def evaluate_with_fallback(self, content):
        """Shared error handling pattern"""
        try:
            return self.evaluate(content)
        except Exception:
            return self.fallback_evaluate(content)
```

### Anti-Pattern 4: Ignoring Coupling During Extraction

**What:** Extracting modules without considering dependencies
**Why Bad:** Creates circular imports, tight coupling, hard to test
**Example:**
```python
# WRONG: Extract without considering dependencies
# callbacks/tool_selection.py
from callbacks.results_display import ResultsDisplayCallbacks  # Imports results

# callbacks/results_display.py
from callbacks.tool_selection import ToolSelectionCallbacks  # Imports tool selection

# Circular import error
```

**Instead:**
```python
# RIGHT: Design dependency flow before extraction
# callbacks/tool_selection.py
# No imports from other callbacks

# callbacks/results_display.py
# No imports from other callbacks

# dashboard.py coordinates both
from callbacks.tool_selection import ToolSelectionCallbacks
from callbacks.results_display import ResultsDisplayCallbacks

def setup_callbacks(app, data_loader):
    # Pass shared dependencies via constructor
    ToolSelectionCallbacks(app, data_loader)
    ResultsDisplayCallbacks(app, data_loader)
```

### Anti-Pattern 5: Changing Interfaces During Refactoring

**What:** Modifying function signatures while extracting modules
**Why Bad:** Breaks backwards compatibility, requires updating all callers
**Example:**
```python
# WRONG: Change interface during extraction
# Before
def format_metric(value, type):
    pass

# After extraction - changed signature
def format_metric(value, metric_config, display_options):
    pass

# Now all callers break
```

**Instead:**
```python
# RIGHT: Maintain interface during extraction
# Before
def format_metric(value, type):
    pass

# After extraction - same signature
def format_metric(value, type):
    # Implementation moved to utils, but interface unchanged
    from utils.formatting import format_metric_internal
    return format_metric_internal(value, type)

# Callers unchanged, refactoring safe
```

### Anti-Pattern 6: Skipping Commit Points

**What:** Making multiple changes before committing
**Why Bad:** No rollback points, hard to identify what broke
**Example:**
```python
# WRONG: Multiple refactorings without commits
extract_utilities()
extract_layout()
extract_callbacks()
# Now tests fail - which change broke it?
git commit -m "Refactored dashboard"
```

**Instead:**
```python
# RIGHT: Commit after each successful extraction
extract_utilities()
run_tests()  # Pass
git commit -m "Extract utilities from dashboard"

extract_layout()
run_tests()  # Pass
git commit -m "Extract layout from dashboard"

extract_callbacks()
run_tests()  # Fail - rollback this change only
git reset --hard HEAD
# Fix issue, try again
```

## Success Metrics

### Quantitative Metrics

**Before vs After Comparison:**

| Metric | Before | Target After | Measurement Tool |
|--------|--------|--------------|------------------|
| Dashboard file size | 2002 lines | <500 lines | `wc -l` |
| Average function length | 50+ lines | <20 lines | `radon cc -a` |
| Cyclomatic complexity | 15-30 | <10 | `radon cc` |
| Maintainability index | 40-60 | >70 | `radon mi` |
| Test coverage | 30% | >80% | `pytest --cov` |
| Number of functions per file | 50+ | <15 | Manual count |
| Import depth | 4-5 levels | 2-3 levels | `pydeps` |
| Circular imports | Present | 0 | `pydeps --show-cycles` |

**Dashboard-Specific Metrics:**

| Metric | Before | Target After |
|--------|--------|--------------|
| dashboard.py | 2002 lines | 400 lines |
| Number of modules | 1 | 10-12 |
| Callback complexity | High (all in one) | Low (grouped by domain) |
| Layout complexity | Mixed with logic | Separated |

**Metric Evaluator Files:**

| File | Before | Target After |
|------|--------|--------------|
| polished.py | 670 lines | 150 lines |
| structured.py | 640 lines | 150 lines |
| output_generator.py | 642 lines | 150 lines |
| geoevaluator/main.py | 633 lines | 150 lines |

### Qualitative Metrics

**Developer Experience Improvements:**
- [ ] New developer can understand module structure in <30 minutes
- [ ] Adding new metric evaluator requires touching <3 files
- [ ] Adding new dashboard callback takes <2 hours
- [ ] Test suite runs in <30 seconds
- [ ] Failed tests clearly indicate which module has issue

**Maintainability Improvements:**
- [ ] Modules have single, clear responsibility
- [ ] Dependencies flow in one direction (no cycles)
- [ ] Each module can be tested independently
- [ ] Bug fixes affect single module 90% of time
- [ ] Code review focuses on one module at a time

**Architecture Quality:**
- [ ] Clear separation of concerns (UI, logic, data)
- [ ] Interface contracts documented and enforced
- [ ] Minimal coupling between modules
- [ ] High cohesion within modules
- [ ] New functionality has obvious home

## Validation Checklist

Before declaring refactoring complete:

### Functionality
- [ ] All existing tests pass
- [ ] Manual testing shows no regressions
- [ ] Dashboard loads and displays all tools
- [ ] All tool outputs validated against JSON schema
- [ ] Integration tests pass (tool → dashboard flow)

### Code Quality
- [ ] Cyclomatic complexity <10 per function
- [ ] Maintainability index >70
- [ ] No circular imports detected
- [ ] All modules <500 lines
- [ ] All functions <50 lines

### Testing
- [ ] Test coverage >80%
- [ ] Unit tests for all new modules
- [ ] Integration tests for module interactions
- [ ] Contract tests for JSON schema
- [ ] Performance tests show no regression

### Documentation
- [ ] Module docstrings explain purpose
- [ ] README updated with new structure
- [ ] Architecture diagram shows module relationships
- [ ] Import map documents dependencies
- [ ] Migration guide for future refactoring

### Backwards Compatibility
- [ ] JSON schema unchanged or versioned
- [ ] File paths unchanged or symlinked
- [ ] Public APIs unchanged
- [ ] Deprecation warnings for changed functions
- [ ] No breaking changes to external integrations

## Sources

Research for this architecture document drew from:

### Python Refactoring Best Practices
- [Organizing Python Code into Modules for Better Organization and Reusability](https://llego.dev/posts/organizing-python-code-modules-better-organization-reusability/)
- [Structuring Your Project — The Hitchhiker's Guide to Python](https://docs.python-guide.org/writing/structure/)
- [Best Practices in Structuring Python Projects](https://dagster.io/blog/python-project-best-practices)
- [Refactoring Python Applications for Simplicity – Real Python](https://realpython.com/python-refactoring/)
- [How to Refactor Complex Codebases – A Practical Guide for Devs](https://www.freecodecamp.org/news/how-to-refactor-complex-codebases/)
- [Python Refactoring: Techniques, Tools, and Best Practices](https://www.codesee.io/learning-center/python-refactoring)
- [A Simple Guide to Writing Modular Python Code](https://derekarmstrong.dev/a-practical-guide-to-writing-modular-python-code)

### Refactoring Tools and Automation
- [GitHub - python-rope/rope: a python refactoring library](https://github.com/python-rope/rope)
- [Rope Overview — rope 1.14.0 documentation](https://rope.readthedocs.io/en/latest/overview.html)
- [Pylsp Plugins Python Rope: Refactoring Extract Method Rename Inline Debugger 2026](https://johal.in/pylsp-plugins-python-rope-refactoring-extract-method-rename-inline-debugger-2026/)
- [Rope: Python Refactoring for Claude & CLI](https://mcpmarket.com/server/rope)

### Dash Application Structure
- [App Structure, Buildpacks, and Deployment Lifecycle | Dash for Python Documentation | Plotly](https://dash.plotly.com/dash-enterprise/application-structure)
- [Structuring a large Dash application - best practices to follow](https://community.plotly.com/t/structuring-a-large-dash-application-best-practices-to-follow/62739)
- [Dash Project Structure: Multi-Tab App with Callbacks in Different Files](https://www.purfe.com/dash-project-structure-multi-tab-app-with-callbacks-in-different-files/)
- [How to Structure and Organize Your Python Project (Dash Apps) in a Modular Fashion](https://medium.com/@gautam.ishu5/how-to-structure-and-organize-your-python-project-dash-apps-in-a-modular-fashion-1f5586d88fa7)

### Backwards Compatibility Strategies
- [PEP 387 – Backwards Compatibility Policy](https://peps.python.org/pep-0387/)
- [When Code Changes Break the World: Python Backward Compatibility in 2025](https://an4t.com/python-backward-compatibility/)
- [Maintaining Backward Compatibility with Versioning in Python](https://codesignal.com/learn/courses/backward-compatibility-in-software-development/lessons/maintaining-backward-compatibility-with-versioning-in-python)

### JSON Schema and Interface Contracts
- [jsonschema 4.26.0 documentation](https://python-jsonschema.readthedocs.io/)
- [JSON Schema - as a specification, contract and validation!](https://pritibiyani.github.io/blog/using-json-schema-as-specification-contract-and-validate-your-api)
- [7 OpenAPI/JSON-Schema Moves for Python Contract Testing](https://medium.com/@Modexa/7-openapi-json-schema-moves-for-python-contract-testing-1fdd1f7e201f)

### Test-Driven Development and Refactoring
- [What is test-driven development (TDD)? The complete guide for 2026](https://monday.com/blog/rnd/test-driven-development-tdd/)
- [Red, Green, Refactor | Codecademy](https://www.codecademy.com/article/tdd-red-green-refactor)
- [Test-driven development (TDD) - The GDS Way](https://gds-way.digital.cabinet-office.gov.uk/standards/test-driven-development.html)

### Strangler Fig Pattern
- [Strangler Fig Pattern for Refactoring Monolith into Microservices](https://mehmetozkaya.medium.com/strangler-fig-pattern-for-refactoring-monolith-into-microservices-%EF%B8%8F-88e667c096c8)
- [Strangler fig pattern - AWS Prescriptive Guidance](https://docs.aws.amazon.com/prescriptive-guidance/latest/modernization-decomposing-monoliths/strangler-fig.html)
- [How the Strangler Fig Pattern Enables Safe and Gradual Refactoring](https://www.gocodeo.com/post/how-the-strangler-fig-pattern-enables-safe-and-gradual-refactoring)
- [Refactoring Legacy Code with the Strangler Fig Pattern - Shopify](https://shopify.engineering/refactoring-legacy-code-strangler-fig-pattern)

## Appendix: Quick Reference Guide

### Refactoring Decision Tree

```
START: Need to refactor large file (600+ lines)
  |
  ├─> Has external integration contracts? (e.g., dashboard-data.json)
  |   YES: Create JSON schema contract FIRST
  |   NO: Continue
  |
  ├─> Has existing tests?
  |   YES: Review test coverage, add characterization tests for gaps
  |   NO: Write characterization tests NOW (cannot proceed without)
  |
  ├─> Identify module boundaries:
  |   ├─> Pure functions (no state)? → Extract to utils/ (Pattern 2)
  |   ├─> Related functions sharing state? → Extract to class (Pattern 1)
  |   ├─> Different layers mixed? → Separate layers (Pattern 3)
  |   └─> Complex dependencies? → Use strangler fig (Pattern 4)
  |
  ├─> Plan extraction order:
  |   1. Utilities (lowest risk)
  |   2. UI/Presentation (medium risk)
  |   3. Business logic (medium-high risk)
  |   4. Callbacks/handlers (highest risk)
  |
  ├─> For each extraction:
  |   ├─> Create target module
  |   ├─> Copy code (don't delete yet)
  |   ├─> Update imports
  |   ├─> Run tests
  |   ├─> Tests pass? Remove original code
  |   ├─> Tests fail? Debug, fix, repeat
  |   └─> Commit
  |
  └─> DONE: Validate with checklist, measure metrics
```

### Command Cheatsheet

```bash
# Measure complexity before refactoring
radon cc dashboard/dashboard.py -a -s
radon mi dashboard/dashboard.py

# Find functions to extract
grep -n "    def " dashboard/dashboard.py | wc -l  # Function count
grep -n "^class " dashboard/dashboard.py  # Class definitions

# Detect circular imports
pydeps dashboard --show-cycles

# Run tests with coverage
pytest dashboard/tests/ --cov=dashboard --cov-report=html -v

# Validate JSON schema
python -c "from shared.dashboard_contract import DashboardDataContract; DashboardDataContract.validate_file('graspevaluator/results/2025-07-19/dashboard-data.json')"

# Find all dashboard-data.json files
find . -name "dashboard-data.json" -path "*/results/*"

# Measure improvement
echo "Before: $(git show HEAD~10:dashboard/dashboard.py | wc -l) lines"
echo "After: $(wc -l dashboard/dashboard.py)"

# Watch tests during refactoring
ptw dashboard/ tests/  # Auto-run on file changes
```

### File Size Targets

```
Target sizes after refactoring:

Main orchestrator files:    300-500 lines
Layer modules (UI, data):   200-300 lines
Callback groups:            100-200 lines
Utility modules:            50-100 lines
Individual functions:       <20 lines
Test files:                 200-400 lines (more is okay)

If file exceeds target:
  - Identify next extraction candidate
  - Apply refactoring patterns again
  - Continue until target reached
```

### Risk Level by Module Type

```
LOW RISK (extract first):
  - Pure utility functions
  - Constants and configuration
  - Data model classes
  - Formatters and helpers

MEDIUM RISK (extract second):
  - UI layout components
  - Data transformation logic
  - Visualization generators
  - Report generators

HIGH RISK (extract last):
  - Callbacks with shared state
  - Complex business logic
  - API integrations
  - Database operations

CRITICAL (special care):
  - Interface contracts (JSON schema)
  - Public APIs
  - External integrations
  - Backwards compatibility facades
```
