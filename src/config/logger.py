import logging


class Logger:
    @staticmethod
    def logger_setup() -> logging.Logger:
        """
        Custom logger
        """
        logger = logging.getLogger(__name__)
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s %(levelname)s %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

        return logger


logger_instance = Logger()
logger = logger_instance.logger_setup()
