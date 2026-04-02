import sys
import json
import re
import logging
import random
from abc import abstractmethod


from .input_event import *
from .utg import UTG

# 最大重启次数限制
MAX_NUM_RESTARTS = 5
# 应用外最大步数限制（正常返回和强制杀死应用）
MAX_NUM_STEPS_OUTSIDE = 5
MAX_NUM_STEPS_OUTSIDE_KILL = 10
# 最大重试次数
MAX_REPLY_TRIES = 5
# 最大LLM查询次数
MAX_NUM_QUERY_LLM = 15

# 输入事件标志位
EVENT_FLAG_STARTED = "+started"      # 已开始
EVENT_FLAG_START_APP = "+start_app"  # 启动应用
EVENT_FLAG_STOP_APP = "+stop_app"    # 停止应用
EVENT_FLAG_EXPLORE = "+explore"      # 探索模式
EVENT_FLAG_NAVIGATE = "+navigate"    # 导航模式
EVENT_FLAG_TOUCH = "+touch"          # 触摸事件

# 策略分类
POLICY_NAIVE_DFS = "dfs_naive"       # 朴素深度优先搜索
POLICY_GREEDY_DFS = "dfs_greedy"     # 贪心深度优先搜索
POLICY_NAIVE_BFS = "bfs_naive"       # 朴素广度优先搜索
POLICY_GREEDY_BFS = "bfs_greedy"     # 贪心广度优先搜索
POLICY_REPLAY = "replay"             # 重放策略
POLICY_MANUAL = "manual"             # 手动策略
POLICY_MONKEY = "monkey"             # 猴子策略（随机）
POLICY_TASK = "task"                 # 任务策略
POLICY_NONE = "none"                 # 无策略
POLICY_HYBIRD = "hybird"             # 混合策略
POLICY_RANDOM = "random"             # 随机策略


class InputInterruptedException(Exception):
    """输入中断异常类"""
    pass


class InputPolicy(object):
    """
    输入策略基类
    负责生成事件来刺激应用行为，应该持续调用AppEventManager.send_event方法
    """

    def __init__(self, device, app):
        """
        初始化输入策略
        
        Args:
            device: 设备对象
            app: 应用对象
        """
        self.logger = logging.getLogger(self.__class__.__name__)
        self.device = device
        self.app = app
        self.action_count = 0          # 动作计数器
        self.master = None             # 主策略引用
        self.last_event = None         # 上一个事件
        self.last_state = None         # 上一个状态
        self.current_state = None      # 当前状态
        self.__action_history=[]       # 动作历史记录
        self.__activity_history= set() # 活动历史记录
        self.__all_action_history=set()# 所有动作历史记录
        self.llm_event = []            # LLM生成的事件记录
        self.reuse_event = []          # 重用的事件记录

    def start(self, input_manager):
        """
        开始产生事件
        
        Args:
            input_manager: InputManager实例
        """
        tarpit_name = None
        while input_manager.enabled and self.action_count < input_manager.event_count:
            try:
                self.current_state = self.device.get_current_state(self.action_count)
                # 确保第一个事件是回到HOME屏幕
                # 第二个事件是启动应用
                if self.action_count == 0 and self.master is None:
                    event = KeyEvent(name="HOME")
                elif self.action_count == 1 and self.master is None:
                    event = IntentEvent(self.app.get_start_intent())    
                else:
                    if input_manager.sim_calculator.detected_ui_tarpit(input_manager):
                        # 如果检测到UI陷阱，停止随机策略，启动LLM策略
                        current_state_screen = self.current_state.get_state_screen()
                        is_known_tarpit, tarpit_name = input_manager.sim_calculator.check_or_add_new_trap(current_state_screen,self.action_count)
                        if is_known_tarpit:
                            # 如果是已知的UI陷阱，随机选择LLM策略或重用策略
                            if random.random() < 0.5:
                                tarpit_actions = input_manager.sim_calculator.get_tarpit_actions_by_name(tarpit_name)
                                if len(tarpit_actions) > 0:
                                    self.execute_tarpit_actions(tarpit_actions,input_manager,self.llm_event,self.reuse_event)
                                    continue
                        if input_manager.sim_calculator.sim_count > MAX_NUM_QUERY_LLM:
                            # 如果LLM查询次数过多，返回
                            self.logger.info(f'query too much. go back!')
                            event = KeyEvent(name="BACK")
                            self.clear_action_history()
                            input_manager.sim_calculator.sim_count = 0
                        else:
                            llm_policy = HybirdPolicy(self.device,self.app,input_manager.random_input,self.action_count, self.__activity_history, self.__action_history,self.current_state)
                            event = llm_policy.generate_event()
                            self.llm_event.append(int(self.action_count)) 
                        input_manager.sim_calculator.update_tarpit_actions(tarpit_name,event)
                    else:
                        tarpit_name = None
                        event = self.generate_event()
                self.last_event = event
                self.last_state = self.current_state
                self.__activity_history.add(self.current_state.foreground_activity)
                self.current_state.save2dir(input_manager.img_output, event)
                # 执行事件
                input_manager.add_event(event)
                # if tarpit_name and not input_manager.sim_calculator.is_similar_page(input_manager,self.device.get_current_state()):
                #     # 执行事件后，如果进入不同的UI页面，则添加有效的陷阱动作
                #     input_manager.sim_calculator.update_tarpit_actions(tarpit_name,event)
                self.action_count += 1
            except KeyboardInterrupt:
                break
            except InputInterruptedException as e:
                self.logger.warning("stop sending events: %s" % e)
                break
            except AttributeError as e:
                self.logger.error("AttributeError: %s" % e)
                continue  # 处理属性错误
            except Exception as e:
                self.logger.warning("exception during sending events: %s" % e)
                import traceback
                traceback.print_exc()
                continue

    def get_last_state(self):
        """获取上一个状态"""
        return self.last_state  
    
    def get_current_state(self):
        """获取当前状态"""
        return self.current_state
    
    def clear_action_history(self):
        """清空动作历史"""
        self.__action_history = []
    
    # def __update_utg(self):
    #     self.utg.add_transition(self.last_event, self.last_state, self.current_state) 

    def execute_tarpit_actions(self, actions, input_manager, llm_event, reuse_event):
        """
        执行UI陷阱动作
        
        Args:
            actions: 动作列表
            input_manager: 输入管理器
            llm_event: LLM事件列表
            reuse_event: 重用事件列表
        """
        self.logger.info('executing reuse actions...')
        for event in actions:
            self.current_state = self.device.get_current_state(self.action_count)
            self.last_state = self.current_state
            self.last_event = event
            self.reuse_event.append(int(self.action_count)) 
            self.current_state.save2dir(input_manager.img_output, event)
            input_manager.add_event(event)
            self.action_count += 1
            if not input_manager.sim_calculator.detected_ui_tarpit(input_manager):
                # 如果逃出当前陷阱，跳过
                break
        self.logger.info('ending reuse actions...')

    @abstractmethod
    def generate_event(self):
        """
        生成一个事件（抽象方法）
        
        Returns:
            InputEvent: 输入事件
        """
        pass


class HybirdPolicy(InputPolicy):
    """混合策略类，结合LLM和随机策略"""
    
    def __init__(self, device, app, random_input, action_count, activity_history, action_history,current_state):
        """
        初始化混合策略
        
        Args:
            device: 设备对象
            app: 应用对象
            random_input: 是否启用随机输入
            action_count: 动作计数
            activity_history: 活动历史
            action_history: 动作历史
            current_state: 当前状态
        """
        super(HybirdPolicy, self).__init__(device, app)
        self.logger = logging.getLogger(self.__class__.__name__)
        self.task = "You are an expert in App GUI testing. Please guide the testing tool to enhance the coverage of functional scenarios in testing the App based on your extensive App testing experience. "
        self.random_input = random_input
        self.__nav_target = None           # 导航目标
        self.__nav_num_steps = -1          # 导航步数
        self.__num_restarts = 0            # 重启次数
        self.__num_steps_outside = 0        # 应用外步数
        self.__event_trace = ""            # 事件轨迹
        self.__missed_states = set()       # 错过的状态
        self.__random_explore = random_input  # 随机探索标志
        self.__action_history=action_history  # 动作历史
        self.__all_action_history=set()    # 所有动作历史
        self.__activity_history = activity_history  # 活动历史
        self.action_count = action_count   # 动作计数
        self.current_state = current_state  # 当前状态

    def generate_event(self):
        """
        生成一个事件
        
        Returns:
            InputEvent: 输入事件
        """

        # 获取当前设备状态
        # self.current_state = self.device.get_current_state(self.action_count)
        if self.current_state is None:
            import time
            time.sleep(5)
            return KeyEvent(name="BACK")

        event = self.generate_event_based_on_utg()

        self.last_state = self.current_state
        self.last_event = event
        return event

    def generate_event_based_on_utg(self):
        """
        基于当前UTG生成事件
        
        Returns:
            InputEvent: 输入事件
        """
        current_state = self.current_state
        self.logger.info("Current state: %s" % current_state.state_str)
        if current_state.state_str in self.__missed_states:
            self.__missed_states.remove(current_state.state_str)

        if current_state.get_app_activity_depth(self.app) < 0:
            # 如果应用不在活动栈中
            start_app_intent = self.app.get_start_intent()

            # 应用似乎卡在某个状态，可能的情况：
            # 1) 强制停止 (START, STOP)
            #    通过增加self.__num_restarts来重新启动应用
            # 2) 至少启动过一次但无法启动 (START)
            #    传递给viewclient处理这种情况
            # 3) 正常情况
            #    正常启动，清除self.__num_restarts

            if self.__event_trace.endswith(EVENT_FLAG_START_APP + EVENT_FLAG_STOP_APP) \
                    or self.__event_trace.endswith(EVENT_FLAG_START_APP):
                self.__num_restarts += 1
                self.logger.info("The app had been restarted %d times.", self.__num_restarts)
            else:
                self.__num_restarts = 0

            # 传递 (START) 事件
            if not self.__event_trace.endswith(EVENT_FLAG_START_APP):
                if self.__num_restarts > MAX_NUM_RESTARTS:
                    # 如果应用重启次数过多，进入随机模式
                    msg = "The app had been restarted too many times. Entering random mode."
                    self.logger.info(msg)
                    self.__random_explore = True
                else:
                    # 启动应用
                    self.__event_trace += EVENT_FLAG_START_APP
                    self.logger.info("Trying to start the app...")
                    self.__action_history = [f'- start the app {self.app.app_name}']
                    return IntentEvent(intent=start_app_intent)

        elif current_state.get_app_activity_depth(self.app) > 0:
            # 如果应用在活动栈中但不在前台
            self.__num_steps_outside += 1

            if self.__num_steps_outside > MAX_NUM_STEPS_OUTSIDE:
                # 如果应用长时间不在前台，尝试返回
                if self.__num_steps_outside > MAX_NUM_STEPS_OUTSIDE_KILL:
                    stop_app_intent = self.app.get_stop_intent()
                    go_back_event = IntentEvent(stop_app_intent)
                else:
                    go_back_event = KeyEvent(name="BACK")
                self.__event_trace += EVENT_FLAG_NAVIGATE
                self.logger.info("Going back to the app...")
                self.__action_history.append('- go back')
                return go_back_event
        else:
            # 如果应用在前台
            self.__num_steps_outside = 0

        action, candidate_actions, action_id = self._get_action_with_LLM(current_state, self.__action_history,self.__activity_history,self.__all_action_history)
        if action is not None:
            action_str = f"{current_state.get_action_desc(action)} ({action_id})"
            self.__action_history.append(action_str)
            self.__all_action_history.add(action_str)
            return action

        if self.__random_explore:
            self.logger.info("Trying random event...")
            action = random.choice(candidate_actions)
            self.__action_history.append(current_state.get_action_desc(action))
            self.__all_action_history.add(current_state.get_action_desc(action))
            return action

        # 如果找不到探索目标，停止应用
        stop_app_intent = self.app.get_stop_intent()
        self.logger.info("Cannot find an exploration target. Trying to restart app...")
        self.__action_history.append('- stop the app')
        self.__all_action_history.add('- stop the app')
        self.__event_trace += EVENT_FLAG_STOP_APP
        return IntentEvent(intent=stop_app_intent)
        
    def _query_llm(self, prompt, model_name='gpt-3.5-turbo'):
        """
        查询LLM获取响应
        
        Args:
            prompt: 提示词
            model_name: 模型名称
            
        Returns:
            str: LLM响应内容
        """
        # TODO: 替换为您自己的LLM
        from openai import OpenAI
        gpt_url = ''
        gpt_key = ''
        client = OpenAI(
            base_url=gpt_url,
            api_key=gpt_key
        )

        messages=[{"role": "user", "content": prompt}]
        completion = client.chat.completions.create(
            messages=messages,
            model=model_name,
            timeout=30
        )
        res = completion.choices[0].message.content
        return res

    def _get_action_with_LLM(self, current_state, action_history,activity_history,all_action_history):
        """
        使用LLM获取下一个动作
        
        Args:
            current_state: 当前状态
            action_history: 动作历史
            activity_history: 活动历史
            all_action_history: 所有动作历史
            
        Returns:
            tuple: (选择的动作, 候选动作列表, 动作ID)
        """
        activity = current_state.foreground_activity
        task_prompt = self.task +f"Currently, the App is stuck on the {activity} page, unable to explore more features. You task is to select an action based on the current GUI Infomation to perform next and help the app escape the UI tarpit."
        # visisted_page_prompt = f'I have already visited the following activities: \n' + '\n'.join(activity_history)
        # all_history_prompt = f'I have already completed the following actions to explore the app: \n' + '\n'.join(all_action_history)
        history_prompt = f'I have already tried the following steps with action id in parentheses which should not be selected anymore: \n ' + ';\n '.join(action_history)
        state_prompt, candidate_actions = current_state.get_described_actions()
        question = 'Which action should I choose next? Just return the action id and nothing else.\nIf no more action is needed, return -1.'
        prompt = f'{task_prompt}\n{state_prompt}\n{history_prompt}\n{question}'
        print(prompt)
        response = self._query_llm(prompt)
        print(f'response: {response}')
        # if '-1' in response:
            # input(f"Seems the task is completed. Press Enter to continue...")

        match = re.search(r'\d+', response)
        if not match:
            return None, candidate_actions
        idx = int(match.group(0))
        selected_action = candidate_actions[idx]
        if isinstance(selected_action, SetTextEvent):
            view_text = current_state.get_view_desc(selected_action.view)
            question = f'What text should I enter to the {view_text}? Just return the text and nothing else.'
            prompt = f'{task_prompt}\n{state_prompt}\n{question}'
            print(prompt)
            response = self._query_llm(prompt)
            print(f'response: {response}')
            selected_action.text = response.replace('"', '')
            if len(selected_action.text) > 30:  # 启发式地禁用长文本输入
                selected_action.text = ''
        return selected_action, candidate_actions ,idx

    
class UtgRandomPolicy(InputPolicy):
    """
    基于UTG的随机输入策略
    """

    def __init__(self, device, app, random_input=True, number_of_events_that_restart_app=100, clear_and_restart_app_data_after_100_events=False):
        """
        初始化随机策略
        
        Args:
            device: 设备对象
            app: 应用对象
            random_input: 是否启用随机输入
            number_of_events_that_restart_app: 重启应用的事件数阈值
            clear_and_restart_app_data_after_100_events: 是否在100个事件后清除并重启应用数据
        """
        super(UtgRandomPolicy, self).__init__(
            device, app
        )
        self.number_of_events_that_restart_app = number_of_events_that_restart_app
        self.clear_and_restart_app_data_after_100_events = clear_and_restart_app_data_after_100_events
        self.logger = logging.getLogger(self.__class__.__name__)
        self.random_input = random_input
        self.preferred_buttons = [
            "yes",
            "ok",
            "activate",
            "detail",
            "more",
            "access",
            "allow",
            "check",
            "agree",
            "try",
            "go",
            "next",
        ]
        self.__num_restarts = 0
        self.__num_steps_outside = 0
        self.__event_trace = ""
        self.__missed_states = set()
        self.number_of_steps_outside_the_shortest_path = 0
        self.reached_state_on_the_shortest_path = []
        self.last_rotate_events = KEY_RotateDeviceNeutralEvent

    def get_action_history(self):
        """获取动作历史"""
        return self.__action_history

    def get_all_action_history(self):
        """获取所有动作历史"""
        return self.__all_action_history

    def get_activity_history(self):
        """获取活动历史"""
        return self.__activity_history

    def generate_event(self):
        """
        生成一个事件
        
        Returns:
            InputEvent: 输入事件
        """
        
        # 获取当前设备状态
        # self.current_state = self.device.get_current_state(self.action_count)
        if self.current_state is None:
            import time
            time.sleep(5)
            return KeyEvent(name="BACK")

        # self.__update_utg()
        event = None

        if self.action_count % self.number_of_events_that_restart_app == 0 and self.clear_and_restart_app_data_after_100_events:
            self.logger.info("clear and restart app after %s events" % self.number_of_events_that_restart_app)
            return ReInstallAppEvent(self.app)

        if event is None:
            event = self.generate_event_based_on_utg()
        
        if isinstance(event, RotateDevice):
            if self.last_rotate_events == KEY_RotateDeviceNeutralEvent:
                self.last_rotate_events = KEY_RotateDeviceRightEvent
                event = RotateDeviceRightEvent()
            else:
                self.last_rotate_events = KEY_RotateDeviceNeutralEvent
                event = RotateDeviceNeutralEvent()

        self.last_state = self.current_state
        self.last_event = event
        return event
    
    def generate_event_based_on_utg(self):
        """
        基于当前UTG生成事件
        
        Returns:
            InputEvent: 输入事件
        """
        current_state = self.current_state
        self.logger.info("Current state: %s" % current_state.state_str)
        if current_state.state_str in self.__missed_states:
            self.__missed_states.remove(current_state.state_str)

        if current_state.get_app_activity_depth(self.app) < 0:
            # 如果应用不在活动栈中
            start_app_intent = self.app.get_start_intent()

            # 应用似乎卡在某个状态，可能的情况：
            # 1) 强制停止 (START, STOP)
            #    通过增加self.__num_restarts来重新启动应用
            # 2) 至少启动过一次但无法启动 (START)
            #    传递给viewclient处理这种情况
            # 3) 正常情况
            #    正常启动，清除self.__num_restarts

            if self.__event_trace.endswith(
                EVENT_FLAG_START_APP + EVENT_FLAG_STOP_APP
            ) or self.__event_trace.endswith(EVENT_FLAG_START_APP):
                self.__num_restarts += 1
                self.logger.info(
                    "The app had been restarted %d times.", self.__num_restarts
                )
            else:
                self.__num_restarts = 0

            # 传递 (START) 事件
            if not self.__event_trace.endswith(EVENT_FLAG_START_APP):
                if self.__num_restarts > MAX_NUM_RESTARTS:
                    # 如果应用重启次数过多，进入随机模式
                    msg = "The app had been restarted too many times. Entering random mode."
                    self.logger.info(msg)
                else:
                    # 启动应用
                    self.__event_trace += EVENT_FLAG_START_APP
                    self.logger.info("Trying to start the app...")
                    return IntentEvent(intent=start_app_intent)

        elif current_state.get_app_activity_depth(self.app) > 0:
            # 如果应用在活动栈中但不在前台
            self.__num_steps_outside += 1

            if self.__num_steps_outside > MAX_NUM_STEPS_OUTSIDE:
                # 如果应用长时间不在前台，尝试返回
                if self.__num_steps_outside > MAX_NUM_STEPS_OUTSIDE_KILL:
                    stop_app_intent = self.app.get_stop_intent()
                    go_back_event = IntentEvent(stop_app_intent)
                else:
                    go_back_event = KeyEvent(name="BACK")
                self.__event_trace += EVENT_FLAG_NAVIGATE
                self.logger.info("Going back to the app...")
                return go_back_event
        else:
            # 如果应用在前台
            self.__num_steps_outside = 0

        possible_events = current_state.get_possible_input()

        if self.random_input:
            random.shuffle(possible_events)
        possible_events.append(KeyEvent(name="BACK"))
        possible_events.append(RotateDevice())

        self.__event_trace += EVENT_FLAG_EXPLORE
        event = random.choice(possible_events)
        return event


