import json
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.exceptions import DenyConnection
from django.utils import timezone


class ChatConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        user = self.scope.get('user')
        if not user:
            # Reject connection
            await self.close(code=4401)
            return
        await self.accept()
        self.user = user

    async def disconnect(self, code):
        # Broadcast leave notifications for rooms we were in (store rooms on self.scope)
        rooms = getattr(self, 'rooms', set())
        for room in list(rooms):
            await self.channel_layer.group_discard(room, self.channel_name)
            await self.channel_layer.group_send(
                room,
                {
                    'type': 'notification',
                    'event': 'leave',
                    'user': self.user.username,
                    'room': room,
                    'ts': timezone.now().isoformat(),
                }
            )

    async def receive_json(self, content):
        t = content.get('type')
        if t == 'join':
            await self.handle_join(content)
        elif t == 'message':
            await self.handle_message(content)
        else:
            await self.send_json({'error': 'unknown_type'})

    async def handle_join(self, payload):
        room = payload.get('room')
        if not room:
            return await self.send_json({'error': 'room required'})
        await self.channel_layer.group_add(room, self.channel_name)
        self.rooms = getattr(self, 'rooms', set())
        self.rooms.add(room)
        await self.channel_layer.group_send(
            room,
            {
                'type': 'notification',
                'event': 'join',
                'user': self.user.username,
                'room': room,
                'ts': timezone.now().isoformat(),
            }
        )

    async def handle_message(self, payload):
        room = payload.get('room')
        text = payload.get('text')
        if not room or not text:
            return await self.send_json({'error': 'room and text required'})
        msg = {
            'type': 'message',
            'user': self.user.username,
            'text': text,
            'room': room,
            'ts': timezone.now().isoformat(),
        }
        await self.channel_layer.group_send(room, msg)

    # Handlers for group_send
    async def message(self, event):
        await self.send_json(event)

    async def notification(self, event):
        await self.send_json(event)
