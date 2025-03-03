import logging
import tomllib
from os import PathLike
from pathlib import Path
from typing import TypedDict

from webcam_surveillance import PARENT_DIR

log = logging.getLogger(__name__)

class WebcamConfiguration(TypedDict):
    device_index: int
    width: int
    height: int
    default_fps: int

class EmailNotificationConfiguration(TypedDict):
    enabled: bool
    smtp_host: str
    smtp_port: int
    sender_email: str
    sender_password: str
    receiver_email: str

class Configuration(TypedDict):
    webcam: WebcamConfiguration
    email_notification: EmailNotificationConfiguration

def get_configuration(config_file: PathLike | None = None) -> Configuration:
    """
    Load the configuration from the configuration file.

    NOTE: NO VALIDATION IS PERFORMED ON THE CONFIGURATION FILE.
    """
    if config_file is None:
        config_file = PARENT_DIR / "config.toml"
    else:
        config_file = Path(str(config_file))

    if not config_file.is_file():
        raise FileNotFoundError(f"Configuration file '{config_file}' not found.")
    log.debug(f"Loading configuration from {config_file=}")
    with config_file.open(mode="rb") as config_file_d:
        return tomllib.load(config_file_d)