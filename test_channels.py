import os
import django

# Setup Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'investigator.settings')
django.setup()

import asyncio
from channels.layers import get_channel_layer

async def test_channel_layer():
    channel_layer = get_channel_layer()
    
    print(f"Channel layer: {channel_layer}")
    print(f"Channel layer type: {type(channel_layer)}")
    
    # Send test message
    await channel_layer.group_send(
        'test_group',
        {
            'type': 'test.message',
            'text': 'Hello, WebSocket!'
        }
    )
    print("✅ Message sent successfully!")
    print("✅ Channel layer is working correctly!")

if __name__ == '__main__':
    # Run test
    asyncio.run(test_channel_layer())