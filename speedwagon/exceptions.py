class SpeedwagonException(Exception):
    """The base class for speedwagon exceptions"""

    def __init__(self, *args: object) -> None:
        super().__init__(*args)


class MissingConfiguration(SpeedwagonException):
    description = "Missing required configuration settings"
