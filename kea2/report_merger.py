import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
from collections import defaultdict

from kea2.utils import getLogger

logger = getLogger(__name__)


class TestReportMerger:
    """
    Merge multiple test result directories into a single combined dataset
    Only processes result_*.json and coverage.log files for the simplified template
    """
    
    def __init__(self):
        self.merged_data = {}
        self.result_dirs = []
        
    def merge_reports(self, result_paths: List[Union[str, Path]], output_dir: Optional[Union[str, Path]] = None) -> Path:
        """
        Merge multiple test result directories
        
        Args:
            result_paths: List of paths to test result directories (res_* directories)
            output_dir: Output directory for merged data (optional)
            
        Returns:
            Path to the merged data directory
        """
        try:
            # Convert paths and validate
            self.result_dirs = [Path(p).resolve() for p in result_paths]
            self._validate_result_dirs()
            
            # Setup output directory
            timestamp = datetime.now().strftime("%Y%m%d%H_%M%S")
            if output_dir is None:
                output_dir = Path.cwd() / f"merged_report_{timestamp}"
            else:
                output_dir = Path(output_dir).resolve() / f"merged_report_{timestamp}"
            
            output_dir.mkdir(parents=True, exist_ok=True)
            
            logger.debug(f"Merging {len(self.result_dirs)} test result directories...")
            
            # Merge different types of data
            merged_property_stats, property_source_mapping = self._merge_property_results()
            merged_coverage_data = self._merge_coverage_data()
            merged_crash_anr_data = self._merge_crash_dump_data()

            # Calculate final statistics
            final_data = self._calculate_final_statistics(merged_property_stats, merged_coverage_data, merged_crash_anr_data, property_source_mapping)
            
            # Add merge information to final data
            final_data['merge_info'] = {
                'merge_timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'source_count': len(self.result_dirs),
                'source_directories': [str(Path(d).name) for d in self.result_dirs]
            }

            # Generate HTML report (now includes merge info)
            report_file = self._generate_html_report(final_data, output_dir)
            
            logger.debug(f"Reports generated successfully in: {output_dir}")
            return output_dir
            
        except Exception as e:
            logger.error(f"Error merging test reports: {e}")
            raise
    
    def _validate_result_dirs(self):
        """Validate that all result directories exist and contain required files"""
        for result_dir in self.result_dirs:
            if not result_dir.exists():
                raise FileNotFoundError(f"Result directory does not exist: {result_dir}")
            
            # Check for required files pattern
            result_files = list(result_dir.glob("result_*.json"))
            if not result_files:
                raise FileNotFoundError(f"No result_*.json file found in: {result_dir}")
            
            logger.debug(f"Validated result directory: {result_dir}")
    
    def _merge_property_results(self) -> Tuple[Dict[str, Dict], Dict[str, List[Dict]]]:
        """
        Merge property test results from all directories

        Returns:
            Tuple of (merged_property_results, property_source_mapping)
            - merged_property_results: Merged property execution results
            - property_source_mapping: Maps property names to list of source directory info with fail/error
              Each entry contains: {'dir_name': str, 'report_path': str}
        """
        merged_results = defaultdict(lambda: {
            "precond_satisfied": 0,
            "executed": 0,
            "fail": 0,
            "error": 0
        })

        # Track which directories have fail/error for each property
        property_source_mapping = defaultdict(list)

        for result_dir in self.result_dirs:
            result_files = list(result_dir.glob("result_*.json"))
            if not result_files:
                logger.warning(f"No result file found in {result_dir}")
                continue

            result_file = result_files[0]  # Take the first (should be only one)
            dir_name = result_dir.name  # Get the directory name (e.g., res_2025072011_5048015228)

            # Find the HTML report file in the result directory
            html_report_path = None
            # First try to find HTML files directly in the result directory
            html_files = list(result_dir.glob("*.html"))
            if html_files:
                # Use absolute file:// URL for direct access
                html_report_path = f"file://{html_files[0].resolve()}"
            else:
                # Fallback: try to find in output_* subdirectories
                output_dirs = list(result_dir.glob("output_*"))
                if output_dirs:
                    html_files = list(output_dirs[0].glob("*.html"))
                    if html_files:
                        # Use absolute file:// URL for direct access
                        html_report_path = f"file://{html_files[0].resolve()}"

            try:
                with open(result_file, 'r', encoding='utf-8') as f:
                    test_results = json.load(f)

                # Merge results for each property
                for prop_name, prop_result in test_results.items():
                    for key in ["precond_satisfied", "executed", "fail", "error"]:
                        merged_results[prop_name][key] += prop_result.get(key, 0)

                    # Track source directories for properties with fail/error
                    if prop_result.get('fail', 0) > 0 or prop_result.get('error', 0) > 0:
                        # Check if this directory is already in the mapping
                        existing_dirs = [item['dir_name'] for item in property_source_mapping[prop_name]]
                        if dir_name not in existing_dirs:
                            property_source_mapping[prop_name].append({
                                'dir_name': dir_name,
                                'report_path': html_report_path
                            })

                logger.debug(f"Merged results from: {result_file}")

            except Exception as e:
                logger.error(f"Error reading result file {result_file}: {e}")
                continue

        return dict(merged_results), dict(property_source_mapping)
    
    def _merge_coverage_data(self) -> Dict:
        """
        Merge coverage data from all directories
        
        Returns:
            Final merged coverage information
        """
        all_activities = set()
        tested_activities = set()
        activity_counts = defaultdict(int)
        total_steps = 0
        
        for result_dir in self.result_dirs:
            # Find coverage log file
            output_dirs = list(result_dir.glob("output_*"))
            if not output_dirs:
                logger.warning(f"No output directory found in {result_dir}")
                continue
                
            coverage_file = output_dirs[0] / "coverage.log"
            if not coverage_file.exists():
                logger.warning(f"No coverage.log found in {output_dirs[0]}")
                continue
            
            try:
                # Read the last line of coverage.log to get final state
                last_coverage = None
                with open(coverage_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.strip():
                            last_coverage = json.loads(line)
                
                if last_coverage:
                    # Collect all activities
                    all_activities.update(last_coverage.get("totalActivities", []))
                    tested_activities.update(last_coverage.get("testedActivities", []))
                    
                    # Update activity counts (take maximum)
                    for activity, count in last_coverage.get("activityCountHistory", {}).items():
                        activity_counts[activity] += count
                    
                    # Add steps count
                    total_steps += last_coverage.get("stepsCount", 0)
                
                logger.debug(f"Merged coverage data from: {coverage_file}")
                
            except Exception as e:
                logger.error(f"Error reading coverage file {coverage_file}: {e}")
                continue
        
        # Calculate final coverage percentage (rounded to 2 decimal places)
        coverage_percent = round((len(tested_activities) / len(all_activities) * 100), 2) if all_activities else 0.00
        
        return {
            "coverage_percent": coverage_percent,
            "total_activities": list(all_activities),
            "tested_activities": list(tested_activities),
            "total_activities_count": len(all_activities),
            "tested_activities_count": len(tested_activities),
            "activity_count_history": dict(activity_counts),
            "total_steps": total_steps
        }

    def _merge_crash_dump_data(self) -> Dict:
        """
        Merge crash and ANR data from all directories

        Returns:
            Dict containing merged crash and ANR events
        """
        all_crash_events = []
        all_anr_events = []

        for result_dir in self.result_dirs:
            # Find crash dump log file
            output_dirs = list(result_dir.glob("output_*"))
            if not output_dirs:
                logger.warning(f"No output directory found in {result_dir}")
                continue

            crash_dump_file = output_dirs[0] / "crash-dump.log"
            if not crash_dump_file.exists():
                logger.debug(f"No crash-dump.log found in {output_dirs[0]}")
                continue

            try:
                # Parse crash and ANR events from this file
                crash_events, anr_events = self._parse_crash_dump_file(crash_dump_file)
                all_crash_events.extend(crash_events)
                all_anr_events.extend(anr_events)

                logger.debug(f"Merged {len(crash_events)} crash events and {len(anr_events)} ANR events from: {crash_dump_file}")

            except Exception as e:
                logger.error(f"Error reading crash dump file {crash_dump_file}: {e}")
                continue

        # Deduplicate events based on content and timestamp
        unique_crash_events = self._deduplicate_crash_events(all_crash_events)
        unique_anr_events = self._deduplicate_anr_events(all_anr_events)

        logger.debug(f"Total unique crash events: {len(unique_crash_events)}, ANR events: {len(unique_anr_events)}")

        return {
            "crash_events": unique_crash_events,
            "anr_events": unique_anr_events,
            "total_crash_count": len(unique_crash_events),
            "total_anr_count": len(unique_anr_events)
        }
    
    def _parse_crash_dump_file(self, crash_dump_file: Path) -> Tuple[List[Dict], List[Dict]]:
        """
        Parse crash and ANR events from crash-dump.log file

        Args:
            crash_dump_file: Path to crash-dump.log file

        Returns:
            tuple: (crash_events, anr_events) - Lists of crash and ANR event dictionaries
        """
        crash_events = []
        anr_events = []

        try:
            with open(crash_dump_file, "r", encoding="utf-8") as f:
                content = f.read()

            # Parse crash events
            crash_events = self._parse_crash_events(content)

            # Parse ANR events
            anr_events = self._parse_anr_events(content)

        except Exception as e:
            logger.error(f"Error parsing crash dump file {crash_dump_file}: {e}")

        return crash_events, anr_events

    def _parse_crash_events(self, content: str) -> List[Dict]:
        """
        Parse crash events from crash-dump.log content

        Args:
            content: Content of crash-dump.log file

        Returns:
            List[Dict]: List of crash event dictionaries
        """
        crash_events = []

        # Pattern to match crash blocks
        crash_pattern = r'(\d{14})\ncrash:\n(.*?)\n// crash end'

        for match in re.finditer(crash_pattern, content, re.DOTALL):
            timestamp_str = match.group(1)
            crash_content = match.group(2)

            # Parse timestamp (format: YYYYMMDDHHMMSS)
            try:
                timestamp = datetime.strptime(timestamp_str, "%Y%m%d%H%M%S")
                formatted_time = timestamp.strftime("%Y-%m-%d %H:%M:%S")
            except ValueError:
                formatted_time = timestamp_str

            # Extract crash information
            crash_info = self._extract_crash_info(crash_content)

            crash_event = {
                "time": formatted_time,
                "exception_type": crash_info.get("exception_type", "Unknown"),
                "process": crash_info.get("process", "Unknown"),
                "stack_trace": crash_info.get("stack_trace", "")
            }

            crash_events.append(crash_event)

        return crash_events

    def _parse_anr_events(self, content: str) -> List[Dict]:
        """
        Parse ANR events from crash-dump.log content

        Args:
            content: Content of crash-dump.log file

        Returns:
            List[Dict]: List of ANR event dictionaries
        """
        anr_events = []

        # Pattern to match ANR blocks
        anr_pattern = r'(\d{14})\nanr:\n(.*?)\nanr end'

        for match in re.finditer(anr_pattern, content, re.DOTALL):
            timestamp_str = match.group(1)
            anr_content = match.group(2)

            # Parse timestamp (format: YYYYMMDDHHMMSS)
            try:
                timestamp = datetime.strptime(timestamp_str, "%Y%m%d%H%M%S")
                formatted_time = timestamp.strftime("%Y-%m-%d %H:%M:%S")
            except ValueError:
                formatted_time = timestamp_str

            # Extract ANR information
            anr_info = self._extract_anr_info(anr_content)

            anr_event = {
                "time": formatted_time,
                "reason": anr_info.get("reason", "Unknown"),
                "process": anr_info.get("process", "Unknown"),
                "trace": anr_info.get("trace", "")
            }

            anr_events.append(anr_event)

        return anr_events

    def _extract_crash_info(self, crash_content: str) -> Dict:
        """
        Extract crash information from crash content

        Args:
            crash_content: Content of a single crash block

        Returns:
            Dict: Extracted crash information
        """
        crash_info = {
            "exception_type": "Unknown",
            "process": "Unknown",
            "stack_trace": ""
        }

        lines = crash_content.strip().split('\n')

        for line in lines:
            line = line.strip()

            # Extract PID from CRASH line
            if line.startswith("// CRASH:"):
                # Pattern: // CRASH: process_name (pid xxxx) (dump time: ...)
                pid_match = re.search(r'\(pid\s+(\d+)\)', line)
                if pid_match:
                    crash_info["process"] = pid_match.group(1)

            # Extract exception type from Long Msg line
            elif line.startswith("// Long Msg:"):
                # Pattern: // Long Msg: ExceptionType: message
                exception_match = re.search(r'// Long Msg:\s+([^:]+)', line)
                if exception_match:
                    crash_info["exception_type"] = exception_match.group(1).strip()

        # Extract full stack trace (all lines starting with //)
        stack_lines = []
        for line in lines:
            if line.startswith("//"):
                # Remove the "// " prefix for cleaner display
                clean_line = line[3:] if line.startswith("// ") else line[2:]
                stack_lines.append(clean_line)

        crash_info["stack_trace"] = '\n'.join(stack_lines)

        return crash_info

    def _extract_anr_info(self, anr_content: str) -> Dict:
        """
        Extract ANR information from ANR content

        Args:
            anr_content: Content of a single ANR block

        Returns:
            Dict: Extracted ANR information
        """
        anr_info = {
            "reason": "Unknown",
            "process": "Unknown",
            "trace": ""
        }

        lines = anr_content.strip().split('\n')

        for line in lines:
            line = line.strip()

            # Extract PID from ANR line
            if line.startswith("// ANR:"):
                # Pattern: // ANR: process_name (pid xxxx) (dump time: ...)
                pid_match = re.search(r'\(pid\s+(\d+)\)', line)
                if pid_match:
                    anr_info["process"] = pid_match.group(1)

            # Extract reason from Reason line
            elif line.startswith("Reason:"):
                # Pattern: Reason: Input dispatching timed out (...)
                reason_match = re.search(r'Reason:\s+(.+)', line)
                if reason_match:
                    full_reason = reason_match.group(1).strip()
                    # Simplify the reason by extracting the main part before parentheses
                    simplified_reason = self._simplify_anr_reason(full_reason)
                    anr_info["reason"] = simplified_reason

        # Store the full ANR trace content
        anr_info["trace"] = anr_content

        return anr_info

    def _simplify_anr_reason(self, full_reason: str) -> str:
        """
        Simplify ANR reason by extracting the main part

        Args:
            full_reason: Full ANR reason string

        Returns:
            str: Simplified ANR reason
        """
        # Common ANR reason patterns to simplify
        simplification_patterns = [
            # Input dispatching timed out (details...) -> Input dispatching timed out
            (r'^(Input dispatching timed out)\s*\(.*\).*$', r'\1'),
            # Broadcast of Intent (details...) -> Broadcast timeout
            (r'^Broadcast of Intent.*$', 'Broadcast timeout'),
            # Service timeout -> Service timeout
            (r'^Service.*timeout.*$', 'Service timeout'),
            # ContentProvider timeout -> ContentProvider timeout
            (r'^ContentProvider.*timeout.*$', 'ContentProvider timeout'),
        ]

        # Apply simplification patterns
        for pattern, replacement in simplification_patterns:
            match = re.match(pattern, full_reason, re.IGNORECASE)
            if match:
                if callable(replacement):
                    return replacement(match)
                elif '\\1' in replacement:
                    return re.sub(pattern, replacement, full_reason, flags=re.IGNORECASE)
                else:
                    return replacement

        # If no pattern matches, try to extract the part before the first parenthesis
        paren_match = re.match(r'^([^(]+)', full_reason)
        if paren_match:
            simplified = paren_match.group(1).strip()
            # Remove trailing punctuation
            simplified = re.sub(r'[.,;:]+$', '', simplified)
            return simplified

        # If all else fails, return the original but truncated
        return full_reason[:50] + "..." if len(full_reason) > 50 else full_reason

    def _deduplicate_crash_events(self, crash_events: List[Dict]) -> List[Dict]:
        """
        Deduplicate crash events based on exception type and stack trace

        Args:
            crash_events: List of crash events

        Returns:
            List[Dict]: Deduplicated crash events
        """
        seen_crashes = set()
        unique_crashes = []

        for crash in crash_events:
            # Create a hash key based on exception type and first few lines of stack trace
            exception_type = crash.get("exception_type", "")
            stack_trace = crash.get("stack_trace", "")

            # Use first 3 lines of stack trace for deduplication
            stack_lines = stack_trace.split('\n')[:3]
            crash_key = (exception_type, '\n'.join(stack_lines))

            if crash_key not in seen_crashes:
                seen_crashes.add(crash_key)
                unique_crashes.append(crash)

        return unique_crashes

    def _deduplicate_anr_events(self, anr_events: List[Dict]) -> List[Dict]:
        """
        Deduplicate ANR events based on reason and process

        Args:
            anr_events: List of ANR events

        Returns:
            List[Dict]: Deduplicated ANR events
        """
        seen_anrs = set()
        unique_anrs = []

        for anr in anr_events:
            # Create a hash key based on reason and process
            reason = anr.get("reason", "")
            process = anr.get("process", "")
            anr_key = (reason, process)

            if anr_key not in seen_anrs:
                seen_anrs.add(anr_key)
                unique_anrs.append(anr)

        return unique_anrs

    def _calculate_final_statistics(self, property_stats: Dict, coverage_data: Dict, crash_anr_data: Dict = None, property_source_mapping: Dict = None) -> Dict:
        """
        Calculate final statistics for template rendering

        Note: Total bugs count only includes property test failures/errors,
        not crashes or ANRs (which are tracked separately)

        Args:
            property_stats: Merged property statistics
            coverage_data: Merged coverage data
            crash_anr_data: Merged crash and ANR data (optional)
            property_source_mapping: Maps property names to source directories with fail/error (optional)

        Returns:
            Complete data for template rendering
        """
        # Calculate bug count from property failures
        property_bugs_found = sum(1 for result in property_stats.values()
                                if result.get('fail', 0) > 0 or result.get('error', 0) > 0)

        # Calculate property counts
        all_properties_count = len(property_stats)
        executed_properties_count = sum(1 for result in property_stats.values()
                                      if result.get('executed', 0) > 0)

        # Initialize crash/ANR data
        crash_events = []
        anr_events = []
        total_crash_count = 0
        total_anr_count = 0

        if crash_anr_data:
            crash_events = crash_anr_data.get('crash_events', [])
            anr_events = crash_anr_data.get('anr_events', [])
            total_crash_count = crash_anr_data.get('total_crash_count', 0)
            total_anr_count = crash_anr_data.get('total_anr_count', 0)

        # Calculate total bugs found (only property bugs, not including crashes/ANRs)
        total_bugs_found = property_bugs_found

        # Prepare final data
        final_data = {
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'bugs_found': total_bugs_found,
            'property_bugs_found': property_bugs_found,
            'all_properties_count': all_properties_count,
            'executed_properties_count': executed_properties_count,
            'property_stats': property_stats,
            'property_source_mapping': property_source_mapping or {},
            'crash_events': crash_events,
            'anr_events': anr_events,
            'total_crash_count': total_crash_count,
            'total_anr_count': total_anr_count,
            **coverage_data  # Include all coverage data
        }

        return final_data
    
    def get_merge_summary(self) -> Dict:
        """
        Get summary of the merge operation
        
        Returns:
            Dictionary containing merge summary information
        """
        if not self.result_dirs:
            return {}
        
        return {
            "merged_directories": len(self.result_dirs),
            "source_paths": [str(p) for p in self.result_dirs],
            "merge_timestamp": datetime.now().isoformat()
        }

    def _generate_html_report(self, data: Dict, output_dir: Path) -> str:
        """
        Generate HTML report using the merged template

        Args:
            data: Final merged data
            output_dir: Output directory

        Returns:
            Path to the generated HTML report
        """
        try:
            from jinja2 import Environment, FileSystemLoader, PackageLoader, select_autoescape

            # Set up Jinja2 environment
            try:
                jinja_env = Environment(
                    loader=PackageLoader("kea2", "templates"),
                    autoescape=select_autoescape(['html', 'xml'])
                )
            except (ImportError, ValueError):
                # Fallback to file system loader
                current_dir = Path(__file__).parent
                templates_dir = current_dir / "templates"

                jinja_env = Environment(
                    loader=FileSystemLoader(templates_dir),
                    autoescape=select_autoescape(['html', 'xml'])
                )

            # Render template
            template = jinja_env.get_template("merged_bug_report_template.html")
            html_content = template.render(**data)

            # Save HTML report
            report_file = output_dir / "merged_report.html"
            with open(report_file, 'w', encoding='utf-8') as f:
                f.write(html_content)

            logger.debug(f"HTML report generated: {report_file}")
            return str(report_file)

        except Exception as e:
            logger.error(f"Error generating HTML report: {e}")
            raise



