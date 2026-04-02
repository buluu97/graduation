# -*- coding: utf-8 -*-
"""
DroidBot核心模块 - Android应用自动化测试框架的主控制器

这个文件包含了DroidBot的主类，是整个自动化测试框架的核心协调者。
在AVD启动、应用安装、adb设置完成后，通过配置和创建DroidBot实例，
DroidBot会像人类一样与Android设备进行交互。
"""
import logging
import os
import sys
import pkg_resources
import shutil
from threading import Timer

# 导入项目内部模块
from .device import Device          # 设备管理模块
from .app import App                # 应用管理模块
from .env_manager import AppEnvManager  # 环境管理模块
from .input_manager import InputManager  # 输入管理模块

import coloredlogs
coloredlogs.install()  # 安装彩色日志


class DroidBot(object):
    """
    DroidBot主类 - Android应用自动化测试框架的核心控制器
    
    这个类负责协调设备管理、应用管理、环境管理和输入管理的完整生命周期，
    是整个自动化测试流程的大脑和调度中心。
    """
    # 这是一个单例类，确保全局只有一个DroidBot实例
    instance = None

    def __init__(self,
                 app_path=None,               # APK文件路径
                 device_serial=None,          # 设备序列号
                 task=None,                   # 任务描述（自然语言）
                 is_emulator=False,           # 是否为模拟器
                 output_dir=None,             # 输出目录
                 env_policy=None,             # 环境策略
                 policy_name=None,            # 输入策略名称
                 random_input=False,          # 是否使用随机输入
                 script_path=None,            # 脚本路径
                 event_count=None,            # 事件总数
                 event_interval=None,         # 事件间隔（秒）
                 timeout=None,                # 超时时间（分钟）
                 keep_app=None,               # 测试后是否保留应用
                 keep_env=False,              # 测试后是否保留环境
                 cv_mode=False,               # 计算机视觉模式
                 debug_mode=False,            # 调试模式
                 profiling_method=None,       # 性能分析方法
                 grant_perm=False,            # 是否自动授予权限
                 enable_accessibility_hard=False,  # 是否强制启用无障碍服务
                 master=None,                 # 主控制器（用于分布式）
                 humanoid=None,               # 人性化设置
                 ignore_ad=False,             # 是否忽略广告视图
                 replay_output=None):         # 回放输出
        """
        初始化DroidBot配置
        
        参数:
            app_path: APK文件路径，必需参数
            device_serial: 设备序列号，如果为None则使用默认设备
            task: 任务描述，用于指导输入策略
            is_emulator: 标识目标设备是否为模拟器
            output_dir: 输出目录，用于存储测试结果和截图
            env_policy: 环境部署策略
            policy_name: 输入策略名称（如：random, monkey, hybrid等）
            random_input: 是否使用随机输入
            script_path: 自定义脚本路径
            event_count: 要生成的事件总数
            event_interval: 事件之间的间隔时间（秒）
            timeout: 超时时间（分钟），-1表示无限制
            keep_app: 测试后是否保留应用
            keep_env: 测试后是否保留测试环境
            cv_mode: 是否启用计算机视觉模式
            debug_mode: 是否启用调试模式
            profiling_method: 性能分析方法
            grant_perm: 安装时是否自动授予所有权限
            enable_accessibility_hard: 是否强制启用无障碍服务
            master: 主控制器实例（用于分布式测试）
            humanoid: 人性化设置参数
            ignore_ad: 是否忽略广告视图
            replay_output: 回放输出配置
        """
        # 配置日志级别
        logging.basicConfig(level=logging.DEBUG if debug_mode else logging.INFO)

        self.logger = logging.getLogger('DroidBot')
        DroidBot.instance = self  # 设置单例实例

        # 设置输出目录并准备报告资源
        self.output_dir = output_dir
        if output_dir is not None:
            if not os.path.isdir(output_dir):
                os.makedirs(output_dir)  # 创建输出目录
            
            # 复制HTML报告模板和样式表
            html_index_path = pkg_resources.resource_filename("droidbot", "resources/index.html")
            stylesheets_path = pkg_resources.resource_filename("droidbot", "resources/stylesheets")
            target_stylesheets_dir = os.path.join(output_dir, "stylesheets")
            
            if os.path.exists(target_stylesheets_dir):
                shutil.rmtree(target_stylesheets_dir)  # 清理旧样式表
            
            shutil.copy(html_index_path, output_dir)  # 复制HTML模板
            shutil.copytree(stylesheets_path, target_stylesheets_dir)  # 复制样式表

        # 配置超时和资源管理
        self.timeout = timeout * 60  # 转换为秒
        self.timer = None  # 超时计时器
        self.keep_env = keep_env  # 是否保留环境
        self.keep_app = keep_app  # 是否保留应用

        # 初始化组件引用
        self.device = None  # 设备管理实例
        self.app = None     # 应用管理实例
        self.task = task    # 任务描述
        self.droidbox = None  # DroidBox实例（安全分析）
        self.env_manager = None  # 环境管理实例
        self.input_manager = None  # 输入管理实例
        self.enable_accessibility_hard = enable_accessibility_hard  # 无障碍服务设置
        self.humanoid = humanoid  # 人性化设置
        self.ignore_ad = ignore_ad  # 广告忽略设置
        self.replay_output = replay_output  # 回放输出设置

        self.enabled = True  # 启用状态标志

        try:
            # 初始化设备管理
            self.device = Device(
                device_serial=device_serial,
                is_emulator=is_emulator,
                output_dir=self.output_dir,
                cv_mode=cv_mode,
                grant_perm=grant_perm,
                enable_accessibility_hard=self.enable_accessibility_hard,
                humanoid=self.humanoid,
                ignore_ad=ignore_ad)
            
            # 初始化应用管理
            self.app = App(app_path, output_dir=self.output_dir)

            # 初始化环境管理
            self.env_manager = AppEnvManager(
                device=self.device,
                app=self.app,
                env_policy=env_policy)
            
            # 初始化输入管理（核心组件）
            self.input_manager = InputManager(
                device=self.device,
                app=self.app,
                task=self.task,
                policy_name=policy_name,
                random_input=random_input,
                event_count=event_count,
                event_interval=event_interval,
                script_path=script_path,
                profiling_method=profiling_method,
                master=master,
                replay_output=replay_output)
        
        except Exception:
            # 异常处理：打印堆栈跟踪并停止
            import traceback
            traceback.print_exc()
            self.stop()
            sys.exit(-1)

    @staticmethod
    def get_instance():
        """
        获取DroidBot单例实例
        
        返回:
            DroidBot实例
        
        异常:
            如果DroidBot未初始化，则退出程序
        """
        if DroidBot.instance is None:
            print("Error: DroidBot is not initiated!")
            sys.exit(-1)
        return DroidBot.instance

    def start(self):
        """
        启动DroidBot交互流程
        
        这个方法按照以下顺序执行：
        1. 设置超时计时器
        2. 设置设备环境
        3. 连接设备
        4. 安装应用
        5. 部署测试环境
        6. 启动输入管理（核心测试逻辑）
        """
        if not self.enabled:
            return
        
        self.logger.info("Starting DroidBot")
        
        try:
            # 设置超时计时器
            if self.timeout > 0:
                self.timer = Timer(self.timeout, self.stop)
                self.timer.start()

            # 步骤1: 设置设备环境
            self.device.set_up()

            if not self.enabled:
                return
            
            # 步骤2: 连接设备
            self.device.connect()

            if not self.enabled:
                return
            
            # 步骤3: 安装应用
            self.device.install_app(self.app)

            if not self.enabled:
                return
            
            # 步骤4: 部署测试环境
            self.env_manager.deploy()

            if not self.enabled:
                return
            
            # 步骤5: 启动输入管理（核心测试逻辑）
            if self.droidbox is not None:
                # 使用DroidBox进行安全分析的模式
                self.droidbox.set_apk(self.app.app_path)
                self.droidbox.start_unblocked()
                self.input_manager.start()
                self.droidbox.stop()
                self.droidbox.get_output()
            else:
                # 普通测试模式
                self.input_manager.start()
        
        except KeyboardInterrupt:
            # 处理用户中断
            self.logger.info("Keyboard interrupt.")
            pass
        except Exception:
            # 处理其他异常
            import traceback
            traceback.print_exc()
            self.stop()
            sys.exit(-1)

        # 测试完成，停止DroidBot
        self.stop()
        self.logger.info("DroidBot Stopped")

    def stop(self):
        """
        停止DroidBot并清理资源
        
        这个方法按照以下顺序执行：
        1. 取消超时计时器
        2. 停止环境管理
        3. 停止输入管理
        4. 停止DroidBox（如果存在）
        5. 断开设备连接
        6. 清理环境（如果不保留）
        7. 卸载应用（如果不保留）
        """
        self.enabled = False  # 设置禁用状态
        
        # 取消超时计时器
        if self.timer and self.timer.is_alive():
            self.timer.cancel()
        
        # 停止环境管理
        if self.env_manager:
            self.env_manager.stop()
        
        # 停止输入管理
        if self.input_manager:
            self.input_manager.stop()
        
        # 停止DroidBox
        if self.droidbox:
            self.droidbox.stop()
        
        # 断开设备连接
        if self.device:
            self.device.disconnect()
        
        # 清理环境（如果不保留）
        if not self.keep_env:
            self.device.tear_down()
            # self.device.clear_data(self.app.package_name)  # 可选：清理应用数据
        
        # 卸载应用（如果不保留）
        if not self.keep_app:
            self.device.uninstall_app(self.app)


class DroidBotException(Exception):
    """DroidBot自定义异常类"""
    pass
