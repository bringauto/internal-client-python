import json
import logging
import random
import asyncio

from internal_client import CarAccessoryInternalClient, exceptions


async def main_loop():
    # create client instance and connect to server
    try:
        client = CarAccessoryInternalClient("127.0.0.1", 8888, "button1", 0, "left_button", 0)
    except exceptions.CommunicationExceptions as e:
        logging.error(f"Couldn't connect to server: {e}")
        return False
    except exceptions.ConnectExceptions as e:
        logging.error(
            f"Device could not be connected because server responded with: {type(e)}"
        )
        return False

    while True:
        my_status = json.dumps({"pressed": random.random() < 0.5})
        try:
            client.send_status(my_status.encode(), timeout=10)
        except exceptions.ServerTookTooLong:
            logging.error("Server timed out, context invalid")
            break
        except (exceptions.CommunicationExceptions, exceptions.ConnectExceptions):
            logging.error("Server error, conext invalid")
            break

        command = client.get_command()
        print(command)

    client.destroy()


if __name__ == "__main__":
    asyncio.run(main_loop())
