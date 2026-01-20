from pathlib import Path
import json
from typing import Set

from ..utils import getLogger

logger = getLogger(__name__)


RECORD_PERIOD = 25


class WidgetCoverage:
    def __init__(self, output_dir):
        self.output_dir = output_dir
        self.steps_log = Path(output_dir) / "steps.log"
    
    def generate_coverage_report(self):
        logger.info("Generating widget coverage report...")
        if not self.steps_log.exists():
            raise FileNotFoundError(f"Steps log file not found: {self.steps_log}")
        
        triggered_widgets = self._analyze_steps()
        self.__dump_triggered_widgets(triggered_widgets)


    
    def __dump_triggered_widgets(self, triggered_widgets: Set, stepsCount: int = None):
        file_name = f"widget_coverage_report_on_step{stepsCount}.txt" if stepsCount else "widget_coverage_report.txt"
        output_file = Path(self.output_dir) / file_name
        with open(output_file, "w", encoding="utf-8") as f:
            for widget in triggered_widgets:
                f.write(f"{widget}\n")
        
    def _analyze_steps(self):
        triggered_widgets = set()
        
        with open(self.steps_log, "r", encoding="utf-8") as f:
            for line in f:
                data = json.loads(line)
                if not data.get("Type", "") == "Monkey":
                    continue

                widget_repr = self.__get_widget_repr(data)
                triggered_widgets.add(widget_repr)

                stepsCount = int(data['MonkeyStepsCount'])
                if stepsCount % RECORD_PERIOD == 0:
                    self.__dump_triggered_widgets(triggered_widgets, stepsCount) 
                

        return triggered_widgets
    
    def __get_widget_repr(self, data):
        activity = data.get("Activity", "")
        if not activity:
            return ""
        act_info = json.loads(data["Info"])
        if act_info.get("act") == "BACK":
            resource_id = "KEY_BACK"
            description = "KEY_BACK"
            className = "KEY_BACK"
        else:
            act_widget = json.loads(act_info["widget"])
            resource_id = act_widget.get("resource-id", "")
            description = act_widget.get("content-desc", "")
            className = act_widget.get("class", "")
        if not any((resource_id, description, className)):
            return ""
            
        widget_repr = f"activity:{activity}|class:{className}|resourceId:{resource_id}|content-desc:{description}|"
        return widget_repr


if __name__ == "__main__":
    w = WidgetCoverage("/Users/atria/Desktop/coding/Kea2/output/res_2026011916_0842195130/output_2026011916_0842195130")
    w.generate_coverage_report()