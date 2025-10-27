from typing import Optional, List, Callable, Any, Union, Dict
import unittest
from pathlib import Path
import sys
import threading
from kea2 import KeaTestRunner, Options, precondition, prob, max_tries
from .u2Driver import U2Driver
from .utils import getLogger, TimeStamp
from .adbUtils import ADBDevice
import time
logger = getLogger(__name__)

class Kea2Tester:
    """
    Kea2 property tester
    
    This class allows users to directly launch Kea2 property tests in existing test scripts.
    """
    
    def __init__(self):
        self.options: Optional[Options] = None
        self.properties: List[unittest.TestCase] = []
        
    def configure(
        self,
        package_name: Union[str, List[str]],
        serial: Optional[str] = None,
        transport_id: Optional[str] = None,
        running_minutes: int = 10,
        max_step: Optional[int] = None,
        throttle: int = 200,
        output_dir: str = "output",
        take_screenshots: bool = False,
        **kwargs
    ):
        """
        Configure Kea2 property test parameters
        Args:
            package_name: Target application package name (string or list)
            serial: Device serial number
            transport_id: Device transport_id
            running_minutes: Running duration (minutes)
            max_step: Maximum number of steps
            throttle: Event interval (milliseconds)
            output_dir: Output directory
            take_screenshots: Whether to take screenshots
            **kwargs: Other parameters supported by Options
        """
        if isinstance(package_name, str):
            package_names = [package_name]
        else:
            package_names = package_name
        
        self.options = Options(
            driverName="d",
            Driver=U2Driver,
            packageNames=package_names,
            serial=serial,
            transport_id=transport_id,
            running_mins=running_minutes,
            maxStep=max_step if max_step else float("inf"),
            throttle=throttle,
            output_dir=output_dir,
            take_screenshots=take_screenshots,
            agent="u2",
            **kwargs
        )
        
        logger.info("Kea2 configuration has been set up.")
        return self
    
    def add_property(self, test_class: type):
        """
        Add property test class.
        
        Args:
            test_class: Test class inherited from unittest.TestCase
            
        Returns:
            self: Supports chain calls
        """
        if not issubclass(test_class, unittest.TestCase):
            raise TypeError(f"{test_class} Must inherit from unittest.TestCase")
        
        self.properties.append(test_class)
        logger.info(f"Added property test class: {test_class.__name__}")
        return self
    
    def start(
        self, 
        current_driver=None, 
    ):
        """
        Launch property test.
        
        Args:
            current_driver: Currently used driver object. (pass self.d for U2, self.driver for Appium)
            
        Returns:
            Returns test results.
        """
        if self.options is None:
            raise ValueError("Please call configure() first to set up the configuration.")
        
        if len(self.properties) == 0:
            raise ValueError("No property test class has been added.")
        
        if current_driver is not None:
            driver_type = self._detect_driver_type(current_driver)
            logger.info(f"Detected current driver type: {driver_type}")
            
            if driver_type == "u2":
                logger.info("The current driver is U2 (self.d), no handling required.")
            elif driver_type == "appium":
                logger.info("Detected Appium driver (self.driver), closing Appium connection...")
                self.stop_appium_session(current_driver)
                logger.info("Appium connection has been closed.")
            else:
                logger.warning(f"Unknown driver type: {driver_type}, no driver handling performed.")
        
        KeaTestRunner.setOptions(self.options)
        
        test_suite = unittest.TestSuite()
        for test_class in self.properties:
            tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
            test_suite.addTests(tests)
        
        logger.info("Starting Kea2 property test...")
        runner = KeaTestRunner()
        result = runner.run(test_suite)
        logger.info("Kea2 property test completed.")
        return result
    
    def run_kea2_testing(
        self,
        package_name: Union[str, List[str]],
        property_classes: Union[type, List[type]],
        current_driver=None,
        serial: Optional[str] = None,
        transport_id: Optional[str] = None,
        running_minutes: int = 10,
        max_step: Optional[int] = None,
        throttle: int = 200,
        output_dir: str = "output",
        take_screenshots: bool = False,
        preserve_state: bool = True,
        **kwargs
    ):
        """
        A convenient function to launch Kea2 property tests with one click
        
        This is the main API function, which can be called anywhere in the test script.
        
        Args:
            package_name: Target application package name (string or list)
            property_classes: Property test class or list of classes (inherited from unittest.TestCase)
            current_driver: Currently used driver object (pass self.d for U2, self.driver for Appium)
            serial: Device serial number
            transport_id: Device transport_id
            running_minutes: Running duration (minutes)
            max_step: Maximum number of steps
            throttle: Event interval (milliseconds)
            output_dir: Output directory
            take_screenshots: Whether to take screenshots
            **kwargs: Other parameters supported by Options
            
        Returns:
            Test results
            
        Example:
            >>> # Call anywhere in the existing script
            >>> from kea2 import start_property_testing
            >>> from appium import webdriver
            >>> 
            >>> # Define property tests
            >>> class MyProperties(unittest.TestCase):
            >>>     @precondition(lambda self: self.d(text="Login").exists)
            >>>     def test_login(self):
            >>>         self.d(text="Login").click()
            >>>         assert self.d(text="Welcome").exists
            >>> 
            >>> # Initialize Appium driver
            >>> appium_driver = webdriver.Remote("http://localhost:4723", {...})
            >>> 
            >>> # Launch property tests in the script
            >>> start_property_testing(
            >>>     package_name="com.example.app",
            >>>     property_classes=MyProperties,
            >>>     current_driver=appium_driver,  # Pass self.driver
            >>>     running_minutes=5
            >>> )
        """        
        # config
        self.configure(
            package_name=package_name,
            serial=serial,
            transport_id=transport_id,
            running_minutes=running_minutes,
            max_step=max_step,
            throttle=throttle,
            output_dir=output_dir,
            take_screenshots=take_screenshots,
            **kwargs
        )
        
        # Add property test class
        if isinstance(property_classes, list):
            for prop_class in property_classes:
                self.add_property(prop_class)
        else:
            self.add_property(property_classes)
        
        # Launch property test
        return self.start(
            current_driver=current_driver,
            preserve_state=preserve_state,
        )

    @staticmethod
    def stop_appium_session(driver_obj):
        """
        Stop Appium session
        
        Args:
            driver_obj: Appium driver object
        """
        try:
            logger.info("Stopping Appium session...")
            if hasattr(driver_obj, "quit"):
                driver_obj.quit()
            elif hasattr(driver_obj, "close"):
                driver_obj.close()
            logger.info("Appium session has been stopped")
            time.sleep(2)
        except Exception as e:
            logger.warning(f"Error stopping Appium session: {e}")

    @staticmethod
    def _detect_driver_type(driver_obj) -> str:
        """
        Detect the current driver type

        Args:
            driver_obj: driver object

        Returns:
            str: "u2", "appium", "unknown"
        """
        if driver_obj is None:
            logger.warning("The driver object is None，returning unknown")
            return "unknown"

        try:
            driver_class = driver_obj.__class__
            driver_class_name = driver_class.__name__
            driver_module = driver_class.__module__ or ""
            logger.debug(f"Driver class name: {driver_class_name}, module: {driver_module}")

            # detect uiautomator2
            if driver_module.startswith("uiautomator2") or "uiautomator2" in driver_module:
                logger.debug("Detected that the module contains uiautomator2")
                return "u2"
            if driver_class_name == "Device" or hasattr(driver_obj, "uiautomator2"):
                logger.debug("Detected uiautomator2 Device or uiautomator2 attribute")
                return "u2"
            # Check the inheritance relationship to confirm if it is a subclass of uiautomator2
            for cls in driver_class.__mro__:
                if "uiautomator2" in cls.__module__ or cls.__name__ == "Device":
                    logger.debug(f"Detected a class inherited from uiautomator2: {cls.__name__}")
                    return "u2"

            # detect Appium
            if driver_module.startswith("appium") or "appium" in driver_module:
                logger.debug("Detected that the module contains appium")
                return "appium"
            if driver_class_name in ["WebDriver", "Remote"] or hasattr(driver_obj, "desired_capabilities"):
                logger.debug("Detected Appium WebDriver/Remote or desired_capabilities attribute")
                return "appium"

            # Additional check for specific methods or attributes of uiautomator2
            u2_methods = ["click", "swipe", "dump_hierarchy"]
            if any(hasattr(driver_obj, method) for method in u2_methods):
                logger.debug(f"Detected unique methods of uiautomator2: {u2_methods}")
                return "u2"

            logger.warning(f"Unable to identify driver type, class name: {driver_class_name}, module: {driver_module}")
            return "unknown"

        except Exception as e:
            logger.error(f"Error detecting driver type: {e}")
            return "unknown"
    