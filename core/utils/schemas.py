"""
JSON schemas for validating WiseFlow configurations and data structures.
"""

# Main configuration schema
CONFIG_SCHEMA = {
    "type": "object",
    "properties": {
        "api_keys": {
            "type": "object",
            "properties": {
                "openai": {"type": "string"},
                "exa": {"type": "string"},
                "zhipu": {"type": "string"},
                "anthropic": {"type": "string"}
            },
            "additionalProperties": True
        },
        "llm": {
            "type": "object",
            "properties": {
                "default_model": {"type": "string"},
                "temperature": {"type": "number", "minimum": 0, "maximum": 1},
                "max_tokens": {"type": "integer", "minimum": 1},
                "timeout": {"type": "integer", "minimum": 1}
            },
            "required": ["default_model"],
            "additionalProperties": True
        },
        "plugins": {
            "type": "object",
            "properties": {
                "enabled": {"type": "array", "items": {"type": "string"}},
                "paths": {"type": "array", "items": {"type": "string"}}
            },
            "additionalProperties": True
        },
        "connectors": {
            "type": "object",
            "additionalProperties": {
                "type": "object"
            }
        },
        "logging": {
            "type": "object",
            "properties": {
                "level": {"type": "string", "enum": ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]},
                "file": {"type": "string"}
            },
            "additionalProperties": True
        },
        "storage": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "type": {"type": "string", "enum": ["local", "s3", "azure"]}
            },
            "additionalProperties": True
        },
        "web_crawler": {
            "type": "object",
            "properties": {
                "timeout": {"type": "integer", "minimum": 1},
                "max_retries": {"type": "integer", "minimum": 0},
                "user_agent": {"type": "string"},
                "cache_mode": {"type": "string", "enum": ["DISABLED", "READ_ONLY", "WRITE_ONLY", "READ_WRITE"]}
            },
            "additionalProperties": True
        }
    },
    "required": ["llm"],
    "additionalProperties": True
}

# Entity schema
ENTITY_SCHEMA = {
    "type": "object",
    "properties": {
        "entity_id": {"type": "string", "pattern": "^[a-zA-Z0-9_-]+$"},
        "name": {"type": "string"},
        "entity_type": {"type": "string"},
        "sources": {"type": "array", "items": {"type": "string"}},
        "metadata": {"type": "object"}
    },
    "required": ["entity_id", "name", "entity_type", "sources"],
    "additionalProperties": False
}

# Relationship schema
RELATIONSHIP_SCHEMA = {
    "type": "object",
    "properties": {
        "relationship_id": {"type": "string", "pattern": "^[a-zA-Z0-9_-]+$"},
        "source_id": {"type": "string"},
        "target_id": {"type": "string"},
        "relationship_type": {"type": "string"},
        "metadata": {"type": "object"}
    },
    "required": ["relationship_id", "source_id", "target_id", "relationship_type"],
    "additionalProperties": False
}

# Reference schema
REFERENCE_SCHEMA = {
    "type": "object",
    "properties": {
        "reference_id": {"type": "string", "pattern": "^[a-zA-Z0-9_-]+$"},
        "focus_id": {"type": "string"},
        "content": {"type": "string"},
        "reference_type": {"type": "string"},
        "metadata": {"type": "object"}
    },
    "required": ["reference_id", "focus_id", "content", "reference_type"],
    "additionalProperties": False
}

# Task schema
TASK_SCHEMA = {
    "type": "object",
    "properties": {
        "task_id": {"type": "string", "pattern": "^[a-zA-Z0-9_-]+$"},
        "name": {"type": "string"},
        "description": {"type": ["string", "null"]},
        "status": {"type": "string", "enum": ["pending", "running", "completed", "failed", "cancelled"]},
        "created_at": {"type": "string", "format": "date-time"},
        "updated_at": {"type": ["string", "null"], "format": "date-time"},
        "metadata": {"type": "object"}
    },
    "required": ["task_id", "name", "status", "created_at"],
    "additionalProperties": False
}

# Plugin configuration schema
PLUGIN_CONFIG_SCHEMA = {
    "type": "object",
    "properties": {
        "name": {"type": "string"},
        "description": {"type": "string"},
        "version": {"type": "string"},
        "enabled": {"type": "boolean"},
        "config": {"type": "object"}
    },
    "required": ["name", "enabled"],
    "additionalProperties": False
}

# Connector configuration schema
CONNECTOR_CONFIG_SCHEMA = {
    "type": "object",
    "properties": {
        "name": {"type": "string"},
        "description": {"type": "string"},
        "version": {"type": "string"},
        "enabled": {"type": "boolean"},
        "config": {"type": "object"}
    },
    "required": ["name", "enabled"],
    "additionalProperties": False
}

# Export configuration schema
EXPORT_CONFIG_SCHEMA = {
    "type": "object",
    "properties": {
        "format": {"type": "string", "enum": ["json", "csv", "pdf", "xml"]},
        "path": {"type": "string"},
        "include_metadata": {"type": "boolean"},
        "compress": {"type": "boolean"}
    },
    "required": ["format", "path"],
    "additionalProperties": False
}

# Webhook configuration schema
WEBHOOK_CONFIG_SCHEMA = {
    "type": "object",
    "properties": {
        "url": {"type": "string", "format": "uri"},
        "method": {"type": "string", "enum": ["GET", "POST", "PUT", "DELETE"]},
        "headers": {"type": "object"},
        "auth": {
            "type": "object",
            "properties": {
                "type": {"type": "string", "enum": ["basic", "bearer", "api_key"]},
                "username": {"type": "string"},
                "password": {"type": "string"},
                "token": {"type": "string"},
                "key_name": {"type": "string"},
                "key_value": {"type": "string"}
            },
            "additionalProperties": False
        },
        "retry": {
            "type": "object",
            "properties": {
                "max_retries": {"type": "integer", "minimum": 0},
                "retry_delay": {"type": "integer", "minimum": 0}
            },
            "additionalProperties": False
        }
    },
    "required": ["url", "method"],
    "additionalProperties": False
}

# LLM request schema
LLM_REQUEST_SCHEMA = {
    "type": "object",
    "properties": {
        "model": {"type": "string"},
        "messages": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "role": {"type": "string", "enum": ["system", "user", "assistant"]},
                    "content": {"type": "string"}
                },
                "required": ["role", "content"],
                "additionalProperties": False
            }
        },
        "temperature": {"type": "number", "minimum": 0, "maximum": 1},
        "max_tokens": {"type": "integer", "minimum": 1},
        "stream": {"type": "boolean"}
    },
    "required": ["messages"],
    "additionalProperties": True
}

# Knowledge graph schema
KNOWLEDGE_GRAPH_SCHEMA = {
    "type": "object",
    "properties": {
        "entities": {
            "type": "object",
            "additionalProperties": ENTITY_SCHEMA
        },
        "relationships": {
            "type": "object",
            "additionalProperties": RELATIONSHIP_SCHEMA
        },
        "metadata": {"type": "object"}
    },
    "required": ["entities", "relationships"],
    "additionalProperties": False
}

