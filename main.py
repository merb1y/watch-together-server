import sys
import json
import time
from typing import Dict, List
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="WatchTogether Cloud Relay Server")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ConnectionManager:
    def __init__(self):
        # room_id -> { client_id: {"ws": WebSocket, "username": str} }
        self.rooms: Dict[str, Dict[str, dict]] = {}
        # room_id -> { "action": str, "time": float, "url": str, "updated_at": float }
        self.room_states: Dict[str, dict] = {}

    async def connect(self, room_id: str, client_id: str, username: str, websocket: WebSocket):
        await websocket.accept()
        if room_id not in self.rooms:
            self.rooms[room_id] = {}
            self.room_states[room_id] = {
                "action": "pause",
                "time": 0.0,
                "url": "",
                "updated_at": time.time()
            }
        
        self.rooms[room_id][client_id] = {
            "ws": websocket,
            "username": username
        }

        members = [info["username"] for info in self.rooms[room_id].values()]
        await self.broadcast(room_id, {
            "type": "member-update",
            "message": f"{username} odaya katildi",
            "members": members,
            "state": self.room_states[room_id]
        })

    def disconnect(self, room_id: str, client_id: str):
        if room_id in self.rooms and client_id in self.rooms[room_id]:
            username = self.rooms[room_id][client_id]["username"]
            del self.rooms[room_id][client_id]
            if not self.rooms[room_id]:
                del self.rooms[room_id]
                if room_id in self.room_states:
                    del self.room_states[room_id]
            return username
        return None

    async def broadcast(self, room_id: str, message: dict, sender_id: str = None):
        if room_id not in self.rooms:
            return
        
        dead_clients = []
        for client_id, client in self.rooms[room_id].items():
            if sender_id and client_id == sender_id:
                continue
            try:
                await client["ws"].send_text(json.dumps(message))
            except Exception:
                dead_clients.append(client_id)
        
        for dead_id in dead_clients:
            self.disconnect(room_id, dead_id)

manager = ConnectionManager()

@app.get("/")
def home():
    return {
        "status": "online",
        "service": "WatchTogether Cloud Server",
        "active_rooms": len(manager.rooms),
        "total_connected_users": sum(len(room) for room in manager.rooms.values())
    }

@app.websocket("/ws/{room_id}/{username}")
async def websocket_endpoint(websocket: WebSocket, room_id: str, username: str):
    client_id = f"{username}_{time.time()}"
    await manager.connect(room_id, client_id, username, websocket)
    try:
        while True:
            data_text = await websocket.receive_text()
            data = json.loads(data_text)
            msg_type = data.get("type")

            if msg_type == "action":
                action = data.get("action")
                current_time = float(data.get("time", 0.0))
                
                if room_id in manager.room_states:
                    manager.room_states[room_id]["action"] = action
                    manager.room_states[room_id]["time"] = current_time
                    manager.room_states[room_id]["updated_at"] = time.time()

                await manager.broadcast(room_id, {
                    "type": "action",
                    "sender": username,
                    "action": action,
                    "time": current_time
                }, sender_id=client_id)

            elif msg_type == "navigate":
                target_url = data.get("url")
                if room_id in manager.room_states:
                    manager.room_states[room_id]["url"] = target_url
                await manager.broadcast(room_id, {
                    "type": "navigate",
                    "sender": username,
                    "url": target_url
                }, sender_id=client_id)

            elif msg_type == "chat":
                await manager.broadcast(room_id, {
                    "type": "chat",
                    "sender": username,
                    "message": data.get("message", "")
                })

            elif msg_type == "request-state":
                await websocket.send_text(json.dumps({
                    "type": "state-response",
                    "state": manager.room_states.get(room_id, {})
                }))

    except WebSocketDisconnect:
        left_user = manager.disconnect(room_id, client_id)
        if room_id in manager.rooms:
            members = [info["username"] for info in manager.rooms[room_id].values()]
            await manager.broadcast(room_id, {
                "type": "member-update",
                "message": f"{left_user} odadan ayrildi",
                "members": members
            })
