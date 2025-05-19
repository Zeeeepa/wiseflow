# Redundant Files to Remove

Based on the analysis of the WiseFlow project, the following files are identified as redundant and can be safely removed:

## Duplicate Files

1. **Utility Files**:
   - `dashboard/general_utils.py` (Keep `core/utils/general_utils.py` instead)
   - `core/utils/export_example.py` (Keep `core/export/examples/export_example.py` instead)

2. **Monitoring Files**:
   - `dashboard/resource_monitor.py` (Keep `core/resource_monitor.py` instead)

3. **Task Management**:
   - `core/task_manager.py` (Keep `core/task_management/task_manager.py` instead)

4. **Validation and Error Handling**:
   - `core/plugins/validation.py` (Keep `core/utils/validation.py` instead)
   - `core/llms/error_handling.py` (Keep `core/utils/error_handling.py` instead)

## Duplicate Test Files

1. **Event System Tests**:
   - `tests/test_event_system.py` (Keep `tests/unit/core/test_event_system.py` instead)

2. **Knowledge Graph Tests**:
   - `tests/test_knowledge_graph.py` (Keep `tests/unit/core/test_knowledge_graph.py` instead)

3. **Plugin System Tests**:
   - `tests/integration/plugins/test_plugin_system.py` (Keep `tests/core/plugins/test_plugin_system.py` instead)

## Unused Files

1. **Example Files**:
   - `integration_example.py` (Convert to proper documentation or test)

2. **Unused Dashboard Components**:
   - `dashboard/search_api.py`
   - `dashboard/data_mining_api.py`
   - `dashboard/get_report.py`
   - `dashboard/parallel_research.py`
   - `dashboard/get_search.py`
   - `dashboard/research_api.py`
   - `dashboard/tranlsation_volcengine.py`

3. **Unused Core Components**:
   - `core/run_task_new.py` (Appears to be a replacement for `run_task.py`)
   - `core/windows_run.py` (Platform-specific file that can be integrated into main execution)
   - `core/unified_task_manager.py` (Appears to be a replacement for task management)

## Redundant Configuration Files

Consider consolidating these configuration files into a hierarchical system:

1. `core/config.py`
2. `core/task/config.py`
3. `core/crawl4ai/config.py`
4. `core/crawl4ai/html2text/config.py`

## Note

Before removing any files, ensure that:
1. All functionality is preserved
2. Tests pass after removal
3. Any dependencies are updated to reference the remaining files

