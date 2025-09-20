#!/usr/bin/env python3

import pandas as pd
import csv
import re
from io import StringIO

def fix_csv_structure(input_file, output_file='fixed_gitcommitchanges.csv'):
    """Fix CSV structure issues like inconsistent field counts"""
    
    print(f"Analyzing CSV structure in {input_file}...")
    
    # Expected columns 
    expected_columns = ['PROJECT_ID', 'FILE', 'COMMIT_HASH', 'DATE', 'COMMITTER_ID', 'LINES_ADDED', 'LINES_REMOVED', 'NOTE']
    expected_field_count = len(expected_columns)
    
    fixed_rows = []
    problematic_lines = []
    
    # Try different encodings
    encodings = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']
    working_encoding = None
    
    for encoding in encodings:
        try:
            with open(input_file, 'r', encoding=encoding, errors='replace') as f:
                first_line = f.readline()
                working_encoding = encoding
                print(f"Using encoding: {encoding}")
                break
        except:
            continue
    
    if not working_encoding:
        working_encoding = 'utf-8'
    
    print("Reading and fixing CSV structure...")
    
    with open(input_file, 'r', encoding=working_encoding, errors='replace') as f:
        line_num = 0
        
        for line in f:
            line_num += 1
            line = line.strip()
            
            if not line:
                continue
            
            # Parse CSV line manually to handle embedded commas
            try:
                # Use csv.reader to properly handle quoted fields
                csv_reader = csv.reader(StringIO(line))
                fields = next(csv_reader)
                
                if len(fields) == expected_field_count:
                    fixed_rows.append(fields)
                elif len(fields) > expected_field_count:
                    # Too many fields - likely unescaped commas in NOTE field
                    # Merge extra fields into the NOTE field
                    fixed_fields = fields[:expected_field_count-1]  # All but NOTE
                    note_parts = fields[expected_field_count-1:]    # NOTE and extra parts
                    merged_note = ', '.join(note_parts)
                    fixed_fields.append(merged_note)
                    fixed_rows.append(fixed_fields)
                    
                    if len(problematic_lines) < 10:  # Show first 10 examples
                        problematic_lines.append((line_num, len(fields), line[:100]))
                
                elif len(fields) < expected_field_count:
                    # Too few fields - pad with empty strings
                    while len(fields) < expected_field_count:
                        fields.append('')
                    fixed_rows.append(fields)
                    
                    if len(problematic_lines) < 10:
                        problematic_lines.append((line_num, len(fields), line[:100]))
                
            except Exception as e:
                # If CSV parsing fails, try manual splitting
                fields = line.split(',')
                if len(fields) >= expected_field_count:
                    # Take first 7 fields, merge rest into NOTE
                    fixed_fields = fields[:expected_field_count-1]
                    merged_note = ', '.join(fields[expected_field_count-1:])
                    fixed_fields.append(merged_note)
                    fixed_rows.append(fixed_fields)
                else:
                    # Pad with empty fields
                    while len(fields) < expected_field_count:
                        fields.append('')
                    fixed_rows.append(fields)
            
            if line_num % 50000 == 0:
                print(f"Processed {line_num} lines, fixed {len(fixed_rows)} rows")
    
    print(f"\nProcessed {line_num} lines total")
    print(f"Fixed {len(fixed_rows)} rows")
    
    if problematic_lines:
        print(f"\nFound {len(problematic_lines)} problematic lines (showing first 10):")
        for line_num, field_count, sample in problematic_lines[:10]:
            print(f"  Line {line_num}: {field_count} fields - {sample}...")
    
    # Write fixed CSV
    print(f"\nWriting fixed CSV to {output_file}...")
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(expected_columns)  # Header
        writer.writerows(fixed_rows)
    
    print(f"Fixed CSV saved as {output_file}")
    return output_file

def enhance_fixed_csv(input_file, output_file='enhanced_gitcommitchanges.csv'):
    """Enhance the fixed CSV with additional features"""
    
    def has_fix_keyword(commit_message):
        fix_keywords = [
            'fix', 'fixes', 'fixed', 'fixing', 'bug', 'bugfix', 'patch',
            'resolve', 'resolves', 'resolved', 'resolving', 'close', 'closes',
            'closed', 'closing', 'issue', 'error', 'correct', 'repair'
        ]
        message_lower = str(commit_message).lower()
        return any(keyword in message_lower for keyword in fix_keywords)

    def is_test_file(filename):
        test_patterns = [
            r'test.*\.py$', r'.*test\.py$', r'.*_test\.py$',
            r'test.*\.java$', r'.*Test\.java$', r'.*Tests\.java$',
            r'test.*\.js$', r'.*test\.js$', r'.*\.test\.js$',
            r'test.*\.ts$', r'.*test\.ts$', r'.*\.test\.ts$',
            r'.*\.spec\.(js|ts|py|java)$',
            r'.*/tests?/.*', r'.*/test/.*'
        ]
        return any(re.search(pattern, str(filename), re.IGNORECASE) for pattern in test_patterns)
    
    print(f"Enhancing {input_file}...")
    
    chunk_size = 10000
    first_chunk = True
    total_processed = 0
    
    for chunk in pd.read_csv(input_file, chunksize=chunk_size):
        print(f"Processing chunk starting at row {total_processed}...")
        
        # Add has_fix_keyword column
        chunk['has_fix_keyword'] = chunk['NOTE'].apply(has_fix_keyword)
        
        # Add is_test_file column for individual files
        chunk['is_test_file'] = chunk['FILE'].apply(is_test_file)
        
        # Calculate files_changed per commit
        files_per_commit = chunk.groupby('COMMIT_HASH').size().to_dict()
        chunk['files_changed'] = chunk['COMMIT_HASH'].map(files_per_commit)
        
        # Calculate changed_tests per commit (any test file in commit)
        test_per_commit = chunk.groupby('COMMIT_HASH')['is_test_file'].any().to_dict()
        chunk['changed_tests'] = chunk['COMMIT_HASH'].map(test_per_commit)
        
        # Remove temporary column
        chunk = chunk.drop('is_test_file', axis=1)
        
        # Write to output
        mode = 'w' if first_chunk else 'a'
        header = first_chunk
        chunk.to_csv(output_file, mode=mode, header=header, index=False, encoding='utf-8')
        
        total_processed += len(chunk)
        first_chunk = False
        print(f"✓ Processed {len(chunk)} rows, total: {total_processed}")
    
    print(f"\nnhancement complete! Output saved to {output_file}")
    
    # Show sample
    sample = pd.read_csv(output_file, nrows=3)
    print("\nSample of enhanced data:")
    print(sample[['COMMIT_HASH', 'files_changed', 'has_fix_keyword', 'changed_tests']].to_string())

def main():
    input_file = 'gitcommitchanges.csv'
    
    print("=== Robust CSV Processing ===")
    print("Fixing CSV structure issues...")
    
    fixed_file = fix_csv_structure(input_file)
    
    print("\nEnhancing with additional features...")
    enhance_fixed_csv(fixed_file)
    
    print("\nAll done! Your enhanced dataset is ready.")

if __name__ == "__main__":
    main()