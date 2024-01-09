import socket
import logging

from .protobuf_clients import InternalProtocol_pb2 as internalProto
from . import exceptions
from .request import Request


class InternalClient:

    CONNECTION_TIMEOUT = 1
    CONNECTION_RETRY_COUNT = 1
    SEND_RETRY_COUNT = 1

    CONNECT_RESPONSE_EXCEPTIONS = {
        1: exceptions.AlreadyConnected,
        2: exceptions.ModuleNotSupported,
        3: exceptions.DeviceNotSupported,
        4: exceptions.HigherPriorityAlreadyConnected,
    }

    def __init__(
        self,
        module_id: int,
        hostname: str,
        port: int,
        device_name: str,
        device_type: int,
        device_role: str,
        device_priority: int = 0,
        ) -> None:
        """Initialize context and connect to desired server.

        Args:
            module_id (int): Module ID
            hostname (str): IP of server (module gateway)
            port (int): Port
            device_name (str): Name of this device
            device_type (int): Module specific device type
            device_role (str): Device role
            device_priority (int, optional): Priority of device. Defaults to 0.

        Raises:
            exceptions.ConnectionRefused: Could not establish connection with server.
            exceptions.CommunicationError: Error in communication with server.
            exceptions.ServerTookTooLong: Server did not respond in time.

            Any of exceptions.ConnectExceptions: Server did not allow device to connect.
        """
        self._module_id = module_id
        self._hostname = hostname
        self._port = port
        self._device_name = device_name
        self._device_type = device_type
        self._device_role = device_role
        self._device_priority = device_priority

        self._logger = logging.getLogger(f"InternalClient({self._device_name})")
        self._init_device_message()

        self._client_socket:None|socket.socket = None
        self._current_command = None
        self._is_connected = False
        self._establish_connection()

    @property
    def is_connected(self) -> bool:
        return self._is_connected

    def __repr__(self) -> str:
        return f"InternalClient(moduleId={self._module_id}, deviceName={self._device_name}, deviceType={self._device_type}, priority={self._device_priority})."

    def destroy(self) -> None:
        """Destroy context and disconnect from server."""
        if self._client_socket is not None:
            self._client_socket.close()
            self._client_socket = None
            self._is_connected = False

    def send_status(self, data: bytes, timeout: int) -> None:
        """Send device status (blocking). If status was not sent
           before timeout or another error occured,
           will try to reconnect and reestablish connection.

        Args:
            data (bytes): binary data of status
            timeout (int): max time to wait for send

        Raises:
            exceptions.ContextAlreadyDestroyed: Current context is invalid and was destroyed.
            ValueError: Negative timeout.
            Any of exceptions.CommunicationExceptions: Error occured in communication and
                connection was not reestablished.
            Any of exceptions.ConnectExceptions: Server didn't allow device to connect.
        """
        if self._client_socket is None:
            raise exceptions.ContextAlreadyDestroyed
        if timeout < 0:
            raise ValueError("Timeout must be positive.")

        # try to send status
        status_message = self._create_DeviceStatus_message(data)
        try:
            command_res = self._send_request(status_message, timeout=timeout)
        except (exceptions.CommunicationError, exceptions.ServerTookTooLong):
            self._logger.error("Send_status unsuccessful, will try to reconnect.")
            status_sent = False
            self._is_connected = False
        else:
            status_sent = True

        # if status send was not successful, try to reconnect and send again
        tried = 0
        while tried < InternalClient.SEND_RETRY_COUNT and not status_sent:
            self._logger.info(f"Trying to reestablish connection and send status.")
            try:
                self._establish_connection()
                command_res = self._send_request(status_message, timeout=timeout)
            except exceptions.CommunicationExceptions as e:
                last_exception = e
            except exceptions.ConnectExceptions as e:
                # don't try again since server responded with DeviceConnectResponse.responseType != OK
                self.destroy()
                raise e
            else:
                self._logger.info(
                    f"Status was successfully sent after {tried+1} reconnection{'s' if tried+1>1 else ''}."
                )
                status_sent = True
                break
            tried += 1

        if not status_sent:
            self._logger.error(
                f"Status was not sent after {tried} reconnection{'s' if tried > 1 else ''}. Context is invalid."
            )
            self.destroy()
            raise last_exception

        InternalServer_msg = internalProto.InternalServer.FromString(command_res)
        if not InternalServer_msg.HasField("deviceCommand"):
            self._logger.error(f"DeviceCommand missing in InternalServer message.")
            raise exceptions.CommunicationError("Invalid InternalServer message.")
        self._current_command = InternalServer_msg.deviceCommand.commandData

    def get_command(self) -> bytes:
        """Get last available command.

        Raises:
            exceptions.ContextAlreadyDestroyed: Current context is invalid and was destroyed.
            exceptions.NoCommandError: Send status was not called and no command is available.

        Returns:
            bytes: Command binary data
        """
        if self._client_socket is None:
            raise exceptions.ContextAlreadyDestroyed
        if self._current_command is None:
            raise exceptions.NoCommandError("There is no command available, call send_status first.")
        return self._current_command

    def _init_device_message(self) -> None:
        device = internalProto.Device()

        device.module = self._module_id
        device.deviceType = self._device_type
        device.deviceName = self._device_name
        device.deviceRole = self._device_role
        device.priority = self._device_priority

        self._device_message = device

    def _establish_connection(self) -> None:
        if self._client_socket is not None:
            self._client_socket.close()

        tried_count = 0
        while tried_count < InternalClient.CONNECTION_RETRY_COUNT:
            try:
                self._logger.info(
                    f"{'Retrying. ' if tried_count else ''}Connecting to {self._hostname}:{self._port}."
                )
                self._client_socket = socket.create_connection(
                    (self._hostname, self._port), timeout=InternalClient.CONNECTION_TIMEOUT
                )
                self._connection_sequence()
            except (TimeoutError, socket.timeout, exceptions.ServerTookTooLong):
                self._logger.error(f"Connection timed-out.")
                last_exception = exceptions.ServerTookTooLong
            except ConnectionError as e:
                self._logger.error(f"{e}")
                last_exception = exceptions.ConnectionRefused
            except exceptions.CommunicationError as e:
                self._logger.error(f"Communication Error while connecting: {e}.")
                last_exception = exceptions.CommunicationError
            else:
                self._is_connected = True
                self._logger.info(f"Connected to server.")
            tried_count += 1

        if not self._is_connected:
            self.destroy()
            raise last_exception(
                f"Couldn't establish connection to server. Tried {InternalClient.CONNECTION_RETRY_COUNT} times. Context is invalid."
            )

    def _send_request(self, msg: bytes, timeout: int) -> bytes:
        self._client_socket.settimeout(timeout)

        request = Request(self._client_socket, msg)
        try:
            response = request.send_request()
        except ConnectionError as e:
            raise exceptions.CommunicationError(e) from None

        return response

    def _connection_sequence(self) -> None:
        DeviceConnect_msg = self._create_DeviceConnect_message()
        req = Request(self._client_socket, DeviceConnect_msg)
        response = req.send_request()

        InternalServer_msg = internalProto.InternalServer.FromString(response)
        if not InternalServer_msg.HasField("deviceConnectResponse"):
            self._logger.error(f"InternalServer message missing in DeviceConnectResponse.")
            raise exceptions.CommunicationError("Invalid InternalServer message.")
        try:
            response_type = InternalServer_msg.deviceConnectResponse.responseType
        except AttributeError:
            self._logger.error(f"responseType missing in DeviceConnectResponse.")
            raise exceptions.CommunicationError("Invalid DeviceConnectResponse message.")

        if response_type != internalProto.DeviceConnectResponse.ResponseType.OK:
            if response_type not in InternalClient.CONNECT_RESPONSE_EXCEPTIONS:
                raise exceptions.CommunicationError(
                    f"Invalid responseType in DeviceConnectResponse {response_type}."
                )

            raise self.CONNECT_RESPONSE_EXCEPTIONS[response_type]

    def _create_DeviceConnect_message(self) -> bytes:
        dconnect_msg = internalProto.DeviceConnect()
        dconnect_msg.device.CopyFrom(self._device_message)
        msg = internalProto.InternalClient()
        msg.deviceConnect.CopyFrom(dconnect_msg)

        return msg.SerializeToString()

    def _create_DeviceStatus_message(self, status_data: bytes) -> bytes:
        status = internalProto.DeviceStatus()
        status.device.CopyFrom(self._device_message)
        status.statusData = status_data
        msg = internalProto.InternalClient()
        msg.deviceStatus.CopyFrom(status)

        return msg.SerializeToString()

