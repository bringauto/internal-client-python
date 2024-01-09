# Internal Client
Implementation of Internal client library for fleet protocol v2 as described
[here](https://docs.google.com/document/d/19h2yEh3DzIizKZc-iHWpUrQIrLyop7FQUBzUi_K9LWY/edit).
API of this implementation is based on ANSI C API proposed in fleet protocol internal client [header file](https://gitlab.bringauto.com/bring-auto/fleet-protocol-v2/fleet-protocol/-/blob/master/lib/internal_client/include/internal_client.h). Some things are adapted to Python ways of doing things, e.g. errors are handled via exceptions instead of return values.

## Requirements

- `protobuf >= 4.25.0`

## Installation

Before installing the package it is advised to create and activate a virtual environment by running
```bash
python -m venv .venv
source .venv/bin/activate
```
You can get install the internal client as a python package by running
```bash
pip install git+https://github.com/bringauto/internal-client-python.git@BAF-705/internal-client-as-package
```

## Usage
Example usage can be seen in `example.py` file.

Every client is an instance of `InternalClient` class defined in [`InternalClient.py`](/internal_client/InternalClient.py). The class can be imported from the package.

```python
from internal_client import InternalClient
```
Every method of client can raise [exceptions](/internal_client/exceptions.py) defined in internal client library. To catch these exceptions, it is needed to import them:
```python
from internal_client import exceptions
```
### Client initialization
First you need to initialize the client with information about device and desired internal server:
```python
client = InternalClient(
    module_id=2,
    hostname="127.0.0.1",
    port="8888",
    device_name="test_device",
    device_type="0",
    device_role="test_device",
    device_priority="3")
```
Two types of exceptions can be raised:
1. any of `CommunicationExceptions` indicating problem with connection to server on transport layer
2. any of `ConnectExceptions` indicating that server refused to connect device based on response in fleet protocol (e.g. `DeviceNotSupported`)

If no exception was raised during initialization, client is now connected to internal server and ready to be used.

### Sending and receiving data
After connection was established with server, device status can be sent. This is done by using `send_status` method:
```python
client.send_status(binary_payload, timeout=10)
```
Client will try to send status with provided binary payload to server. If no error occurs during communication and command response is received, it can be obtained using:
```python
binary_command = client.get_command()
```
which returns binary payload of command.
If error occurs during communication, client will try to reestablish connection with server and try again. If status was not sent even after reconnection, client connection will be destroyed and one of these exceptions will be raised from `send_status`:
1. any of `CommunicationExceptions` indicating problem with connection to server on transport layer even after reconnection
2. any of `ConnectExceptions` indicating that during reconnection server refused to connect device based on response in fleet protocol (e.g. `ModuleNotSupported`)

After raising exception, client is destroyed and needs to be [recreated](#client-initialization) to communicate with internal server.

### Destroying client
After client is no longer needed, it needs to be destroyed using:
```python
client.destroy()
```
>**Note**: If exception was raised during initialization or sending status, client is destroyed automatically.


