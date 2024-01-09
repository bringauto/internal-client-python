"""Client library exceptions"""


class ConnectExceptions(Exception):
    """Internal protocol specific exception.
       Contains exceptions which corresponds to DeviceConnectResponse.ResponseType.
    """
    pass


class AlreadyConnected(ConnectExceptions):
    """Device with same name and type is already connected."""
    pass

class ModuleNotSupported(ConnectExceptions):
    """Module is not supported by server (module gateway)."""
    pass

class DeviceNotSupported(ConnectExceptions):
    """Device type not supported by module."""
    pass

class HigherPriorityAlreadyConnected(ConnectExceptions):
    """Device of same type and higher priority is already connected."""
    pass



class CommunicationExceptions(Exception):
    """Transport layer exceptions."""
    pass


class ConnectionRefused(CommunicationExceptions):
    """Server refused to established communication socket."""
    pass

class CommunicationError(CommunicationExceptions):
    """Invalid data was sent during communication."""
    pass

class ServerTookTooLong(CommunicationExceptions):
    """Server timed out."""
    pass



class NoCommandError(Exception):
    """No get_status called before get_command."""
    pass

class ContextAlreadyDestroyed(Exception):
    """Context is destroyed and invalid."""
    pass