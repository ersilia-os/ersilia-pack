import logging
import os
import socket


def find_free_port(host="localhost"):
  s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
  s.bind((host, 0))
  port = s.getsockname()[1]
  s.close()
  return int(port)


def get_logger():
  logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
  )
  logger = logging.getLogger(__name__)
  return logger


def eval_conda_prefix():
  # This returns an empty string if conda is not discoverable
  return os.popen("conda info --base").read().strip()


logger = get_logger()
