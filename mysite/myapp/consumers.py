import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import User
from .models import ChatRoom, ChatMessage, UserOnlineStatus
from django.utils import timezone

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_name = self.scope['url_route']['kwargs']['room_name']
        self.room_group_name = f'chat_{self.room_name}'
        
        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Mark user as online
        await self.set_user_online(True)
        
        # Send online status to room
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'user_status',
                'username': self.scope['user'].username,
                'is_online': True
            }
        )
    
    async def disconnect(self, close_code):
        # Mark user as offline
        await self.set_user_online(False)
        
        # Send offline status to room
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'user_status',
                'username': self.scope['user'].username,
                'is_online': False
            }
        )
        
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
    
    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message = text_data_json['message']
        sender = self.scope['user']
        
        # Save message to database
        await self.save_message(sender, message)
        
        # Send message to room group
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message': message,
                'sender': sender.username,
                'timestamp': timezone.now().strftime('%I:%M %p')
            }
        )
    
    async def chat_message(self, event):
        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'type': 'message',
            'message': event['message'],
            'sender': event['sender'],
            'timestamp': event['timestamp']
        }))
    
    async def user_status(self, event):
        await self.send(text_data=json.dumps({
            'type': 'status',
            'username': event['username'],
            'is_online': event['is_online']
        }))
    
    @database_sync_to_async
    def save_message(self, sender, message):
        room, _ = ChatRoom.objects.get_or_create(
            room_id=self.room_name,
            defaults={'room_type': 'user_admin'}
        )
        if not room.user and sender.username != 'admin':
            room.user = sender
            room.save()
        
        ChatMessage.objects.create(
            room=room,
            sender=sender,
            message=message
        )
    
    @database_sync_to_async
    def set_user_online(self, is_online):
        status, _ = UserOnlineStatus.objects.get_or_create(user=self.scope['user'])
        status.is_online = is_online
        status.last_seen = timezone.now()
        status.save()


class AdminChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user_id = self.scope['url_route']['kwargs']['user_id']
        self.room_group_name = f'admin_chat_{self.user_id}'
        
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
    
    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
    
    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message = text_data_json['message']
        sender = self.scope['user']
        
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'admin_message',
                'message': message,
                'sender': sender.username,
                'timestamp': timezone.now().strftime('%I:%M %p')
            }
        )
    
    async def admin_message(self, event):
        await self.send(text_data=json.dumps({
            'type': 'message',
            'message': event['message'],
            'sender': event['sender'],
            'timestamp': event['timestamp']
        }))