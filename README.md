
# Build Failure Prediction Dataset Creation

This project implements two distinct approaches for creating machine learning datasets from git commit data to predict build outcomes. Based on research with Apache Software Foundation projects and public GitHub repositories, each approach addresses specific data collection challenges and research requirements.

## Project Background

The goal is to create labeled datasets where each commit is associated with features (code changes, commit metadata) and a target variable (build success/failure). This enables training ML models to predict whether a commit will cause build failures in CI/CD pipelines.

## Installation

```bash
pip install -r requirements.txt
```

Set up your GitHub Personal Access Token:
```bash
export GITHUB_TOKEN="your_github_token_here"
```

---

## Approach 1: Technical Debt Dataset Enhancement

**Best suited for**: Large-scale historical analysis, existing commit datasets from established projects

### Overview
This approach leverages the existing Technical Debt Dataset from 33 Apache Software Foundation Java projects. The dataset contains over 1 million commit samples with basic metadata (commit_sha, date, file, lines_added, lines_removed, notes). We enhance this data by extracting additional features and attempting to label build outcomes via GitHub API.

### Data Source
- **Origin**: Technical Debt Dataset (Apache Software Foundation)
- **Projects**: 33 Java projects
- **Scale**: >1 million commit samples
- **Initial Features**: commit_sha, date, file, lines_added, lines_removed, notes

### Data Pipeline
```
Technical Debt Dataset (gitcommitchanges.csv)
    ↓ CSV Structure Fixing & Feature Extraction
Enhanced Dataset (enhanced_gitcommitchanges.csv)
    ↓ GitHub API Build Labeling
Labeled Dataset (labeled_git_commit_changes.csv)
```

### Implementation Files
| Component | File | Purpose |
|-----------|------|---------|
| **Data Processor** | `get_metadata_from_commit.py` | Fixes CSV structure, extracts commit features |
| **Build Labeler** | `label.py` | Attempts build outcome labeling via GitHub API |
| **Data Inspector** | `data.py` | Dataset analysis and validation |

### Features Extracted
**Basic Commit Features**:
- `files_changed` - Number of files modified per commit
- `has_fix_keyword` - Presence of fix-related keywords in commit messages
- `changed_tests` - Boolean indicating test file modifications
- `lines_added/removed` - Code change volume metrics

**Attempted Build Labels**:
- `build_label` - Build outcome attempts: `passed`, `failed`, `no_ci`, `unknown`
- `remote_has_ci` - CI/CD pipeline detection
- `remote_has_pr` - Pull request association

### Usage Example
```bash
# Step 1: Process Technical Debt Dataset
python Approach1/get_metadata_from_commit.py

# Step 2: Attempt build outcome labeling
python Approach1/label.py --token $GITHUB_TOKEN

# Step 3: Analyze results
python data.py
```

### Pros ✅
- **Massive Scale**: Access to >1 million commit samples
- **Established Projects**: Data from mature Apache Software Foundation projects
- **Historical Depth**: Long-term project evolution data
- **Java Focus**: Consistent technology stack across projects
- **Rich Metadata**: Detailed commit information already available
- **No Repository Cloning**: Works with existing CSV data
- **Fast Processing**: Efficient handling of large datasets

### Cons ❌
- **Labeling Challenges**: Many GitHub Actions return 'pending' or 'not_processed'
- **Missing Build Data**: Historical commits often lack corresponding CI/CD runs
- **Old Projects**: Some Apache projects may have outdated CI/CD practices
- **Limited Build Context**: Difficulty correlating commits with actual build outcomes
- **API Limitations**: GitHub API may not have historical build data for older commits
- **Inconsistent CI/CD**: Varied CI/CD adoption across different Apache projects
- **Data Quality Issues**: Some commits may not have clear build outcome mappings

### Current Limitations
- **Build Labeling Ineffective**: Most attempts result in 'pending' or 'not_processed' status
- **Historical Gap**: Older commits lack modern CI/CD pipeline data
- **Correlation Issues**: Difficulty matching commits to corresponding builds

---

## Approach 2: Fresh Public Repository Mining

**Best suited for**: Research projects requiring clean build labels, modern CI/CD analysis

### Overview
This approach collects fresh data directly from public GitHub repositories with active GitHub Actions workflows. It first extracts build outcome data (id, sha, conclusion) from GitHub Actions, then uses PyDriller to mine detailed commit metadata, ensuring accurate build-commit correlation.

### Data Source
- **Origin**: Live public GitHub repositories
- **Selection Criteria**: Active GitHub Actions workflows
- **Scale**: Smaller datasets (hundreds to thousands of commits)
- **Quality**: High-quality build outcome labels

### Data Pipeline
```
Public GitHub Repository
    ↓ GitHub Actions Data Collection
Build Outcomes (gha_runs.json)
    ↓ PyDriller Commit Mining
Labeled Dataset (pr_dataset.csv)
```

### Implementation Files
| Component | File | Purpose |
|-----------|------|---------|
| **Build Collector** | `github_actions_pull.py` | Extracts GitHub Actions workflow results |
| **Repository Miner** | `mine.py` | Mines commit data using PyDriller with build correlation |

### Features Extracted
**Build Outcome Labels**:
- `pipeline_failed` - Binary target variable (0=success, 1=failure)
- `conclusion` - Detailed build status from GitHub Actions

**Detailed Git Metrics**:
- `lines_added/deleted` - Precise line counts from git diffs
- `changed_tests` - Count of modified test files
- `files_changed` - Number of files modified
- `has_fix_keyword` - Fix-related keyword detection
- `commit_hash` - Unique commit identifier
- `author_date` - Commit timestamp

**Advanced Features** (via PyDriller):
- File-level change analysis
- Commit message sentiment analysis
- Developer activity patterns
- Code complexity metrics

### Usage Example
```bash
# Step 1: Collect GitHub Actions build data
python Approach2/github_actions_pull.py \
  --owner facebook \
  --repo react \
  --token $GITHUB_TOKEN \
  --out gha_runs.json

# Step 2: Mine repository data with build correlation
python Approach2/mine.py \
  --gha_json gha_runs.json \
  --local_repo /path/to/react \
  --out_csv pr_dataset.csv

# Alternative: Remote repository mining
python Approach2/mine.py \
  --gha_json gha_runs.json \
  --repo_url https://github.com/facebook/react \
  --out_csv pr_dataset.csv
```

### Pros ✅
- **Clean Build Labels**: Direct correlation between commits and build outcomes
- **Modern CI/CD**: Works with current GitHub Actions workflows
- **High Data Quality**: Accurate build-commit relationships
- **Rich Feature Set**: Comprehensive git metadata via PyDriller
- **Flexible Repository Selection**: Can target specific types of projects
- **Real-time Data**: Fresh data from active development
- **Precise Measurements**: Exact line counts and file modifications

### Cons ❌
- **Limited Scale**: Smaller datasets compared to historical approaches
- **Public Repository Constraint**: Limited to publicly accessible repositories
- **Processing Intensive**: Slower due to full repository analysis
- **Storage Requirements**: Needs local repository clones for optimal performance
- **Setup Complexity**: More complex configuration and dependencies
- **Repository Dependency**: Requires active GitHub Actions workflows
- **Network Intensive**: Repository cloning can be bandwidth-heavy

### Current Status
- **Data Volume**: Limited to public repositories with active CI/CD
- **Quality Focus**: Emphasis on accurate build outcome labeling
- **Scalability Challenge**: Need to expand to more repositories for larger datasets

---

## Approach Comparison

| Aspect | Approach 1 (Technical Debt) | Approach 2 (Fresh Mining) |
|--------|------------------------------|----------------------------|
| **Dataset Size** | >1 million samples | Hundreds to thousands |
| **Data Quality** | High volume, poor labels | Lower volume, high-quality labels |
| **Build Labeling** | Problematic (pending/not_processed) | Accurate (success/failure) |
| **Processing Speed** | Fast (CSV processing) | Slow (full git analysis) |
| **Historical Depth** | Extensive (years of data) | Recent (active projects) |
| **Setup Complexity** | Low | Medium-High |
| **Research Value** | Large-scale analysis | Precise prediction models |
| **Reproducibility** | High | Medium |

## Research Challenges & Solutions

### Current Challenges
1. **Approach 1 Labeling Issues**: Historical commits lack corresponding build data
2. **Approach 2 Scale Limitations**: Limited to public repositories with active CI/CD
3. **Feature Engineering**: Need for dependency and environment-related features

### Future Development Directions
- **Enhanced Feature Collection**: 
  - Dependency change analysis
  - Environment configuration tracking
  - Code complexity metrics
  - Developer experience indicators

- **Improved Labeling Strategies**:
  - Alternative build outcome sources
  - Hybrid labeling approaches
  - Manual validation for critical samples

- **Scale Expansion**:
  - Multi-repository data collection
  - Cross-language project analysis
  - Enterprise repository integration

## Choosing the Right Approach

### Use Approach 1 when:
- You need large-scale datasets for statistical analysis
- You're studying long-term software evolution patterns
- You have computational resources for processing large datasets
- Build outcome accuracy is less critical than sample size

### Use Approach 2 when:
- You need accurate build outcome labels for ML model training
- You're focusing on modern CI/CD practices
- You can work with smaller, high-quality datasets
- You need detailed git analysis features

## Dependencies

```
pandas>=1.3.0      # Data manipulation and CSV processing
requests>=2.25.0   # GitHub API communication
chardet>=4.0.0     # Character encoding detection for CSV files
pydriller>=2.0     # Git repository mining (Approach 2 only)
```

## Getting Started

1. **For large-scale analysis**: Start with Approach 1 and the Technical Debt Dataset
2. **For ML model training**: Use Approach 2 for clean, labeled data
3. **For research comparison**: Implement both approaches on overlapping repositories
4. **For production systems**: Consider hybrid approaches combining both methods



