import unittest
import uiautomator2 as u2

from time import sleep
from kea2 import precondition, prob, KeaTestRunner, Options, keaTestLoader, invariant
from kea2.u2Driver import U2Driver


class Omni_Notes_Sample(unittest.TestCase):
    d: u2.Device

    @classmethod
    def setUpClass(cls):
        """Here you can setup the initialize setting for uiautomator2
        """ 
        print("Setting driver settings")
        cls.d.settings["wait_timeout"] = 5.0
        cls.d.settings["operation_delay"] = (0, 1.0)

    @prob(0.5)
    @precondition(
        lambda self: self.d(description="Navigate up").exists
    )
    def navigate_up(self):
        print("Navigate back")
        self.d(description="Navigate up").click()
        sleep(0.5)

    @prob(0.5)
    @precondition(
        lambda self: self.d(description="drawer closed").exists
    )
    def open_drawer(self):
        print("Open drawer")
        self.d(description="drawer closed").click()
        sleep(0.5)

    @prob(0.7)  # The probability of executing the function when precondition is satisfied.
    @precondition(
        lambda self: self.d(text="Omni Notes Alpha").exists
        and self.d(text="Settings").exists
    )
    def go_to_privacy_settings(self):
        """
        The ability to jump out of the UI tarpits

        precond:
            The drawer was opened
        action:
            go to settings -> privacy
        """
        print("trying to click Settings")
        self.d(text="Settings").click()
        sleep(0.5)
        print("trying to click Privacy")
        self.d(text="Privacy").click()

    @precondition(
        lambda self: self.d(resourceId="it.feio.android.omninotes.alpha:id/search_src_text").exists
    )
    def rotation_should_not_close_the_search_input(self):
        """
        The ability to make assertion to find functional bug

        precond:
            The search input box is opened
        action:
            rotate the device (set it to landscape, then back to natural)
        assertion:
            The search input box is still being opened
        """
        print("rotate the device")
        self.d.set_orientation("l")
        sleep(2)
        self.d.set_orientation("n")
        sleep(2)
        assert self.d(resourceId="it.feio.android.omninotes.alpha:id/search_src_text").exists

    @invariant
    def search_button_and_search_input_box_should_not_exists_at_the_same_time(self):
        """Search input box and search button should not exists at the same time
        """
        search_input_box_exists = self.d(resourceId="it.feio.android.omninotes.alpha:id/search_src_text").exists
        serach_button_exists = self.d(resourceId="it.feio.android.omninotes.alpha:id/menu_search").exists
        if search_input_box_exists or serach_button_exists:
            assert search_input_box_exists ^ serach_button_exists

URL = "https://raw.githubusercontent.com/ecnusse/Kea2/refs/heads/dev_test_hidden_algorithm/omninotes.apk"
PACKAGE_NAME = "it.feio.android.omninotes.alpha"
FILE_NAME = "omninotes.apk"


def check_installation():
    import os
    from pathlib import Path
    if not os.path.exists(Path(".") / FILE_NAME):
        print(f"[INFO] omninote.apk not exists. Downloading from {URL}", flush=True)
        import urllib.request
        urllib.request.urlretrieve(URL, FILE_NAME)

    d = u2.connect()
    # automatically install omni-notes
    if PACKAGE_NAME not in d.app_list():
        print("[INFO] Installing omninotes.", flush=True)
        d.app_install(FILE_NAME)
    d.stop_uiautomator()


if __name__ == "__main__":
    check_installation()
    KeaTestRunner.setOptions(
        Options(
            debug=False,
            driverName="d",
            Driver=U2Driver,
            packageNames=[PACKAGE_NAME],
            # serial="emulator-5554",   # specify the serial
            maxStep=50,
            # running_mins=10,  # specify the maximal running time in minutes, default value is 10m
            # throttle=200,   # specify the throttle in milliseconds, default value is 200ms
            # agent='native'  # 'native' for running the vanilla Fastbot, 'u2' for running Kea2
        )
    )
    unittest.main(testRunner=KeaTestRunner, testLoader=keaTestLoader)
