import pytest
from unittest.mock import patch, MagicMock
from backend.services.ollama_client import OllamaClient


class TestOllamaClient:
    def setup_method(self):
        self.client = OllamaClient()

    def test_is_available_true(self):
        with patch("httpx.Client") as mock_client_cls:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_client_cls.return_value.__enter__.return_value.get.return_value = mock_response
            assert self.client.is_available() is True

    def test_is_available_false_on_connection_error(self):
        with patch("httpx.Client") as mock_client_cls:
            import httpx
            mock_client_cls.return_value.__enter__.return_value.get.side_effect = httpx.RequestError("conn refused")
            assert self.client.is_available() is False

    def test_generate_returns_string(self):
        mock_response = {
            "message": {"content": "This is a test response from Ollama."}
        }
        with patch.object(self.client, "_post", return_value=mock_response):
            result = self.client.generate("Test prompt")
            assert isinstance(result, str)
            assert "test response" in result

    def test_generate_json_valid(self):
        mock_response = {
            "message": {"content": '{"role_title": "Engineer", "must_have_skills": ["python"]}'}
        }
        with patch.object(self.client, "_post", return_value=mock_response):
            result = self.client.generate_json("Extract JSON")
            assert isinstance(result, dict)
            assert result["role_title"] == "Engineer"

    def test_generate_json_invalid_raises(self):
        mock_response = {
            "message": {"content": "This is not JSON at all, just plain text."}
        }
        with patch.object(self.client, "_post", return_value=mock_response):
            with pytest.raises(ValueError, match="invalid JSON"):
                self.client.generate_json("Extract JSON")

    def test_retry_on_connection_error(self):
        import httpx
        call_count = 0

        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise httpx.RequestError("temporary failure")
            return {"message": {"content": "success"}}

        with patch.object(self.client, "_post", side_effect=side_effect):
            # _post itself handles retries, so mock at httpx level
            pass

        with patch("httpx.Client") as mock_cls:
            import httpx
            mock_instance = mock_cls.return_value.__enter__.return_value
            mock_instance.post.side_effect = [
                httpx.RequestError("fail 1"),
                httpx.RequestError("fail 2"),
                httpx.RequestError("fail 3"),
            ]
            with pytest.raises(ConnectionError):
                self.client._post("/api/chat", {"model": "llama3"})

    def test_generate_with_system_prompt(self):
        mock_response = {"message": {"content": "response with system"}}
        with patch.object(self.client, "_post", return_value=mock_response) as mock_post:
            self.client.generate("prompt", system="You are a helpful assistant")
            call_args = mock_post.call_args
            payload = call_args[0][1]
            messages = payload["messages"]
            assert messages[0]["role"] == "system"
            assert messages[1]["role"] == "user"
