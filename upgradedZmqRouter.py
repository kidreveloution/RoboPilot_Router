import zmq
import json
import signal
import sys
import time
import logging


# Set up logging to write to a file
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='router_logs.log',  # Specify the log file here
    filemode='a'  # Append mode, change to 'w' for overwrite mode
)

# Set up logging
def signal_handler(sig, frame):
    logging.info("Shutting down...")
    router.close()
    context.term()
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

context = zmq.Context()
router = context.socket(zmq.ROUTER)
router.bind("tcp://*:5555")

connections = {}

def process_message(message):
    tx_id, message_content = message[1].decode('utf-8'), message[2].decode('utf-8')
    message_data = json.loads(message_content)
    rx_id = message_data.get("rx_id")

    logging.info(f"Received message: {message_data}")

    if message_data["msg_name"] == "register":
        handle_registration(tx_id, message_data)
    elif message_data["msg_name"] == "getRegister":
        handle_get_register()
    else:
        handle_regular_message(tx_id, rx_id, message_content)

    logging.info(f"Current connections: {connections}")

def handle_registration(tx_id, message_data):
    if tx_id in connections:
        router.send_multipart([tx_id.encode('utf-8'), b"Already Registered"])
        logging.info(f"TX ID {tx_id} is already registered.")
    else:
        ip_address = message_data["content"]["ip_address"]
        connections[tx_id] = ip_address
        router.send_multipart([tx_id.encode('utf-8'), b"YOU HAVE BEEN REGISTERED"])
        try:
            router.send_multipart([b"MOTHER", json.dumps(message_data).encode('utf-8')])
        except zmq.ZMQError:
            logging.error("MOTHER not registered")
        logging.info(f"Registered connection: {tx_id} with IP: {ip_address}")

def handle_get_register():
    format_message = {
        "msg_name": "register_list",
        "content": connections
    }
    router.send_multipart([b"MOTHER", json.dumps(format_message).encode('utf-8')])

def handle_regular_message(tx_id, rx_id, message_content):
    if tx_id in connections:
        router.send_multipart([rx_id.encode('utf-8'), message_content.encode('utf-8')])
        logging.info(f"Sent message to receiver {rx_id}")
    else:
        logging.warning(f"TX ID {tx_id} not recognized.")

def main():
    while True:
        try:
            message = router.recv_multipart(flags=zmq.NOBLOCK)
            process_message(message)
        except zmq.Again:
            time.sleep(0.1)
        except Exception as e:
            logging.error(f"Error occurred: {e}")
            time.sleep(1)

if __name__ == "__main__":
    main()

