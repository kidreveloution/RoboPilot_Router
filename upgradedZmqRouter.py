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

# Set up signal handler for clean shutdown
def signal_handler(sig, frame):
    logging.info("Shutting down...")
    print("Shutting down...")
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

    log_message = f"Received message: {message_data}"
    logging.info(log_message)
    print(log_message)

    if message_data["msg_name"] == "register":
        handle_registration(tx_id, message_data)
    elif message_data["msg_name"] == "getRegister":
        handle_get_register()
    else:
        handle_regular_message(tx_id, rx_id, message_content)

    log_connections = f"Current connections: {connections}"
    logging.info(log_connections)
    print(log_connections)

def handle_registration(tx_id, message_data):
    if tx_id in connections:
        response = "Already Registered"
        router.send_multipart([tx_id.encode('utf-8'), response.encode('utf-8')])
        log_message = f"TX ID {tx_id} is already registered."
        logging.info(log_message)
        print(log_message)
    else:
        ip_address = message_data["content"]["ip_address"]
        connections[tx_id] = ip_address
        response = "YOU HAVE BEEN REGISTERED"
        router.send_multipart([tx_id.encode('utf-8'), response.encode('utf-8')])
        try:
            router.send_multipart([b"MOTHER", json.dumps(message_data).encode('utf-8')])
        except zmq.ZMQError:
            log_message = "MOTHER not registered"
            logging.error(log_message)
            print(log_message)
        log_message = f"Registered connection: {tx_id} with IP: {ip_address}"
        logging.info(log_message)
        print(log_message)

def handle_get_register():
    format_message = {
        "msg_name": "register_list",
        "content": connections
    }
    try:
        router.send_multipart([b"MOTHER", json.dumps(format_message).encode('utf-8')])
        log_message = "Sent register list to MOTHER"
        logging.info(log_message)
        print(log_message)
    except zmq.ZMQError as e:
        log_message = f"Failed to send register list to MOTHER: {e}"
        logging.error(log_message)
        print(log_message)

def handle_regular_message(tx_id, rx_id, message_content):
    if tx_id in connections:
        router.send_multipart([rx_id.encode('utf-8'), message_content.encode('utf-8')])
        log_message = f"Sent message to receiver {rx_id}"
        logging.info(log_message)
        print(log_message)
    else:
        log_message = f"TX ID {tx_id} not recognized."
        logging.warning(log_message)
        print(log_message)

def main():
    while True:
        try:
            message = router.recv_multipart(flags=zmq.NOBLOCK)
            process_message(message)
        except zmq.Again:
            time.sleep(0.1)
        except Exception as e:
            log_message = f"Error occurred: {e}"
            logging.error(log_message)
            print(log_message)
            time.sleep(1)

if __name__ == "__main__":
    main()
