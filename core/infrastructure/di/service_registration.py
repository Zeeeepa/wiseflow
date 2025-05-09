#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Service Registration.

This module registers services with the dependency injection container.
"""

import logging
from typing import Dict, Any

from core.di_container import DIContainer, ServiceLifetime
from core.domain.services.llm_service import LLMService
from core.domain.services.information_service import InformationService, DefaultInformationService
from core.domain.repositories.information_repository import InformationRepository
from core.infrastructure.config.configuration_service import ConfigurationService, get_configuration_service
from core.infrastructure.services.openai_llm_service import OpenAILLMService
from core.infrastructure.repositories.pocketbase_information_repository import PocketBaseInformationRepository

logger = logging.getLogger(__name__)

def register_services(container: DIContainer) -> None:
    """
    Register services with the dependency injection container.
    
    Args:
        container: The dependency injection container
    """
    logger.info("Registering services with dependency injection container")
    
    # Register configuration service
    container.register_instance(ConfigurationService, get_configuration_service())
    
    # Register repositories
    container.register(InformationRepository, PocketBaseInformationRepository, ServiceLifetime.SINGLETON)
    
    # Register services
    container.register(LLMService, OpenAILLMService, ServiceLifetime.SINGLETON)
    container.register(InformationService, DefaultInformationService, ServiceLifetime.SINGLETON)
    
    logger.info("Services registered successfully")

def register_services_with_configuration(container: DIContainer, config: Dict[str, Any]) -> None:
    """
    Register services with the dependency injection container using configuration.
    
    Args:
        container: The dependency injection container
        config: Configuration dictionary
    """
    logger.info("Registering services with dependency injection container using configuration")
    
    # Register configuration service
    configuration_service = get_configuration_service()
    for key, value in config.items():
        configuration_service.set(key, value)
    container.register_instance(ConfigurationService, configuration_service)
    
    # Register repositories
    repository_type = config.get("INFORMATION_REPOSITORY_TYPE", "pocketbase")
    if repository_type == "pocketbase":
        container.register(InformationRepository, PocketBaseInformationRepository, ServiceLifetime.SINGLETON)
    else:
        logger.warning(f"Unknown repository type: {repository_type}, using PocketBaseInformationRepository")
        container.register(InformationRepository, PocketBaseInformationRepository, ServiceLifetime.SINGLETON)
    
    # Register services
    llm_service_type = config.get("LLM_SERVICE_TYPE", "openai")
    if llm_service_type == "openai":
        container.register(LLMService, OpenAILLMService, ServiceLifetime.SINGLETON)
    else:
        logger.warning(f"Unknown LLM service type: {llm_service_type}, using OpenAILLMService")
        container.register(LLMService, OpenAILLMService, ServiceLifetime.SINGLETON)
    
    # Register information service
    container.register(InformationService, DefaultInformationService, ServiceLifetime.SINGLETON)
    
    logger.info("Services registered successfully with configuration")

