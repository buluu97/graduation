import pytest
import uiautomator2 as u2
import time
from kea2 import Kea2Tester


PACKAGE_NAME = "it.feio.android.omninotes.alpha"
tester = Kea2Tester()

@pytest.fixture(scope="function")
def driver():
    d = u2.connect()
    d.app_start("it.feio.android.omninotes.alpha")
    yield d
    # d.app_stop("it.feio.android.omninotes.alpha")
    # d.disconnect()

def test_add_note_and_category_u2(driver):
    '''
    add note -> add category -> start kea2 testing
    '''
    driver(resourceId="it.feio.android.omninotes.alpha:id/fab_expand_menu_button").long_click()
    time.sleep(1)

    driver(resourceId="it.feio.android.omninotes.alpha:id/detail_content").set_text("Hello world")
    time.sleep(1)

    driver(resourceId="it.feio.android.omninotes.alpha:id/menu_category").click()
    time.sleep(0.5)

    driver(resourceId="it.feio.android.omninotes.alpha:id/md_buttonDefaultPositive").click()
    time.sleep(0.5)

    driver(resourceId="it.feio.android.omninotes.alpha:id/category_title").set_text("aaa")
    driver(resourceId="it.feio.android.omninotes.alpha:id/save").click()

    assert driver(text="aaa").exists, "Add category 'aaa' failed"
    
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