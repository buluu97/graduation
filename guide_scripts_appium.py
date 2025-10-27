import unittest
from time import sleep
from appium import webdriver
from appium.webdriver.common.appiumby import AppiumBy
from appium.options.android import UiAutomator2Options
from kea2 import Kea2Tester
from properties.Omninotes_Sample import Omni_Notes_Propertytest_Sample

PACKAGE_NAME = "it.feio.android.omninotes.alpha"


class Omni_Notes_Appium_Sample(unittest.TestCase):

    tester = Kea2Tester()
    def setUp(self):
        self.desired_caps = {
            "platformName": "Android",
            "deviceName": "Android Device",
            "udid": "emulator-5554",
            "appPackage": "it.feio.android.omninotes.alpha",
            "appActivity": "it.feio.android.omninotes.MainActivity",
            "automationName": "UiAutomator2",
            "noReset": True,
            "newCommandTimeout": 30
        }


        self.driver = webdriver.Remote(
            command_executor="http://localhost:4723",
            options=UiAutomator2Options().load_capabilities(self.desired_caps)
        )

    def test_unittest_add_note_add_category(self):
        '''
        add note -> add category -> start kea2 testing
        '''

        driver = self.driver

        add_btn = driver.find_element(
            by=AppiumBy.ID,
            value="it.feio.android.omninotes.alpha:id/fab_expand_menu_button"
        )
        add_btn.click()  
        sleep(1)
        
        add_note_btn = driver.find_element(
            by=AppiumBy.ID,
            value="it.feio.android.omninotes.alpha:id/fab_note"
        )
        add_note_btn.click()  #
        sleep(1)

        note_content = driver.find_element(
            by=AppiumBy.ID,
            value="it.feio.android.omninotes.alpha:id/detail_content"
        )
        note_content.send_keys("Hello world")
        sleep(1)

        category_menu = driver.find_element(
            by=AppiumBy.ID,
            value="it.feio.android.omninotes.alpha:id/menu_category"
        )
        category_menu.click()
        sleep(1)

        confirm_btn = driver.find_element(
            by=AppiumBy.ID,
            value="it.feio.android.omninotes.alpha:id/md_buttonDefaultPositive"
        )
        confirm_btn.click()
        sleep(1)

        category_title = driver.find_element(
            by=AppiumBy.ID,
            value="it.feio.android.omninotes.alpha:id/category_title"
        )
        category_title.send_keys("aaa")

        save_btn = driver.find_element(
            by=AppiumBy.ID,
            value="it.feio.android.omninotes.alpha:id/save"
        )
        save_btn.click()

        self.tester.run_kea2_testing(
            package_name=PACKAGE_NAME,
            property_classes=Omni_Notes_Propertytest_Sample,
            current_driver=self.driver,
            serial="emulator-5554",
            running_minutes=10,
            max_step=50,
        )

    def tearDown(self):
        """close driver"""
        print("================default teardown=============")
        if hasattr(self, "driver"):
            self.driver.quit()

if __name__ == "__main__":
    unittest.main(verbosity=2)