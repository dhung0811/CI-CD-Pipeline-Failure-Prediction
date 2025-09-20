import argparse, json, os
import pandas as pd
from pydriller import Repository

def load_labels(gha_json_path):
    with open(gha_json_path, "r", encoding="utf-8") as f:
        runs = json.load(f)
    labels = {}
    for run in runs:
        sha = run.get("head_sha")
        conclusion = (run.get("conclusion") or "").lower()
        if sha and conclusion in ("success", "failure"):
            labels[sha] = 0 if conclusion == "success" else 1
    return labels

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gha_json", required=True, help="Path to gha_runs.json")
    ap.add_argument("--out_csv", default="data/processed/pr_dataset.csv")
    # Choose ONE of these:
    ap.add_argument("--local_repo", help="Path to a local git clone (recommended on Windows)")
    ap.add_argument("--repo_url", help="Remote repo URL (if you don't have a local clone)")
    ap.add_argument("--cache_dir", help="Folder to cache remote clones (e.g., C:\\repos\\cache)")
    args = ap.parse_args()

    os.makedirs(os.path.dirname(args.out_csv), exist_ok=True)

    sha_to_label = load_labels(args.gha_json)
    if not sha_to_label:
        raise SystemExit("No labeled SHAs found in gha_json (need success/failure).")

    # Build RepositoryMining parameters
    rm_kwargs = {"only_commits": list(sha_to_label.keys())}
    if args.local_repo:
        repo_source = args.local_repo  # local path
    elif args.repo_url:
        repo_source = args.repo_url    # remote URL
        if args.cache_dir:
            rm_kwargs["clone_repo_to"] = args.cache_dir  # persistent clone to avoid temp cleanup
    else:
        raise SystemExit("Provide either --local_repo or --repo_url (optionally with --cache_dir).")

    rows = []
    # Traverse commits
    for commit in Repository(repo_source, **rm_kwargs).traverse_commits():
        # Robust per-commit aggregation
        mf_list = commit.modified_files or []
        files_changed = len(mf_list)
        lines_added = sum((mf.added_lines or 0) for mf in mf_list)
        lines_deleted = sum((mf.deleted_lines or 0) for mf in mf_list)

        # Simple keywords in message
        msg = (commit.msg or "").lower()
        has_fix_keyword = int(("fix" in msg) or ("bug" in msg))

        # Count test files changed
        def is_test(mf):
            p1 = (mf.new_path or "") .lower()
            p2 = (mf.old_path or "") .lower()
            return ("test" in p1) or ("tests" in p1) or ("test" in p2) or ("tests" in p2)

        changed_tests = sum(1 for mf in mf_list if is_test(mf))

        label = sha_to_label.get(commit.hash)
        if label is None:
            # SHA not matched (e.g., CI ran on a merge/PR ref not in default history); skip
            continue

        rows.append({
            "commit_hash": commit.hash,
            "lines_added": lines_added,
            "lines_deleted": lines_deleted,
            "files_changed": files_changed,
            "has_fix_keyword": has_fix_keyword,
            "changed_tests": changed_tests,
            "pipeline_failed": label
        })

    if not rows:
        raise SystemExit("No rows mined. Check that your SHAs exist in this repo/branch history.")

    df = pd.DataFrame(rows).drop_duplicates(subset=["commit_hash"])
    
    # Check if output file exists to determine if we need headers
    file_exists = os.path.exists(args.out_csv)
    
    # Append to existing file or create new one
    df.to_csv(args.out_csv, mode='a', header=not file_exists, index=False, encoding="utf-8")
    
    action = "Appended" if file_exists else "Saved"
    print(f"{action} {len(df)} rows to {args.out_csv}")

if __name__ == "__main__":
    main()
