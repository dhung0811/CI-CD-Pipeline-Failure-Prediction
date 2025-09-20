# GitHub Actions workflow runs -> CSV with head_sha + conclusion
# Usage: python src/collect/github_actions_pull.py --owner ORG --repo REPO --token $GITHUB_TOKEN --out data/raw/gha_runs.json
import argparse, requests, json, os

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--owner", required=True)
    ap.add_argument("--repo", required=True)
    ap.add_argument("--token", required=True, help="GitHub Personal Access Token")
    ap.add_argument("--out", required=True)
    ap.add_argument("--per_page", type=int, default=100)
    args = ap.parse_args()

    url = f"https://api.github.com/repos/{args.owner}/{args.repo}/actions/runs"
    headers = {"Authorization": f"token {args.token}", "Accept": "application/vnd.github+json"}
    params = {"per_page": args.per_page, "page": 1}
    all_runs = []
    while True:
        r = requests.get(url, headers=headers, params=params, timeout=30)
        r.raise_for_status()
        data = r.json()
        runs = data.get("workflow_runs", [])
        if not runs:
            break
        all_runs.extend([
            {
                "id": run["id"],
                "head_sha": run.get("head_sha"),
                "conclusion": run.get("conclusion"),
                "event": run.get("event"),
                "created_at": run.get("created_at")
            } for run in runs
        ])
        params["page"] += 1
        if params["page"] > 30:  # cap pages for safety; adjust as needed
            break

    # Load existing runs if file exists
    existing_runs = []
    if os.path.exists(args.out):
        try:
            with open(args.out, "r", encoding="utf-8") as f:
                existing_runs = json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            existing_runs = []
    
    # Get existing run IDs to avoid duplicates
    existing_ids = {run.get("id") for run in existing_runs if run.get("id")}
    
    # Filter out runs that already exist
    new_runs = [run for run in all_runs if run.get("id") not in existing_ids]
    
    # Combine existing and new runs
    combined_runs = existing_runs + new_runs
    
    # Write combined data back to file
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(combined_runs, f, indent=2)
    
    action = "Added" if existing_runs else "Wrote"
    print(f"{action} {len(new_runs)} new runs to {args.out} (total: {len(combined_runs)})")

if __name__ == "__main__":
    main()
