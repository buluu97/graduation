## Kea2 案例教程   
  
1. 在 [微信](Scenario_Examples_zh.md) 上应用 Kea2 功能 2 和 3 的小教程。  
  
## Kea2 的脚本  
  
Kea2 使用 [Unittest](https://docs.python.org/3/library/unittest.html) 管理脚本。所有 Kea2 的脚本均遵循 unittest 的规则（即测试方法应以 `test_` 开头，测试类应继承 `unittest.TestCase`）。  
  
Kea2 使用 [Uiautomator2](https://github.com/openatx/uiautomator2) 操作 Android 设备。详情请参考 [Uiautomator2 文档](https://github.com/openatx/uiautomator2?tab=readme-ov-file#quick-start)。  
  
通常，可以通过以下两步编写 Kea2 脚本：  
  
1. 创建继承 `unittest.TestCase` 的测试类。  
  
```python  
import unittest   
  
class MyFirstTest(unittest.TestCase):  
    ...  
```  
  
2. 通过定义测试方法编写脚本  
  
默认情况下，只有以 `test_` 开头的测试方法会被 unittest 识别。可以通过 `@precondition` 装饰函数。装饰器 `@precondition` 接收一个返回布尔值的函数作为参数。当函数返回 `True` 时，前置条件成立，脚本会被激活，Kea2 会根据装饰器 `@prob` 定义的概率运行该脚本。  
  
注意：如果测试方法未被 `@precondition` 装饰，则在自动化 UI 测试中永远不会被激活，会被当作普通 `unittest` 测试方法处理。因此，当测试方法应始终执行时，需显式指定 `@precondition(lambda self: True)`。若未装饰 `@prob`，默认概率为 1（即前置条件满足时始终执行）。  
  
```python  
import unittest  
from kea2 import precondition  
  
class MyFirstTest(unittest.TestCase):  
  
    @prob(0.7)  
    @precondition(lambda self: ...)  
    def test_func1(self):  
        ...  
```  
  
更多细节请阅读 [Kea - 编写你的第一个性质](https://kea-docs.readthedocs.io/en/latest/part-keaUserManuel/first_property.html)。  
  
## 装饰器  
  
### `@precondition`  
  
```python  
@precondition(lambda self: ...)  
def test_func1(self):  
    ...  
```  
  
装饰器 `@precondition` 接收一个返回布尔值的函数作为参数。当该函数返回 `True` 时，前置条件成立，函数 `test_func1` 会被激活，Kea2 会根据装饰器 `@prob` 定义的概率值运行 `test_func1`。若未指定 `@prob`，默认概率为 1（即前置条件满足时始终执行）。  
  
### `@prob`  
  
```python  
@prob(0.7)  
@precondition(lambda self: ...)  
def test_func1(self):  
    ...  
```  
  
装饰器 `@prob` 接收一个浮点数参数，表示前置条件满足时执行函数 `test_func1` 的概率。概率值范围应在 0 到 1 之间。若未指定 `@prob`，默认概率为 1（前置条件满足时始终执行）。  
  
当多个函数的前置条件均满足时，Kea2 会根据它们的概率值随机选择一个函数执行。具体而言，Kea2 会生成一个 0 到 1 的随机值 `p`，根据该值和概率值决定最终执行哪个函数。  
  
例如，若 `test_func1`、`test_func2` 和 `test_func3` 的前置条件均满足，概率值分别为 `0.2`、`0.4` 和 `0.6`：  
- 情况 1：若 `p` 随机为 `0.3`，`test_func1` 的概率 `0.2` 小于 `p`，失去执行机会。Kea2 会从 `test_func2` 和 `test_func3` 中随机选择一个执行。  
- 情况 2：若 `p` 随机为 `0.1`，Kea2 会从 `test_func1`、`test_func2` 和 `test_func3` 中随机选择一个执行。  
- 情况 3：若 `p` 随机为 `0.7`，Kea2 会跳过这三个函数的执行。  
  
### `@max_tries`  
  
```python  
@max_tries(1)  
@precondition(lambda self: ...)  
def test_func1(self):  
    ...  
```  
  
装饰器 `@max_tries` 接收一个整数参数，表示前置条件满足时函数 `test_func1` 最多执行次数。默认值为 `inf`（无限次）。  
  
## 启动 Kea2  
  
我们提供两种方式启动 Kea2。  
  
### 1. 通过 shell 命令启动  
  
通过 `kea2 run` 命令启动 Kea2。  
  
`kea2 run` 包含两部分参数：第一部分是 Kea2 的选项，第二部分是子命令及其参数。  
  
### 1.1 `kea2 run` 参数说明  
  
| 参数 | 含义 | 默认值 |   
| --- | --- | --- |  
| -s | 设备序列号（可通过 `adb devices` 查看） | |  
| -t | 设备 transport_id（可通过 `adb devices -l` 查看） | |  
| -p | 指定目标应用包名（如 `com.example.app`）*支持多个包：`-p pkg1 pkg2 pkg3`* | |  
| -o | 日志和结果输出目录 | `output` |  
| --agent | `{native, u2}`。默认使用 `u2`，支持 Kea2 所有三个重要功能。如需运行原生 Fastbot，请使用 `native` | `u2` |  
| --running-minutes | Kea2 运行时间（分钟） | `10` |  
| --max-step | 发送的 monkey 事件最大数量（仅在 `--agent u2` 有效） | `inf`（无限） |  
| --throttle | 两次 monkey 事件间的延迟时间（毫秒） | `200` |  
| --driver-name | Kea2 脚本使用的驱动名称。若指定 `--driver-name d`，则需使用 `d` 操作设备（如 `self.d(..).click()`） | |  
| --log-stamp | 日志和结果文件标识符。例：`--log-stamp 123` 会生成 `fastbot_123.log` 和 `result_123.json` | 当前时间戳 |  
| --profile-period | 覆盖率分析和截图采集周期（单位：猴子事件数）。截图保存在设备 SD 卡，根据设备存储调整值 | `25` |  
| --take-screenshots | 每个 monkey 事件后截图，截图会周期性地从设备拉取到主机（周期由 `--profile-period` 指定） | |  
| --device-output-root | 设备输出目录根路径。Kea2 会将截图和日志暂存于 `"<device-output-root>/output_*********/"`。请确保该目录可访问 | `/sdcard` |  
  
### 1.2 子命令及参数说明  
Kea2 支持 3 个子命令：`propertytest`、`unittest` 和 `--`（扩展参数）。  
  
#### **1.2.1 `propertytest` 子命令及测试发现（基于性质的测试）**  
  
Kea2 兼容 `unittest` 框架。你可以使用 unittest 风格管理测试用例，并通过 [unittest 自动发现选项](https://docs.python.org/3/library/unittest.html#test-discovery) 自动发现性质脚本。启动命令如下：  
  
```bash  
# <unittest discover cmds> 为 unittest 自动发现命令，如 `discover -p quicktest.py`  
kea2 run <Kea2 参数> propertytest <unittest discover参数>   
```  
示例命令：  
  
```bash  
# 启动 Kea2 并加载单脚本 quicktest.py  
kea2 run -s "emulator-5554" -p it.feio.android.omninotes.alpha --agent u2 --running-minutes 10 --throttle 200 --driver-name d propertytest discover -p quicktest.py  
  
# 启动 Kea2 并从目录 mytests/omni_notes 加载多脚本  
kea2 run -s "emulator-5554" -p it.feio.android.omninotes.alpha --agent u2 --running-minutes 10 --throttle 200 --driver-name d propertytest discover -s mytests/omni_notes -p test*.py  
```  
  
#### **1.2.2 (实验功能) `unittest` 子命令（混合测试）**  
  
> 此功能仍在开发中。欢迎反馈！如有兴趣请联系开发者。  
  
`unittest` 子命令用于功能 4（混合测试）。可通过 `kea run` 配合驱动参数和 `unittest` 子命令启动。与 `propertytest` 一样，可以用 [unittest 自动发现选项](https://docs.python.org/3/library/unittest.html#test-discovery) 加载测试用例。  
  
#### **1.2.3 `--` 子命令（扩展参数）**  
  
如需传递扩展参数给底层 Fastbot，可在常规参数后追加 `--`，再添加扩展参数。例如设置触摸事件比例为 30%：  
  
```bash  
kea2 run -s "emulator-5554" -p it.feio.android.omninotes.alpha --agent u2 --running-minutes 10 --throttle 200 --driver-name d -- --pct-touch 30 unittest discover -p quicktest.py  
```  
  
### 2. 通过 `unittest.main` 启动  
  
像 unittest 一样，可以通过 `unittest.main` 方法启动 Kea2。  
  
示例保存为 `mytest.py`，选项直接在脚本中定义：  
  
```python  
import unittest  
  
from kea2 import KeaTestRunner, Options  
from kea2.u2Driver import U2Driver  
  
class MyTest(unittest.TestCase):  
    ...  
    # <请在此处定义你的测试方法>  
  
if __name__ == "__main__":  
    KeaTestRunner.setOptions(  
        Options(  
            driverName="d",  
            Driver=U2Driver,  
            packageNames=[PACKAGE_NAME],  
            # serial="emulator-5554",   # 指定设备序列号  
            maxStep=100,  
            # running_mins=10,  # 指定最大运行时间（分钟），默认 10 分钟  
            # throttle=200,   # 指定延迟时间（毫秒），默认 200 毫秒  
            # agent='native'  # 'native' 运行原生 Fastbot  
        )  
    )  
    # 声明 KeaTestRunner  
    unittest.main(testRunner=KeaTestRunner)  
```  
  
运行该脚本启动 Kea2：  
```bash  
python3 mytest.py  
```  
  
以下是 `Options` 中所有可用选项：  
  
```python  
# 脚本中的驱动名称（如 self.d，则填 d）  
driverName: str  
# 驱动（当前只有 U2Driver）  
Driver: U2Driver  
# 包名列表，指定被测试的应用  
packageNames: List[str]  
# 目标设备序列号  
serial: str = None  
# 测试代理，默认 "u2"  
agent: "u2" | "native" = "u2"  
# 探索时最大步数（阶段 2~3 可用）  
maxStep: int # 默认 "inf"  
# 探索时长（分钟）  
running_mins: int = 10  
# 探索时等待时间（毫秒）  
throttle: int = 200  
# 日志和结果保存目录  
output_dir: str = "output"  
# 日志文件和结果文件的时间戳标识，默认当前时间戳  
log_stamp: str = None  
# 覆盖率采样周期  
profile_period: int = 25  
# 是否每步截图  
take_screenshots: bool = False  
# 设备上的输出目录根路径  
device_output_root: str = "/sdcard"  
# 是否启用调试模式  
debug: bool = False  
```  
  
## 管理 Kea2 报告  
  
### 生成 Kea2 报告（`kea2 report`）  
  
`kea2 report` 命令根据已有测试结果生成 HTML 测试报告。该命令会分析测试数据并生成包含测试执行统计、覆盖率信息、性质违规和崩溃详情的可视化报告。  
  
| 参数 | 含义 | 是否必需 | 默认值 |  
| --- | --- | --- | --- |  
| -p, --path | 测试结果目录路径（res_* 目录） | 是 | |  
  
**使用示例：**  
  
```bash  
# 从测试结果目录生成报告  
kea2 report -p res_20240101_120000  
  
# 启用调试模式生成报告  
kea2 -d report -p res_20240101_120000  
  
# 使用相对路径生成报告  
kea2 report -p ./output/res_20240101_120000  
```  
  
**报告内容包括：**  
- **测试摘要**：发现的总缺陷数、执行时间、覆盖率百分比  
- **性质测试结果**：每个测试性质的执行统计（前置条件满足次数、执行次数、失败次数、错误次数）  
- **代码覆盖率**：Activity 覆盖趋势及详细覆盖信息  
- **性质违规**：失败测试性质的详细信息及错误堆栈  
- **崩溃事件**：测试过程中检测到的应用崩溃  
- **ANR 事件**：应用无响应事件  
- **截图**：测试过程中采集的 UI 截图（如启用）  
- **Activity 遍历**：测试过程中访问的 Activity 历史  
  
**输出内容：**  
报告命令生成：  
- 指定测试结果目录下的 HTML 报告文件（`bug_report.html`）  
- 覆盖率和执行趋势的交互式图表和可视化  
- 详细的错误信息和堆栈跟踪，便于调试  
  
**输入目录结构示例：**  
```  
res_<timestamp>/  
├── result_<timestamp>.json          # 性质测试结果  
├── output_<timestamp>/  
│   ├── steps.log                    # 测试执行步骤  
│   ├── coverage.log                 # 覆盖率数据  
│   ├── crash-dump.log               # 崩溃和 ANR 事件  
│   └── screenshots/                 # UI 截图（如启用）  
└── property_exec_info_<timestamp>.json  # 性质执行详情  
```  
  
### 合并多个测试报告（`kea2 merge`）  
  
`kea2 merge` 命令允许合并多个测试报告目录，生成综合报告。适用于多个测试会话结果的汇总。  
  
| 参数 | 含义 | 是否必需 | 默认值 |  
| --- | --- | --- | --- |  
| -p, --paths | 需要合并的测试报告目录路径（res_* 目录），至少两个路径 | 是 | |  
| -o, --output | 合并报告的输出目录 | 否 | `merged_report_<timestamp>` |  
  
**使用示例：**  
  
```bash  
# 合并两个测试报告目录  
kea2 merge -p res_20240101_120000 res_20240102_130000  
  
# 合并多个测试报告目录并指定输出目录  
kea2 merge -p res_20240101_120000 res_20240102_130000 res_20240103_140000 -o my_merged_report  
  
# 启用调试模式合并  
kea2 -d merge -p res_20240101_120000 res_20240102_130000  
```  
  
**合并内容包括：**  
- 性质测试执行统计（前置条件满足、执行、失败、错误次数）  
- 代码覆盖率数据（覆盖的 Activity、覆盖率百分比）  
- 崩溃和 ANR 事件  
- 测试执行步骤和时间信息  
  
**输出内容：**  
合并命令生成：  
- 包含汇总数据的合并报告目录  
- 带有可视化摘要的 HTML 报告（`merged_report.html`）  
- 合并元数据，包括源目录和时间戳  
  
## 调试模式（`kea2 -d ...`）  
  
可在使用 Kea2 时添加 `-d` 参数启用调试模式。进入调试模式后，Kea2 会打印更详细的日志以帮助诊断问题。  
  
| 参数 | 含义 | 默认值 |  
| --- | --- | --- |  
| -d | 启用调试模式 | |  
  
> ```bash  
> # 添加 -d 启用调试模式  
> kea2 -d run -s "emulator-5554" -p it.feio.android.omninotes.alpha --agent u2 --running-minutes 10 --throttle 200 --driver-name d unittest discover -p quicktest.py  
> ```  
  
## 查看脚本运行统计  
  
如需查看脚本是否执行及执行次数，测试结束后打开 `result.json` 文件。  
  
示例：  
  
```json  
{  
    "test_goToPrivacy": {  
        "precond_satisfied": 8,  
        "executed": 2,  
        "fail": 0,  
        "error": 1  
    },  
    ...  
}  
```  
  
**如何解读 `result.json`**  
  
字段 | 说明 | 含义  
--- | --- | --- |  
precond_satisfied | 探索过程中，测试方法的前置条件满足次数 | 是否到达了对应状态   
executed | UI 测试过程中，测试方法被执行的次数 | 该测试方法是否执行过  
fail | UI 测试中，测试方法断言失败次数 | 失败时，测试方法发现了可能的功能缺陷   
error | UI 测试中，测试方法因发生意外错误（如找不到某些 UI 组件）中断的次数 | 出现错误时，意味着脚本需要更新或修复  
  
## 配置文件  
  
执行 `Kea2 init` 后，`configs` 目录会生成配置文件。  
这些配置属于 `Fastbot`，详情请见 [配置文件介绍](https://github.com/bytedance/Fastbot_Android/blob/main/handbook-cn.md#%E4%B8%93%E5%AE%B6%E7%B3%BB%E7%BB%9F)。  
  
## 用户配置文件更新  
更新 Kea2 时，本地配置需同步更新（最新 Kea2 版本可能与旧版配置不兼容）。  
  
当检测到运行时错误时，Kea2 会检查配置文件是否兼容当前版本。如果不兼容，控制台会打印警告信息。请按以下步骤更新配置：  
  
1. 备份本地配置文件  
2. 删除项目根目录中 `/configs` 下的所有配置文件  
3. 运行 `kea2 init` 生成最新配置文件  
4. 根据需求将旧配置合并到新文件中  
  
## 应用崩溃缺陷  
  
Kea2 会将触发的崩溃缺陷转储在 `-o` 指定输出目录的 `fastbot_*.log` 文件中。可以在 `fastbot_*.log` 中搜索 `FATAL EXCEPTION` 获取崩溃缺陷详情。  
  
这些崩溃缺陷也会记录在设备上。[详情请参考 Fastbot 手册](https://github.com/bytedance/Fastbot_Android/blob/main/handbook-cn.md#%E7%BB%93%E6%9E%9C%E8%AF%B4%E6%98%8E)。  
  
## 与三方包交互  
Kea2 默认在探索时阻止三方包（如支付等）。如需与这些包交互，请在 [扩展参数](#---sub-command-扩展参数) 中添加 `--allow-any-starts`。  
  
示例：  
```bash  
kea2 run -s "emulator-5554" -p it.feio.android.omninotes.alpha --agent u2 --running-minutes 10 --throttle 200 --driver -- --allow-any-starts propertytest discover -p quicktest.py  
```