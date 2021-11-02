import pytest
import pusher
from mock import Mock


class TestSoftwareVersion:
    @pytest.fixture
    def softwareversion(self):
        return pusher.SoftwareVersion(
            human_name="test",
            matching_pattern="16.06.04a",
            platform_pattern="c9300",
            boot_check="flash:/something.bin",
            FTP_path="ftp://rwsar",
            verification_path="test",
            md5_sum="1234",
        )

    def test_create_softwareVersion_missing_arguments(self):
        with pytest.raises(TypeError):
            pusher.SoftwareVersion()

    def test_create_softwareVersion_some_missing_arguments(self):
        with pytest.raises(TypeError):
            pusher.SoftwareVersion(
                human_name="test",
                matching_pattern="16.06.04a",
                platform_pattern="c9300",
            )

    def test_create_softwareVersion_object(self):
        self.obj = pusher.SoftwareVersion(
            human_name="test",
            matching_pattern="16.06.04a",
            platform_pattern="c9300",
            boot_check="flash:/something.bin",
            FTP_path="ftp://rwsar",
            verification_path="test",
            md5_sum="1234",
        )

    def test_human_name(self, softwareversion):
        assert softwareversion.human_name == "test"

    def test_matching_pattern(self, softwareversion):
        assert softwareversion.matching_pattern == "16.06.04a"

    def test_platform_pattern(self, softwareversion):
        assert softwareversion.platform_pattern == "c9300"

    def test_boot_check(self, softwareversion):
        assert softwareversion.boot_check == "flash:/something.bin"

    def test_FTP_path(self, softwareversion):
        assert softwareversion.FTP_path == "ftp://rwsar"

    def test_verification_path(self, softwareversion):
        assert softwareversion.verification_path == "test"

    def test_md5_sum(self, softwareversion):
        assert softwareversion.md5_sum == "1234"


class TestSwitch:
    @pytest.fixture
    def switch(self):
        return pusher.Switch("TEST_HOSTNAME", "hostname.local")

    def test_int_as_hostname(self):
        with pytest.raises(TypeError):
            pusher.Switch(1, "test.local")

    def test_int_as_address(self):
        with pytest.raises(TypeError):
            pusher.Switch("hostname", 1234)

    def test_hostname(self, switch):
        assert switch.hostname == "TEST_HOSTNAME"

    def test_address(self, switch):
        assert switch.address == "hostname.local"

    def test_software_version_pre_gathering(self, switch):
        assert switch.software_version == None

    def test_platform_pre_gathering(self, switch):
        assert switch.platform == None

    def test_conn_pre_connect(self, switch):
        assert switch.conn == None

    def test_createSSHConn_bool_as_username(self, switch):
        with pytest.raises(TypeError):
            switch.createSSHConnection(True, "password")

    def test_createSSHConn_bool_as_password(self, switch):
        with pytest.raises(TypeError):
            switch.createSSHConnection("Username", False)

    def test_createSSHConn(self, switch):
        pusher.ConnectHandler = Mock()
        print(switch.createSSHConnection("test", "test"))

    @pytest.fixture
    def switch_with_fake_conn(self):
        pusher.ConnectHandler = Mock()
        o = pusher.Switch("TEST_HOSTNAME", "hostname.local")
        o.createSSHConnection("test", "test")
        return o

    def mock_send_command(self, command, use_textfsm=False):
        if use_textfsm:
            if command == "show version":  # Only implementing needed data
                return [{"version": "fake_ver", "hardware": ["fake_hardware"]}]
        else:
            if command == "show boot":
                return "BOOT path-list      : flash:fake_ver.bin"

            if "verify /md5" in command:
                return "correct_fake_checksum"

    def test_gatherFacts(self, switch_with_fake_conn):
        switch_with_fake_conn.conn.send_command = Mock(
            side_effect=self.mock_send_command
        )
        switch_with_fake_conn.gatherFacts()

    @pytest.fixture
    def switch_with_fake_data(self):
        pusher.ConnectHandler = Mock()
        o = pusher.Switch("TEST_HOSTNAME", "hostname.local")
        o.createSSHConnection("test", "test")
        o.conn.send_command = Mock(side_effect=self.mock_send_command)
        o.gatherFacts()
        return o

    def test_isCompatibleWithSoftware_string_as_software(self, switch_with_fake_data):
        with pytest.raises(TypeError):
            switch_with_fake_data.isCompatibleWithSoftware(
                "16.06.04a - this should be a software object"
            )

    def test_isCompatibleWithSoftware(self, switch_with_fake_data):
        sw = pusher.SoftwareVersion(
            human_name="fake software",
            matching_pattern="fake_pattern",
            platform_pattern="fake_hardware",
            boot_check="fake_boot",
            FTP_path="ftp://test",
            verification_path="flash:/test.bin",
            md5_sum="12345",
        )
        assert switch_with_fake_data.isCompatibleWithSoftware(sw)

    def test_updateSwitch_string_as_sw(self, switch_with_fake_data):
        with pytest.raises(TypeError):
            switch_with_fake_data.updateSwitch("this should not work")

    def test_updateSwitch(self, switch_with_fake_data):
        sw = pusher.SoftwareVersion(
            human_name="fake software",
            matching_pattern="fake_pattern",
            platform_pattern="fake_hardware",
            boot_check="fake_boot",
            FTP_path="ftp://test",
            verification_path="flash:/test.bin",
            md5_sum="12345",
        )
        switch_with_fake_data.updateSwitch(sw)

    def test_isRunningCorrectSoftware_string_as_input(self, switch_with_fake_data):
        with pytest.raises(TypeError):
            switch_with_fake_data.isRunningCorrectSoftware("this is a string")

    def test_isRunningCorrectSoftware_answer_no(self, switch_with_fake_data):
        sw = pusher.SoftwareVersion(
            human_name="fake software",
            matching_pattern="fake_old_ver",
            platform_pattern="fake_hardware",
            boot_check="fake_boot",
            FTP_path="ftp://test",
            verification_path="flash:/test.bin",
            md5_sum="12345",
        )
        assert switch_with_fake_data.isRunningCorrectSoftware(sw) == False

    def test_isRunningCorrectSoftware(self, switch_with_fake_data):
        sw = pusher.SoftwareVersion(
            human_name="fake software",
            matching_pattern="fake_ver",
            platform_pattern="fake_hardware",
            boot_check="fake_boot",
            FTP_path="ftp://test",
            verification_path="flash:/test.bin",
            md5_sum="12345",
        )
        assert switch_with_fake_data.isRunningCorrectSoftware(sw)

    def test_needsUpgrade_string_as_sw(self, switch_with_fake_data):
        with pytest.raises(TypeError):
            switch_with_fake_data.needsUpgrade("this should not work")

    def test_needsUpgrade_software_doesnt_need_update(self, switch_with_fake_data):
        sw = pusher.SoftwareVersion(
            human_name="fake software",
            matching_pattern="fake_ver",
            platform_pattern="fake_hardware",
            boot_check="fake_boot",
            FTP_path="ftp://test",
            verification_path="flash:/test.bin",
            md5_sum="12345",
        )
        assert switch_with_fake_data.needsUpgrade(sw) == False

    def test_needsUpgrade_software_does_need_update(self, switch_with_fake_data):
        sw = pusher.SoftwareVersion(
            human_name="fake software",
            matching_pattern="fake_old_ver",
            platform_pattern="fake_hardware",
            boot_check="fake_boot",
            FTP_path="ftp://test",
            verification_path="flash:/test.bin",
            md5_sum="12345",
        )
        assert switch_with_fake_data.needsUpgrade(sw)

    def test_verifySoftware_sw_as_string(self, switch_with_fake_data):
        with pytest.raises(TypeError):
            switch_with_fake_data.verifySoftware("this should generate an exception")

    def test_verifySoftware_verification_error(self, switch_with_fake_data):
        sw = pusher.SoftwareVersion(
            human_name="fake software",
            matching_pattern="fake_old_ver",
            platform_pattern="fake_hardware",
            boot_check="fake_boot",
            FTP_path="ftp://test",
            verification_path="flash:/test.bin",
            md5_sum="12345",
        )
        assert switch_with_fake_data.verifySoftware(sw) == False

    def test_verifySoftware(self, switch_with_fake_data):
        sw = pusher.SoftwareVersion(
            human_name="fake software",
            matching_pattern="fake_old_ver",
            platform_pattern="fake_hardware",
            boot_check="fake_boot",
            FTP_path="ftp://test",
            verification_path="flash:/test.bin",
            md5_sum="correct_fake_checksum",
        )
        assert switch_with_fake_data.verifySoftware(sw)


# TODO: Find some way to test worker function


class TestGetDevices:
    def test_nonetype_as_username(self):
        with pytest.raises(TypeError):
            pusher.getDevices(None, "test")

    def test_nonetype_as_password(self):
        with pytest.raises(TypeError):
            pusher.getDevices("test", None)

    class mock_provider:
        def __init__(self, username, password):
            pass

        def get(self):
            return [["test", "test"], ["test1", "test1"]]

    def test_getDevices(self):
        pusher.provider = Mock(side_effect=self.mock_provider)
        assert type(pusher.getDevices("test", "test")) == list
