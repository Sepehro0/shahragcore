# -*- coding: utf-8 -*-
"""
Master Test Runner
اجرای تمام تست‌های سیستم و گزارش نهایی
"""

import sys
import time
import subprocess
from pathlib import Path

sys.path.insert(0, "/home/user01/qwen-api/enhanced_rag_system_dev")


class TestRunner:
    """اجرای تمام تست‌ها"""
    
    def __init__(self):
        self.base_dir = Path("/home/user01/qwen-api/enhanced_rag_system_dev")
        self.results = []
        
    def run_test_file(self, test_file: Path, category: str) -> dict:
        """اجرای یک فایل تست"""
        print(f"\n{'='*70}")
        print(f"🧪 Running: {test_file.name}")
        print(f"   Category: {category}")
        print(f"{'='*70}")
        
        start_time = time.time()
        
        try:
            result = subprocess.run(
                [sys.executable, str(test_file)],
                capture_output=True,
                text=True,
                timeout=60,
                cwd=str(self.base_dir)
            )
            
            duration = time.time() - start_time
            
            success = result.returncode == 0
            
            test_result = {
                'name': test_file.name,
                'category': category,
                'success': success,
                'duration': duration,
                'returncode': result.returncode,
                'stdout': result.stdout,
                'stderr': result.stderr,
            }
            
            # Parse output for test counts
            stdout = result.stdout
            if 'Tests run:' in stdout:
                lines = stdout.split('\n')
                for line in lines:
                    if 'Tests run:' in line:
                        import re
                        match = re.search(r'Tests run: (\d+)', line)
                        if match:
                            test_result['tests_run'] = int(match.group(1))
                    if 'Passed:' in line:
                        match = re.search(r'Passed: (\d+)', line)
                        if match:
                            test_result['tests_passed'] = int(match.group(1))
                    if 'Failed:' in line:
                        match = re.search(r'Failed: (\d+)', line)
                        if match:
                            test_result['tests_failed'] = int(match.group(1))
            
            status = "✅ PASS" if success else "❌ FAIL"
            print(f"\n{status} - Completed in {duration:.2f}s")
            
            return test_result
            
        except subprocess.TimeoutExpired:
            duration = time.time() - start_time
            print(f"\n⏱️  TIMEOUT after {duration:.2f}s")
            return {
                'name': test_file.name,
                'category': category,
                'success': False,
                'duration': duration,
                'error': 'timeout'
            }
        except Exception as e:
            duration = time.time() - start_time
            print(f"\n❌ ERROR: {e}")
            return {
                'name': test_file.name,
                'category': category,
                'success': False,
                'duration': duration,
                'error': str(e)
            }
    
    def run_all_unit_tests(self):
        """اجرای تمام unit tests"""
        unit_test_dir = self.base_dir / "tests" / "unit"
        
        if not unit_test_dir.exists():
            print(f"⚠️  Unit test directory not found: {unit_test_dir}")
            return
        
        test_files = list(unit_test_dir.glob("test_*.py"))
        
        print(f"\n{'#'*70}")
        print(f"# UNIT TESTS ({len(test_files)} files)")
        print(f"{'#'*70}")
        
        for test_file in sorted(test_files):
            result = self.run_test_file(test_file, "Unit Test")
            self.results.append(result)
    
    def run_all_integration_tests(self):
        """اجرای تمام integration tests"""
        integration_test_dir = self.base_dir / "tests" / "integration"
        
        if not integration_test_dir.exists():
            print(f"\n⚠️  Integration test directory not found: {integration_test_dir}")
            return
        
        test_files = list(integration_test_dir.glob("test_*.py"))
        
        if not test_files:
            print(f"\n⚠️  No integration tests found")
            return
        
        print(f"\n{'#'*70}")
        print(f"# INTEGRATION TESTS ({len(test_files)} files)")
        print(f"{'#'*70}")
        
        for test_file in sorted(test_files):
            result = self.run_test_file(test_file, "Integration Test")
            self.results.append(result)
    
    def print_summary(self):
        """چاپ خلاصه نتایج"""
        print(f"\n\n{'='*70}")
        print(f"📊 FINAL TEST SUMMARY")
        print(f"{'='*70}\n")
        
        # Overall statistics
        total_files = len(self.results)
        passed_files = sum(1 for r in self.results if r['success'])
        failed_files = total_files - passed_files
        total_duration = sum(r['duration'] for r in self.results)
        
        # Test counts
        total_tests = sum(r.get('tests_run', 0) for r in self.results)
        passed_tests = sum(r.get('tests_passed', 0) for r in self.results)
        failed_tests = sum(r.get('tests_failed', 0) for r in self.results)
        
        # By category
        unit_tests = [r for r in self.results if r['category'] == 'Unit Test']
        integration_tests = [r for r in self.results if r['category'] == 'Integration Test']
        
        print("📦 Test Files:")
        print(f"   Total: {total_files}")
        print(f"   ✅ Passed: {passed_files}")
        print(f"   ❌ Failed: {failed_files}")
        print(f"   Success Rate: {(passed_files/total_files*100):.1f}%")
        
        print(f"\n🧪 Individual Tests:")
        print(f"   Total: {total_tests}")
        print(f"   ✅ Passed: {passed_tests}")
        print(f"   ❌ Failed: {failed_tests}")
        if total_tests > 0:
            print(f"   Success Rate: {(passed_tests/total_tests*100):.1f}%")
        
        print(f"\n⏱️  Duration:")
        print(f"   Total: {total_duration:.2f}s")
        print(f"   Average: {total_duration/total_files:.2f}s per file")
        
        print(f"\n📂 By Category:")
        print(f"   Unit Tests: {len(unit_tests)} files, {sum(1 for r in unit_tests if r['success'])} passed")
        print(f"   Integration Tests: {len(integration_tests)} files, {sum(1 for r in integration_tests if r['success'])} passed")
        
        # Detailed results
        print(f"\n📋 Detailed Results:")
        for result in self.results:
            status = "✅" if result['success'] else "❌"
            name = result['name']
            duration = result['duration']
            tests_info = ""
            if 'tests_run' in result:
                tests_info = f" ({result.get('tests_passed', 0)}/{result.get('tests_run', 0)} passed)"
            
            print(f"   {status} {name:40s} {duration:6.2f}s{tests_info}")
        
        # Failed tests details
        failed = [r for r in self.results if not r['success']]
        if failed:
            print(f"\n❌ Failed Tests Details:")
            for result in failed:
                print(f"\n   📁 {result['name']}")
                if 'error' in result:
                    print(f"      Error: {result['error']}")
                if result.get('stderr'):
                    print(f"      Stderr (last 10 lines):")
                    stderr_lines = result['stderr'].split('\n')[-10:]
                    for line in stderr_lines:
                        if line.strip():
                            print(f"         {line}")
        
        print(f"\n{'='*70}")
        
        # Overall status
        if failed_files == 0:
            print("🎉 ALL TESTS PASSED!")
        elif failed_files <= 2:
            print(f"⚠️  {failed_files} test file(s) failed (minor issues)")
        else:
            print(f"❌ {failed_files} test file(s) failed (needs attention)")
        
        print(f"{'='*70}\n")
        
        return failed_files == 0


def main():
    """Main function"""
    print("\n" + "="*70)
    print("🚀 Enhanced RAG System - Complete Test Suite")
    print("="*70)
    
    runner = TestRunner()
    
    # Run all tests
    runner.run_all_unit_tests()
    runner.run_all_integration_tests()
    
    # Print summary
    success = runner.print_summary()
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())

