"""
tarpit_advisor.py
为每个检测到的 UI Tarpit 调用 DeepSeek API，生成 Kea2 脚本编写建议。
"""

import requests
from ..utils import getLogger

logger = getLogger(__name__)

DEEPSEEK_API_URL = "https://api.deepseek.com/chat/completions"
DEEPSEEK_MODEL = "deepseek-chat"

SYSTEM_PROMPT = """\
You are an expert in Android UI testing, specializing in the Kea2 automated testing framework.
Kea2 supports writing small Python scripts to guide random testing (Fastbot) out of difficult UI states.

A Kea2 script consists of:
1. @precondition(lambda self: ...) — when to activate the script (check for unique UI elements)
2. @prob(0.5) — probability of activation (optional, default 1.0)
3. def test_<name>(self): — the interaction steps to execute

UI selectors available (via self.d):
- self.d(text="...").click()
- self.d(description="...").click()
- self.d(resourceId="...").click()
- self.d(text="...").exists  (for precondition checks)

Example script:
    @prob(0.5)
    @precondition(lambda self: self.d(text="Settings").exists)
    def test_goBack(self):
        self.d.press("back")

Keep suggestions concise and practical. Output in English.
"""


def _build_prompt(package_name: str, trap_name: str, trigger_count: int,
                  event_times: list, sim_k: int, ui_hierarchy: str = "") -> str:
    times_str = "\n".join(f"  - {t}" for t in event_times) if event_times else "  - (no timestamp available)"

    # 构建UI层级信息部分
    if ui_hierarchy:
        hierarchy_section = f"""
The following is the UI hierarchy (XML) of the screen when this tarpit was detected.
Use the actual resource IDs, text labels, and content descriptions from this hierarchy
to write precise @precondition checks and interaction steps.

```xml
{ui_hierarchy}
```
"""
    else:
        hierarchy_section = """
No UI hierarchy data is available for this tarpit. Please suggest generic escape strategies
and use placeholder identifiers that the tester should replace.
"""

    return f"""\
A UI Tarpit has been detected during automated testing of the Android app `{package_name}`.

Tarpit details:
- Trap ID: {trap_name}
- Total triggers: {trigger_count}
- sim_k (consecutive similar frames to declare tarpit): {sim_k}
- Occurrence times:
{times_str}

This tarpit means the UI stopped changing for {sim_k} or more consecutive testing steps,
indicating the random testing tool got stuck on a static or looping screen.
{hierarchy_section}
Please do the following:
1. Briefly explain what kind of UI state likely caused this tarpit (e.g., a dialog, a loading screen, a dead-end page).
2. Suggest a Kea2 script snippet that could help the tester escape this tarpit.
   - Use @precondition to detect the stuck state (use the actual UI element identifiers from the hierarchy above if available).
   - Use interaction steps such as pressing back, dismissing dialogs, or navigating away.
   - Add a comment explaining what the tester needs to customize (e.g., replace placeholder widget identifiers).

Be concise. The script snippet should be minimal and directly usable as a starting point.
"""


def generate_tarpit_advice(ui_tarpit_data: dict, package_name: str, api_key: str) -> dict:
    """
    为 ui_tarpit_data 中每个唯一的 tarpit 生成 DeepSeek 建议。

    Args:
        ui_tarpit_data: save_report() 生成的完整 tarpit 报告字典
        package_name:   被测应用包名
        api_key:        DeepSeek API Key

    Returns:
        dict: {trap_name: advice_str}，调用失败时对应值为错误提示字符串
    """
    if not ui_tarpit_data or not ui_tarpit_data.get("tarpits"):
        return {}

    tarpits = ui_tarpit_data.get("tarpits", [])
    events = ui_tarpit_data.get("events", [])
    sim_k = ui_tarpit_data.get("sim_k", 5)

    # 按 tarpit_name 归集触发时间
    times_by_trap: dict = {t["name"]: [] for t in tarpits}
    for ev in events:
        name = ev.get("tarpit_name", "")
        if name in times_by_trap:
            raw_time = ev.get("time", "")
            times_by_trap[name].append(raw_time[:19].replace("T", " ") if raw_time else "")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    advice_map: dict = {}
    for trap in tarpits:
        trap_name = trap["name"]
        trigger_count = trap.get("count", 1)
        event_times = times_by_trap.get(trap_name, [])
        ui_hierarchy = trap.get("ui_hierarchy", "")

        prompt = _build_prompt(package_name, trap_name, trigger_count, event_times, sim_k, ui_hierarchy)

        logger.debug(f"[TarpitAdvisor] {trap_name} 完整Prompt:")
        print(f"\n{'='*60}")
        print(f"[TarpitAdvisor] {trap_name} 发送给模型的完整Prompt：")
        print(f"{'='*60}")
        print(prompt)
        print(f"{'='*60}\n")

        payload = {
            "model": DEEPSEEK_MODEL,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            "max_tokens": 1200,
            "temperature": 0.3,
        }

        try:
            logger.info(f"[TarpitAdvisor] 正在为 {trap_name} 请求 DeepSeek 建议...")
            resp = requests.post(DEEPSEEK_API_URL, headers=headers, json=payload, timeout=60)
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"]
            advice_map[trap_name] = content.strip()
            logger.info(f"[TarpitAdvisor] {trap_name} 建议获取成功")
            print(f"\n{'='*60}")
            print(f"[TarpitAdvisor] {trap_name} AI 建议内容：")
            print(f"{'='*60}")
            print(content.strip())
            print(f"{'='*60}\n")
        except requests.exceptions.Timeout:
            logger.warning(f"[TarpitAdvisor] {trap_name} 请求超时")
            advice_map[trap_name] = "⚠️ Request timed out. Please retry or check your network."
        except Exception as e:
            logger.warning(f"[TarpitAdvisor] {trap_name} 请求失败: {e}")
            advice_map[trap_name] = f"⚠️ Failed to get advice: {e}"

    return advice_map
