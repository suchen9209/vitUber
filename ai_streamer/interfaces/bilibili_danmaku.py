"""
B站弹幕监听 - WebSocket连接
"""
import asyncio
import json
import re
from typing import Callable, Optional, List
import aiohttp
from loguru import logger


class BilibiliDanmaku:
    """B站弹幕监听器"""
    
    def __init__(self, room_id: int, on_danmaku: Optional[Callable] = None):
        self.room_id = room_id
        self.on_danmaku = on_danmaku
        
        self.ws = None
        self.session = None
        self.running = False
        
        # B站弹幕服务器
        self.ws_url = f"wss://broadcastlv.chat.bilibili.com:2245/sub"
        
        # 房间信息API
        self.room_api = f"https://api.live.bilibili.com/room/v1/Room/room_init?id={room_id}"
    
    async def _get_room_info(self) -> dict:
        """获取房间信息"""
        async with aiohttp.ClientSession() as session:
            async with session.get(self.room_api) as resp:
                data = await resp.json()
                return data.get("data", {})
    
    def _make_packet(self, data: dict, op: int) -> bytes:
        """构造B站WebSocket数据包"""
        body = json.dumps(data).encode("utf-8")
        header = bytearray([
            0, 0, 0, 0,  # 包长度(后面填)
            0, 16,       # 头部长度固定16
            0, 1,        # 协议版本
            0, op,       # 操作码
            0, 0, 0, 1,  # 序列号
        ])
        
        packet_len = len(header) + len(body)
        header[0:4] = packet_len.to_bytes(4, "big")
        
        return bytes(header) + body
    
    def _parse_packet(self, data: bytes) -> List[dict]:
        """解析B站数据包"""
        messages = []
        offset = 0
        
        while offset < len(data):
            if offset + 16 > len(data):
                break
            
            packet_len = int.from_bytes(data[offset:offset+4], "big")
            header_len = int.from_bytes(data[offset+4:offset+6], "big")
            proto_ver = int.from_bytes(data[offset+6:offset+8], "big")
            op = int.from_bytes(data[offset+8:offset+12], "big")
            seq = int.from_bytes(data[offset+12:offset+16], "big")
            
            body = data[offset+header_len:offset+packet_len]
            offset += packet_len
            
            if op == 5:  # 弹幕消息
                try:
                    msg = json.loads(body.decode("utf-8"))
                    messages.append(msg)
                except:
                    pass
        
        return messages
    
    async def connect(self):
        """连接弹幕服务器"""
        # 获取真实房间ID
        room_info = await self._get_room_info()
        real_room_id = room_info.get("room_id", self.room_id)
        
        logger.info(f"连接到房间: {real_room_id}")
        
        # 创建会话
        self.session = aiohttp.ClientSession()
        
        # 连接WebSocket
        self.ws = await self.session.ws_connect(self.ws_url)
        
        # 发送认证包
        auth_data = {
            "uid": 0,
            "roomid": real_room_id,
            "protover": 3,
            "platform": "web",
            "type": 2
        }
        await self.ws.send_bytes(self._make_packet(auth_data, 7))
        
        # 启动心跳
        asyncio.create_task(self._heartbeat_loop())
        
        # 接收消息
        self.running = True
        async for msg in self.ws:
            if msg.type == aiohttp.WSMsgType.BINARY:
                messages = self._parse_packet(msg.data)
                for message in messages:
                    await self._handle_message(message)
            elif msg.type == aiohttp.WSMsgType.ERROR:
                logger.error(f"WebSocket错误: {msg.data}")
                break
        
        self.running = False
    
    async def _heartbeat_loop(self):
        """心跳保持"""
        while self.running:
            try:
                await self.ws.send_bytes(self._make_packet({}, 2))
                await asyncio.sleep(30)
            except:
                break
    
    async def _handle_message(self, msg: dict):
        """处理消息"""
        cmd = msg.get("cmd", "")
        
        if cmd == "DANMU_MSG":
            # 弹幕消息
            info = msg.get("info", [])
            if len(info) >= 2:
                content = info[1]  # 弹幕内容
                user_info = info[2] if len(info) > 2 else []
                user_id = user_info[0] if len(user_info) > 0 else "0"
                username = user_info[1] if len(user_info) > 1 else "未知用户"
                
                logger.debug(f"[弹幕] {username}: {content}")
                
                if self.on_danmaku:
                    await self.on_danmaku(str(user_id), username, content)
        
        elif cmd == "SEND_GIFT":
            # 礼物消息
            data = msg.get("data", {})
            username = data.get("uname", "未知用户")
            gift_name = data.get("giftName", "礼物")
            logger.info(f"[礼物] {username} 赠送了 {gift_name}")
        
        elif cmd == "INTERACT_WORD":
            # 进入直播间
            data = msg.get("data", {})
            username = data.get("uname", "未知用户")
            logger.debug(f"[进入] {username} 进入了直播间")
    
    async def disconnect(self):
        """断开连接"""
        self.running = False
        if self.ws:
            await self.ws.close()
        if self.session:
            await self.session.close()
        logger.info("弹幕监听器已断开")
