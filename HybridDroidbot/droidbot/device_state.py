import copy
import json
import math
import os

from .utils import md5
from .input_event import TouchEvent, LongTouchEvent, ScrollEvent, SetTextEvent, KeyEvent, UIEvent


class DeviceState(object):
    """
    设备状态类，表示Android设备的当前UI状态
    
    该类封装了设备的UI视图信息、活动栈、后台服务、截图等信息，
    提供了状态比较、视图处理、事件生成等功能。
    
    主要属性：
    - device: 关联的设备对象
    - foreground_activity: 前台活动名称
    - activity_stack: 活动栈列表
    - background_services: 后台服务列表
    - tag: 状态标签（时间戳）
    - screenshot_path: 截图文件路径
    - views: 解析后的视图列表
    - view_tree: 组装后的视图树
    - state_str: 状态字符串（MD5哈希）
    - structure_str: 内容无关的状态字符串
    - search_content: 搜索内容文本
    - possible_events: 可能的输入事件列表
    - width/height: 设备屏幕宽高
    """

    def __init__(self, device, views, foreground_activity, activity_stack, background_services,
                 tag=None, screenshot_path=None):
        """
        初始化设备状态对象
        
        参数:
        - device: Device对象，关联的设备
        - views: 原始视图列表，从UI dump获取
        - foreground_activity: 前台活动名称
        - activity_stack: 活动栈信息
        - background_services: 后台服务列表
        - tag: 状态标签，默认为时间戳
        - screenshot_path: 截图文件路径
        """
        self.device = device
        self.foreground_activity = foreground_activity
        self.activity_stack = activity_stack if isinstance(activity_stack, list) else []
        self.background_services = background_services
        if tag is None:
            from datetime import datetime
            tag = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        self.tag = tag
        self.screenshot_path = screenshot_path
        self.views = self.__parse_views(views)  # 解析原始视图数据
        self.view_tree = {}
        self.__assemble_view_tree(self.view_tree, self.views)  # 组装视图树结构
        self.__generate_view_strs()  # 生成视图字符串
        self.state_str = self.__get_state_str()  # 生成状态哈希字符串
        self.structure_str = self.__get_content_free_state_str()  # 生成内容无关状态哈希
        self.search_content = self.__get_search_content()  # 生成搜索内容
        self.possible_events = None  # 可能的输入事件（延迟初始化）
        self.width = device.get_width(refresh=True)  # 获取设备宽度
        self.height = device.get_height(refresh=False)  # 获取设备高度

    @property
    def activity_short_name(self):
        """
        获取前台活动的短名称（去掉包名前缀）
        
        返回:
        - str: 活动类的短名称
        """
        return self.foreground_activity.split('.')[-1]

    def to_dict(self):
        """
        将设备状态转换为字典格式
        
        返回:
        - dict: 包含所有状态信息的字典
        """
        state = {'tag': self.tag,
                 'state_str': self.state_str,
                 'state_str_content_free': self.structure_str,
                 'foreground_activity': self.foreground_activity,
                 'activity_stack': self.activity_stack,
                 'background_services': self.background_services,
                 'width': self.width,
                 'height': self.height,
                 'views': self.views}
        return state

    def to_json(self):
        """
        将设备状态转换为JSON字符串
        
        返回:
        - str: JSON格式的状态信息
        """
        import json
        return json.dumps(self.to_dict(), indent=2)

    def __parse_views(self, raw_views):
        """
        解析原始视图数据
        
        参数:
        - raw_views: 从UI dump获取的原始视图列表
        
        返回:
        - list: 处理后的视图列表
        """
        views = []
        if not raw_views or len(raw_views) == 0:
            return views

        for view_dict in raw_views:
            # # 简化resource_id（注释掉的代码）
            # resource_id = view_dict['resource_id']
            # if resource_id is not None and ":" in resource_id:
            #     resource_id = resource_id[(resource_id.find(":") + 1):]
            #     view_dict['resource_id'] = resource_id
            views.append(view_dict)
        return views

    def __assemble_view_tree(self, root_view, views):
        """
        递归组装视图树结构
        
        参数:
        - root_view: 当前根视图
        - views: 所有视图列表
        """
        if not len(self.view_tree): # 初始引导
            self.view_tree = copy.deepcopy(views[0])
            self.__assemble_view_tree(self.view_tree, views)
        else:
            children = list(enumerate(root_view["children"]))
            if not len(children):
                return
            for i, j in children:
                root_view["children"][i] = copy.deepcopy(self.views[j])
                self.__assemble_view_tree(root_view["children"][i], views)

    def __generate_view_strs(self):
        """
        为所有视图生成字符串标识符
        
        遍历所有视图，为每个视图调用__get_view_str方法生成唯一标识符
        可选地也可以生成视图结构信息（当前被注释）
        """
        for view_dict in self.views:
            self.__get_view_str(view_dict)
            # self.__get_view_structure(view_dict)

    @staticmethod
    def __calculate_depth(views):
        """
        计算视图树中所有视图的深度
        
        找到根视图（父视图为-1），然后递归为所有视图分配深度值
        
        参数:
        - views: 视图列表
        """
        root_view = None
        for view in views:
            if DeviceState.__safe_dict_get(view, 'parent') == -1:
                root_view = view
                break
        DeviceState.__assign_depth(views, root_view, 0)

    @staticmethod
    def __assign_depth(views, view_dict, depth):
        """
        递归为视图及其所有子视图分配深度值
        
        参数:
        - views: 视图列表
        - view_dict: 当前视图字典
        - depth: 当前深度值
        """
        view_dict['depth'] = depth
        for view_id in DeviceState.__safe_dict_get(view_dict, 'children', []):
            DeviceState.__assign_depth(views, views[view_id], depth + 1)

    def __get_state_str(self):
        """
        生成状态字符串的MD5哈希值
        
        返回:
        - str: 状态字符串的MD5哈希
        """
        state_str_raw = self.__get_state_str_raw()
        return md5(state_str_raw)

    def __get_state_str_raw(self):
        """
        生成原始状态字符串
        
        如果配置了humanoid服务，使用远程服务渲染视图树；
        否则使用本地算法生成基于视图签名的状态字符串
        
        返回:
        - str: 原始状态字符串
        """
        if self.device.humanoid is not None:
            import json
            from xmlrpc.client import ServerProxy
            proxy = ServerProxy("http://%s/" % self.device.humanoid)
            return proxy.render_view_tree(json.dumps({
                "view_tree": self.view_tree,
                "screen_res": [self.device.display_info["width"],
                               self.device.display_info["height"]]
            }))
        else:
            view_signatures = set()
            for view in self.views:
                view_signature = DeviceState.__get_view_signature(view)
                if view_signature:
                    view_signatures.add(view_signature)
            return "%s{%s}" % (self.foreground_activity, ",".join(sorted(view_signatures)))

    def __get_content_free_state_str(self):
        """
        生成内容无关的状态字符串哈希
        
        与__get_state_str类似，但使用内容无关的视图签名，
        忽略文本内容等可变信息，只关注视图结构
        
        返回:
        - str: 内容无关状态字符串的MD5哈希
        """
        if self.device.humanoid is not None:
            import json
            from xmlrpc.client import ServerProxy
            proxy = ServerProxy("http://%s/" % self.device.humanoid)
            state_str = proxy.render_content_free_view_tree(json.dumps({
                "view_tree": self.view_tree,
                "screen_res": [self.device.display_info["width"],
                               self.device.display_info["height"]]
            }))
        else:
            view_signatures = set()
            for view in self.views:
                view_signature = DeviceState.__get_content_free_view_signature(view)
                if view_signature:
                    view_signatures.add(view_signature)
            state_str = "%s{%s}" % (self.foreground_activity, ",".join(sorted(view_signatures)))
        import hashlib
        return hashlib.md5(state_str.encode('utf-8')).hexdigest()

    def __get_search_content(self):
        """
        生成用于状态搜索的文本内容
        
        组合所有视图的resource_id和text属性，用于全文搜索
        
        返回:
        - str: 搜索内容文本
        """
        words = [",".join(self.__get_property_from_all_views("resource_id")),
                 ",".join(self.__get_property_from_all_views("text"))]
        return "\n".join(words)

    def __get_property_from_all_views(self, property_name):
        """
        从所有视图中获取指定属性的值集合
        
        参数:
        - property_name: 属性名称
        
        返回:
        - set: 属性值的集合
        """
        property_values = set()
        for view in self.views:
            property_value = DeviceState.__safe_dict_get(view, property_name, None)
            if property_value:
                property_values.add(property_value)
        return property_values

    def save2dir(self, output_dir=None, event=None):
        """
        将设备状态保存到指定目录
        
        保存状态JSON文件和截图，并更新报告文件
        
        参数:
        - output_dir: 输出目录，默认为设备输出目录下的states子目录
        - event: 关联的事件对象，用于在截图上绘制事件标记
        """
        try:
            if output_dir is None:
                if self.device.output_dir is None:
                    return
                else:
                    output_dir = os.path.join(self.device.output_dir, "states")
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)
                
            json_dir = os.path.join(self.device.output_dir, "report_screenshot.json")
            dest_state_json_path = "%s/state_%s.json" % (output_dir, self.tag)
            if self.device.adapters[self.device.minicap]:
                dest_screenshot_path = "%s/screen_%s.jpg" % (output_dir, self.tag)
            else:
                dest_screenshot_path = "%s/screen_%s.png" % (output_dir, self.tag)

            try:
                with open(json_dir, 'r') as json_file:
                    report_screens = json.load(json_file)
            except FileNotFoundError:
                report_screens = []
            
            if self.screenshot_path != dest_screenshot_path:
                state_json_file = open(dest_state_json_path, "w")
                state_json_file.write(self.to_json())
                state_json_file.close()
                import shutil

                shutil.copyfile(self.screenshot_path, dest_screenshot_path)
                report_screen = {
                        "event": "",
                        "event_index": str(self.tag),
                        "screen_shoot": "screen_" + str(self.tag) + ".png"
                    }
                report_screens.append(report_screen)

            if event is not None:
                self.draw_event(event, dest_screenshot_path)
                report_screens[-1]["event"] = event.get_event_name()
            with open(json_dir, 'w') as json_file:
                json.dump(report_screens, json_file, indent=4)
            self.screenshot_path = dest_screenshot_path
            # from PIL.Image import Image
            # if isinstance(self.screenshot_path, Image):
            #     self.screenshot_path.save(dest_screenshot_path)
        except Exception as e:
            self.device.logger.warning(e)
    
    def draw_event(self, event, screenshot_path):
        """
        在截图上绘制事件标记
        
        根据事件类型在对应位置绘制不同颜色的矩形框或文本
        
        参数:
        - event: 事件对象
        - screenshot_path: 截图文件路径
        """
        import cv2
        image = cv2.imread(screenshot_path)
        if event is not None and screenshot_path is not None:
            if isinstance(event, TouchEvent):
                # 红色矩形框表示点击事件
                cv2.rectangle(image, (int(event.view['bounds'][0][0]),int(event.view['bounds'][0][1])),(int(event.view['bounds'][1][0]),int(event.view['bounds'][1][1])), (0, 0, 255), 5)
            elif isinstance(event, LongTouchEvent):
                # 绿色矩形框表示长按事件
                cv2.rectangle(image, (int(event.view['bounds'][0][0]),int(event.view['bounds'][0][1])),(int(event.view['bounds'][1][0]),int(event.view['bounds'][1][1])), (0, 255, 0), 5)
            elif isinstance(event, SetTextEvent):
                # 蓝色矩形框表示文本输入事件
                cv2.rectangle(image, (int(event.view['bounds'][0][0]),int(event.view['bounds'][0][1])),(int(event.view['bounds'][1][0]),int(event.view['bounds'][1][1])), (255, 0, 0), 5)
            elif isinstance(event, ScrollEvent):
                # 黄色矩形框表示滚动事件
                cv2.rectangle(image, (int(event.view['bounds'][0][0]),int(event.view['bounds'][0][1])),(int(event.view['bounds'][1][0]),int(event.view['bounds'][1][1])), (255, 255, 0), 5)
            elif isinstance(event, KeyEvent):
                # 在指定位置绘制按键名称
                cv2.putText(image,event.name, (100,300), cv2.FONT_HERSHEY_SIMPLEX, 5,(0, 255, 0), 3, cv2.LINE_AA)
            else:
                return
            try:
                cv2.imwrite(screenshot_path, image)
            except Exception as e:
                self.logger.warning(e)

    def get_state_screen(self): 
        """
        获取当前状态的截图文件路径
        
        返回:
        - str: 截图文件路径
        """
        return self.screenshot_path

    def save_view_img(self, view_dict, output_dir=None):
        try:
            if output_dir is None:
                if self.device.output_dir is None:
                    return
                else:
                    output_dir = os.path.join(self.device.output_dir, "views")
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)
            view_str = view_dict['view_str']
            if self.device.adapters[self.device.minicap]:
                view_file_path = "%s/view_%s.jpg" % (output_dir, view_str)
            else:
                view_file_path = "%s/view_%s.png" % (output_dir, view_str)
            if os.path.exists(view_file_path):
                return
            from PIL import Image
            # Load the original image:
            view_bound = view_dict['bounds']
            original_img = Image.open(self.screenshot_path)
            # view bound should be in original image bound
            view_img = original_img.crop((min(original_img.width - 1, max(0, view_bound[0][0])),
                                          min(original_img.height - 1, max(0, view_bound[0][1])),
                                          min(original_img.width, max(0, view_bound[1][0])),
                                          min(original_img.height, max(0, view_bound[1][1]))))
            view_img.convert("RGB").save(view_file_path)
        except Exception as e:
            self.device.logger.warning(e)

    def is_different_from(self, another_state):
        """
        比较当前状态与另一个状态是否不同
        
        通过比较状态字符串的MD5哈希来判断状态是否相同。
        状态字符串包含了前台活动名称和所有视图的签名信息。
        
        参数:
        - another_state: 另一个DeviceState对象
        
        返回:
        - boolean: True表示状态不同，False表示状态相同
        """
        return self.state_str != another_state.state_str

    @staticmethod
    def __get_view_signature(view_dict):
        """
        获取视图的签名字符串
        
        签名包含视图的类名、资源ID、文本内容以及状态属性（启用、选中、选择状态）
        用于生成唯一标识视图的字符串
        
        参数:
        - view_dict: 视图字典，DeviceState.views列表中的元素
        
        返回:
        - str: 视图签名字符串
        """
        if 'signature' in view_dict:
            return view_dict['signature']

        view_text = DeviceState.__safe_dict_get(view_dict, 'text', "None")
        if view_text is None or len(view_text) > 50:
            view_text = "None"

        signature = "[class]%s[resource_id]%s[text]%s[%s,%s,%s]" % \
                    (DeviceState.__safe_dict_get(view_dict, 'class', "None"),
                     DeviceState.__safe_dict_get(view_dict, 'resource_id', "None"),
                     view_text,
                     DeviceState.__key_if_true(view_dict, 'enabled'),
                     DeviceState.__key_if_true(view_dict, 'checked'),
                     DeviceState.__key_if_true(view_dict, 'selected'))
        view_dict['signature'] = signature
        return signature

    @staticmethod
    def __get_content_free_view_signature(view_dict):
        """
        获取内容无关的视图签名
        
        与普通签名不同，内容无关签名只包含视图的类名和资源ID，
        忽略文本内容等可变信息，用于检测UI结构变化而非内容变化
        
        参数:
        - view_dict: 视图字典，DeviceState.views列表中的元素
        
        返回:
        - str: 内容无关的视图签名字符串
        """
        if 'content_free_signature' in view_dict:
            return view_dict['content_free_signature']
        content_free_signature = "[class]%s[resource_id]%s" % \
                                 (DeviceState.__safe_dict_get(view_dict, 'class', "None"),
                                  DeviceState.__safe_dict_get(view_dict, 'resource_id', "None"))
        view_dict['content_free_signature'] = content_free_signature
        return content_free_signature

    def __get_view_str(self, view_dict):
        """
        生成视图的唯一标识字符串
        
        组合当前活动、视图自身签名、所有祖先签名和所有子视图签名，
        然后计算MD5哈希值作为视图的唯一标识符
        
        参数:
        - view_dict: 视图字典，DeviceState.views列表中的元素
        
        返回:
        - str: 视图的MD5哈希标识字符串
        """
        if 'view_str' in view_dict:
            return view_dict['view_str']
        view_signature = DeviceState.__get_view_signature(view_dict)
        parent_strs = []
        for parent_id in self.get_all_ancestors(view_dict):
            parent_strs.append(DeviceState.__get_view_signature(self.views[parent_id]))
        parent_strs.reverse()
        child_strs = []
        for child_id in self.get_all_children(view_dict):
            child_strs.append(DeviceState.__get_view_signature(self.views[child_id]))
        child_strs.sort()
        view_str = "Activity:%s\nSelf:%s\nParents:%s\nChildren:%s" % \
                   (self.foreground_activity, view_signature, "//".join(parent_strs), "||".join(child_strs))
        import hashlib
        view_str = hashlib.md5(view_str.encode('utf-8')).hexdigest()
        view_dict['view_str'] = view_str
        return view_str

    def __get_view_structure(self, view_dict):
        """
        获取视图的树形结构表示
        
        递归构建视图的层次结构，包含类名、尺寸和子视图的相对位置信息
        
        参数:
        - view_dict: 视图字典，DeviceState.views列表中的元素
        
        返回:
        - dict: 表示视图结构的字典，格式为{类名(宽*高): {子视图相对位置: 子视图结构}}
        """
        if 'view_structure' in view_dict:
            return view_dict['view_structure']
        width = DeviceState.get_view_width(view_dict)
        height = DeviceState.get_view_height(view_dict)
        class_name = DeviceState.__safe_dict_get(view_dict, 'class', "None")
        children = {}

        root_x = view_dict['bounds'][0][0]
        root_y = view_dict['bounds'][0][1]

        child_view_ids = self.__safe_dict_get(view_dict, 'children')
        if child_view_ids:
            for child_view_id in child_view_ids:
                child_view = self.views[child_view_id]
                child_x = child_view['bounds'][0][0]
                child_y = child_view['bounds'][0][1]
                relative_x, relative_y = child_x - root_x, child_y - root_y
                children["(%d,%d)" % (relative_x, relative_y)] = self.__get_view_structure(child_view)

        view_structure = {
            "%s(%d*%d)" % (class_name, width, height): children
        }
        view_dict['view_structure'] = view_structure
        return view_structure

    @staticmethod
    def __key_if_true(view_dict, key):
        """
        如果视图字典中指定键存在且为真值，返回键名，否则返回空字符串
        
        用于生成视图签名时标记布尔属性
        
        参数:
        - view_dict: 视图字典
        - key: 要检查的键名
        
        返回:
        - str: 键名或空字符串
        """
        return key if (key in view_dict and view_dict[key]) else ""

    @staticmethod
    def __safe_dict_get(view_dict, key, default=None):
        """
        安全地从字典中获取值，避免KeyError异常
        
        参数:
        - view_dict: 要查询的字典
        - key: 键名
        - default: 默认值，当键不存在时返回
        
        返回:
        - 键对应的值或默认值
        """
        return view_dict[key] if (key in view_dict) else default

    @staticmethod
    def get_view_center(view_dict):
        """
        计算视图的中心点坐标
        
        参数:
        - view_dict: 视图字典，DeviceState.views列表中的元素
        
        返回:
        - tuple: (x, y)坐标对，表示视图中心点
        """
        bounds = view_dict['bounds']
        return (bounds[0][0] + bounds[1][0]) / 2, (bounds[0][1] + bounds[1][1]) / 2

    @staticmethod
    def get_view_width(view_dict):
        """
        计算视图的宽度
        
        参数:
        - view_dict: 视图字典，DeviceState.views列表中的元素
        
        返回:
        - int: 视图宽度（像素）
        """
        bounds = view_dict['bounds']
        return int(math.fabs(bounds[0][0] - bounds[1][0]))

    @staticmethod
    def get_view_height(view_dict):
        """
        计算视图的高度
        
        参数:
        - view_dict: 视图字典，DeviceState.views列表中的元素
        
        返回:
        - int: 视图高度（像素）
        """
        bounds = view_dict['bounds']
        return int(math.fabs(bounds[0][1] - bounds[1][1]))

    def get_all_ancestors(self, view_dict):
        """
        获取指定视图的所有祖先视图ID
        
        递归查找视图的父视图，直到根视图
        
        参数:
        - view_dict: 视图字典，DeviceState.views列表中的元素
        
        返回:
        - list: 祖先视图ID列表，从直接父视图到根视图
        """
        result = []
        parent_id = self.__safe_dict_get(view_dict, 'parent', -1)
        if 0 <= parent_id < len(self.views):
            result.append(parent_id)
            result += self.get_all_ancestors(self.views[parent_id])
        return result

    def get_all_children(self, view_dict):
        """
        获取指定视图的所有子视图ID（包括子孙视图）
        
        递归查找视图的所有子视图和孙子视图
        
        参数:
        - view_dict: 视图字典，DeviceState.views列表中的元素
        
        返回:
        - set: 所有子视图ID的集合
        """
        children = self.__safe_dict_get(view_dict, 'children')
        if not children:
            return set()
        children = set(children)
        for child in children:
            children_of_child = self.get_all_children(self.views[child])
            children.union(children_of_child)
        return children

    def get_app_activity_depth(self, app):
        """
        获取应用活动在活动栈中的深度
        
        深度从0开始计数，0表示前台活动，数值越大表示在栈中越深
        
        参数:
        - app: App对象，包含包名信息
        
        返回:
        - int: 活动深度，-1表示未找到该应用的活动
        """
        depth = 0
        for activity_str in self.activity_stack:
            if app.package_name in activity_str:
                return depth
            depth += 1
        return -1

    def get_possible_input(self):
        """
        获取当前状态下可能的输入事件列表
        
        根据视图的可交互属性（可点击、可滚动、可勾选、可长按、可编辑等）
        生成对应的输入事件，用于自动化测试的探索策略
        
        返回:
        - list: InputEvent对象列表
        """
        if self.possible_events:
            return [] + self.possible_events
        possible_events = []
        enabled_view_ids = []
        touch_exclude_view_ids = set()
        for view_dict in self.views:
            # 排除导航栏和状态栏背景视图
            if self.__safe_dict_get(view_dict, 'enabled') and \
                    self.__safe_dict_get(view_dict, 'visible') and \
                    self.__safe_dict_get(view_dict, 'resource_id') not in \
               ['android:id/navigationBarBackground',
                'android:id/statusBarBackground']:
                enabled_view_ids.append(view_dict['temp_id'])
        # enabled_view_ids.reverse()

        # 处理可点击视图
        for view_id in enabled_view_ids:
            if self.__safe_dict_get(self.views[view_id], 'clickable'):
                possible_events.append(TouchEvent(view=self.views[view_id]))
                touch_exclude_view_ids.add(view_id)
                touch_exclude_view_ids.union(self.get_all_children(self.views[view_id]))

        # 处理可滚动视图
        for view_id in enabled_view_ids:
            if self.__safe_dict_get(self.views[view_id], 'scrollable'):
                possible_events.append(ScrollEvent(view=self.views[view_id], direction="UP"))
                possible_events.append(ScrollEvent(view=self.views[view_id], direction="DOWN"))
                possible_events.append(ScrollEvent(view=self.views[view_id], direction="LEFT"))
                possible_events.append(ScrollEvent(view=self.views[view_id], direction="RIGHT"))

        # 处理可勾选视图
        for view_id in enabled_view_ids:
            if self.__safe_dict_get(self.views[view_id], 'checkable'):
                possible_events.append(TouchEvent(view=self.views[view_id]))
                touch_exclude_view_ids.add(view_id)
                touch_exclude_view_ids.union(self.get_all_children(self.views[view_id]))

        # 处理可长按视图
        for view_id in enabled_view_ids:
            if self.__safe_dict_get(self.views[view_id], 'long_clickable'):
                possible_events.append(LongTouchEvent(view=self.views[view_id]))

        # 处理可编辑视图
        for view_id in enabled_view_ids:
            if self.__safe_dict_get(self.views[view_id], 'editable'):
                possible_events.append(SetTextEvent(view=self.views[view_id], text="HelloWorld"))
                touch_exclude_view_ids.add(view_id)
                # TODO figure out what event can be sent to editable views
                pass

        # 注释掉的代码：处理非交互容器的点击事件
        # for view_id in enabled_view_ids:
        #     if view_id in touch_exclude_view_ids:
        #         continue
        #     children = self.__safe_dict_get(self.views[view_id], 'children')
        #     if children and len(children) > 0:
        #         continue
        #     possible_events.append(TouchEvent(view=self.views[view_id]))

        # 注释掉的代码：旧版Android导航栏菜单键
        # possible_events.append(KeyEvent(name="MENU"))

        self.possible_events = possible_events
        return [] + possible_events
    
    def _get_self_ancestors_property(self, view, key, default=None):
        """
        获取视图及其所有祖先视图的指定属性值
        
        从当前视图开始，向上查找祖先视图，直到找到第一个非空属性值
        
        参数:
        - view: 当前视图字典
        - key: 要查找的属性键名
        - default: 默认值，当所有视图中都找不到该属性时返回
        
        返回:
        - 属性值或默认值
        """
        all_views = [view] + [self.views[i] for i in self.get_all_ancestors(view)]
        for v in all_views:
            value = self.__safe_dict_get(v, key)
            if value:
                return value
        return default
    
    def get_described_actions(self):
        """
        获取当前状态的文本描述和可用动作列表
        
        生成人类可读的UI状态描述，包含所有可交互视图及其对应的操作选项
        
        返回:
        - tuple: (状态描述文本, 可用动作列表)
        """
        enabled_view_ids = []
        for view_dict in self.views:
            # 排除导航栏和状态栏背景视图
            if self.__safe_dict_get(view_dict, 'visible') and \
                self.__safe_dict_get(view_dict, 'resource_id') not in \
               ['android:id/navigationBarBackground',
                'android:id/statusBarBackground']:
                enabled_view_ids.append(view_dict['temp_id'])

        view_descs = []
        available_actions = []
        for view_id in enabled_view_ids:
            view = self.views[view_id]
            clickable = self._get_self_ancestors_property(view, 'clickable')
            scrollable = self.__safe_dict_get(view, 'scrollable')
            checkable = self._get_self_ancestors_property(view, 'checkable')
            long_clickable = self._get_self_ancestors_property(view, 'long_clickable')
            editable = self.__safe_dict_get(view, 'editable')
            actionable = clickable or scrollable or checkable or long_clickable or editable
            checked = self.__safe_dict_get(view, 'checked')
            selected = self.__safe_dict_get(view, 'selected')
            content_description = self.__safe_dict_get(view, 'content_description', default='')
            view_text = self.__safe_dict_get(view, 'text', default='')
            if not content_description and not view_text and not scrollable:  # actionable?
                continue
            
            view_status = ''
            if editable:
                view_status += 'editable '
            if checked or selected:
                view_status += 'checked '
            view_desc = f'- a {view_status}view'
            if content_description:
                content_description = content_description.replace('\n', '  ')
                content_description = f'{content_description[:20]}...' if len(content_description) > 20 else content_description
                view_desc += f' "{content_description}"'
            if view_text:
                view_text = view_text.replace('\n', '  ')
                view_text = f'{view_text[:20]}...' if len(view_text) > 20 else view_text
                view_desc += f' with text "{view_text}"'
            if actionable:
                view_actions = []
                if editable:
                    view_actions.append(f'edit ({len(available_actions)})')
                    available_actions.append(SetTextEvent(view=view, text='HelloWorld'))
                if clickable or checkable:
                    view_actions.append(f'click ({len(available_actions)})')
                    available_actions.append(TouchEvent(view=view))
                # if checkable:
                #     view_actions.append(f'check/uncheck ({len(available_actions)})')
                #     available_actions.append(TouchEvent(view=view))
                # if long_clickable:
                #     view_actions.append(f'long click ({len(available_actions)})')
                #     available_actions.append(LongTouchEvent(view=view))
                if scrollable:
                    view_actions.append(f'scroll up ({len(available_actions)})')
                    available_actions.append(ScrollEvent(view=view, direction='UP'))
                    view_actions.append(f'scroll down ({len(available_actions)})')
                    available_actions.append(ScrollEvent(view=view, direction='DOWN'))
                view_actions_str = ', '.join(view_actions)
                view_desc += f' that can {view_actions_str}'
            view_descs.append(view_desc)
        view_descs.append(f'- a key to go back ({len(available_actions)})')
        available_actions.append(KeyEvent(name='BACK'))
        state_desc = 'The current state has the following UI views and corresponding actions, with action id in parentheses:\n '
        state_desc += ';\n '.join(view_descs)
        return state_desc, available_actions
    
    def get_view_description(self, view):
        """
        获取视图的文本描述
        
        生成人类可读的视图描述，包含内容描述、文本内容和可滚动属性
        
        参数:
        - view: 视图字典
        
        返回:
        - str: 视图描述文本
        """
        content_description = self.__safe_dict_get(view, 'content_description', default='')
        view_text = self.__safe_dict_get(view, 'text', default='')
        scrollable = self.__safe_dict_get(view, 'scrollable')
        view_desc = 'view'
        if scrollable:
            view_desc = 'scrollable view'
        if content_description:
            view_desc += f' "{content_description}"'
        if view_text:
            view_text = view_text.replace('\n', '  ')
            view_text = f'{view_text[:20]}...' if len(view_text) > 20 else view_text
            view_desc += f' with text "{view_text}"'
        return view_desc
    
    def get_action_description(self, action):
        """
        获取动作的文本描述
        
        根据动作类型生成对应的描述文本
        
        参数:
        - action: 输入事件对象
        
        返回:
        - str: 动作描述文本
        """
        desc = action.event_type
        if isinstance(action, KeyEvent):
            desc = f'- go {action.name.lower()}'
        if isinstance(action, UIEvent):
            action_name = action.event_type
            if isinstance(action, LongTouchEvent):
                action_name = 'long click'
            elif isinstance(action, SetTextEvent):
                action_name = f'enter "{action.text}" into'
            elif isinstance(action, ScrollEvent):
                action_name = f'scroll {action.direction.lower()}'
            desc = f'- {action_name} {self.get_view_description(action.view)}'
        return desc

