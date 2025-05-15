from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel
from typing import Literal, Optional, Dict, Any
from fastapi.middleware.cors import CORSMiddleware
import logging
import asyncio

# Add logger
logger = logging.getLogger(__name__)

# backend的操作也应该是针对 pb 操作的，即添加信源、兴趣点等都应该存入 pb，而不是另起一个进程实例
# 当然也可以放弃 pb，但那是另一个问题，数据和设置的管理应该是一套
# 简单说用户侧（api dashboard等）和 core侧 不应该直接对接，都应该通过底层的data infrastructure 进行

# Implement the missing message_manager function
async def message_manager(_input: Dict[str, Any]):
    """
    Process incoming messages and route them to appropriate handlers.
    
    Args:
        _input: Dictionary containing message data
            - user_id: User ID
            - type: Message type
            - content: Message content
            - addition: Optional additional data
    """
    try:
        logger.info(f"Processing message from user {_input.get('user_id')}: {_input.get('type')}")
        
        # Here you would implement the actual message processing logic
        # For now, we'll just log the message
        message_type = _input.get('type')
        content = _input.get('content')
        
        if message_type == "text":
            logger.info(f"Processing text message: {content[:50]}...")
            # Process text message
        elif message_type == "publicMsg":
            logger.info(f"Processing public message: {content[:50]}...")
            # Process public message
        elif message_type == "site":
            logger.info(f"Processing site message: {content[:50]}...")
            # Process site message
        elif message_type == "url":
            logger.info(f"Processing URL message: {content[:50]}...")
            # Process URL message
        else:
            logger.info(f"Processing {message_type} message")
            # Process other message types
            
        logger.info(f"Message processing completed for user {_input.get('user_id')}")
    except Exception as e:
        logger.error(f"Error processing message: {str(e)}")


class Request(BaseModel):
    """
    Input model
    input = {'user_id': str, 'type': str, 'content':str， 'addition': Optional[str]}
    Type is one of "text", "publicMsg", "site" and "url"；
    """
    user_id: str
    type: Literal["text", "publicMsg", "file", "image", "video", "location", "chathistory", "site", "attachment", "url"]
    content: str
    addition: Optional[str] = None


app = FastAPI(
    title="WiseFlow Union Backend",
    description="From Wiseflow Team.",
    version="0.3.1",
    openapi_url="/openapi.json"
)

app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


@app.get("/")
def read_root():
    msg = "Hello, this is Wise Union Backend, version 0.3.1"
    return {"msg": msg}


@app.post("/feed")
async def call_to_feed(background_tasks: BackgroundTasks, request: Request):
    background_tasks.add_task(message_manager, _input=request.model_dump())
    return {"msg": "received well"}
