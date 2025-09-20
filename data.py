import pandas as pd

# Fix dtype warning by specifying data types and handling mixed types
dtype_dict = {
    'PROJECT_ID': 'str',
    'FILE': 'str', 
    'COMMIT_HASH': 'str',
    'DATE': 'str',
    'COMMITTER_ID': 'str',
    'LINES_ADDED': 'str',  # Read as string first to handle mixed types
    'LINES_REMOVED': 'str',  # Read as string first to handle mixed types
    'NOTE': 'str'
}

raw_data = pd.read_csv("enhanced_gitcommitchanges.csv", dtype=dtype_dict, low_memory=False)

# Clean and convert numeric columns
def clean_numeric_column(col):
    """Clean and convert column to numeric, handling mixed types"""
    return pd.to_numeric(col.astype(str).str.replace(r'[^\d.-]', '', regex=True), errors='coerce').fillna(0).astype(int)

raw_data['LINES_ADDED'] = clean_numeric_column(raw_data['LINES_ADDED'])
raw_data['LINES_REMOVED'] = clean_numeric_column(raw_data['LINES_REMOVED'])

print(f"Loaded {len(raw_data)} rows")
print(f"Data types:")
print(raw_data.dtypes)
print(f"\nFirst few rows:")
print(raw_data.head())

# Show sample of cleaned numeric columns
print(f"\nSample LINES_ADDED values: {raw_data['LINES_ADDED'].head().tolist()}")
print(f"Sample LINES_REMOVED values: {raw_data['LINES_REMOVED'].head().tolist()}")

# Show basic stats
print(f"\nDataset shape: {raw_data.shape}")
print(f"Columns: {list(raw_data.columns)}")
