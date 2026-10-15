import asyncio

from fastapi import HTTPException, APIRouter, WebSocket, WebSocketDisconnect, status
from jose import JWTError, jwt

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models.bus_location import BusLocation

router = APIRouter(tags=["Realtime"])
settings = get_settings()


class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, list[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, bus_id: str):
        await websocket.accept()
        if bus_id not in self.active_connections:
            self.active_connections[bus_id] = []
        self.active_connections[bus_id].append(websocket)

    def disconnect(self, websocket: WebSocket, bus_id: str):
        self.active_connections.get(bus_id, []).remove(websocket)


manager = ConnectionManager()


async def authenticate_ws_token(token: str | None):
    if not token:
        raise ValueError("Missing token")
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
    except JWTError as exc:
        raise ValueError("Invalid token") from exc
    if payload.get("type") != "access":
        raise ValueError("Token type invalid")
    return payload


@router.websocket("/ws/buses/{bus_id}/location")
async def bus_location_socket(websocket: WebSocket, bus_id: str):
    token = websocket.query_params.get("token")
    try:
        payload = await authenticate_ws_token(token)
        from app.models.parent import Parent
        from app.services.transport_service import authorize_bus
        with SessionLocal() as db:
            user = db.get(Parent, int(payload["sub"]))
            if user is None:
                raise ValueError("Unknown user")
            authorize_bus(db, user, int(bus_id))
    except (ValueError, KeyError, HTTPException):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await manager.connect(websocket, bus_id)
    try:
        while True:
            with SessionLocal() as db:
                user = db.get(Parent, int(payload["sub"]))
                if user is None:
                    raise HTTPException(status_code=403)
                authorize_bus(db, user, int(bus_id))
                latest = db.query(BusLocation).filter(BusLocation.bus_id == int(bus_id)).order_by(BusLocation.server_time.desc()).first()
            if latest:
                await websocket.send_json({
                    "bus_id": int(bus_id),
                    "lat": latest.lat,
                    "lng": latest.lng,
                    "speed": latest.speed,
                    "heading": latest.heading,
                    "server_time": latest.server_time.isoformat(),
                })
            await asyncio.sleep(5)
    except HTTPException:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(websocket, bus_id)
