
import json
import pickle
import logging
import os
import cv2
from droidbot import utils
from droidbot.input_event import KeyEvent
from droidbot.input_policy import HybirdPolicy, EVENT_FLAG_EXPLORE

# 默认相似度阈值，低于此值认为页面不同
DEFAULT_THREGHOLD = 0.95
# 重用阈值，高于此值认为遇到已知的UI陷阱
REUSE_THREGHOLD = 0.99

class UITarpitDetector(object):
    """
    UI Tarpit（界面陷阱）检测器类
    负责检测Android应用中的界面陷阱，即用户无法前进或后退的界面状态
    """
    
    def __init__(self, sim_k, device) -> None:
        """
        初始化UI陷阱检测器
        
        Args:
            sim_k (int): 连续相似次数阈值，达到此次数认为进入UI陷阱
            device: 设备对象，用于获取输出目录等信息
        """
        self.sim_k = sim_k  # 连续相似次数阈值
        self.sim_count = 0   # 当前连续相似次数
        self.device = device  # 设备对象
        self.logger = logging.getLogger('UITarpitDetector')  # 日志记录器
        # UI陷阱保存目录
        self.tarpit_save_dir = os.path.join(self.device.output_dir, "ui_tarpits")
        if not os.path.exists(self.tarpit_save_dir):
            os.makedirs(self.tarpit_save_dir)
        self.tarpits = {}  # 内存中的UI陷阱字典
        self.to_save_tarpits = {}  # 待保存的UI陷阱字典
    
    def is_similar_page(self, input_manager, current_state=None):
        """
        判断当前页面是否与上一个页面相似
        
        Args:
            input_manager: 输入管理器对象
            current_state: 当前状态对象，如果为None则从输入管理器获取
            
        Returns:
            bool: 如果页面相似返回True，否则返回False
        """
        # 获取上一个状态和当前状态
        last_state = input_manager.policy.get_last_state()
        last_state_screen = last_state.get_state_screen()  # 上一个状态的截图路径
        
        if not current_state:
            current_state = input_manager.policy.get_current_state()
        current_state_screen = current_state.get_state_screen()  # 当前状态的截图路径
        
        # 计算两个截图的相似度
        sim_score = self.calculate_similarity(last_state_screen, current_state_screen)
        self.logger.info(f'similarity score:{sim_score}')
        
        # 如果相似度低于阈值，认为页面不同
        if sim_score < DEFAULT_THREGHOLD:
            self.logger.info(f'different page!')  
            return False
        return True  

    def detected_ui_tarpit(self, input_manager):
        """
        检测是否进入UI陷阱状态
        
        Args:
            input_manager: 输入管理器对象
            
        Returns:
            bool: 如果检测到UI陷阱返回True，否则返回False
        """
        # 检查页面是否相似
        if not self.is_similar_page(input_manager):
            self.sim_count = 0  # 重置相似计数
            input_manager.policy.clear_action_history()  # 清空动作历史
        else:
            self.sim_count += 1   # 增加相似计数
        
        # 如果连续相似次数达到阈值，认为进入UI陷阱
        if self.sim_count >= self.sim_k:
            return True
        return False  
    
    # def load_ui_tarpits(self):
    #     """加载保存的UI陷阱"""
    #     try:
    #         with open(os.path.join(self.trap_save_dir, 'UITarpits.pkl'), 'rb') as f:
    #             traps = pickle.load(f)
    #         return traps
    #     except FileNotFoundError:
    #         return {}

    def load_ui_tarpits(self):
        """
        从JSON文件加载保存的UI陷阱
        
        Returns:
            dict: 加载的UI陷阱字典，如果文件不存在或解析失败返回空字典
        """
        try:
            with open(os.path.join(self.tarpit_save_dir, 'UITarpits.json'), 'r') as f:
                traps = json.load(f)  # 使用 json.load() 加载 JSON 数据
            self.logger.info("UI traps loaded successfully.")
            return traps
        except FileNotFoundError:
            self.logger.warning("No saved UI traps found. Returning an empty dictionary.")
            return {}
        except json.JSONDecodeError:
            self.logger.error("Error decoding JSON. Returning an empty dictionary.")
            return {}
        
    # def save_ui_tarpits(self):
    #     """保存UI陷阱"""
    #     with open(os.path.join(self.trap_save_dir, 'UITarpits.pkl'), 'wb') as f:
    #         pickle.dump(self.traps, f)

    def to_dict(self):
        """将对象转换为字典（待实现）"""
        pass

    def save_ui_tarpits(self):
        """
        将UI陷阱保存为JSON格式文件
        """
        try:
            with open(os.path.join(self.tarpit_save_dir, 'UITarpits.json'), 'w') as f:
                json.dump(self.to_save_tarpits, f, indent=4)  # 使用 indent=4 使 JSON 更易读
            self.logger.info("UI traps saved successfully.")
        except Exception as e:
            self.logger.error(f"Error saving UI traps: {e}")

    def print_ui_tarpits(self):
        """打印所有UI陷阱信息"""
        for tarpit_name, tarpit_info in self.tarpits.items():
            print(f'tarpit name:{tarpit_name}, info: {tarpit_info}')
        print(f'total tarpits:{len(self.tarpits)}')
    
    def check_or_add_new_trap(self, screenshot, tag):
        """
        检查截图是否属于已知UI陷阱，如果不是则添加新陷阱
        
        Args:
            screenshot: 截图文件路径
            tag: 标签标识
            
        Returns:
            tuple: (是否已知陷阱, 陷阱名称)
        """
        # 检查是否已有相似的陷阱
        for tarpit_name, tarpit_info in self.tarpits.items():
            tarpit_img = tarpit_info['screen_shoot']
            similarity = self.calculate_similarity(screenshot, tarpit_img)
            if similarity >= REUSE_THREGHOLD:
                self.logger.info(f"Visiting known tarpit: {tarpit_name}")
                self.tarpits[tarpit_name]['count'] = int(self.tarpits[tarpit_name]['count']) + 1 # 增加count并保存
                return True, tarpit_name
        
        # 添加一个新的UI陷阱
        new_tarpit_name = f"trap_{len(self.tarpits) + 1}"
        # dest_screenshot_path = "%s/screen_%s.png" % (self.tarpit_save_dir,tag)
        # if screenshot != dest_screenshot_path:
        #         import shutil
        #         shutil.copyfile(screenshot, dest_screenshot_path)
        self.tarpits[new_tarpit_name] = {'screen_shoot': screenshot, 'count': 1, 'actions':[]}
        # self.to_save_tarpits[new_tarpit_name] = {'screen_shoot': screenshot, 'count': 1, 'actions':[]}
        # self.save_ui_tarpits()
        self.logger.info(f"New UI tarpit saved: {new_tarpit_name}")
        return False, new_tarpit_name

    def update_tarpit_actions(self, tarpit_name, event):
        """
        更新UI陷阱的动作历史
        
        Args:
            tarpit_name: 陷阱名称
            event: 输入事件对象
        """
        self.tarpits[tarpit_name]['actions'].append(event)
        # self.to_save_tarpits[tarpit_name]['actions'].append(event.get_event_name())
        # self.save_ui_tarpits()
        self.logger.info(f"UI tarpit updated: {tarpit_name}, add event:{event.get_event_name()}")
    
    def clear_tarpit_actions(self, tarpit_name):
        """
        清空指定UI陷阱的动作历史
        
        Args:
            tarpit_name: 陷阱名称
        """
        self.tarpits[tarpit_name]['actions'].clear()

    def get_tarpit_by_name(self, tarpit_name):
        """
        根据名称获取UI陷阱信息
        
        Args:
            tarpit_name: 陷阱名称
            
        Returns:
            dict: UI陷阱信息字典，如果不存在返回None
        """
        return self.tarpits.get(tarpit_name)
    
    def get_tarpit_actions_by_name(self, tarpit_name):
        """
        根据名称获取UI陷阱的动作历史
        
        Args:
            tarpit_name: 陷阱名称
            
        Returns:
            list: 动作历史列表
        """
        return self.tarpits[tarpit_name]['actions']
    
    @staticmethod
    def dhash(image, hash_size=8):
        """
        计算图像的差异哈希（dHash）
        
        Args:
            image: 输入图像
            hash_size: 哈希大小，默认为8
            
        Returns:
            int: 图像的哈希值
        """
        # 转换为灰度并缩放图像
        resized = cv2.resize(image, (hash_size + 1, hash_size), interpolation=cv2.INTER_AREA)
        gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)

        # 计算差异值（相邻像素比较）
        diff = gray[:, 1:] > gray[:, :-1]

        # 将布尔数组转换为哈希值
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
        # 计算两个哈希值之间的汉明距离
        return bin(hash1 ^ hash2).count("1")

    @staticmethod
    def calculate_similarity(fileA, fileB):
        """
        计算两个图像文件的相似度
        
        Args:
            fileA: 第一个图像文件路径
            fileB: 第二个图像文件路径
            
        Returns:
            float: 相似度分数（0.0-1.0）
        """
        # 读取两个图像文件
        imgA = cv2.imread(fileA)
        imgB = cv2.imread(fileB)
        
        # 计算图像的哈希值
        hashA = UITarpitDetector.dhash(imgA)
        hashB = UITarpitDetector.dhash(imgB)
        
        # 计算汉明距离相似度分数
        similarity_score = 1 - UITarpitDetector.hamming_distance(hashA, hashB) / 64.0  # 64是dhash算法哈希位数
        return similarity_score