import loguru


class SingletonLogger:
    __instance = None

    @staticmethod
    def get_logger():
        """
        Create or return the singleton instance for the SingletonLogger class
        :return: SingletonLogger instance
        """
        if not SingletonLogger.__instance:
            SingletonLogger.__instance = loguru.logger
        return SingletonLogger.__instance


logger = SingletonLogger.get_logger()
