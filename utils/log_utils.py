from loguru import logger


class SingletonLogger:
    __instance = None

    @staticmethod
    def get_logger():
        if not SingletonLogger.__instance:
            SingletonLogger.__instance = logger
        return SingletonLogger.__instance


logger = SingletonLogger.get_logger()
