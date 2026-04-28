"""
Laptop Control Router
WebSocket endpoint for laptop client connections
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Dict, Set
import asyncio
import json
from services import laptop_service

router = APIRouter()

# Store connected laptop clients
connected_laptops: Dict[str, WebSocket] = {}


@router.websocket("/ws/laptop")
async def laptop_websocket(websocket: WebSocket):
    """WebSocket endpoint for laptop clients"""
    
    await websocket.accept()
    
    # Generate client ID
    client_id = f"laptop_{id(websocket)}"
    connected_laptops[client_id] = websocket
    
    print(f"[LAPTOP_WS] Client connected: {client_id}")
    print(f"[LAPTOP_WS] Total connected laptops: {len(connected_laptops)}")
    
    try:
        # Send welcome message
        await websocket.send_json({
            "type": "connected",
            "client_id": client_id,
            "message": "Connected to backend"
        })
        
        # Keep connection alive and handle incoming messages
        while True:
            try:
                # Receive message from laptop client
                data = await websocket.receive_text()
                message = json.loads(data)
                
                print(f"[LAPTOP_WS] Received from {client_id}: {message}")
                
                # Handle different message types
                msg_type = message.get("type")
                
                if msg_type == "ping":
                    await websocket.send_json({"type": "pong"})
                
                elif msg_type == "status":
                    # Laptop reporting its status
                    print(f"[LAPTOP_WS] {client_id} status: {message.get('status')}")
                
                elif msg_type == "result":
                    # Laptop reporting command execution result
                    print(f"[LAPTOP_WS] {client_id} result: {message.get('success')}")
                
                else:
                    print(f"[LAPTOP_WS] Unknown message type: {msg_type}")
                    
            except json.JSONDecodeError:
                print(f"[ERROR] [LAPTOP_WS] Invalid JSON from {client_id}")
            except Exception as e:
                print(f"[ERROR] [LAPTOP_WS] Error receiving message: {e}")
                break
                
    except WebSocketDisconnect:
        print(f"[LAPTOP_WS] Client disconnected: {client_id}")
    except Exception as e:
        print(f"[ERROR] [LAPTOP_WS] Exception: {e}")
    finally:
        # Remove from connected clients
        if client_id in connected_laptops:
            del connected_laptops[client_id]
        print(f"[LAPTOP_WS] {client_id} removed. Remaining: {len(connected_laptops)}")


async def send_command_to_laptops(command: Dict) -> bool:
    """
    Send command to all connected laptops
    
    Args:
        command: Command dict with action and parameters
        
    Returns:
        True if sent to at least one laptop
    """
    
    if not connected_laptops:
        print("[LAPTOP_WS] No laptops connected")
        return False
    
    print(f"[LAPTOP_WS] Broadcasting command to {len(connected_laptops)} laptop(s): {command}")
    
    # Send to all connected laptops
    disconnected = []
    success_count = 0
    
    for client_id, websocket in connected_laptops.items():
        try:
            await websocket.send_json({
                "type": "command",
                "command": command
            })
            success_count += 1
            print(f"[LAPTOP_WS] Sent to {client_id}")
        except Exception as e:
            print(f"[ERROR] [LAPTOP_WS] Failed to send to {client_id}: {e}")
            disconnected.append(client_id)
    
    # Clean up disconnected clients
    for client_id in disconnected:
        if client_id in connected_laptops:
            del connected_laptops[client_id]
    
    return success_count > 0


@router.get("/laptop/status")
async def get_laptop_status():
    """Get status of connected laptops"""
    return {
        "connected": len(connected_laptops),
        "clients": list(connected_laptops.keys())
    }


@router.post("/laptop/command")
async def send_laptop_command(command: Dict):
    """
    Manually send command to laptops (for testing)
    
    Body example:
    {
        "action": "open_youtube",
        "query": "test video"
    }
    """
    
    success = await send_command_to_laptops(command)
    
    if success:
        return {"status": "success", "message": "Command sent to laptops"}
    else:
        return {"status": "error", "message": "No laptops connected"}
