#!/usr/bin/env python3
"""
Remote build labeler using only GitHub API - no local cloning required
"""

import pandas as pd
import requests
import time
from typing import Dict, List, Optional
import json

class RemoteBuildLabeler:
    def __init__(self, github_token: str):
        if not github_token:
            raise ValueError("GitHub token is required for remote API access")
        
        self.github_token = github_token
        self.headers = {
            'Authorization': f'token {github_token}',
            'Accept': 'application/vnd.github.v3+json'
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        
        # Rate limiting
        self.api_calls = 0
        self.start_time = time.time()

    def check_rate_limit(self):
        """Check and handle GitHub API rate limiting"""
        self.api_calls += 1
        
        # Check rate limit every 50 calls
        if self.api_calls % 50 == 0:
            try:
                response = self.session.get('https://api.github.com/rate_limit')
                if response.status_code == 200:
                    data = response.json()
                    remaining = data['rate']['remaining']
                    reset_time = data['rate']['reset']
                    
                    print(f"API calls made: {self.api_calls}, Remaining: {remaining}")
                    
                    if remaining < 100:
                        wait_time = reset_time - time.time() + 60
                        if wait_time > 0:
                            print(f"Rate limit low, waiting {wait_time:.0f} seconds...")
                            time.sleep(wait_time)
            except:
                pass
        
        # Basic rate limiting
        time.sleep(0.1)

    def extract_github_info(self, project_id: str) -> Optional[Dict[str, str]]:
        """Extract GitHub owner and repo from project_id"""
        if project_id.startswith('org.apache:'):
            repo = project_id.split(':')[1]
            return {'owner': 'apache', 'repo': repo}
        elif ':' in project_id:
            parts = project_id.split(':')
            if len(parts) >= 2:
                owner = parts[0].replace('org.', '').replace('com.', '')
                repo = parts[1]
                return {'owner': owner, 'repo': repo}
        elif '/' in project_id:
            parts = project_id.split('/')
            if len(parts) >= 2:
                return {'owner': parts[0], 'repo': parts[1]}
        return None

    def get_commit_details_api(self, owner: str, repo: str, commit_hash: str) -> Optional[Dict]:
        """Get commit details using GitHub API"""
        url = f"https://api.github.com/repos/{owner}/{repo}/commits/{commit_hash}"
        
        try:
            self.check_rate_limit()
            response = self.session.get(url)
            
            if response.status_code == 200:
                data = response.json()
                
                # Extract relevant information
                stats = data.get('stats', {})
                files = data.get('files', [])
                
                # Analyze file changes
                test_files = 0
                file_types = {}
                
                for file_info in files:
                    filename = file_info.get('filename', '')
                    
                    # Check if test file
                    if self.is_test_file(filename):
                        test_files += 1
                    
                    # Count file types
                    ext = filename.split('.')[-1].lower() if '.' in filename else 'no_ext'
                    file_types[ext] = file_types.get(ext, 0) + 1
                
                return {
                    'files_changed': len(files),
                    'additions': stats.get('additions', 0),
                    'deletions': stats.get('deletions', 0),
                    'total_changes': stats.get('total', 0),
                    'test_files_changed': test_files,
                    'has_test_changes': test_files > 0,
                    'file_types': file_types,
                    'commit_message': data.get('commit', {}).get('message', ''),
                    'author': data.get('commit', {}).get('author', {}).get('name', ''),
                    'date': data.get('commit', {}).get('author', {}).get('date', ''),
                    'parents_count': len(data.get('parents', [])),
                    'is_merge': len(data.get('parents', [])) > 1
                }
            elif response.status_code == 404:
                print(f"Commit {commit_hash} not found in {owner}/{repo}")
                return None
            else:
                print(f"Error fetching commit {commit_hash}: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"Exception fetching commit {commit_hash}: {e}")
            return None

    def is_test_file(self, filename: str) -> bool:
        """Check if filename is a test file"""
        import re
        test_patterns = [
            r'test.*\.py$', r'.*test\.py$', r'.*_test\.py$',
            r'test.*\.java$', r'.*Test\.java$', r'.*Tests\.java$',
            r'test.*\.js$', r'.*test\.js$', r'.*\.test\.js$',
            r'test.*\.ts$', r'.*test\.ts$', r'.*\.test\.ts$',
            r'.*\.spec\.(js|ts|py|java)$',
            r'.*/tests?/.*', r'.*/test/.*'
        ]
        return any(re.search(pattern, filename, re.IGNORECASE) for pattern in test_patterns)

    def get_github_actions_status(self, owner: str, repo: str, commit_hash: str) -> Dict:
        """Search GitHub Actions builds using commit SHA and extract detailed metadata"""
        print(f"    🔍 Searching GitHub Actions for commit SHA: {commit_hash[:8]}...")
        
        url = f"https://api.github.com/repos/{owner}/{repo}/actions/runs"
        params = {'head_sha': commit_hash, 'per_page': 100}
        
        try:
            self.check_rate_limit()
            response = self.session.get(url, params=params)
            
            if response.status_code == 200:
                data = response.json()
                runs = data.get('workflow_runs', [])
                
                if not runs:
                    print(f"    No GitHub Actions found for SHA {commit_hash[:8]}")
                    return self.get_commit_status_checks(owner, repo, commit_hash)
                
                print(f"    Found {len(runs)} GitHub Actions runs for SHA {commit_hash[:8]}")
                
                # Extract detailed metadata from each run
                run_details = []
                for run in runs:
                    run_detail = {
                        'id': run.get('id'),
                        'name': run.get('name', 'unknown'),
                        'status': run.get('status'),
                        'conclusion': run.get('conclusion'),
                        'event': run.get('event'),
                        'created_at': run.get('created_at'),
                        'updated_at': run.get('updated_at'),
                        'run_number': run.get('run_number'),
                        'workflow_id': run.get('workflow_id'),
                        'url': run.get('html_url')
                    }
                    run_details.append(run_detail)
                
                # Analyze workflow runs for labeling
                conclusions = [run.get('conclusion') for run in runs if run.get('conclusion')]
                statuses = [run.get('status') for run in runs]
                events = [run.get('event') for run in runs]
                
                # Count different outcomes
                success_count = conclusions.count('success')
                failure_count = conclusions.count('failure')
                cancelled_count = conclusions.count('cancelled')
                skipped_count = conclusions.count('skipped')
                
                # Determine build label based on GitHub Actions metadata
                if failure_count > 0:
                    build_conclusion = 'failed'
                    print(f"     LABEL: FAILED ({failure_count} failed runs)")
                elif success_count > 0 and failure_count == 0:
                    build_conclusion = 'passed'
                    print(f"     LABEL: PASSED ({success_count} successful runs)")
                elif cancelled_count > 0:
                    build_conclusion = 'cancelled'
                    print(f"     LABEL: CANCELLED ({cancelled_count} cancelled runs)")
                elif conclusions:
                    build_conclusion = 'mixed'
                    print(f"     LABEL: MIXED (various outcomes)")
                else:
                    build_conclusion = 'pending'
                    print(f"     LABEL: PENDING (no conclusions yet)")
                
                # Calculate timing metrics
                run_durations = []
                for run in runs:
                    if run.get('created_at') and run.get('updated_at'):
                        try:
                            from datetime import datetime
                            created = datetime.fromisoformat(run['created_at'].replace('Z', '+00:00'))
                            updated = datetime.fromisoformat(run['updated_at'].replace('Z', '+00:00'))
                            duration = (updated - created).total_seconds()
                            run_durations.append(duration)
                        except:
                            pass
                
                avg_duration = sum(run_durations) / len(run_durations) if run_durations else 0
                
                return {
                    'build_conclusion': build_conclusion,
                    'total_workflows': len(runs),
                    'success_workflows': success_count,
                    'failure_workflows': failure_count,
                    'cancelled_workflows': cancelled_count,
                    'skipped_workflows': skipped_count,
                    'has_ci': True,
                    'workflow_names': [run.get('name', 'unknown') for run in runs],
                    'workflow_events': list(set(events)),
                    'run_details': run_details[:3],  # Store first 3 runs for reference
                    'avg_run_duration_seconds': avg_duration,
                    'latest_run_id': runs[0].get('id') if runs else None,
                    'latest_run_url': runs[0].get('html_url') if runs else None
                }
            else:
                print(f"     GitHub Actions API error {response.status_code} for SHA {commit_hash[:8]}")
                return self.get_commit_status_checks(owner, repo, commit_hash)
                
        except Exception as e:
            print(f"     Exception getting GitHub Actions for {commit_hash}: {e}")
            return {'build_conclusion': 'error', 'has_ci': False}

    def get_commit_status_checks(self, owner: str, repo: str, commit_hash: str) -> Dict:
        """Get commit status checks as fallback"""
        url = f"https://api.github.com/repos/{owner}/{repo}/commits/{commit_hash}/status"
        
        try:
            self.check_rate_limit()
            response = self.session.get(url)
            
            if response.status_code == 200:
                data = response.json()
                state = data.get('state', 'unknown')
                statuses = data.get('statuses', [])
                
                # Map GitHub status to our labels
                if state == 'success':
                    build_conclusion = 'passed'
                elif state in ['failure', 'error']:
                    build_conclusion = 'failed'
                elif state == 'pending':
                    build_conclusion = 'pending'
                else:
                    build_conclusion = 'unknown'
                
                return {
                    'build_conclusion': build_conclusion,
                    'has_ci': len(statuses) > 0,
                    'status_checks': len(statuses),
                    'status_contexts': [s.get('context', 'unknown') for s in statuses[:5]]
                }
            else:
                return {'build_conclusion': 'no_ci', 'has_ci': False}
                
        except Exception as e:
            print(f"Error getting status checks for {commit_hash}: {e}")
            return {'build_conclusion': 'error', 'has_ci': False}

    def get_workflow_run_details(self, owner: str, repo: str, run_id: int) -> Dict:
        """Get detailed information about a specific workflow run"""
        if not run_id:
            return {}
            
        url = f"https://api.github.com/repos/{owner}/{repo}/actions/runs/{run_id}"
        
        try:
            self.check_rate_limit()
            response = self.session.get(url)
            
            if response.status_code == 200:
                run_data = response.json()
                
                # Get job details
                jobs_url = f"https://api.github.com/repos/{owner}/{repo}/actions/runs/{run_id}/jobs"
                jobs_response = self.session.get(jobs_url)
                jobs_data = jobs_response.json() if jobs_response.status_code == 200 else {}
                jobs = jobs_data.get('jobs', [])
                
                # Analyze job outcomes
                job_conclusions = [job.get('conclusion') for job in jobs if job.get('conclusion')]
                failed_jobs = [job.get('name') for job in jobs if job.get('conclusion') == 'failure']
                
                return {
                    'run_attempt': run_data.get('run_attempt', 1),
                    'total_jobs': len(jobs),
                    'failed_jobs': failed_jobs,
                    'failed_job_count': len(failed_jobs),
                    'job_conclusions': job_conclusions,
                    'workflow_file': run_data.get('path', ''),
                    'trigger_event': run_data.get('event', ''),
                    'run_started_at': run_data.get('run_started_at'),
                    'actor': run_data.get('actor', {}).get('login', 'unknown')
                }
            else:
                return {}
                
        except Exception as e:
            print(f"      Error getting workflow run details: {e}")
            return {}

    def get_pull_request_info(self, owner: str, repo: str, commit_hash: str) -> Dict:
        """Get pull request information for commit"""
        url = f"https://api.github.com/repos/{owner}/{repo}/commits/{commit_hash}/pulls"
        
        try:
            self.check_rate_limit()
            response = self.session.get(url)
            
            if response.status_code == 200:
                pulls = response.json()
                if pulls:
                    pr = pulls[0]  # First PR
                    return {
                        'has_pr': True,
                        'pr_number': pr.get('number'),
                        'pr_state': pr.get('state'),
                        'pr_merged': pr.get('merged', False),
                        'pr_title': pr.get('title', '')
                    }
            
            return {'has_pr': False}
            
        except Exception as e:
            print(f"Error getting PR info for {commit_hash}: {e}")
            return {'has_pr': False}

    def process_commits_remote(self, df: pd.DataFrame, max_commits: int = 1000) -> pd.DataFrame:
        """Process commits using only remote GitHub API"""
        
        # Get unique commits to avoid duplicates
        unique_commits = df[['PROJECT_ID', 'COMMIT_HASH']].drop_duplicates()
        
        if len(unique_commits) > max_commits:
            print(f"Limiting to first {max_commits} commits (out of {len(unique_commits)})")
            unique_commits = unique_commits.head(max_commits)
        
        print(f"Processing {len(unique_commits)} unique commits via GitHub API...")
        
        commit_data = {}
        processed = 0
        
        for idx, row in unique_commits.iterrows():
            project_id = row['PROJECT_ID']
            commit_hash = row['COMMIT_HASH']
            
            processed += 1
            print(f"Processing {processed}/{len(unique_commits)}: {project_id} - {commit_hash[:8]}")
            
            github_info = self.extract_github_info(project_id)
            if not github_info:
                print(f"  Could not extract GitHub info from: {project_id}")
                continue
            
            owner, repo = github_info['owner'], github_info['repo']
            
            # Get commit details
            commit_details = self.get_commit_details_api(owner, repo, commit_hash)
            if not commit_details:
                print(f"  Could not get commit details")
                continue
            
            # Get build status using commit SHA
            build_status = self.get_github_actions_status(owner, repo, commit_hash)
            
            # Get detailed workflow run information if we have a run ID
            workflow_details = {}
            if build_status.get('latest_run_id'):
                print(f"    🔍 Getting detailed workflow metadata...")
                workflow_details = self.get_workflow_run_details(owner, repo, build_status['latest_run_id'])
            
            # Get PR info
            pr_info = self.get_pull_request_info(owner, repo, commit_hash)
            
            # Combine all data including detailed workflow metadata
            commit_data[commit_hash] = {
                **commit_details,
                **build_status,
                **workflow_details,
                **pr_info,
                'project_id': project_id,
                'owner': owner,
                'repo': repo
            }
            
            # Show detailed results
            conclusion = build_status.get('build_conclusion', 'unknown')
            workflows = build_status.get('total_workflows', 0)
            files = commit_details.get('files_changed', 0)
            
            print(f"     Result: {conclusion.upper()}, Workflows: {workflows}, Files: {files}")
            
            # Progress update
            if processed % 10 == 0:
                elapsed = time.time() - self.start_time
                rate = processed / elapsed * 60  # commits per minute
                print(f"\n   Progress: {processed}/{len(unique_commits)} ({rate:.1f} commits/min)")
                print(f"    Elapsed: {elapsed/60:.1f} minutes\n")
        
        # Add data to dataframe
        print("Adding data to dataframe...")
        
        # Map commit data to all rows
        basic_cols = ['build_conclusion', 'files_changed', 'additions', 'deletions', 
                     'has_test_changes', 'is_merge', 'has_ci', 'has_pr']
        
        # Add GitHub Actions specific metadata
        gha_cols = ['total_workflows', 'success_workflows', 'failure_workflows', 
                   'cancelled_workflows', 'avg_run_duration_seconds', 'latest_run_id']
        
        all_cols = basic_cols + gha_cols
        
        for col in all_cols:
            default_val = 'not_processed' if col == 'build_conclusion' else 0
            df[f'gha_{col}'] = df['COMMIT_HASH'].map(
                lambda x: commit_data.get(x, {}).get(col, default_val)
            )
        
        # Create final build label based on GitHub Actions metadata
        def create_build_label(conclusion):
            if conclusion == 'failed':
                return 'FAILED'
            elif conclusion == 'passed':
                return 'PASSED'
            elif conclusion == 'cancelled':
                return 'CANCELLED'
            elif conclusion == 'no_ci':
                return 'NO_CI'
            else:
                return 'UNKNOWN'
        
        df['build_label'] = df['gha_build_conclusion'].apply(create_build_label)
        
        # Add workflow names and events as string columns
        df['gha_workflow_names'] = df['COMMIT_HASH'].map(
            lambda x: ';'.join(commit_data.get(x, {}).get('workflow_names', []))
        )
        df['gha_workflow_events'] = df['COMMIT_HASH'].map(
            lambda x: ';'.join(commit_data.get(x, {}).get('workflow_events', []))
        )
        
        return df

def main():
    print("=== Remote Build Labeler (GitHub API Only) ===")
    
    # Get inputs
    input_file = input("Enter input CSV file (default: enhanced_git_commit_changes.csv): ").strip()
    if not input_file:
        input_file = 'enhanced_git_commit_changes.csv'
    
    output_file = input("Enter output CSV file (default: labeled_git_commit_changes.csv): ").strip()
    if not output_file:
        output_file = 'labeled_git_commit_changes.csv'
    
    github_token = input("Enter GitHub token (REQUIRED): ").strip()
    if not github_token:
        print("GitHub token is required for remote API access")
        return
    
    max_commits = input("Max commits to process (default: 1000): ").strip()
    try:
        max_commits = int(max_commits) if max_commits else 1000
    except:
        max_commits = 1000
    
    # Initialize labeler
    try:
        labeler = RemoteBuildLabeler(github_token)
    except ValueError as e:
        print(f"{e}")
        return
    
    # Read data
    print(f"\nReading {input_file}...")
    df = pd.read_csv(input_file)
    print(f"Loaded {len(df)} rows")
    
    # Process commits
    labeled_df = labeler.process_commits_remote(df, max_commits)
    
    # Save results
    labeled_df.to_csv(output_file, index=False)
    print(f"\nRemote labeled dataset saved to {output_file}")
    
    # Show summary
    label_counts = labeled_df['build_label'].value_counts()
    print(f"\nBuild Label Summary:")
    print(label_counts)
    
    # Show additional stats
    if 'remote_has_ci' in labeled_df.columns:
        ci_stats = labeled_df['remote_has_ci'].value_counts()
        print(f"\nCI/CD Coverage:")
        print(ci_stats)

if __name__ == "__main__":
    main()