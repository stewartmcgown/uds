"""File containing custom runtime exceptions"""
import sys


class Error(Exception):
    """Base class for exceptions in this module"""

    def __init__(self):
        pass

    @staticmethod
    def formatter(instance=None, exception_has=None):
        """
        :param instance:
        :param exception_has:
        """
        try:
            if exception_has:
                raise instance(exception_has)
            else:
                raise instance()
        except instance as err:
            print("\nFailed with: {}\n".format(type(err).__name__))
            print(err)
        finally:
            sys.exit("")


class FileNotUDSError(Error):
    """Raises when file is found, but it is not of type uds

    Attributes:
        message -- explanation of why exception was raised. 

    """

    def __init__(self, message=None):
        self.message = message

    def __str__(self):
        return "{}".format(self.message)


class PythonVersionError(Error):
    """Raised when this a script is run with an unsupported Python version (<=3.0.0).
    
    Attributes:
        version_used -- the python version that caught the error.
        command_used -- the full command used to run this script.
        message      -- explanation of why exception was raised.

    """

    def __init__(self, version_used):
        self.version_used = version_used
        self.message = 'Attempted to run the module with Python version of {}, ' \
                       'which is not supported by this module\n' \
                       'Please use Python 3 (or higher) instead.'.format(self.version_used)
    def __str__(self):
        return "{}".format(self.message)


class NoClientSecretError(Error):
    """Raised when the current working directory has no file name 'client_secret.json'

    If this error is raised, be sure you renamed 'credentials.json' to 'client_secret.json'

    Attributes:
        message  -- explanation why exception was raised.

    """

    def __init__(self):
        self.message = "No file named 'client_secret.json' in current working directory. " \
                       "Ensure you've followed the installation instructions on GitHub."

    def __str__(self):
        return "{}".format(self.message)
