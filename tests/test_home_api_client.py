from unittest.mock import MagicMock

import requests

from smart_house_agent.clients.home_api import HomeApiClient


def test_post_update_device_uses_session_and_url():
    session = MagicMock(spec=requests.Session)
    response = MagicMock()
    response.status_code = 200
    session.post.return_value = response

    client = HomeApiClient("http://localhost:8000", session=session)
    out = client.post_update_device("light", "on")

    assert out is response
    session.post.assert_called_once()
    call_kw = session.post.call_args
    assert call_kw[0][0] == "http://localhost:8000/update_device"
    assert call_kw[1]["json"] == {"device_id": "light", "action": "on"}


def test_get_status_parses_json():
    session = MagicMock(spec=requests.Session)
    response = MagicMock()
    response.json.return_value = {"light": "off"}
    session.get.return_value = response

    client = HomeApiClient("http://127.0.0.1:8000", session=session)
    assert client.get_status() == {"light": "off"}
