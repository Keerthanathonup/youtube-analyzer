# update_claude_models.py
import os
import re

def update_model_references(directory, old_model, new_model):
    """
    Scans all Python files in the directory and updates Claude model references
    
    Args:
        directory: The base directory to search in
        old_model: The old model name to replace
        new_model: The new model name to use
    """
    updated_files = []
    
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith(".py"):
                file_path = os.path.join(root, file)
                
                # Read the file content
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Check if the old model name is in the content
                if old_model in content:
                    # Replace the old model with the new one
                    updated_content = content.replace(old_model, new_model)
                    
                    # Write the updated content back
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(updated_content)
                    
                    updated_files.append(file_path)
    
    return updated_files

if __name__ == "__main__":
    base_dir = "."  # Current directory
    old_model = "claude-3-haiku-20240307"  # The deprecated model
    new_model = "claude-3-haiku-20240307"   # A current model that's fast and affordable
    
    print(f"Updating Claude model references from '{old_model}' to '{new_model}'...")
    
    updated = update_model_references(base_dir, old_model, new_model)
    
    if updated:
        print(f"Updated {len(updated)} files:")
        for file in updated:
            print(f"  - {file}")
    else:
        print("No files needed updating.")
    
    print("\nDon't forget to update your .env file or environment variables if needed!")
    print("You can also update your config.py file to set a default model.")