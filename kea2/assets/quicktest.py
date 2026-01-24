import unittest
import uiautomator2 as u2

from time import sleep
from kea2 import precondition, prob, KeaTestRunner, Options, keaTestLoader, invariant


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

    @prob(0.5)
    @precondition(
        lambda self: self.d(description="drawer closed").exists and 
        not self.d(text="Omni Notes Alpha").exists
    )
    def open_drawer(self):
        print("Open drawer")
        self.d(description="drawer closed").click()

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
        self.d.set_orientation("n")
        assert self.d(resourceId="it.feio.android.omninotes.alpha:id/search_src_text").exists

    @invariant
    def search_button_and_search_input_box_should_not_exists_at_the_same_time(self):
        """Search input box and search button should not exists at the same time
        """
        search_input_box_exists = self.d(resourceId="it.feio.android.omninotes.alpha:id/search_src_text").exists
        serach_button_exists = self.d(resourceId="it.feio.android.omninotes.alpha:id/menu_search").exists
        if search_input_box_exists or serach_button_exists:
            assert search_input_box_exists ^ serach_button_exists

    @precondition(lambda self: "camera" in self.d.app_current().get("package", ""))
    def exit_camera(self):
        """Exit camera app if it is launched 
        (fastbot can't exit camera app by itself, we use kea2 to exit it to aviod getting stuck in camera)
        """
        print("Exiting camera app")
        pkg_camera = self.d.app_current().get("package", "")
        print(f"Current package: {pkg_camera}")
        if "camera" in pkg_camera:
            self.d.app_stop(pkg_camera)

URL = "https://github.com/federicoiosue/Omni-Notes/releases/download/6.2.0_alpha/OmniNotes-alphaRelease-6.2.0.apk"
FALL_BACK_URL = "https://gitee.com/XixianLiang/Kea2/raw/main/omninotes.apk"
PACKAGE_NAME = "it.feio.android.omninotes.alpha"
FILE_NAME = "omninotes.apk"


def download_omninotes():
    import socket
    socket.setdefaulttimeout(30)
    try:
        import urllib.request
        urllib.request.urlretrieve(URL, FILE_NAME)
    except Exception as e:
        print(f"[WARN] Download from {URL} failed: {e}. Try to download from fallback URL {FALL_BACK_URL}", flush=True)
        try:
            urllib.request.urlretrieve(FALL_BACK_URL, FILE_NAME)
        except Exception as e2:
            print(f"[ERROR] Download from fallback URL {FALL_BACK_URL} also failed: {e2}", flush=True)
            raise e2


def check_installation(serial=None):
    import os
    from pathlib import Path
    
    d = u2.connect(serial)
    # automatically install omni-notes
    if PACKAGE_NAME not in d.app_list():
        if not os.path.exists(Path(".") / FILE_NAME):
            print(f"[INFO] omninote.apk not exists. Downloading from {URL}", flush=True)
            download_omninotes()
        print("[INFO] Installing omninotes.", flush=True)
        d.app_install(FILE_NAME)
    d.stop_uiautomator()


if __name__ == "__main__":
    check_installation(serial=None)
    KeaTestRunner.setOptions(
        Options(
            driverName="d",
            packageNames=[PACKAGE_NAME],
            # serial="emulator-5554",   # specify the serial
            maxStep=50,
            profile_period=10,
            take_screenshots=True,  # whether to take screenshots, default is False
            # running_mins=10,  # specify the maximal running time in minutes, default value is 10m
            # throttle=200,   # specify the throttle in milliseconds, default value is 200ms
            agent="u2"  # 'native' for running the vanilla Fastbot, 'u2' for running Kea2
        )
    )
    unittest.main(testRunner=KeaTestRunner, testLoader=keaTestLoader)
