"""
Test routes for Private LLM integration.
"""
import httpx
import json
import logging
import time
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

router = APIRouter(prefix="/api/test", tags=["test"])

# Private LLM Configuration
PRIVATE_LLM_URL = "https://privatellm.kadellabs.com/api/chat"
PRIVATE_LLM_MODEL = "qwen2.5:7b"

logger = logging.getLogger(__name__)


class TestLLMRequest(BaseModel):
    message: Optional[str] = "Summarize loan portfolio risks in 3 bullets."
    system_prompt: Optional[str] = "You are a financial risk analyst."


class CustomLLMRequest(BaseModel):
    """Request model for custom LLM test with full control over payload."""
    model: Optional[str] = PRIVATE_LLM_MODEL
    messages: List[Dict[str, str]]
    stream: Optional[bool] = False


@router.post("/llm")
async def test_private_llm(request: TestLLMRequest = None):
    """
    Test endpoint for Private LLM integration with static/custom data.
    
    Usage:
    - POST /api/test/llm (uses default static data)
    - POST /api/test/llm with body {"message": "your question", "system_prompt": "your system prompt"}
    """
    if request is None:
        request = TestLLMRequest()
    
    logger.info("=" * 80)
    logger.info("PRIVATE LLM TEST - STARTING")
    logger.info("=" * 80)
    
    # Build payload
    payload = {
        "model": PRIVATE_LLM_MODEL,
        "messages": [
            {"role": "system", "content": request.system_prompt},
            {"role": "user", "content": request.message}
        ],
        "stream": False
    }
    
    logger.info(f"[STEP 1] Payload prepared")
    logger.info(f"  - URL: {PRIVATE_LLM_URL}")
    logger.info(f"  - Model: {PRIVATE_LLM_MODEL}")
    logger.info(f"  - System Prompt: {request.system_prompt}")
    logger.info(f"  - User Message: {request.message}")
    logger.info(f"  - Full Payload: {json.dumps(payload, indent=2)}")
    
    try:
        logger.info(f"[STEP 2] Creating HTTP client...")
        start_time = time.time()
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            logger.info(f"[STEP 3] HTTP client created. Sending POST request to {PRIVATE_LLM_URL}...")
            logger.info(f"  - Timeout: 120 seconds")
            
            try:
                response = await client.post(
                    PRIVATE_LLM_URL,
                    json=payload,
                    headers={"Content-Type": "application/json"}
                )
                
                elapsed_time = time.time() - start_time
                logger.info(f"[STEP 4] Response received in {elapsed_time:.2f} seconds")
                logger.info(f"  - Status Code: {response.status_code}")
                logger.info(f"  - Response Headers: {dict(response.headers)}")
                
                if response.status_code != 200:
                    logger.error(f"[ERROR] Non-200 status code: {response.status_code}")
                    logger.error(f"  - Response Text: {response.text}")
                    return {
                        "success": False,
                        "error": f"LLM returned status code {response.status_code}",
                        "status_code": response.status_code,
                        "response_text": response.text,
                        "elapsed_time": elapsed_time
                    }
                
                logger.info(f"[STEP 5] Parsing JSON response...")
                result = response.json()
                
                logger.info(f"[STEP 6] JSON parsed successfully")
                logger.info(f"  - Response Keys: {list(result.keys())}")
                logger.info(f"  - Full Response: {json.dumps(result, indent=2, default=str)[:3000]}")
                
                # Extract content
                content = result.get("message", {}).get("content", "")
                if not content:
                    content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
                if not content:
                    content = result.get("response", "")
                
                logger.info(f"[STEP 7] Content extracted")
                logger.info(f"  - Content Length: {len(content)} characters")
                logger.info(f"  - Content Preview: {content[:1000]}...")
                
                logger.info("=" * 80)
                logger.info("PRIVATE LLM TEST - SUCCESS")
                logger.info("=" * 80)
                
                return {
                    "success": True,
                    "status_code": response.status_code,
                    "elapsed_time": elapsed_time,
                    "model": PRIVATE_LLM_MODEL,
                    "request": {
                        "system_prompt": request.system_prompt,
                        "message": request.message
                    },
                    "response": {
                        "raw_keys": list(result.keys()),
                        "content": content,
                        "content_length": len(content),
                        "full_response": result
                    }
                }
                
            except httpx.TimeoutException as e:
                elapsed_time = time.time() - start_time
                logger.error(f"[ERROR] Request timed out after {elapsed_time:.2f} seconds")
                logger.error(f"  - Error: {str(e)}")
                return {
                    "success": False,
                    "error": "Request timed out",
                    "error_type": "TimeoutException",
                    "error_details": str(e),
                    "elapsed_time": elapsed_time
                }
                
            except httpx.ConnectError as e:
                elapsed_time = time.time() - start_time
                logger.error(f"[ERROR] Connection failed after {elapsed_time:.2f} seconds")
                logger.error(f"  - Error: {str(e)}")
                return {
                    "success": False,
                    "error": "Connection failed - Unable to reach LLM server",
                    "error_type": "ConnectError",
                    "error_details": str(e),
                    "elapsed_time": elapsed_time
                }
                
            except httpx.HTTPStatusError as e:
                elapsed_time = time.time() - start_time
                logger.error(f"[ERROR] HTTP error after {elapsed_time:.2f} seconds")
                logger.error(f"  - Status Code: {e.response.status_code}")
                logger.error(f"  - Response: {e.response.text}")
                return {
                    "success": False,
                    "error": f"HTTP error: {e.response.status_code}",
                    "error_type": "HTTPStatusError",
                    "error_details": str(e),
                    "response_text": e.response.text,
                    "elapsed_time": elapsed_time
                }
    
    except Exception as e:
        logger.error(f"[ERROR] Unexpected error: {type(e).__name__}")
        logger.error(f"  - Error Message: {str(e)}")
        import traceback
        logger.error(f"  - Traceback: {traceback.format_exc()}")
        
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__,
            "traceback": traceback.format_exc()
        }


@router.get("/llm")
async def test_private_llm_get():
    """
    GET version of the test endpoint with default static data.
    
    Usage: GET /api/test/llm
    """
    return await test_private_llm(TestLLMRequest())


@router.get("/llm/ping")
async def ping_private_llm():
    """
    Quick ping test to check if Private LLM server is reachable.
    
    Usage: GET /api/test/llm/ping
    """
    logger.info("=" * 80)
    logger.info("PRIVATE LLM PING TEST")
    logger.info("=" * 80)
    
    try:
        start_time = time.time()
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            logger.info(f"[PING] Attempting to reach {PRIVATE_LLM_URL}...")
            
            # Just try to connect (HEAD or small POST)
            response = await client.post(
                PRIVATE_LLM_URL,
                json={
                    "model": PRIVATE_LLM_MODEL,
                    "messages": [{"role": "user", "content": "Hi"}],
                    "stream": False
                },
                headers={"Content-Type": "application/json"}
            )
            
            elapsed_time = time.time() - start_time
            
            logger.info(f"[PING] Response received in {elapsed_time:.2f}s - Status: {response.status_code}")
            
            return {
                "success": True,
                "reachable": True,
                "status_code": response.status_code,
                "elapsed_time": elapsed_time,
                "url": PRIVATE_LLM_URL
            }
            
    except httpx.ConnectError as e:
        elapsed_time = time.time() - start_time
        logger.error(f"[PING] Connection failed: {str(e)}")
        return {
            "success": False,
            "reachable": False,
            "error": "Connection failed",
            "error_details": str(e),
            "elapsed_time": elapsed_time,
            "url": PRIVATE_LLM_URL
        }
        
    except httpx.TimeoutException as e:
        elapsed_time = time.time() - start_time
        logger.error(f"[PING] Timeout: {str(e)}")
        return {
            "success": False,
            "reachable": False,
            "error": "Connection timed out",
            "error_details": str(e),
            "elapsed_time": elapsed_time,
            "url": PRIVATE_LLM_URL
        }
        
    except Exception as e:
        logger.error(f"[PING] Unexpected error: {str(e)}")
        return {
            "success": False,
            "reachable": False,
            "error": str(e),
            "error_type": type(e).__name__,
            "url": PRIVATE_LLM_URL
        }


@router.post("/llm/custom")
async def test_custom_llm(request: CustomLLMRequest):
    """
    Test endpoint for LLM with custom payload - no static data.
    
    Usage:
    POST /api/test/llm/custom
    Body:
    {
        "model": "qwen2.5:7b",
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello, how are you?"}
        ],
        "stream": false
    }
    """
    logger.info("=" * 80)
    logger.info("CUSTOM LLM TEST - STARTING")
    logger.info("=" * 80)
    
    # Build payload from custom data
    payload = {
        "model": request.model,
        "messages": request.messages,
        "stream": request.stream
    }
    
    logger.info(f"[STEP 1] Custom payload prepared")
    logger.info(f"  - URL: {PRIVATE_LLM_URL}")
    logger.info(f"  - Model: {request.model}")
    logger.info(f"  - Messages Count: {len(request.messages)}")
    logger.info(f"  - Full Payload: {json.dumps(payload, indent=2)}")
    
    try:
        logger.info(f"[STEP 2] Creating HTTP client...")
        start_time = time.time()
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            logger.info(f"[STEP 3] HTTP client created. Sending POST request to {PRIVATE_LLM_URL}...")
            
            try:
                response = await client.post(
                    PRIVATE_LLM_URL,
                    json=payload,
                    headers={"Content-Type": "application/json"}
                )
                
                elapsed_time = time.time() - start_time
                logger.info(f"[STEP 4] Response received in {elapsed_time:.2f} seconds")
                logger.info(f"  - Status Code: {response.status_code}")
                
                if response.status_code != 200:
                    logger.error(f"[ERROR] Non-200 status code: {response.status_code}")
                    logger.error(f"  - Response Text: {response.text}")
                    return {
                        "success": False,
                        "error": f"LLM returned status code {response.status_code}",
                        "status_code": response.status_code,
                        "response_text": response.text,
                        "elapsed_time": elapsed_time
                    }
                
                logger.info(f"[STEP 5] Parsing JSON response...")
                result = response.json()
                
                logger.info(f"[STEP 6] JSON parsed successfully")
                logger.info(f"  - Response Keys: {list(result.keys())}")
                logger.info(f"  - Full Response: {json.dumps(result, indent=2, default=str)}")
                
                # Extract content
                content = result.get("message", {}).get("content", "")
                if not content:
                    content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
                if not content:
                    content = result.get("response", "")
                
                logger.info(f"[STEP 7] Content extracted")
                logger.info(f"  - Content Length: {len(content)} characters")
                
                logger.info("=" * 80)
                logger.info("CUSTOM LLM TEST - SUCCESS")
                logger.info("=" * 80)
                
                return {
                    "success": True,
                    "status_code": response.status_code,
                    "elapsed_time": elapsed_time,
                    "request": {
                        "model": request.model,
                        "messages": request.messages,
                        "payload": payload
                    },
                    "response": {
                        "raw_keys": list(result.keys()),
                        "content": content,
                        "content_length": len(content),
                        "full_response": result
                    }
                }
                
            except httpx.TimeoutException as e:
                elapsed_time = time.time() - start_time
                logger.error(f"[ERROR] Request timed out after {elapsed_time:.2f} seconds")
                return {
                    "success": False,
                    "error": "Request timed out",
                    "error_type": "TimeoutException",
                    "error_details": str(e),
                    "elapsed_time": elapsed_time
                }
                
            except httpx.ConnectError as e:
                elapsed_time = time.time() - start_time
                logger.error(f"[ERROR] Connection failed after {elapsed_time:.2f} seconds")
                return {
                    "success": False,
                    "error": "Connection failed - Unable to reach LLM server",
                    "error_type": "ConnectError",
                    "error_details": str(e),
                    "elapsed_time": elapsed_time
                }
                
            except httpx.HTTPStatusError as e:
                elapsed_time = time.time() - start_time
                logger.error(f"[ERROR] HTTP error after {elapsed_time:.2f} seconds")
                return {
                    "success": False,
                    "error": f"HTTP error: {e.response.status_code}",
                    "error_type": "HTTPStatusError",
                    "error_details": str(e),
                    "response_text": e.response.text,
                    "elapsed_time": elapsed_time
                }
    
    except Exception as e:
        logger.error(f"[ERROR] Unexpected error: {type(e).__name__}")
        logger.error(f"  - Error Message: {str(e)}")
        import traceback
        logger.error(f"  - Traceback: {traceback.format_exc()}")
        
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__,
            "traceback": traceback.format_exc()
        }
