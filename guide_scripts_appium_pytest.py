import pytest
from appium import webdriver
from appium.webdriver.common.appiumby import AppiumBy
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
from kea2 import Kea2Tester
from appium.options.android import UiAutomator2Options

PACKAGE_NAME = "it.feio.android.omninotes.alpha"

tester = Kea2Tester()

@pytest.fixture(scope="function")
def driver():
    desired_caps = {
        "platformName": "Android",
        "deviceName": "Android Emulator",
        "appPackage": "it.feio.android.omninotes.alpha",
        "appActivity": "it.feio.android.omninotes.MainActivity",
        "automationName": "UiAutomator2",
        "noReset": True, 
        "newCommandTimeout": 60
    }

    driver = webdriver.Remote(
            command_executor="http://localhost:4723",
            options=UiAutomator2Options().load_capabilities(desired_caps)
    )    

    driver.implicitly_wait(10)
    
    yield driver

    driver.quit()

def test_add_note_and_category_appium(driver):
    '''
    add note -> add category -> start kea2 testing
    '''

    add_button = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((AppiumBy.ID, "it.feio.android.omninotes.alpha:id/fab_expand_menu_button"))
    )
    add_button.click()
    time.sleep(1)

    add_note_btn = driver.find_element(
        by=AppiumBy.ID,
        value="it.feio.android.omninotes.alpha:id/fab_note"
    )
    add_note_btn.click()
    time.sleep(1)

    content_box = driver.find_element(AppiumBy.ID, "it.feio.android.omninotes.alpha:id/detail_content")
    content_box.send_keys("Hello world")
    time.sleep(2)

    category_menu = driver.find_element(AppiumBy.ID, "it.feio.android.omninotes.alpha:id/menu_category")
    category_menu.click()
    time.sleep(0.5)

    confirm_btn = driver.find_element(AppiumBy.ID, "it.feio.android.omninotes.alpha:id/md_buttonDefaultPositive")
    confirm_btn.click()
    time.sleep(0.5)

    category_input = driver.find_element(AppiumBy.ID, "it.feio.android.omninotes.alpha:id/category_title")
    category_input.send_keys("aaa")
    save_btn = driver.find_element(AppiumBy.ID, "it.feio.android.omninotes.alpha:id/save")
    save_btn.click()

    from properties.Omninotes_Sample import Omni_Notes_Propertytest_Sample

    tester.run_kea2_testing(
        package_name=PACKAGE_NAME,
        property_classes=Omni_Notes_Propertytest_Sample,
        current_driver=driver,
        serial="emulator-5554",
        running_minutes=10,
        max_step=50,
    )

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
