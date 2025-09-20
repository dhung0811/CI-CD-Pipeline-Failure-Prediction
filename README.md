
# Build Failure Prediction Dataset Creation



## Approach 1: Technical Debt Dataset Enhancement



### Overview
This approach leverages the existing Technical Debt Dataset from 33 Apache Software Foundation Java projects. The dataset contains over 1 million commit samples with basic metadata (commit_sha, date, file, lines_added, lines_removed, notes). We enhance this data by extracting additional features and attempting to label build outcomes via GitHub API.

### Data Source
- **Origin**: Technical Debt Dataset (Apache Software Foundation)
- **Projects**: 33 Java projects
- **Scale**: >1 million commit samples
- **Initial Features**: commit_sha, date, file, lines_added, lines_removed, notes

### Data Pipeline
git_commit.csv![git_commit](access/git_commit_changes.png
)
↓
enhanced_git_commit.csv![enhanced_git_commit](access/enhanced_git_commit_changes.png)
↓
labeled_git_commit.csv![labeld_git_commit](access/labeled_git_commit_changes.png)
```
Technical Debt Dataset (gitcommitchanges.csv)
     CSV Structure Fixing & Feature Extraction
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

### Dataset Structure

**Input CSV Structure** (Technical Debt Dataset):
```
PROJECT_ID, FILE, COMMIT_HASH, DATE, COMMITTER_ID, LINES_ADDED, LINES_REMOVED, NOTE
```

**Enhanced CSV Structure** (after get_metadata_from_commit.py):
```
PROJECT_ID, FILE, COMMIT_HASH, DATE, COMMITTER_ID, LINES_ADDED, LINES_REMOVED, NOTE,
has_fix_keyword, files_changed, changed_tests
```

**Final Labeled CSV Structure** (after label.py):
```
PROJECT_ID, FILE, COMMIT_HASH, DATE, COMMITTER_ID, LINES_ADDED, LINES_REMOVED, NOTE,
has_fix_keyword, files_changed, changed_tests, build_label, remote_files_changed,
remote_additions, remote_deletions, remote_has_ci, remote_has_pr, gha_workflow_names
```

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

### Pros
- **Massive Scale**: Access to >1 million commit samples
- **Established Projects**: Data from mature Apache Software Foundation projects
- **Historical Depth**: Long-term project evolution data
- **Java Focus**: Consistent technology stack across projects
- **Rich Metadata**: Detailed commit information already available
- **No Repository Cloning**: Works with existing CSV data
- **Fast Processing**: Efficient handling of large datasets

### Cons
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

### Dataset Structure

**GitHub Actions JSON Structure** (gha_runs.json):
```json
{
  "id": "workflow_run_id",
  "head_sha": "commit_hash", 
  "conclusion": "success|failure|cancelled|skipped",
  "event": "push|pull_request",
  "workflow_name": "CI workflow name"
}
```

**Final CSV Structure** (pr_dataset.csv):
```
commit_hash, lines_added, lines_deleted, files_changed, has_fix_keyword, changed_tests, pipeline_failed
```

### Features Extracted
**Build Outcome Labels**:
- `pipeline_failed` - Binary target variable (0=success, 1=failure)
- `conclusion` - Detailed build status from GitHub Actions

**Detailed Git Metrics**:
- `lines_added/deleted` - Precise line counts from git diffs
- `changed_tests` - Count of modified test files
- `files_changed` - Number of files modified
- `has_fix_keyword` - Fix-related keyword detection (0/1)
- `commit_hash` - Unique commit identifier

**Advanced Features** (via PyDriller):
- File-level change analysis
- Commit message sentiment analysis
- Developer activity patterns
- Code complexity metrics


### Pros
- **Clean Build Labels**: Direct correlation between commits and build outcomes
- **Modern CI/CD**: Works with current GitHub Actions workflows
- **High Data Quality**: Accurate build-commit relationships
- **Rich Feature Set**: Comprehensive git metadata via PyDriller
- **Flexible Repository Selection**: Can target specific types of projects
- **Real-time Data**: Fresh data from active development
- **Precise Measurements**: Exact line counts and file modifications

### Cons
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

## Data Schema Reference

### Column Descriptions

**Common Columns (Both Approaches)**:
| Column | Type | Description | Example |
|--------|------|-------------|---------|
| `commit_hash` | string | SHA-1 commit identifier | `e45ddd17242da2dc479e69f613563f68efa66170` |
| `lines_added` | integer | Number of lines added in commit | `68` |
| `lines_deleted` | integer | Number of lines removed in commit | `7` |
| `files_changed` | integer | Number of files modified | `3` |
| `has_fix_keyword` | boolean/integer | Contains fix-related keywords (fix, bug) | `1` (True) or `0` (False) |
| `changed_tests` | boolean/integer | Test files were modified | `1` (True) or `0` (False) |

**Approach 1 Specific Columns**:
| Column | Type | Description | Example |
|--------|------|-------------|---------|
| `PROJECT_ID` | string | Apache project identifier | `org.apache:maven` |
| `FILE` | string | Modified file path | `src/main/java/Main.java` |
| `DATE` | datetime | Commit timestamp | `2023-01-15 14:30:00+00:00` |
| `COMMITTER_ID` | string | Committer identifier | `john.doe` |
| `NOTE` | string | Commit message | `fix: resolve null pointer exception` |
| `build_label` | string | Build outcome | `passed`, `failed`, `no_ci`, `unknown` |
| `remote_has_ci` | boolean | Has CI/CD pipeline | `True`/`False` |
| `remote_has_pr` | boolean | Part of pull request | `True`/`False` |

**Approach 2 Specific Columns**:
| Column | Type | Description | Example |
|--------|------|-------------|---------|
| `pipeline_failed` | integer | Binary build outcome | `0` (success) or `1` (failure) |

### Sample Data

**Approach 1 Sample** (labeled_git_commit_changes.csv):
```csv
PROJECT_ID,FILE,COMMIT_HASH,DATE,COMMITTER_ID,LINES_ADDED,LINES_REMOVED,NOTE,has_fix_keyword,files_changed,changed_tests,build_label,remote_has_ci,remote_has_pr
org.apache:maven,pom.xml,abc123...,2023-01-15 14:30:00,john.doe,5,2,"fix: update dependency",1,2,0,passed,1,1
```

**Approach 2 Sample** (pr_dataset.csv):
```csv
commit_hash,lines_added,lines_deleted,files_changed,has_fix_keyword,changed_tests,pipeline_failed
e45ddd17242da2dc479e69f613563f68efa66170,68,7,2,0,1,0
24409692b6400116f732a13dd18541df56c46121,17,2,1,0,0,0
```

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

## Data Management

### Large File Handling
The CSV datasets generated by this project can be very large (>100MB), especially for Approach 1 with the Technical Debt Dataset. These files are excluded from git tracking via `.gitignore` to avoid GitHub's file size limits.

**File Size Expectations**:
- `gitcommitchanges.csv`: ~365MB (original Technical Debt Dataset)
- `enhanced_gitcommitchanges.csv`: ~309MB (with extracted features)
- `labeled_git_commit_changes.csv`: ~350MB (final labeled dataset)
- `pr_dataset.csv`: <10MB (Approach 2 output)

### Data Storage Options

**For Research/Development**:
- Store datasets locally in project directories
- Use cloud storage (Google Drive, Dropbox) for sharing
- Consider data compression (gzip) to reduce file sizes

**For Production/Collaboration**:
- Use Git LFS (Large File Storage) for version control
- Set up dedicated data storage (AWS S3, Google Cloud Storage)
- Implement data versioning and lineage tracking

### Setting up Git LFS (Optional)
If you need to version control large datasets:

```bash
# Install Git LFS
git lfs install

# Track CSV files with LFS
git lfs track "*.csv"
git add .gitattributes

# Add and commit files
git add Approach1/*.csv Approach2/*.csv
git commit -m "Add datasets via Git LFS"
git push
```

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

### Quick Setup
```bash
# Clone the repository
git clone https://github.com/your-username/your-repo.git
cd your-repo

# Install dependencies
pip install -r requirements.txt

# Set up GitHub token
export GITHUB_TOKEN="your_token_here"

# Run Approach 1 (if you have the Technical Debt Dataset)
python Approach1/get_metadata_from_commit.py
python Approach1/label.py --token $GITHUB_TOKEN

# Or run Approach 2 (for fresh data collection)
python Approach2/github_actions_pull.py --owner OWNER --repo REPO --token $GITHUB_TOKEN --out gha_runs.json
python Approach2/mine.py --gha_json gha_runs.json --local_repo /path/to/repo --out_csv pr_dataset.csv
```

### Approach Selection Guide
1. **For large-scale analysis**: Start with Approach 1 and the Technical Debt Dataset
2. **For ML model training**: Use Approach 2 for clean, labeled data
3. **For research comparison**: Implement both approaches on overlapping repositories
4. **For production systems**: Consider hybrid approaches combining both methods









