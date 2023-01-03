import socket
import struct

from . import exceptions


class Request:
    def __init__(self, conn: socket.socket, message: bytes):
        self.conn = conn
        self.message = message

    def send_request(self) -> bytes:
        self._send()
        return self._retrieve()

    def _send(self) -> None:
        message_header = struct.pack(">I", len(self.message))
        self.header_len = len(message_header)
        request_message = message_header + self.message

        self.conn.sendall(request_message)

    def _retrieve(self) -> bytes:
        response_buff = b""
        while len(response_buff) < self.header_len:
            try:
                data = self.conn.recv(self.header_len)
            except (TimeoutError, socket.timeout):
                raise exceptions.ServerTookTooLong from None
            if not data:
                break
            response_buff += data

        if len(response_buff) < self.header_len:
            raise exceptions.CommunicationError(
                f"Expected {self.header_len}, got {len(response_buff)} Bytes"
            )

        expected_response_len = struct.unpack(">I", response_buff[: self.header_len])[0]
        response_buff = response_buff[self.header_len :]

        retrieved = len(response_buff)
        while retrieved < expected_response_len:
            try:
                data = self.conn.recv(1024)
            except (TimeoutError, socket.timeout):
                raise exceptions.ServerTookTooLong from None
            if not data:
                break
            retrieved += len(data)
            response_buff += data

        if retrieved != expected_response_len:
            raise exceptions.CommunicationError(
                f"Expected {expected_response_len}, got {retrieved} Bytes"
            )

        return response_buff
