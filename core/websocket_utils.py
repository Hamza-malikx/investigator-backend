from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync


class WebSocketBroadcaster:
    """
    Utility class for broadcasting events to WebSocket clients.
    Use this from Django views, Celery tasks, or signals.
    """
    
    def __init__(self):
        self.channel_layer = get_channel_layer()
    
    def _send_to_group(self, group_name, event_type, data):
        """Internal method to send message to group"""
        async_to_sync(self.channel_layer.group_send)(
            group_name,
            {
                'type': event_type,
                'data': data
            }
        )
    
    # Investigation events
    def broadcast_status_update(self, investigation_id, status, current_phase=None, progress=None):
        """Broadcast investigation status update"""
        group_name = f'investigation_{investigation_id}'
        data = {
            'investigation_id': str(investigation_id),
            'status': status,
        }
        
        if current_phase:
            data['current_phase'] = current_phase
        if progress is not None:
            data['progress_percentage'] = progress
        
        self._send_to_group(group_name, 'status_update', data)
    
    def broadcast_entity_discovered(self, investigation_id, entity):
        """Broadcast new entity discovery"""
        group_name = f'investigation_{investigation_id}'
        data = {
            'entity_id': str(entity.id),
            'entity_type': entity.entity_type,
            'name': entity.name,
            'confidence': entity.confidence,
            'metadata': entity.metadata,
        }
        
        self._send_to_group(group_name, 'entity_discovered', data)
        
        # Also send to board group
        board_group = f'board_{investigation_id}'
        self._send_to_group(board_group, 'node_added', {
            'id': str(entity.id),
            'type': entity.entity_type,
            'label': entity.name,
            'confidence': entity.confidence,
            'position': {
                'x': entity.position_x or 0,
                'y': entity.position_y or 0
            }
        })
    
    def broadcast_relationship_discovered(self, investigation_id, relationship):
        """Broadcast new relationship discovery"""
        group_name = f'investigation_{investigation_id}'
        data = {
            'relationship_id': str(relationship.id),
            'relationship_type': relationship.relationship_type,
            'source_entity': str(relationship.source_entity.id),
            'source_name': relationship.source_entity.name,
            'target_entity': str(relationship.target_entity.id),
            'target_name': relationship.target_entity.name,
            'confidence': relationship.confidence,
            'strength': relationship.strength,
        }
        
        self._send_to_group(group_name, 'relationship_discovered', data)
        
        # Also send to board group
        board_group = f'board_{investigation_id}'
        self._send_to_group(board_group, 'edge_added', {
            'id': str(relationship.id),
            'source': str(relationship.source_entity.id),
            'target': str(relationship.target_entity.id),
            'type': relationship.relationship_type,
            'label': relationship.description or relationship.relationship_type,
            'confidence': relationship.confidence,
            'strength': relationship.strength
        })
    
    def broadcast_evidence_discovered(self, investigation_id, evidence):
        """Broadcast new evidence discovery"""
        group_name = f'investigation_{investigation_id}'
        data = {
            'evidence_id': str(evidence.id),
            'evidence_type': evidence.evidence_type,
            'title': evidence.title,
            'source_url': evidence.source_url,
            'source_credibility': evidence.source_credibility,
        }
        
        self._send_to_group(group_name, 'evidence_discovered', data)
    
    def broadcast_thought_update(self, investigation_id, thought):
        """Broadcast thought chain update"""
        group_name = f'investigation_{investigation_id}'
        data = {
            'thought_id': str(thought.get('id', '')),
            'thought_type': thought.get('type', ''),
            'content': thought.get('content', ''),
            'confidence': thought.get('confidence', 0),
            'timestamp': thought.get('timestamp', ''),
        }
        
        self._send_to_group(group_name, 'thought_update', data)
    
    def broadcast_progress_update(self, investigation_id, progress_data):
        """Broadcast investigation progress"""
        group_name = f'investigation_{investigation_id}'
        self._send_to_group(group_name, 'progress_update', progress_data)
    
    def broadcast_error(self, investigation_id, error_message, error_type=None):
        """Broadcast error notification"""
        group_name = f'investigation_{investigation_id}'
        data = {
            'message': error_message,
            'error_type': error_type or 'general_error',
            'investigation_id': str(investigation_id)
        }
        
        self._send_to_group(group_name, 'error_occurred', data)
    
    # Board specific events
    def broadcast_board_update(self, investigation_id, board_data):
        """Broadcast complete board state update"""
        group_name = f'board_{investigation_id}'
        self._send_to_group(group_name, 'board_update', board_data)
    
    def broadcast_entity_position_update(self, investigation_id, entity_id, x, y):
        """Broadcast entity position change"""
        group_name = f'board_{investigation_id}'
        data = {
            'entity_id': str(entity_id),
            'position_x': x,
            'position_y': y
        }
        
        self._send_to_group(group_name, 'entity_position_update', data)
    
    def broadcast_layout_change(self, investigation_id, layout_type):
        """Broadcast layout type change"""
        group_name = f'board_{investigation_id}'
        data = {
            'layout_type': layout_type
        }
        
        self._send_to_group(group_name, 'layout_update', data)


# Singleton instance for easy import
broadcaster = WebSocketBroadcaster()


# Convenience functions
def broadcast_status_update(investigation_id, status, **kwargs):
    """Broadcast investigation status update"""
    broadcaster.broadcast_status_update(investigation_id, status, **kwargs)


def broadcast_entity_discovered(investigation_id, entity):
    """Broadcast new entity discovery"""
    broadcaster.broadcast_entity_discovered(investigation_id, entity)


def broadcast_relationship_discovered(investigation_id, relationship):
    """Broadcast new relationship discovery"""
    broadcaster.broadcast_relationship_discovered(investigation_id, relationship)


def broadcast_evidence_discovered(investigation_id, evidence):
    """Broadcast new evidence discovery"""
    broadcaster.broadcast_evidence_discovered(investigation_id, evidence)


def broadcast_thought_update(investigation_id, thought):
    """Broadcast thought chain update"""
    broadcaster.broadcast_thought_update(investigation_id, thought)


def broadcast_progress_update(investigation_id, progress_data):
    """Broadcast investigation progress"""
    broadcaster.broadcast_progress_update(investigation_id, progress_data)


def broadcast_error(investigation_id, error_message, error_type=None):
    """Broadcast error notification"""
    broadcaster.broadcast_error(investigation_id, error_message, error_type)