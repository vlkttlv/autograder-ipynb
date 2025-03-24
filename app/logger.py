import logging

def configure_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(levelname)s - %(message)s - %(name)s - %(asctime)s',
        handlers=[
            logging.StreamHandler()
        ]
    )
