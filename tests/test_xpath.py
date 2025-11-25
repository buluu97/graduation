import unittest
from kea2.u2Driver import U2StaticChecker, U2StaticDevice
from pathlib import Path


XML_PATH = Path(__file__).parent / "xpath_test.xml"


class U2StaticCheckerForTest(U2StaticChecker):
    def __init__(self):
        self.d = U2StaticDevice(script_driver=None)


def get_static_checker():
    xml = ""
    with open(XML_PATH, "r", encoding="utf-8") as f:
        xml = f.read()
    d = U2StaticCheckerForTest()
    return d.getInstance(xml)


class TestXPath(unittest.TestCase):

    def setUp(self):
        self.d = get_static_checker()

    def test_basic_xpath(self):
        assert self.d.xpath("""//*[@text="Hrgshsjs"]""").exists
        assert self.d.xpath("""//android.widget.TextView[@text="hehzhe"]""").exists
        assert self.d.xpath(
            """(//*[@resource-id="it.feio.android.omninotes.alpha:id/category_marker"])[3]"""
        ).exists


if __name__ == "__main__":
    unittest.main()
