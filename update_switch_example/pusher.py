#!/usr/bin/python3
from providers import infoblox_lan as provider
from netmiko import ConnectHandler
from netmiko.ssh_exception import (
    NetMikoAuthenticationException,
    NetMikoTimeoutException,
)
from multiprocessing.dummy import Pool as ThreadPool
from threading import Thread
from getpass import getpass
import logging
from dataclasses import dataclass

# Setup logging
logger = logging.getLogger(name="pusher")
logger.setLevel(logging.INFO)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
ch.setFormatter(formatter)
logger.addHandler(ch)


@dataclass
class SoftwareVersion:
    """Defines all details needed for a specific software version
    """

    human_name: str
    matching_pattern: str
    platform_pattern: str
    boot_check: str
    FTP_path: str
    verification_path: str
    md5_sum: str


class Switch:
    """Defines a switch, and all functions nesseary to update it
        Compatible with Clasic IOS
    """

    def __init__(self, hostname: str, address: str):
        """Initilize switch class

        Args:
            hostname (str): Hostname of device, this is for display purposes only
            address (str): DNS or IP of device, this is used for connections
        """
        # Validate datatypes
        if type(hostname) != str:
            raise TypeError("hostname should be string")
        if type(address) != str:
            raise TypeError("Address should be string")

        # Set variables
        self.hostname = hostname
        self.address = address
        self.software_version = None
        self.platform = None
        self.conn = None

    def createSSHConnection(self, username: str, password: str) -> bool:
        """Creates SSH connection to device

        Args:
            username (str): Username for SSH
            password (str): Password for SSH

        Returns:
            bool: Status of SSH Attempt
        """
        created_conn = False
        if type(username) != str:
            raise TypeError("Username should be string")
        if type(password) != str:
            raise TypeError("Password should be string")
        try:
            profile = {
                "host": self.address,
                "username": username,
                "password": password,
                "device_type": "cisco_ios",
                "timeout": 5,
            }

            # Creates a test connection in order to timeout faster, a longer timeout is needed for software upgrade purposes
            _ = ConnectHandler(**profile)

            profile["timeout"] = 24 * 60 * 60
            self.conn = ConnectHandler(**profile)
            created_conn = True
        except NetMikoAuthenticationException:
            logger.error(f"{self.hostname}: Authentication Failed")
        except NetMikoTimeoutException:
            logger.error(f"{self.hostname} Timeout on SSH connection")
        finally:
            return created_conn

    def gatherFacts(self) -> None:
        """Gathers basic device information

        Raises:
            ConnectionError: Raised if self.conn is not empty
        """
        if self.conn == None:
            raise ConnectionError(f"No active connection to {self.hostname}")

        show_version = self.conn.send_command("show version", use_textfsm=True)
        self.software_version = show_version[0]["version"]
        self.platform = show_version[0]["hardware"][0]

    def isCompatibleWithSoftware(self, sw: SoftwareVersion) -> bool:
        """Checks if the switch platform is compatible with the requested software version

        Args:
            sw (SoftwareVersion): SoftwareVersion object you want to test

        Returns:
            bool: returns True if compatible
        """
        if type(sw) is not SoftwareVersion:
            raise TypeError("sw should be a SoftwareVersion object")
        compatible = False
        if sw.platform_pattern in self.platform:
            compatible = True
        return compatible

    def updateSwitch(self, sw: SoftwareVersion) -> None:
        """Updates a switch with details from the given software version object

        Args:
            sw (SoftwareVersion): SoftwareVersion object
        """
        if type(sw) is not SoftwareVersion:
            raise TypeError("sw should be a SoftwareVersion obejct")

        logger.info(f"STARTING UPDATE ON {self.hostname}")
        self.conn.send_command("delete /recursive /force flash:update")
        self.conn.send_command(
            f"archive download-sw /imageonly /overwrite {sw.FTP_path}"
        )

    def isRunningCorrectSoftware(self, sw: SoftwareVersion) -> bool:
        """Checks if a switch is running the correct software

        Args:
            sw (SoftwareVersion): Software version object for the desired software

        Raises:
            TypeError: Raises TypeError if it doesn't get a software object

        Returns:
            bool: Bool telling if it is running the correct software
        """
        if type(sw) != SoftwareVersion:
            raise TypeError("sw should be SoftwareVersion object")
        if sw.matching_pattern in self.software_version:
            return True
        return False

    def needsUpgrade(self, target_sw: SoftwareVersion) -> bool:
        """Uses softwareVersion object to decide if the switch needs to be updated

        Args:
            target_sw (SoftwareVersion): SoftwareVersion object

        Returns:
            bool: Returns true if it need an update
        """
        if type(target_sw) is not SoftwareVersion:
            raise TypeError("sw should be a SoftwareVersion obejct")

        needs_upgrade = False
        if target_sw.platform_pattern in self.platform:
            show_boot = self.conn.send_command("show boot")
            if self.isRunningCorrectSoftware(target_sw):
                logger.info(f"{self.hostname} already running {target_sw.human_name}")
                if self.verifySoftware(target_sw) == False:
                    needs_upgrade = True
            # else:
            #     if target_sw.boot_check not in show_boot:
            #         needs_upgrade = True
            if target_sw.boot_check not in show_boot:
                needs_upgrade = True
        return needs_upgrade

    def verifySoftware(self, target_sw: SoftwareVersion) -> bool:
        """Verifies the software on the switch

        Args:
            target_sw (SoftwareVersion): Object for desired software

        Raises:
            TypeError: Raises TypeError if it doesn't recive a softwareVersion object

        Returns:
            bool: Returns status
        """
        if type(target_sw) != SoftwareVersion:
            raise TypeError("target_sw should be a SoftwareVersion obejct")
        rv = True
        md5_check = self.conn.send_command(
            f"verify /md5  {target_sw.verification_path} {target_sw.md5_sum}"
        )
        if "Verified" not in md5_check:
            rv = False
        return rv


devices = []


def worker(software_targets: list, username: str, password: str) -> None:
    """Worker thread to handle running the update process

    Args:
        software_targets (list): List of softwareVersion objects
        username (str): SSH Username
        password (str): SSH Password
    """
    global devices
    while len(devices) > 0:
        dev = devices.pop(0)

        ssh_status = dev.createSSHConnection(username, password)
        if ssh_status == False:
            logger.warning(f"{dev.hostname} skipped because of SSH error")
            continue

        dev.gatherFacts()
        for sw in software_targets:
            if dev.isCompatibleWithSoftware(sw):
                if dev.needsUpgrade(sw):
                    dev.updateSwitch(sw)
                verification_status = dev.verifySoftware(sw)
                if verification_status == False:
                    logger.error(f"{dev.hostname}, MD5 error in verification")
                if verification_status and not dev.isRunningCorrectSoftware(sw):
                    logger.info(f"{dev.hostname} Is ready to be reloaded")


def getDevices(username: str, password: str) -> list:
    """Get's a list of switch objects from infoblox

    Args:
        username (str): Infoblox API username
        password (str): Infoblox API Password

    Returns:
        list: List of Switch objects
    """
    if type(username) != str:
        raise TypeError("username should be str")
    if type(password) != str:
        raise TypeError("password should be str")

    P = provider(username, password)
    devices = P.get()
    devices = list(filter(lambda x: "sw-" in x[0].lower(), devices))
    device_objects = [Switch(x[0], x[1]) for x in devices]
    return device_objects


if __name__ == "__main__":
    software_targets = [
        # 2960C 8 port software
        SoftwareVersion(
            human_name="15.2(7)E2",
            matching_pattern="15.2(7)E2",
            platform_pattern="WS-C2960C-8",
            boot_check="152-7.E2",
            FTP_path="ftp://username:password@ftp.example.com/sw/c2960c405-universalk9-tar.152-7.E2.tar",
            verification_path="flash:/c2960c405-universalk9-mz.152-7.E2/c2960c405-universalk9-mz.152-7.E2.bin",
            md5_sum="ac54677d3afc5b165d8b7a6713fbd36f",
        ),
        # 2960C 12 port software
        SoftwareVersion(
            human_name="15.0(2)SE10a",
            matching_pattern="15.0(2)SE10a",
            platform_pattern="WS-C2960C-12",
            boot_check="150-2",
            FTP_path="ftp://username:password@ftp.example.com/sw/c2960c405-universalk9-tar.150-2.SE10a.tar",
            verification_path="flash:/c2960c405-universalk9-mz.150-2.SE10a/c2960c405-universalk9-mz.150-2.SE10a.bin",
            md5_sum="f3eb436beaae124e1058d8945a5e5ffe",
        ),
        # 2960CG Software
        SoftwareVersion(
            human_name="15.2(2)E9",
            matching_pattern="15.2(2)E9",
            platform_pattern="WS-C2960CG-",
            boot_check="152-2.E9",
            FTP_path="ftp://username:password@ftp.example.com/sw/c2960c405ex-universalk9-tar.152-2.E9.tar",
            verification_path="flash:/c2960c405ex-universalk9-mz.152-2.E9/c2960c405ex-universalk9-mz.152-2.E9.bin",
            md5_sum="b6708bcc199b229878b90cb2da0e5320",
        ),
        # 3560CX Software
        SoftwareVersion(
            human_name="15.2(7)E2",
            matching_pattern="15.2(7)E2",
            platform_pattern="WS-C3560CX-",
            boot_check="152-7.E2",
            FTP_path="ftp://username:password@ftp.example.com/sw/c3560cx-universalk9-tar.152-7.E2.tar",
            verification_path="flash:/c3560cx-universalk9-mz.152-7.E2/c3560cx-universalk9-mz.152-7.E2.bin",
            md5_sum="17d91bba7d6f5780c491cd635685a260",
        ),
    ]

    username = input("Username: ")
    password = getpass()

    devices = getDevices(username, password)
    number_of_threads = 32  # This migth need to be lowered if the run is mainly firmware pushing, but works for verification runs

    threadList = []
    for _ in range(0, number_of_threads):
        t = Thread(target=worker, args=[software_targets, username, password])
        t.start()
        threadList.append(t)

    for t in threadList:
        t.join()
