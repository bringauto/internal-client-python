import json
import logging
import random

from internal_client import exceptions, InternalClient

def main_loop():
    # create client instance and connect to server
    try:
        client = InternalClient(
            module_id=1,
            hostname="127.0.0.1",
            port=8888,
            device_name="button1",
            device_type=0,
            device_role="left_button",
            device_priority=0
        )
    except exceptions.CommunicationExceptions as e:
        logging.error(f"Couldn't connect to server: {e}.")
        return False
    except exceptions.ConnectExceptions as e:
        logging.error(
            f"Device could not be connected because server responded with: {type(e)}."
        )
        return False

    while True:
        my_status = json.dumps({"pressed": random.random() < 0.5})
        try:
            client.send_status(my_status.encode(), timeout=10)
        except exceptions.ServerTookTooLong:
            logging.error("Server timed out, context invalid.")
            break
        except (exceptions.CommunicationExceptions, exceptions.ConnectExceptions):
            logging.error("Server error, conext invalid.")
            break

        command = client.get_command()
        print(command)

    client.destroy()


if __name__ == "__main__":
    main_loop()
