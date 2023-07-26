"""
Utility file for logging
"""

import loguru


class SingletonLogger:
    """
    Use Singleton design pattern to create a logger object and share it
    across the entire project
    """
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


LOGGER = SingletonLogger.get_logger()
