import unittest
import uiautomator2 as u2
from time import sleep
from kea2 import Kea2Tester, Options, Kea2Breakpoint
from kea2.u2Driver import U2Driver

PACKAGE_NAME = "it.feio.android.omninotes.alpha"
DEVICE_SERIAL = "emulator-5554"


class TestKea2Breakpoint(unittest.TestCase):    
    
    def setUp(self):
        print("\n" + "="*60)
        print("setUp: 连接设备并重新启动应用")
        print("="*60)
        self.d = u2.connect(DEVICE_SERIAL)
        self.d.app_stop(PACKAGE_NAME)
        self.d.app_start(PACKAGE_NAME)
        sleep(2)
    
    def test_with_breakpoint_enabled(self):
        print("\n" + "="*60)
        print("测试 1：启用断点")
        print("="*60)
        
        print("[脚本] 添加一条笔记...")
        self.d(resourceId=f"{PACKAGE_NAME}:id/fab_expand_menu_button").long_click()
        sleep(1)
        self.d(resourceId=f"{PACKAGE_NAME}:id/detail_content").set_text("Test Note")
        sleep(1)
        self.d.press("back")
        sleep(1)
        print("[脚本] 笔记已添加")
        
        print("\n[Kea2] 启动属性测试...")
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
            ),
            # enable_breakpoint=True  # default
        )
        del tester
        # ↑ 如果 CURRENT_MODE=kea2:
        #    - 执行 Kea2 测试
        #    - 抛出 Kea2Breakpoint (unittest.SkipTest)
        #    - 下面的代码不执行
        #    - 测试标记为 SKIPPED
        #    - 其他 testcase 继续执行
        
        # ↓ 如果 CURRENT_MODE != kea2，会执行到这里
        print(f"\n✅ Kea2 已跳过，测试结果: {result}")
        
        print("\n[脚本] 继续执行后续操作...")
        print("   - 如果 CURRENT_MODE=kea2，这段代码不会执行")
        print("   - 如果 CURRENT_MODE!=kea2，这段代码会执行")
        self.d(resourceId=f"{PACKAGE_NAME}:id/menu_search").click()
        sleep(1)
        print("[脚本] 后续操作完成")
    
    def test_with_breakpoint_disabled(self):
        """
        示例 2：禁用断点
        
        行为：
        - CURRENT_MODE=kea2: 执行 Kea2 测试 → 正常返回结果 → 继续执行后续代码
        - CURRENT_MODE!=kea2: 跳过 Kea2 测试 → 正常返回 → 继续执行后续代码
        """
        print("\n" + "="*60)
        print("测试 2：禁用断点")
        print("="*60)
        
        print("[脚本] 添加一条笔记...")
        self.d(resourceId=f"{PACKAGE_NAME}:id/fab_expand_menu_button").long_click()
        sleep(1)
        self.d(resourceId=f"{PACKAGE_NAME}:id/detail_content").set_text("Test Note 2")
        sleep(1)
        self.d.press("back")
        sleep(1)
        print("[脚本] 笔记已添加")
        
        print("\n[Kea2] 启动属性测试（禁用断点）...")
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
            ),
            enable_breakpoint=False  # 禁用断点
        )
        del tester
        
        print(f"\n Kea2 测试完成，结果: {result}")
        if result['executed']:
            print(f"   输出目录: {result['output_dir']}")
            print(f"   报告路径: {result['bug_report']}")
        elif result['skipped']:
            print(f"   Kea2 已跳过（CURRENT_MODE != kea2）")
        
        print("\n[脚本] 继续执行后续操作...")
        print("   - 无论 Kea2 是否执行，这段代码都会执行")
        self.d(resourceId=f"{PACKAGE_NAME}:id/menu_search").click()
        sleep(1)
        print("[脚本] 后续操作完成")
    
    def test_capture_result(self):

        print("\n" + "="*60)
        print("测试 3：捕获测试结果")
        print("="*60)
        
        # 禁用断点以获取返回值
        tester = Kea2Tester()
        result = tester.run_kea2_testing(
            Options(
                driverName="d",
                Driver=U2Driver,
                packageNames=[PACKAGE_NAME],
                propertytest_args=["discover", "-p", "Omninotes_Sample.py"],
                serial=DEVICE_SERIAL,
                running_mins=1,
                maxStep=10
            ),
            enable_breakpoint=False
        )
        del tester

        print(f"\n 测试结果详情：")
        print(f"   执行状态: {'已执行' if result['executed'] else '未执行'}")
        print(f"   跳过状态: {'已跳过' if result['skipped'] else '未跳过'}")
        
        if result.get('caller_info'):
            caller = result['caller_info']
            print(f"\n Kea2 测试启动位置：")
            print(f"   文件: {caller['file']}")
            print(f"   类: {caller['class']}")
            print(f"   方法: {caller['method']}")
        
        if result['executed']:
            print(f"\n 输出文件：")
            print(f"   输出目录: {result['output_dir']}")
            print(f"   Bug 报告: {result['bug_report'] or '未生成'}")
            print(f"   结果 JSON: {result['result_json'] or '未找到'}")
            print(f"   日志文件: {result['log_file'] or '未找到'}")
        else:
            print("(Kea2 测试被跳过)")
    
    def tearDown(self):
        """测试后的清理工作"""
        print("\n" + "="*60)
        print("\ntearDown: 清理工作")
        print("="*60)


def main():

    unittest.main(verbosity=2)

if __name__ == "__main__":
    main()

