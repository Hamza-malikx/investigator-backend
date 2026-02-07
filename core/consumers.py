import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from investigations.models import Investigation
from entities.models import Entity, Relationship
from evidence.models import Evidence

User = get_user_model()


class InvestigationConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for real-time investigation updates.
    
    Handles:
    - Real-time board updates (entities, relationships)
    - Investigation status changes
    - Thought chain updates
    - Progress notifications
    """
    
    async def connect(self):
        """Handle WebSocket connection"""
        self.investigation_id = self.scope['url_route']['kwargs']['investigation_id']
        self.room_group_name = f'investigation_{self.investigation_id}'
        
        # Verify user has access to this investigation
        user = self.scope.get('user')
        if not user or not user.is_authenticated:
            await self.close()
            return
        
        # Check if user owns this investigation
        has_access = await self.check_investigation_access(user, self.investigation_id)
        if not has_access:
            await self.close()
            return
        
        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Send initial connection confirmation
        await self.send(text_data=json.dumps({
            'type': 'connection_established',
            'message': f'Connected to investigation {self.investigation_id}',
            'investigation_id': str(self.investigation_id)
        }))
    
    async def disconnect(self, close_code):
        """Handle WebSocket disconnection"""
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
    
    async def receive(self, text_data):
        """
        Receive message from WebSocket (client -> server)
        
        Supported message types:
        - pause_investigation
        - resume_investigation
        - redirect_focus
        - request_update
        """
        try:
            data = json.loads(text_data)
            message_type = data.get('type')
            
            if message_type == 'pause_investigation':
                await self.handle_pause_investigation()
            
            elif message_type == 'resume_investigation':
                await self.handle_resume_investigation()
            
            elif message_type == 'redirect_focus':
                focus = data.get('focus')
                await self.handle_redirect_focus(focus)
            
            elif message_type == 'request_update':
                await self.handle_request_update()
            
            else:
                await self.send(text_data=json.dumps({
                    'type': 'error',
                    'message': f'Unknown message type: {message_type}'
                }))
        
        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Invalid JSON'
            }))
    
    # Receive message from room group (server -> client)
    async def status_update(self, event):
        """Send status update to WebSocket"""
        await self.send(text_data=json.dumps({
            'type': 'status_update',
            'data': event['data']
        }))
    
    async def entity_discovered(self, event):
        """Send entity discovery notification"""
        await self.send(text_data=json.dumps({
            'type': 'entity_discovered',
            'data': event['data']
        }))
    
    async def relationship_discovered(self, event):
        """Send relationship discovery notification"""
        await self.send(text_data=json.dumps({
            'type': 'relationship_discovered',
            'data': event['data']
        }))
    
    async def evidence_discovered(self, event):
        """Send evidence discovery notification"""
        await self.send(text_data=json.dumps({
            'type': 'evidence_discovered',
            'data': event['data']
        }))
    
    async def thought_update(self, event):
        """Send thought chain update"""
        await self.send(text_data=json.dumps({
            'type': 'thought_update',
            'data': event['data']
        }))
    
    async def progress_update(self, event):
        """Send progress update"""
        await self.send(text_data=json.dumps({
            'type': 'progress_update',
            'data': event['data']
        }))
    
    async def board_update(self, event):
        """Send board state update"""
        await self.send(text_data=json.dumps({
            'type': 'board_update',
            'data': event['data']
        }))
    
    async def error_occurred(self, event):
        """Send error notification"""
        await self.send(text_data=json.dumps({
            'type': 'error',
            'data': event['data']
        }))
    
    # Handler methods
    async def handle_pause_investigation(self):
        """Handle pause investigation request"""
        success = await self.update_investigation_status('paused')
        
        if success:
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'status_update',
                    'data': {
                        'status': 'paused',
                        'message': 'Investigation paused'
                    }
                }
            )
        else:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Failed to pause investigation'
            }))
    
    async def handle_resume_investigation(self):
        """Handle resume investigation request"""
        success = await self.update_investigation_status('running')
        
        if success:
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'status_update',
                    'data': {
                        'status': 'running',
                        'message': 'Investigation resumed'
                    }
                }
            )
            
            # TODO: Trigger Celery task to resume processing
        else:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Failed to resume investigation'
            }))
    
    async def handle_redirect_focus(self, focus):
        """Handle redirect focus request"""
        if not focus:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Focus is required'
            }))
            return
        
        # TODO: Update investigation plan and signal Celery task
        
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'status_update',
                'data': {
                    'message': f'Investigation focus redirected to: {focus}',
                    'new_focus': focus
                }
            }
        )
    
    async def handle_request_update(self):
        """Send current investigation state"""
        investigation_data = await self.get_investigation_state()
        
        await self.send(text_data=json.dumps({
            'type': 'full_update',
            'data': investigation_data
        }))
    
    # Database operations
    @database_sync_to_async
    def check_investigation_access(self, user, investigation_id):
        """Check if user has access to investigation"""
        try:
            Investigation.objects.get(id=investigation_id, user=user)
            return True
        except Investigation.DoesNotExist:
            return False
    
    @database_sync_to_async
    def update_investigation_status(self, status):
        """Update investigation status"""
        try:
            investigation = Investigation.objects.get(id=self.investigation_id)
            investigation.status = status
            investigation.save()
            return True
        except Investigation.DoesNotExist:
            return False
    
    @database_sync_to_async
    def get_investigation_state(self):
        """Get current investigation state"""
        try:
            investigation = Investigation.objects.get(id=self.investigation_id)
            
            return {
                'id': str(investigation.id),
                'status': investigation.status,
                'current_phase': investigation.current_phase,
                'progress_percentage': investigation.progress_percentage,
                'confidence_score': investigation.confidence_score,
                'entities_count': investigation.entities.count(),
                'relationships_count': investigation.relationships.count(),
                'evidence_count': investigation.evidence.count(),
            }
        except Investigation.DoesNotExist:
            return None


class BoardConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer specifically for investigation board real-time updates.
    
    Handles:
    - Entity position updates
    - Layout changes
    - Annotation updates
    - Filter updates
    """
    
    async def connect(self):
        """Handle WebSocket connection"""
        self.investigation_id = self.scope['url_route']['kwargs']['investigation_id']
        self.room_group_name = f'board_{self.investigation_id}'
        
        # Verify user access
        user = self.scope.get('user')
        if not user or not user.is_authenticated:
            await self.close()
            return
        
        has_access = await self.check_investigation_access(user, self.investigation_id)
        if not has_access:
            await self.close()
            return
        
        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Send initial board state
        board_state = await self.get_board_state()
        await self.send(text_data=json.dumps({
            'type': 'board_state',
            'data': board_state
        }))
    
    async def disconnect(self, close_code):
        """Handle WebSocket disconnection"""
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
    
    async def receive(self, text_data):
        """Receive message from WebSocket"""
        try:
            data = json.loads(text_data)
            message_type = data.get('type')
            
            if message_type == 'update_entity_position':
                await self.handle_entity_position_update(data)
            
            elif message_type == 'update_layout':
                await self.handle_layout_update(data)
            
            elif message_type == 'request_board_state':
                board_state = await self.get_board_state()
                await self.send(text_data=json.dumps({
                    'type': 'board_state',
                    'data': board_state
                }))
        
        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Invalid JSON'
            }))
    
    # Receive from room group
    async def entity_position_update(self, event):
        """Broadcast entity position update"""
        await self.send(text_data=json.dumps({
            'type': 'entity_position_update',
            'data': event['data']
        }))
    
    async def layout_update(self, event):
        """Broadcast layout update"""
        await self.send(text_data=json.dumps({
            'type': 'layout_update',
            'data': event['data']
        }))
    
    async def node_added(self, event):
        """Broadcast new node"""
        await self.send(text_data=json.dumps({
            'type': 'node_added',
            'data': event['data']
        }))
    
    async def edge_added(self, event):
        """Broadcast new edge"""
        await self.send(text_data=json.dumps({
            'type': 'edge_added',
            'data': event['data']
        }))
    
    # Handler methods
    async def handle_entity_position_update(self, data):
        """Handle entity position update from client"""
        entity_id = data.get('entity_id')
        position_x = data.get('position_x')
        position_y = data.get('position_y')
        
        success = await self.update_entity_position(entity_id, position_x, position_y)
        
        if success:
            # Broadcast to other clients
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'entity_position_update',
                    'data': {
                        'entity_id': entity_id,
                        'position_x': position_x,
                        'position_y': position_y
                    }
                }
            )
    
    async def handle_layout_update(self, data):
        """Handle layout update"""
        layout_type = data.get('layout_type')
        
        # Broadcast layout change
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'layout_update',
                'data': {
                    'layout_type': layout_type
                }
            }
        )
    
    # Database operations
    @database_sync_to_async
    def check_investigation_access(self, user, investigation_id):
        """Check if user has access to investigation"""
        try:
            Investigation.objects.get(id=investigation_id, user=user)
            return True
        except Investigation.DoesNotExist:
            return False
    
    @database_sync_to_async
    def update_entity_position(self, entity_id, x, y):
        """Update entity position in database"""
        try:
            entity = Entity.objects.get(id=entity_id, investigation_id=self.investigation_id)
            entity.position_x = x
            entity.position_y = y
            entity.save()
            return True
        except Entity.DoesNotExist:
            return False
    
    @database_sync_to_async
    def get_board_state(self):
        """Get complete board state"""
        try:
            investigation = Investigation.objects.get(id=self.investigation_id)
            entities = Entity.objects.filter(investigation=investigation)
            relationships = Relationship.objects.filter(investigation=investigation)
            
            # Build nodes
            nodes = []
            for entity in entities:
                nodes.append({
                    'id': str(entity.id),
                    'type': entity.entity_type,
                    'label': entity.name,
                    'confidence': entity.confidence,
                    'position': {
                        'x': entity.position_x or 0,
                        'y': entity.position_y or 0
                    },
                    'metadata': entity.metadata
                })
            
            # Build edges
            edges = []
            for rel in relationships:
                edges.append({
                    'id': str(rel.id),
                    'source': str(rel.source_entity.id),
                    'target': str(rel.target_entity.id),
                    'type': rel.relationship_type,
                    'label': rel.description or rel.relationship_type,
                    'confidence': rel.confidence,
                    'strength': rel.strength,
                    'is_active': rel.is_active
                })
            
            return {
                'investigation_id': str(investigation.id),
                'nodes': nodes,
                'edges': edges,
                'total_nodes': len(nodes),
                'total_edges': len(edges)
            }
        
        except Investigation.DoesNotExist:
            return None