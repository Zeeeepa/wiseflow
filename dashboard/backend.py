from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel
from typing import Literal, Optional, Dict, Any
from fastapi.middleware.cors import CORSMiddleware
import logging
import asyncio

# Configure logger
logger = logging.getLogger(__name__)

# Backend operations should be focused on pb operations, such as adding sources, points of interest, etc.
# All should be stored in pb, not in a separate process instance
# Of course, pb can also be abandoned, but that's another issue, data and settings management should be a set
# Simply put, the user side (api dashboard, etc.) and the core side should not interface directly, they should all go through the underlying data infrastructure

class Request(BaseModel):
    """
    Input model
    input = {'user_id': str, 'type': str, 'content':str, 'addition': Optional[str]}
    Type is one of "text", "publicMsg", "site" and "url";
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


async def message_manager(_input: Dict[str, Any]):
    """
    Process incoming messages and route them to appropriate handlers.
    
    Args:
        _input: Dictionary containing message data
            - user_id: ID of the user
            - type: Type of message
            - content: Message content
            - addition: Additional information
    
    Returns:
        None
    """
    try:
        logger.info(f"Processing message from user {_input.get('user_id')}")
        
        # Extract message data
        user_id = _input.get('user_id')
        msg_type = _input.get('type')
        content = _input.get('content')
        addition = _input.get('addition')
        
        if not user_id or not msg_type or not content:
            logger.error("Missing required message fields")
            return
        
        # Process message based on type
        if msg_type == "text":
            # Process text message
            logger.info(f"Processing text message: {content[:50]}...")
            # Implement text processing logic here
            
        elif msg_type == "publicMsg":
            # Process public message
            logger.info(f"Processing public message: {content[:50]}...")
            # Implement public message processing logic here
            
        elif msg_type == "file":
            # Process file
            logger.info(f"Processing file: {content}")
            # Implement file processing logic here
            
        elif msg_type == "image":
            # Process image
            logger.info(f"Processing image: {content}")
            # Implement image processing logic here
            
        elif msg_type == "video":
            # Process video
            logger.info(f"Processing video: {content}")
            # Implement video processing logic here
            
        elif msg_type == "location":
            # Process location
            logger.info(f"Processing location: {content}")
            # Implement location processing logic here
            
        elif msg_type == "chathistory":
            # Process chat history
            logger.info(f"Processing chat history: {content[:50]}...")
            # Implement chat history processing logic here
            
        elif msg_type == "site":
            # Process site
            logger.info(f"Processing site: {content}")
            # Implement site processing logic here
            
        elif msg_type == "attachment":
            # Process attachment
            logger.info(f"Processing attachment: {content}")
            # Implement attachment processing logic here
            
        elif msg_type == "url":
            # Process URL
            logger.info(f"Processing URL: {content}")
            # Implement URL processing logic here
            
        else:
            logger.warning(f"Unknown message type: {msg_type}")
        
        logger.info(f"Message processing completed for user {user_id}")
        
    except Exception as e:
        logger.error(f"Error processing message: {str(e)}")


@app.post("/feed")
async def call_to_feed(background_tasks: BackgroundTasks, request: Request):
    background_tasks.add_task(message_manager, _input=request.model_dump())
    return {"msg": "received well"}
