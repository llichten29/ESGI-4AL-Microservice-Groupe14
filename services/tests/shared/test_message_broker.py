from unittest.mock import MagicMock, patch
import pytest
import pika
import json

from message_broker import MessageBroker


@pytest.fixture
def mock_channel():
    return MagicMock()


@pytest.fixture
def mock_connection(mock_channel):
    conn = MagicMock()
    conn.channel.return_value = mock_channel
    return conn


@pytest.fixture
def broker(mock_connection):
    credentials = pika.PlainCredentials("guest", "guest")
    with patch.object(pika, 'BlockingConnection', return_value=mock_connection):
        with patch.object(pika, 'PlainCredentials', return_value=credentials):
            b = MessageBroker(host="localhost", port=5672, user="guest", password="guest")
            b.connect()
            yield b
            b.close()


class TestMessageBrokerConnect:
    def test_connect_creates_connection_and_channel(self, mock_connection, mock_channel):
        credentials = pika.PlainCredentials("guest", "guest")
        with patch.object(pika, 'BlockingConnection', return_value=mock_connection):
            with patch.object(pika, 'PlainCredentials', return_value=credentials):
                b = MessageBroker()
                b.connect()
                assert b.connection is mock_connection
                assert b.channel is mock_channel
                b.close()

    def test_connect_raises_on_failure(self):
        with patch.object(pika, 'BlockingConnection', side_effect=Exception("connection failed")):
            b = MessageBroker()
            with pytest.raises(Exception, match="connection failed"):
                b.connect()


class TestMessageBrokerDeclare:
    def test_declare_exchange(self, broker, mock_channel):
        broker.declare_exchange("test.exchange", "topic")
        mock_channel.exchange_declare.assert_called_once_with(
            exchange="test.exchange", exchange_type="topic", durable=True
        )

    def test_declare_queue(self, broker, mock_channel):
        broker.declare_queue("test.queue", durable=True)
        mock_channel.queue_declare.assert_called_once_with(queue="test.queue", durable=True)

    def test_bind_queue(self, broker, mock_channel):
        broker.bind_queue("test.queue", "test.exchange", "test.key")
        mock_channel.queue_bind.assert_called_once_with(
            queue="test.queue", exchange="test.exchange", routing_key="test.key"
        )


class TestMessageBrokerPublish:
    def test_publish_event_serializes_json(self, broker, mock_channel):
        event_data = {"type": "TestEvent", "id": "123"}
        broker.publish_event("test.exchange", "test.key", event_data)
        mock_channel.basic_publish.assert_called_once()
        call_args = mock_channel.basic_publish.call_args[1]
        assert call_args["exchange"] == "test.exchange"
        assert call_args["routing_key"] == "test.key"
        assert json.loads(call_args["body"]) == event_data
        assert call_args["properties"].content_type == "application/json"
        assert call_args["properties"].delivery_mode == 2


class TestMessageBrokerSubscribe:
    def test_subscribe_event(self, broker, mock_channel):
        callback = MagicMock()
        broker.subscribe_event("test.queue", callback)
        mock_channel.basic_consume.assert_called_once_with(
            queue="test.queue", on_message_callback=callback, auto_ack=False
        )

    def test_start_consuming(self, broker, mock_channel):
        broker.start_consuming()
        mock_channel.start_consuming.assert_called_once()


class TestMessageBrokerClose:
    def test_close_connection(self, broker, mock_connection):
        mock_connection.is_closed = False
        broker.close()
        mock_connection.close.assert_called_once()

    def test_close_does_not_close_already_closed(self, broker, mock_connection):
        mock_connection.is_closed = True
        broker.close()
        mock_connection.close.assert_not_called()


class TestMessageBrokerContextManager:
    def test_context_manager(self, mock_connection, mock_channel):
        mock_connection.is_closed = False
        credentials = pika.PlainCredentials("guest", "guest")
        with patch.object(pika, 'BlockingConnection', return_value=mock_connection):
            with patch.object(pika, 'PlainCredentials', return_value=credentials):
                with MessageBroker() as b:
                    assert b.connection is mock_connection
                    assert b.channel is mock_channel
                mock_connection.close.assert_called_once()
