from pathlib import Path
import json

from ..utils import getLogger

logger = getLogger(__name__)


class WidgetCoverage:
    def __init__(self, output_dir):
        self.output_dir = output_dir
        self.steps_log = Path(output_dir) / "steps.log"
    
    def generate_coverage_report(self):
        logger.info("Generating widget coverage report...")
        if not self.steps_log.exists():
            raise FileNotFoundError(f"Steps log file not found: {self.steps_log}")
        
        triggered_widgets = self._analyze_steps()

        with open(Path(self.output_dir) / "widget_coverage_report.txt", "w", encoding="utf-8") as f:
            for widget in triggered_widgets:
                f.write(f"{widget}\n")
        
    def _analyze_steps(self):
        triggered_widgets = set()
        
        with open(self.steps_log, "r", encoding="utf-8") as f:
            for line in f:
                data = json.loads(line)
                if not data.get("Type", "") == "Monkey":
                    continue
                activity = data.get("Activity", "")
                if not activity:
                    logger.debug(f"Steps {data['MonkeyStepsCount']} has no activity, skip")
                act_info = json.loads(data["Info"])
                if act_info.get("act") == "BACK":
                    resource_id = "KEY_BACK"
                    description = "KEY_BACK"
                else:
                    act_widget = json.loads(act_info["widget"])
                    resource_id = act_widget.get("resource-id", "")
                    description = act_widget.get("content-desc", "")
                if not all((resource_id, description)):
                    logger.debug(f"""Steps {data["MonkeyStepsCount"]} has no resourceId or content-desc, skip""")
                    continue
                    
                widget_repr = f"activity:{activity}|resourceId:{resource_id}|content-desc:{description}"
                triggered_widgets.add(widget_repr)
        return triggered_widgets

if __name__ == "__main__":
    w = WidgetCoverage("/Users/atria/Desktop/coding/Kea2/output/res_2026010916_2221776159/output_2026010916_2221776159")
    w.generate_coverage_report()