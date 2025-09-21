import pytest
from channels.testing import WebsocketCommunicator
from django.contrib.auth import get_user_model
from project_name.asgi import application
import jwt
from django.conf import settings
from django.utils import timezone

User = get_user_model()

@pytest.mark.asyncio
async def test_websocket_auth_and_chat(transactional_db, settings):
    # create user
    u = User.objects.create(username='bob')
    payload = {
        'sub': str(u.id),
        'iat': int(timezone.now().timestamp()),
        'exp': int((timezone.now() + timezone.timedelta(hours=1)).timestamp()),
    }
    token = jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)

    communicator = WebsocketCommunicator(application, f"/ws/chat/?token={token}")
    connected, subprotocol = await communicator.connect()
    assert connected

    # join room
    await communicator.send_json_to({'type': 'join', 'room': 'general'})
    join_msg = await communicator.receive_json_from()
    assert join_msg['type'] == 'notification'
    assert join_msg['event'] == 'join'

    # send message
    await communicator.send_json_to({'type': 'message', 'room': 'general', 'text': 'hello'})
    msg = await communicator.receive_json_from()
    assert msg['type'] == 'message'
    assert msg['text'] == 'hello'

    await communicator.disconnect()
