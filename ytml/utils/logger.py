import logging

# Create a logger
logger = logging.getLogger("ytml")
# logging.basicConfig(level=logging.INFO)
logger.setLevel(logging.INFO)  # Default: INFO, will be changed in CLI

# Create a console handler
console_handler = logging.StreamHandler()
formatter = logging.Formatter("[%(levelname)s] [%(filename)s] %(message)s")
console_handler.setFormatter(formatter)
# console_handler.setFormatter(logging.Formatter("%(message)s"))

# Add handler to logger (if not already added)
# if not logger.hasHandlers():
logger.addHandler(console_handler)
