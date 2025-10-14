#!/usr/bin/env python3
"""
Migration script for root-level test files

This script helps migrate old root-level test files to the new organized structure.
"""

import os
import shutil
from pathlib import Path


def migrate_test_files():
    """Migrate root-level test files to integration tests directory"""
    
    project_root = Path(__file__).parent
    integration_dir = project_root / "tests" / "integration"
    
    print("🔄 Migrating root-level test files to integration tests...")
    print(f"   Target directory: {integration_dir}")
    
    # Files to migrate (root-level test files)
    root_test_files = [
        "test_streaming_chat.py",
        "test_memory_workflow.py", 
        "test_config_system.py",
        "test_importance_integration.py",
        "test_importance_scoring.py",
        "test_llm_streaming_direct.py",
        "test_memory_decay.py",
        "test_memory_pruning.py",
        "test_ollama_streaming.py",
        "test_performance_optimizations.py",
        "test_pruning_api.py"
    ]
    
    moved_count = 0
    archived_dir = project_root / "tests" / "legacy_integration"
    archived_dir.mkdir(exist_ok=True)
    
    for test_file in root_test_files:
        source_path = project_root / test_file
        
        if source_path.exists():
            # Move to legacy directory for reference
            target_path = archived_dir / test_file
            
            try:
                shutil.move(str(source_path), str(target_path))
                print(f"   ✅ Moved {test_file} → tests/legacy_integration/")
                moved_count += 1
            except Exception as e:
                print(f"   ❌ Failed to move {test_file}: {e}")
        else:
            print(f"   ⚠️  {test_file} not found (already moved?)")
    
    print(f"\n✅ Migration completed: {moved_count} files moved to legacy directory")
    print(f"   📁 Legacy tests archived in: {archived_dir}")
    print(f"   📁 New integration tests in: {integration_dir}")
    
    # Create a notice file
    notice_file = archived_dir / "README.md"
    with open(notice_file, "w") as f:
        f.write("""# Legacy Integration Tests

These are the original root-level test files that have been replaced by 
the new organized integration tests in `tests/integration/`.

## Migration Status

The original test files have been refactored into proper pytest integration tests:

- `test_streaming_chat.py` → `tests/integration/test_streaming_chat_integration.py`
- `test_memory_workflow.py` → `tests/integration/test_memory_workflow_integration.py`
- `test_config_system.py` → `tests/integration/test_config_integration.py`
- `test_importance_scoring.py` → `tests/integration/test_importance_scoring_integration.py`

## Usage

Use the new integration tests instead:

```bash
# Run all integration tests
pytest tests/integration/ -m integration -v

# Run specific test categories
pytest tests/integration/test_streaming_chat_integration.py -v
```

The files in this directory are kept for reference and can be removed once
the migration is confirmed successful.
""")
    
    print(f"   📝 Created migration notice: {notice_file}")


if __name__ == "__main__":
    migrate_test_files()