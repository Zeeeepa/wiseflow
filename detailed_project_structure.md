# WiseFlow Detailed Project Structure

This document provides a detailed view of the project structure, showing which files are used by other files.

```
Directory: .
  analyze_imports.py
  api_server.py
  deploy_wiseflow.py
  generate_structure.py
  integration_example.py
  test_auto_shutdown.py
  test_specialized_prompting.py
  wiseflow.py
Directory: ./dashboard
  __init__.py
  backend.py
  data_mining_api.py
  general_utils.py
  get_report.py
  get_search.py
  main.py
  mp_crawler.py - used by: get_search.py
  parallel_research.py
  research_api.py
  resource_monitor.py
  routes.py
  search_api.py
  simple_crawler.py - used by: get_search.py
  tranlsation_volcengine.py
Directory: ./tests
  __init__.py
  conftest.py
  test_event_system.py
  test_export_utils.py
  test_knowledge_graph.py
  test_llm_integration.py
  test_references.py
  test_unified_task_manager.py
Directory: ./core
  __init__.py - used by: pattern_recognition.py
  cache_manager.py
  config.py - used by: __init__.py
  connection_pool.py
  content_types.py
  di_container.py
  event_system.py
  general_process.py
  imports.py
  initialize.py
  interface.py
  resource_management.py
  resource_monitor.py
  run_task.py
  run_task_new.py
  task_manager.py
  thread_pool_manager.py
  unified_task_manager.py
  windows_run.py
Directory: ./examples
  advanced_llm_features_example.py
  api_integration_example.py
  enhanced_plugin_example.py
  entity_linking_example.py
  error_handling_logging_example.py
  llm_integration_example.py
  plugin_example.py
  recovery_strategies_example.py
  reference_support_example.py
  research_connector_example.py
  robust_error_handling_example.py
Directory: ./test
  craw4ai_fetching.py
  crawlee_fetching.py
  get_info_test.py
  get_visual_info_for_samples.py
  pre_process_test.py
  read_markdown.py
  vl_pic_test.py
Directory: ./weixin_mp
  __init__.py
Directory: ./scripts
  dependency_check.py
  migrate_schema.py
  run_tests.py
Directory: ./dashboard/notification
  __init__.py
Directory: ./dashboard/plugins
  __init__.py
  connector.py
Directory: ./dashboard/visualization
  __init__.py
Directory: ./dashboard/components
  resource_metrics.py
Directory: ./tests/core
  __init__.py
Directory: ./core/utils
  __init__.py
  data_mining_cli.py
  error_handling.py
  error_logging.py
  exa_search.py
  export_example.py
  export_infos.py
  export_utils.py
  general_utils.py - used by: data_mining.py, trend_analysis.py, pattern_recognition.py, multimodal_analysis.py, entity_extraction.py, multimodal_knowledge_integration.py, data_mining_manager.py, insights.py, graph.py
  health_check.py
  logging_config.py
  multimodal_cli.py
  pb_api.py - used by: schema_update.py, data_mining.py, trend_analysis.py, pattern_recognition.py, multimodal_analysis.py, entity_extraction.py, multimodal_knowledge_integration.py, data_mining_manager.py, insights.py, graph.py
  pb_exporter.py
  recovery_strategies.py
  schema_update.py
  validation.py
  zhipu_search.py
Directory: ./core/analysis
  __init__.py - used by: insights.py, graph.py
  data_mining.py - used by: __init__.py, __init__.py, trend_analysis.py, data_mining_manager.py
  entity_extraction.py - used by: __init__.py, __init__.py, multimodal_knowledge_integration.py, multimodal_knowledge_integration.py, multimodal_knowledge_integration.py
  entity_linking.py - used by: __init__.py, __init__.py, multimodal_knowledge_integration.py, graph.py, graph.py
  multimodal_analysis.py - used by: multimodal_knowledge_integration.py
  multimodal_knowledge_integration.py
  pattern_recognition.py - used by: __init__.py, __init__.py
  trend_analysis.py - used by: __init__.py, __init__.py
Directory: ./core/task_management
  __init__.py
  exceptions.py
  executor.py
  task.py
  task_manager.py
Directory: ./core/plugins
  __init__.py
  base.py
  compatibility.py
  isolation.py
  lifecycle.py
  loader.py
  resources.py
  security.py
  utils.py
  validation.py
Directory: ./core/task
  __init__.py
  async_task_manager.py
  config.py
  data_mining_manager.py
  monitor.py
Directory: ./core/crawl4ai
  __init__.py - used by: __init__.py, utils.py
  __version__.py - used by: utils.py
  async_configs.py - used by: __init__.py, async_crawler_strategy.py, install.py, async_webcrawler.py
  async_crawler_strategy.py - used by: async_webcrawler.py
  async_database.py - used by: async_webcrawler.py
  async_logger.py - used by: async_database.py, migrations.py, async_crawler_strategy.py, install.py, async_webcrawler.py
  async_webcrawler.py - used by: __init__.py, install.py, install.py
  cache_context.py - used by: async_configs.py, async_webcrawler.py
  config.py - used by: utils.py, async_configs.py, async_configs.py, async_crawler_strategy.py, content_scraping_strategy.py, content_scraping_strategy.py
  content_scraping_strategy.py - used by: __init__.py, __init__.py, async_configs.py
  install.py
  markdown_generation_strategy.py - used by: __init__.py, async_configs.py
  migrations.py
  models.py - used by: __init__.py, markdown_generation_strategy.py, async_database.py, async_crawler_strategy.py, async_webcrawler.py, content_scraping_strategy.py
  ssl_certificate.py - used by: models.py, async_crawler_strategy.py
  user_agent_generator.py - used by: async_configs.py, async_crawler_strategy.py
  utils.py - used by: async_database.py, async_database.py, async_crawler_strategy.py, async_webcrawler.py, async_webcrawler.py, content_scraping_strategy.py, content_scraping_strategy.py
Directory: ./core/connectors
  __init__.py
Directory: ./core/llms
  __init__.py
  caching.py - used by: litellm_wrapper.py, openai_wrapper.py, __init__.py, __init__.py
  error_handling.py - used by: model_management.py, model_management.py, litellm_wrapper.py, openai_wrapper.py, __init__.py, __init__.py
  litellm_wrapper.py - used by: __init__.py, __init__.py
  model_management.py - used by: litellm_wrapper.py, openai_wrapper.py, __init__.py, __init__.py
  openai_wrapper.py - used by: data_mining.py, trend_analysis.py, multimodal_analysis.py, entity_extraction.py, multimodal_knowledge_integration.py, __init__.py, __init__.py, insights.py, graph.py
  token_management.py - used by: litellm_wrapper.py, openai_wrapper.py, __init__.py, __init__.py
Directory: ./core/scrapers
  __init__.py
  mp_scraper.py - used by: __init__.py
  scraper_data.py - used by: mp_scraper.py
Directory: ./core/references
  __init__.py
  reference_extractor.py - used by: __init__.py
  reference_indexer.py - used by: __init__.py
  reference_linker.py - used by: __init__.py
Directory: ./core/middleware
  __init__.py
  error_handling_middleware.py
Directory: ./core/export
  __init__.py
  webhook.py
Directory: ./core/agents
  __init__.py
  action_dict_scraper.py
  get_info.py
  get_info_prompts.py - used by: get_info.py
  insights.py
Directory: ./core/api
  __init__.py
  client.py
  main.py
Directory: ./core/knowledge
  __init__.py
  graph.py - used by: multimodal_knowledge_integration.py, __init__.py, __init__.py
Directory: ./core/experimental
  __init__.py
  advanced_reasoning.py
Directory: ./core/models
  content_processor_models.py
  research_models.py
  task_models.py
Directory: ./test/analysis
  test_entity_linking.py
Directory: ./dashboard/visualization/trends
  __init__.py
Directory: ./dashboard/visualization/knowledge_graph
  __init__.py
Directory: ./tests/unit/api
  test_api_server.py
Directory: ./tests/unit/dashboard
  test_dashboard.py
Directory: ./tests/unit/core
  test_event_system.py
  test_knowledge_graph.py
Directory: ./tests/integration/dashboard_backend
  test_dashboard_backend_integration.py
Directory: ./tests/integration/plugins
  test_plugin_system.py
Directory: ./tests/integration/api_core
  test_api_core_integration.py
Directory: ./tests/validation/non_functional
  test_non_functional_validation.py
Directory: ./tests/validation/functional
  test_functional_validation.py
Directory: ./tests/core/connectors
  __init__.py
  test_connector_base.py
Directory: ./tests/core/plugins
  test_plugin_system.py
Directory: ./tests/system/workflows
  test_end_to_end_workflow.py
Directory: ./tests/system/error_handling
  test_error_handling.py
Directory: ./tests/system/performance
  test_performance.py
Directory: ./core/domain/repositories
  information_repository.py
Directory: ./core/domain/models
  information.py
Directory: ./core/domain/services
  information_service.py
  llm_service.py
Directory: ./core/plugins/analyzers
  __init__.py
  entity_analyzer.py
  trend_analyzer.py
Directory: ./core/plugins/connectors
  __init__.py
  code_search_connector.py
  github_connector.py
  research_connector.py
  youtube_connector.py
Directory: ./core/plugins/processors
  __init__.py
  text_processor.py
Directory: ./core/crawl4ai/crawlers
  __init__.py
Directory: ./core/crawl4ai/js_snippet
  __init__.py - used by: async_crawler_strategy.py
Directory: ./core/crawl4ai/processors
  __init__.py
Directory: ./core/crawl4ai/html2text
  __init__.py - used by: utils.py, markdown_generation_strategy.py
  _typing.py - used by: __init__.py
  config.py
  elements.py - used by: __init__.py
  utils.py - used by: __init__.py, __init__.py
Directory: ./core/connectors/web
  __init__.py - used by: data_mining_manager.py
Directory: ./core/connectors/github
  __init__.py - used by: data_mining_manager.py
Directory: ./core/connectors/youtube
  __init__.py - used by: data_mining_manager.py
Directory: ./core/connectors/code_search
  __init__.py - used by: data_mining_manager.py
Directory: ./core/connectors/academic
  __init__.py - used by: data_mining_manager.py
Directory: ./core/llms/advanced
  __init__.py
  specialized_prompting.py
Directory: ./core/infrastructure/config
  configuration_service.py
Directory: ./core/infrastructure/services
  openai_llm_service.py
Directory: ./core/infrastructure/repositories
  pocketbase_information_repository.py
Directory: ./core/infrastructure/di
  service_registration.py
Directory: ./core/application/services
  information_processing_service.py
Directory: ./core/export/examples
  export_example.py
  webhook_test.py
Directory: ./core/export/cli
  __init__.py
  export_cli.py
Directory: ./core/export/formats
  __init__.py
  csv_exporter.py
  json_exporter.py
  pdf_exporter.py
  xml_exporter.py
Directory: ./core/api/models
  parallel_research_models.py
Directory: ./core/api/controllers
  error_controller.py
  information_controller.py
  parallel_research_controller.py
  research_controller.py
Directory: ./test/reports/extract_info_from_pics_test_20241222_bigbrother666
  vl_pic_test.py
Directory: ./tests/core/api/controllers
  test_parallel_research_controller.py
Directory: ./core/plugins/connectors/research
  __init__.py
  configuration.py
  graph.py
  graph_workflow.py
  multi_agent.py
  parallel_manager.py
  prompts.py
  state.py
  utils.py
Directory: ./core/plugins/processors/text
  __init__.py
  text_processor.py
Directory: ./core/crawl4ai/crawlers/google_search
  __init__.py
  crawler.py
Directory: ./core/crawl4ai/processors/pdf
  __init__.py
  processor.py - used by: __init__.py
  utils.py - used by: processor.py, processor.py, processor.py
Directory: ./tests/core/plugins/connectors/research
  test_parallel_manager.py```
