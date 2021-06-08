"""Test Suite for this package

Auto discover tests in this package
"""

import doctest
import fnmatch
import os
import os.path
import unittest


def test_suite_test_cases(pattern="*_test.py"):
    """Create the test suite used for the test runner

    Discover tests and load them into a test suite.

    Args:
        pattern (str): The glob pattern used for test discovery

    Returns:
        TestSuite: The test suite to be used for the test runner
    """
    top_level_dir = os.path.dirname(__file__)

    test_loader = unittest.TestLoader()
    suite = test_loader.discover(
        top_level_dir, pattern=pattern, top_level_dir=top_level_dir
    )

    return suite


def test_suite_doctest_folder(path="doctests", pattern="*_test.rst"):
    """Create an test suite from a doctest folder

    These are heavier weight tests designed to make sure all the components
    are working together.

    Args:
        path (str): Where to look for doctests
        pattern (str): The glob pattern used for test discovery

    Returns:
        TestSuite: The test suite to be used for the test runner
    """
    doctest_files = []
    base_dir = os.path.join(os.path.dirname(__file__), path)
    for item_name in os.listdir(base_dir):
        if fnmatch.fnmatch(item_name, pattern):
            doctest_file = os.path.join(base_dir, item_name)
            doctest_files.append(doctest_file)
    option_flags = (
        doctest.NORMALIZE_WHITESPACE
        | doctest.REPORT_ONLY_FIRST_FAILURE
        | doctest.ELLIPSIS
    )
    suite = doctest.DocFileSuite(
        *doctest_files, module_relative=False, optionflags=option_flags
    )
    return suite


def test_suite():
    """The default test suite. Does unit testing."""
    return unittest.TestSuite(
        [
            test_suite_test_cases(pattern="*_test.py"),
            test_suite_doctest_folder(),
        ]
    )


def integration_test_suite():
    """Do integration testing"""
    return unittest.TestSuite(
        [
            test_suite_test_cases(pattern="*_inttest.py"),
            test_suite_doctest_folder(path="integration_test", pattern="*_inttest.rst"),
        ]
    )
