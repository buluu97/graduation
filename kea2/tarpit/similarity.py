import os
import json
import cv2

from datetime import datetime
from ..utils import getLogger

# 默认相似度阈值，低于此值认为页面不同
# 与HybridDroidbot保持一致
DEFAULT_THRESHOLD = 0.8
# 重用阈值，高于此值认为遇到已知的UI陷阱
REUSE_THRESHOLD = 0.99


class UITarpitDetector(object):
    """
    UI Tarpit（界面陷阱）检测器类
    负责检测Android应用中的界面陷阱，即连续多步操作后UI画面几乎不变的状态。

    与HybridDroidbot的版本不同，此版本不依赖其InputManager/InputPolicy链，
    而是直接通过uiautomator2设备对象截图，自行管理前后两帧截图的比较。
    """

    def __init__(self, sim_k, output_dir, u2_device=None):
        """
        初始化UI陷阱检测器

        Args:
            sim_k (int): 连续相似次数阈值，达到此次数认为进入UI陷阱
            output_dir (str|Path): 输出目录，用于保存截图和陷阱记录
            u2_device: uiautomator2设备对象（可选，稍后通过set_device设置）
        """
        self.sim_k = sim_k          # 连续相似次数阈值
        self.sim_count = 0          # 当前连续相似次数
        self.u2_device = u2_device  # uiautomator2设备对象
        self.output_dir = str(output_dir)  # 输出根目录（供保存JSON报告）

        self.logger = getLogger('UITarpitDetector')

        # 截图保存目录
        self.tarpit_save_dir = os.path.join(str(output_dir), "ui_tarpits")
        os.makedirs(self.tarpit_save_dir, exist_ok=True)

        # 截图序号，用于文件命名
        self._screenshot_index = 0
        # 上一帧截图路径（None 表示还没有截过图）
        self._last_screenshot_path = None

        # UI层级转储保存目录
        self.hierarchy_save_dir = os.path.join(str(output_dir), "ui_tarpits", "hierarchies")
        os.makedirs(self.hierarchy_save_dir, exist_ok=True)

        # 内存中已发现的UI陷阱字典
        self.tarpits = {}

        # 每次检测到UI陷阱时记录的事件列表（用于报告）
        # 格式: {"time": "ISO string", "screenshot": "path", "tarpit_name": "trap_1"}
        self.tarpit_events: list = []
        # 测试开始时间（首次截图时记录，用于计算时间比例）
        self._test_start_time: datetime = None
        self._test_end_time: datetime = None

        self.logger.info(
            f"[UITarpitDetector] 初始化完成 | sim_k={sim_k} | 截图目录: {self.tarpit_save_dir}"
        )

    def set_device(self, u2_device):
        """设置uiautomator2设备对象（允许延迟设置）"""
        self.u2_device = u2_device

    def _take_screenshot(self):
        """
        通过uiautomator2截取当前屏幕，保存到tarpit_save_dir。

        Returns:
            str | None: 截图文件路径，失败时返回None
        """
        if self.u2_device is None:
            self.logger.warning("[UITarpitDetector] 未设置u2_device，无法截图")
            return None

        self._screenshot_index += 1
        path = os.path.join(self.tarpit_save_dir, f"screen_{self._screenshot_index:05d}.png")
        try:
            self.u2_device.screenshot(path)
            self.logger.debug(f"[UITarpitDetector] 截图保存: {path}")
            return path
        except Exception as e:
            self.logger.error(f"[UITarpitDetector] 截图失败: {e}")
            return None

    def _dump_ui_hierarchy(self):
        """
        通过uiautomator2获取当前页面的UI层级结构（XML），
        并保存到hierarchy_save_dir目录。

        Returns:
            str | None: UI层级XML字符串，失败时返回None
        """
        if self.u2_device is None:
            return None
        try:
            xml_str = self.u2_device.dump_hierarchy()
            # 保存XML文件到磁盘
            xml_path = os.path.join(
                self.hierarchy_save_dir,
                f"hierarchy_{self._screenshot_index:05d}.xml"
            )
            with open(xml_path, "w", encoding="utf-8") as f:
                f.write(xml_str)
            self.logger.debug(f"[UITarpitDetector] UI层级已保存: {xml_path}")
            return xml_str
        except Exception as e:
            self.logger.warning(f"[UITarpitDetector] 获取UI层级失败: {e}")
            return None

    def check(self, u2_device=None):
        """
        执行一次UI Tarpit检测（Kea2主循环每步调用此方法）。

        方法流程：
          1. 截取当前屏幕
          2. 与上一帧截图比较相似度
          3. 更新连续相似计数
          4. 如果连续相似次数达到 sim_k，判定为UI Tarpit

        Args:
            u2_device: （可选）如果传入则临时覆盖已设置的设备对象

        Returns:
            bool: 检测到UI Tarpit返回True，否则返回False
        """
        if u2_device is not None:
            self.u2_device = u2_device

        # 截取当前帧
        current_path = self._take_screenshot()
        if current_path is None:
            self.logger.warning("[UITarpitDetector] 截图失败，本步跳过检测")
            return False

        # 记录测试开始时间（首次截图时）
        now = datetime.now()
        if self._test_start_time is None:
            self._test_start_time = now
        self._test_end_time = now

        # 第一帧时没有上一帧可以比较
        if self._last_screenshot_path is None:
            self._last_screenshot_path = current_path
            self.logger.info(f"[UITarpitDetector] 首帧截图已保存: {current_path}")
            return False

        # 计算相似度
        sim_score = self.calculate_similarity(self._last_screenshot_path, current_path)

        self.logger.info(
            f"[UITarpitDetector] 相似度: {sim_score:.4f} "
            f"(阈值={DEFAULT_THRESHOLD}, 连续相似次数: {self.sim_count}/{self.sim_k}) | "
            f"{os.path.basename(self._last_screenshot_path)} -> {os.path.basename(current_path)}"
        )

        # 更新连续相似计数
        if sim_score < DEFAULT_THRESHOLD:
            if self.sim_count > 0:
                self.logger.info(
                    f"[UITarpitDetector] 页面已变化，重置相似计数 {self.sim_count} -> 0"
                )
            self.sim_count = 0
        else:
            self.sim_count += 1
            self.logger.info(
                f"[UITarpitDetector] 页面相似，连续相似次数: {self.sim_count}/{self.sim_k}"
            )

        # 更新上一帧路径
        self._last_screenshot_path = current_path

        # 判断是否达到UI Tarpit阈值
        if self.sim_count >= self.sim_k:
            self.logger.warning(
                f"[UITarpitDetector] 检测到UI Tarpit！"
                f"连续相似次数 {self.sim_count}/{self.sim_k} 已达阈值"
            )
            # 记录该陷阱
            is_known, tarpit_name = self.check_or_add_new_trap(current_path, tag=self._screenshot_index)
            # 获取当前页面的UI层级结构
            ui_hierarchy = self._dump_ui_hierarchy()
            # 如果是新陷阱，将UI层级存入陷阱字典
            if not is_known and ui_hierarchy:
                self.tarpits[tarpit_name]['ui_hierarchy'] = ui_hierarchy
            # 记录事件（用于报告）
            self.tarpit_events.append({
                "time": datetime.now().isoformat(),
                "screenshot": current_path,
                "tarpit_name": tarpit_name,
                "is_known": is_known,
                "ui_hierarchy": ui_hierarchy,
            })
            # 重置计数，以便后续继续检测新的陷阱
            self.sim_count = 0
            return True

        return False

    def check_or_add_new_trap(self, screenshot, tag):
        """
        检查截图是否属于已知UI陷阱，如果不是则添加新陷阱

        Args:
            screenshot: 截图文件路径
            tag: 标签标识

        Returns:
            tuple: (是否已知陷阱, 陷阱名称)
        """
        for tarpit_name, tarpit_info in self.tarpits.items():
            tarpit_img = tarpit_info['screen_shoot']
            similarity = self.calculate_similarity(screenshot, tarpit_img)
            if similarity >= REUSE_THRESHOLD:
                self.tarpits[tarpit_name]['count'] = int(self.tarpits[tarpit_name]['count']) + 1
                self.logger.info(f"[UITarpitDetector] 再次进入已知UI陷阱: {tarpit_name} "
                                 f"(累计 {self.tarpits[tarpit_name]['count']} 次)")
                return True, tarpit_name

        new_tarpit_name = f"trap_{len(self.tarpits) + 1}"
        self.tarpits[new_tarpit_name] = {'screen_shoot': screenshot, 'count': 1}
        self.logger.info(f"[UITarpitDetector] 记录新UI陷阱: {new_tarpit_name} ({screenshot})")
        return False, new_tarpit_name

    def print_ui_tarpits(self):
        """打印所有UI陷阱汇总信息，并保存JSON报告"""
        self.logger.info("=" * 60)
        self.logger.info("[UITarpitDetector] UI Tarpit 检测结果汇总")
        self.logger.info("=" * 60)
        if self.tarpits:
            for tarpit_name, tarpit_info in self.tarpits.items():
                count = tarpit_info.get('count', 1)
                screen = tarpit_info.get('screen_shoot', 'N/A')
                self.logger.info(
                    f"  {tarpit_name}: 触发次数={count}, 截图={os.path.basename(screen)}"
                )
            self.logger.info(f"[UITarpitDetector] 共检测到 {len(self.tarpits)} 个不同UI陷阱")
        else:
            self.logger.info("[UITarpitDetector] 未检测到任何UI Tarpit")
        self.logger.info("=" * 60)
        # 同时保存JSON报告
        self.save_report()

    def save_report(self):
        """
        将UI Tarpit检测结果保存为JSON文件，供报告生成器读取。

        输出文件: <output_dir>/ui_tarpit_report.json
        """
        # 计算总测试时长（秒）
        total_seconds = 0.0
        if self._test_start_time and self._test_end_time:
            total_seconds = max(
                0.0,
                (self._test_end_time - self._test_start_time).total_seconds()
            )

        # 计算困在UI Tarpit中的时长（粗略估算：每次触发约消耗 sim_k 个步骤的截图时间）
        # 使用 事件数 * sim_k / 总检测次数 的比例
        tarpit_event_count = len(self.tarpit_events)
        total_checks = self._screenshot_index  # 总截图次数 ≈ 总检测步数

        if total_checks > 0 and total_seconds > 0:
            # 估算：每次触发tarpit消耗了 sim_k 步（这些步骤的时间等比例）
            tarpit_stuck_ratio = min(
                1.0,
                tarpit_event_count * self.sim_k / total_checks
            )
            tarpit_stuck_seconds = tarpit_stuck_ratio * total_seconds
        else:
            tarpit_stuck_ratio = 0.0
            tarpit_stuck_seconds = 0.0

        # 构建陷阱详情列表（便于报告渲染）
        tarpits_list = []
        for name, info in self.tarpits.items():
            screen_path = info.get('screen_shoot', '')
            # 转为相对于output_dir的路径（便于HTML报告引用）
            try:
                rel_path = os.path.relpath(screen_path, self.output_dir)
            except ValueError:
                rel_path = screen_path
            tarpits_list.append({
                "name": name,
                "count": info.get('count', 1),
                "screenshot": rel_path,
                "ui_hierarchy": info.get('ui_hierarchy', ''),
            })

        # 构建事件列表（附上相对路径）
        events_list = []
        for ev in self.tarpit_events:
            screen_path = ev.get('screenshot', '')
            try:
                rel_path = os.path.relpath(screen_path, self.output_dir)
            except ValueError:
                rel_path = screen_path
            events_list.append({
                "time": ev.get("time", ""),
                "screenshot": rel_path,
                "tarpit_name": ev.get("tarpit_name", ""),
                "is_known": ev.get("is_known", False),
            })

        report = {
            "sim_k": self.sim_k,
            "unique_tarpits_count": len(self.tarpits),
            "total_trigger_count": tarpit_event_count,
            "total_checks": total_checks,
            "test_start_time": self._test_start_time.isoformat() if self._test_start_time else None,
            "test_end_time": self._test_end_time.isoformat() if self._test_end_time else None,
            "total_seconds": round(total_seconds, 2),
            "tarpit_stuck_seconds": round(tarpit_stuck_seconds, 2),
            "tarpit_stuck_ratio": round(tarpit_stuck_ratio * 100, 2),  # 百分比
            "tarpits": tarpits_list,
            "events": events_list,
        }

        report_path = os.path.join(self.output_dir, "ui_tarpit_report.json")
        try:
            with open(report_path, "w", encoding="utf-8") as f:
                json.dump(report, f, indent=4, ensure_ascii=False)
            self.logger.info(f"[UITarpitDetector] UI Tarpit报告已保存: {report_path}")
        except Exception as e:
            self.logger.error(f"[UITarpitDetector] 保存报告失败: {e}")

    # ------------------------------------------------------------------
    # 静态工具方法（与HybridDroidbot保持相同算法）
    # ------------------------------------------------------------------

    @staticmethod
    def dhash(image, hash_size=8):
        """
        计算图像的差异哈希（dHash）

        Args:
            image: 输入图像（cv2读取的numpy数组）
            hash_size: 哈希大小，默认为8

        Returns:
            int: 图像的64位哈希值
        """
        resized = cv2.resize(image, (hash_size + 1, hash_size), interpolation=cv2.INTER_AREA)
        gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
        diff = gray[:, 1:] > gray[:, :-1]
        return sum([2 ** i for (i, v) in enumerate(diff.flatten()) if v])

    @staticmethod
    def hamming_distance(hash1, hash2):
        """
        计算两个哈希值之间的汉明距离

        Args:
            hash1: 第一个哈希值
            hash2: 第二个哈希值

        Returns:
            int: 汉明距离（不同位的数量）
        """
        return bin(hash1 ^ hash2).count("1")

    @staticmethod
    def calculate_similarity(fileA, fileB):
        """
        计算两个图像文件的相似度（基于dHash + 汉明距离）

        Args:
            fileA: 第一个图像文件路径
            fileB: 第二个图像文件路径

        Returns:
            float: 相似度分数（0.0-1.0），读取失败时返回0.0
        """
        try:
            imgA = cv2.imread(fileA)
            imgB = cv2.imread(fileB)

            if imgA is None or imgB is None:
                raise ValueError(f"无法读取图像文件: fileA={fileA}, fileB={fileB}")

            # 尺寸不一致时调整为较小尺寸
            if imgA.shape != imgB.shape:
                height = min(imgA.shape[0], imgB.shape[0])
                width = min(imgA.shape[1], imgB.shape[1])
                imgA = cv2.resize(imgA, (width, height))
                imgB = cv2.resize(imgB, (width, height))

            hashA = UITarpitDetector.dhash(imgA)
            hashB = UITarpitDetector.dhash(imgB)
            hamming_dist = UITarpitDetector.hamming_distance(hashA, hashB)
            # 64 是 dhash(hash_size=8) 产生的比特数
            similarity_score = 1 - hamming_dist / 64.0
            return similarity_score

        except Exception as e:
            getLogger('UITarpitDetector').error(f"相似度计算失败: {e}")
            return 0.0
