import unittest
import os
from time import sleep
from appium import webdriver
from appium.webdriver.common.appiumby import AppiumBy
from kea2 import Kea2Tester, Options
from kea2.u2Driver import U2Driver
from appium.options.android import UiAutomator2Options

PACKAGE_NAME = "it.feio.android.omninotes.alpha"
DEVICE_SERIAL = "emulator-5554"
APPIUM_SERVER_URL = "http://localhost:4723"  # Appium 服务地址


class Feat4_Example1(unittest.TestCase):    
    def setUp(self):
        print("\n" + "="*60)
        print("setUp: 连接设备并重新启动应用")
        print("="*60)
        
        # Appium 配置参数
        self.desired_caps = {
            "platformName": "Android",
            "deviceName": "Android Device",
            "uid": DEVICE_SERIAL,
            "appPackage": PACKAGE_NAME,   # 应用包名
            "appActivity": "it.feio.android.omninotes.MainActivity",  # 主活动（根据实际应用调整）
            "automationName": "UiAutomator2",  # 使用 UiAutomator2 引擎
            "noReset": True,  # 每次启动重置应用状态
            "fullReset": False,
            "unicodeKeyboard": True,  # 支持 Unicode 输入
            "resetKeyboard": True     # 重置键盘
        }
        self.option=UiAutomator2Options().load_capabilities(self.desired_caps)
        # 连接 Appium 服务器并启动应用
        self.driver = webdriver.Remote(
            APPIUM_SERVER_URL, 
            options=self.option
        )
        self.driver.implicitly_wait(10)  # 设置隐式等待时间
        self.driver.terminate_app(PACKAGE_NAME)
        self.driver.activate_app(PACKAGE_NAME)

        sleep(2)  # 等待应用启动稳定
    
    def test_case1_add_tag_show_tags(self):
        '''add note -> add tag -> show tags'''
        #  "新建笔记" 按钮（通过 resource-id 定位）
        self.driver.find_element(
            AppiumBy.ID, "it.feio.android.omninotes.alpha:id/fab_expand_menu_button"
        ).click()
        add_note_btn = self.driver.find_element(
            by=AppiumBy.ID,
            value="it.feio.android.omninotes.alpha:id/fab_note"
        )
        add_note_btn.click()  #
        sleep(1)

        # 输入笔记内容（包含标签）
        self.driver.find_element(
            AppiumBy.ID, "it.feio.android.omninotes.alpha:id/detail_content"
        ).send_keys("hello kea2! #hello")
        
        # 点击 "更多选项"（通过描述定位）
        self.driver.find_element(
            AppiumBy.ACCESSIBILITY_ID, "More options"
        ).click()
        
        # 处理 "Disable checklist" 选项
        try:
            self.driver.find_element(
                AppiumBy.XPATH, "//android.widget.TextView[@text='Disable checklist']"
            ).click()
        except:
            self.driver.back()  # 点击返回键
        
        # 检查 KEA2_HYBRID_MODE 环境变量
        if os.environ.get('KEA2_HYBRID_MODE', '').lower() == 'kea2':
            print("关闭 Appium 会话")
            self.driver.quit()  # 关闭当前 Appium 会话
            
            # 运行 Kea2 测试
            tester = Kea2Tester()
            result = tester.run_kea2_testing(
                Options(
                    driverName="d",
                    Driver=U2Driver,
                    packageNames=[PACKAGE_NAME],
                    propertytest_args=["discover", "-p", "Omninotes_Sample.py"],
                    serial=DEVICE_SERIAL,
                    running_mins=2,
                    maxStep=20
                )            
            )
            print(result)
            del tester
            return
        
        # 点击 "标签" 菜单
        self.driver.find_element(
            AppiumBy.ID, "it.feio.android.omninotes.alpha:id/menu_tag"
        ).click()
    
    def test_case2_add_category(self):
        '''add note -> add category -> start kea2 testing'''
        # 长按 "新建笔记" 按钮
        self.driver.find_element(
            AppiumBy.ID, "it.feio.android.omninotes.alpha:id/fab_expand_menu_button"
        ).click()
        sleep(1)
        
        add_note_btn = self.driver.find_element(
            by=AppiumBy.ID,
            value="it.feio.android.omninotes.alpha:id/fab_note"
        )
        add_note_btn.click()  #
        sleep(1)

        # 输入笔记内容
        self.driver.find_element(
            AppiumBy.ID, "it.feio.android.omninotes.alpha:id/detail_content"
        ).send_keys("Hello world")
        sleep(2)
        
        # 点击 "分类" 菜单
        self.driver.find_element(
            AppiumBy.ID, "it.feio.android.omninotes.alpha:id/menu_category"
        ).click()
        sleep(0.5)
        
        # 点击确认按钮（新建分类）
        self.driver.find_element(
            AppiumBy.ID, "it.feio.android.omninotes.alpha:id/md_buttonDefaultPositive"
        ).click()
        sleep(0.5)
        
        # 输入分类名称并保存
        self.driver.find_element(
            AppiumBy.ID, "it.feio.android.omninotes.alpha:id/category_title"
        ).send_keys("aaa")
        sleep(1)
        
        self.driver.find_element(
            AppiumBy.ID, "it.feio.android.omninotes.alpha:id/save"
        ).click()
        
        # 检查 KEA2_HYBRID_MODE 环境变量
        if os.environ.get('KEA2_HYBRID_MODE', '').lower() == 'kea2':
            print("关闭 Appium 会话")
            self.driver.quit()
            
            # 运行 Kea2 测试
            tester = Kea2Tester()
            result = tester.run_kea2_testing(
                Options(
                    driverName="d",
                    Driver=U2Driver,
                    packageNames=[PACKAGE_NAME],
                    propertytest_args=["discover", "-p", "Omninotes_Sample.py"],
                    serial=DEVICE_SERIAL,
                    running_mins=2,
                    maxStep=20
                )            
            )
            print(result)
            del tester
            return
        
        print("在KEA2_HYBRID_MODE等于kea2时，这里不会执行")
    
    def test_case3_delete_note_search(self):
        '''add note -> delete note -> search title'''
        # 长按 "新建笔记" 按钮
        self.driver.find_element(
            AppiumBy.ID, "it.feio.android.omninotes.alpha:id/fab_expand_menu_button"
        ).click()
        

        add_note_btn = self.driver.find_element(
            by=AppiumBy.ID,
            value="it.feio.android.omninotes.alpha:id/fab_note"
        )
        add_note_btn.click()  #
        sleep(1)
        

        # 输入标题和内容
        self.driver.find_element(
            AppiumBy.ID, "it.feio.android.omninotes.alpha:id/detail_title"
        ).send_keys("Hello112233")
        self.driver.find_element(
            AppiumBy.ID, "it.feio.android.omninotes.alpha:id/detail_content"
        ).send_keys("Hello world")
        
        # 打开侧边栏
        self.driver.find_element(
            AppiumBy.ACCESSIBILITY_ID, "drawer open"
        ).click()
        
        # 长按笔记标题
        self.driver.find_element(
            AppiumBy.ID, "it.feio.android.omninotes.alpha:id/note_title"
        ).click()
        
        # 点击 "更多选项" 和 "删除"
        self.driver.find_element(
            AppiumBy.ACCESSIBILITY_ID, "More options"
        ).click()
        self.driver.find_element(
            AppiumBy.XPATH, "//android.widget.TextView[@text='Trash']"
        ).click()
        
        # 检查 KEA2_HYBRID_MODE 环境变量
        if os.environ.get('KEA2_HYBRID_MODE', '').lower() == 'kea2':
            print("关闭 Appium 会话")
            self.driver.quit()
            
            # 运行 Kea2 测试
            tester = Kea2Tester()
            result = tester.run_kea2_testing(
                Options(
                    driverName="d",
                    Driver=U2Driver,
                    packageNames=[PACKAGE_NAME],
                    propertytest_args=["discover", "-p", "Omninotes_Sample.py"],
                    serial=DEVICE_SERIAL,
                    running_mins=2,
                    maxStep=20
                )            
            )
            print(result)
            del tester
            return
        
        # 搜索已删除的笔记
        self.driver.find_element(
            AppiumBy.ID, "it.feio.android.omninotes.alpha:id/menu_search"
        ).click()
        self.driver.find_element(
            AppiumBy.ID, "it.feio.android.omninotes.alpha:id/search_src_text"
        ).send_keys("Hello112233")
        self.driver.press_keycode(66)  # 模拟 Enter 键（Android 键码 66）
    
    def tearDown(self):
        """测试后的清理工作"""
        print("\n" + "="*60)
        print("tearDown: 清理工作")
        print("="*60)
        # self.driver.quit()  # 关闭 Appium 会话


def main():
    unittest.main(verbosity=2)

if __name__ == "__main__":
    main()