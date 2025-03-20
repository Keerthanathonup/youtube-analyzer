# fix_db_types.py

"""
This script makes targeted fixes to the video_repository.py file to fix
the dictionary binding error with SQLite.
"""

import os
import re
import shutil
import json

def backup_file(file_path):
    """Create a backup of the file."""
    backup_path = f"{file_path}.bak"
    shutil.copy2(file_path, backup_path)
    print(f"Created backup: {backup_path}")
    return backup_path

def fix_video_repository():
    """Fix type handling in video_repository.py."""
    file_path = "repositories/video_repository.py"
    
    # Create backup
    backup_file(file_path)
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Locate the create_summary method
    method_pattern = r'def create_summary\(self,.*?key_moments: List\[Dict\[str, Any\]\] = None\) -> Optional\[VideoSummary\]:'
    method_match = re.search(method_pattern, content, re.DOTALL)
    
    if not method_match:
        print("Could not find create_summary method in video_repository.py")
        return False
    
    # Find the method body
    method_start = method_match.end()
    method_indent = 4  # Assuming standard 4-space indentation
    
    # Find position to insert fixes (after the validation check for video)
    insertion_point_pattern = r'\s{' + str(method_indent) + r'}video = self.get_video_by_id\(video_id\)\s+if not video:'
    insert_match = re.search(insertion_point_pattern, content[method_start:], re.DOTALL)
    
    if not insert_match:
        print("Could not find suitable insertion point in create_summary method")
        return False
    
    # Calculate position after the 'if not video:' block
    after_if_block_pattern = r'\s{' + str(method_indent) + r'}[^\s]'
    after_match = re.search(after_if_block_pattern, content[method_start + insert_match.end():], re.DOTALL)
    
    if not after_match:
        print("Could not find end of 'if not video' block")
        return False
    
    insertion_pos = method_start + insert_match.end() + after_match.start()
    
    # Prepare the code to insert
    type_handling_code = f"""
    # Handle dictionary type for summary fields
    if isinstance(short_summary, dict) and 'summary' in short_summary:
        short_summary = short_summary['summary']
    elif isinstance(short_summary, dict):
        short_summary = str(short_summary)
    
    # Handle dictionary type for detailed_summary
    if isinstance(detailed_summary, dict) and 'summary' in detailed_summary:
        detailed_summary = detailed_summary['summary']
    elif isinstance(detailed_summary, dict):
        detailed_summary = str(detailed_summary)
    
    # Convert key_points to string if it's a string that looks like JSON
    if isinstance(key_points, str) and (key_points.startswith('[') or key_points.startswith('{{')):
        try:
            key_points = json.loads(key_points)
        except:
            key_points = [key_points]
    
    # Handle topics if it's a string that looks like JSON
    if isinstance(topics, str) and (topics.startswith('[') or topics.startswith('{{')):
        try:
            topics = json.loads(topics)
        except:
            topics = [topics]
"""

    # Add the import for json if it's not already there
    if 'import json' not in content:
        content = content.replace('import traceback', 'import traceback\nimport json')
    
    # Insert the type handling code
    modified_content = content[:insertion_pos] + type_handling_code + content[insertion_pos:]
    
    # Write the modified content back to the file
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(modified_content)
    
    print(f"Fixed type handling in {file_path}")
    return True

def fix_analysis_service():
    """Fix _parse_claude_response in analysis_service.py."""
    file_path = "services/analysis_service.py"
    
    # Create backup
    backup_file(file_path)
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find the _parse_claude_response method
    method_pattern = r'def _parse_claude_response\(self, response_text: str\) -> Dict\[str, Any\]:'
    method_match = re.search(method_pattern, content)
    
    if not method_match:
        print("Could not find _parse_claude_response method in analysis_service.py")
        return False
    
    # Add check for dict at the beginning of the method
    method_start = method_match.end()
    
    # Find the first line of the method body
    next_line_pattern = r'\n\s+"""'
    doc_match = re.search(next_line_pattern, content[method_start:])
    
    if not doc_match:
        print("Could not find method docstring")
        return False
    
    # Find the first line after the docstring
    doc_end_pattern = r'"""\n\s+'
    after_doc_match = re.search(doc_end_pattern, content[method_start:])
    
    if not after_doc_match:
        print("Could not find end of docstring")
        return False
    
    insertion_pos = method_start + after_doc_match.end()
    
    # Prepare the code to insert
    dict_check_code = """
        # If response_text is already a dict, just return it with required fields
        if isinstance(response_text, dict):
            result = response_text.copy()
            # Ensure minimum required fields exist
            if "summary" not in result:
                result["summary"] = "Summary unavailable"
            if "key_points" not in result:
                result["key_points"] = []
            if "topics" not in result:
                result["topics"] = []
            if "sentiment" not in result:
                result["sentiment"] = "neutral"
            if "sentiment_score" not in result:
                result["sentiment_score"] = 0
            return result
            
"""
    
    # Insert the dict check code
    modified_content = content[:insertion_pos] + dict_check_code + content[insertion_pos:]
    
    # Write the modified content back to the file
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(modified_content)
    
    print(f"Fixed _parse_claude_response in {file_path}")
    return True

if __name__ == "__main__":
    print("Running database type fixes...")
    
    # Fix video_repository.py
    repo_fixed = fix_video_repository()
    
    # Fix analysis_service.py
    analysis_fixed = fix_analysis_service()
    
    if repo_fixed and analysis_fixed:
        print("\n✅ All fixes applied successfully!")
        print("You can now run your application and it should handle dictionary types correctly.")
    else:
        print("\n⚠️ Some fixes could not be applied automatically.")
        print("You may need to manually edit the files as described in the Claude artifact instructions.")
    
    print("\nIf you encounter any issues, you can restore from the .bak files created.")