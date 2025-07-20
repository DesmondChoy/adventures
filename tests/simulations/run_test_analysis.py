"""
Complete Test and Analysis Runner

Runs adventure tests and analyzes the logs automatically.
Includes automatic server startup/shutdown for full automation.
Combines the test runner and log analyzer for easy testing.

Usage:
    python tests/simulations/run_test_analysis.py [--runs N] [--category CATEGORY] [--topic TOPIC]
"""

import asyncio
import argparse
import subprocess
import sys
import socket
from pathlib import Path
from datetime import datetime
import time

def check_port_available(port):
    """Check if a port is available for use."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        result = sock.connect_ex(('localhost', port))
        return result != 0

def wait_for_server(host, port, timeout=30):
    """Wait for server to become available."""
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(1)
                result = sock.connect_ex((host, port))
                if result == 0:
                    return True
        except Exception:
            pass
        time.sleep(1)
    return False

class ServerManager:
    """Manages the uvicorn server lifecycle."""
    
    def __init__(self, host="0.0.0.0", port=8000):
        self.host = host
        self.port = port
        self.process = None
        self.venv_python = None
        
        # Find the virtual environment python
        self.find_venv_python()
    
    def find_venv_python(self):
        """Find the Python executable in the virtual environment."""
        # Try common virtual environment locations
        possible_paths = [
            Path(".venv/bin/python"),
            Path(".venv/Scripts/python.exe"),  # Windows
            Path("venv/bin/python"),
            Path("venv/Scripts/python.exe"),   # Windows
        ]
        
        for path in possible_paths:
            if path.exists():
                self.venv_python = str(path.absolute())
                print(f"Found virtual environment Python: {self.venv_python}")
                return
        
        # Fallback to system Python
        self.venv_python = sys.executable
        print(f"Using system Python: {self.venv_python}")
    
    def start_server(self):
        """Start the uvicorn server."""
        if not check_port_available(self.port):
            print(f"⚠️  Port {self.port} is already in use. Using existing server.")
            return True
        
        print(f"🚀 Starting uvicorn server on {self.host}:{self.port}...")
        
        cmd = [
            self.venv_python, "-m", "uvicorn",
            "app.main:app",
            "--host", self.host,
            "--port", str(self.port),
            "--log-level", "info"
        ]
        
        try:
            # Start server as subprocess
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=Path.cwd()
            )
            
            print(f"Server process started with PID: {self.process.pid}")
            
            # Wait for server to be ready
            if wait_for_server("localhost", self.port, timeout=30):
                print("✅ Server is ready and accepting connections")
                return True
            else:
                print("❌ Server failed to start within timeout")
                self.stop_server()
                return False
                
        except Exception as e:
            print(f"❌ Failed to start server: {e}")
            return False
    
    def stop_server(self):
        """Stop the uvicorn server."""
        if self.process:
            print(f"🛑 Stopping server (PID: {self.process.pid})...")
            
            try:
                # Try graceful shutdown first
                self.process.terminate()
                
                # Wait for graceful shutdown
                try:
                    self.process.wait(timeout=10)
                    print("✅ Server stopped gracefully")
                except subprocess.TimeoutExpired:
                    # Force kill if graceful shutdown fails
                    print("⚠️  Graceful shutdown timeout, force killing...")
                    self.process.kill()
                    self.process.wait(timeout=5)
                    print("✅ Server force stopped")
                    
            except Exception as e:
                print(f"⚠️  Error stopping server: {e}")
            finally:
                self.process = None
    
    def __enter__(self):
        """Context manager entry."""
        if self.start_server():
            return self
        else:
            raise RuntimeError("Failed to start server")
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop_server()

async def run_adventure_tests(args, server_port=8000):
    """Run the adventure test suite."""
    print("🚀 Starting adventure test suite...")
    
    # Build command for test runner
    cmd = [sys.executable, "tests/simulations/adventure_test_runner.py"]
    
    if args.runs:
        cmd.extend(["--runs", str(args.runs)])
    if args.category:
        cmd.extend(["--category", args.category])
    if args.topic:
        cmd.extend(["--topic", args.topic])
    cmd.extend(["--port", str(server_port)])
    if args.host:
        cmd.extend(["--host", args.host])
    
    print(f"Running: {' '.join(cmd)}")
    
    # Run tests
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)  # 1 hour timeout
        
        if result.returncode == 0:
            print("✅ Adventure tests completed successfully")
        else:
            print(f"⚠️  Adventure tests completed with issues (exit code: {result.returncode})")
        
        print("\n📝 Test output:")
        print(result.stdout)
        
        if result.stderr:
            print("\n❌ Test errors:")
            print(result.stderr)
        
        return result.returncode == 0
        
    except subprocess.TimeoutExpired:
        print("❌ Tests timed out after 1 hour")
        return False
    except Exception as e:
        print(f"❌ Failed to run tests: {e}")
        return False

def find_latest_log_file():
    """Find the most recent test log file."""
    log_dir = Path("logs/simulations")
    
    if not log_dir.exists():
        print("❌ No logs directory found")
        return None
    
    # Find test log files
    test_logs = list(log_dir.glob("adventure_test_*.log"))
    
    if not test_logs:
        print("❌ No test log files found")
        return None
    
    # Return the most recent one
    latest_log = max(test_logs, key=lambda p: p.stat().st_mtime)
    print(f"📄 Found latest log file: {latest_log}")
    return latest_log

def analyze_logs(log_file):
    """Analyze the test logs for issues."""
    print("\n🔍 Analyzing test logs for errors and anomalies...")
    
    # Extract run ID from log file name
    log_file_name = Path(log_file).name
    run_id = log_file_name.split('_')[-1].split('.')[0]  # Extract ID from filename
    
    # Generate output file name with same timestamp and run ID
    timestamp = datetime.now().strftime("%Y-%m-%d_%H:%M")
    output_file = Path(f"logs/simulations/analysis_report_{timestamp}_{run_id}.txt")
    
    # Build command for log analyzer
    cmd = [
        sys.executable, 
        "tests/simulations/log_analyzer.py",
        str(log_file),
        "--output", str(output_file)
    ]
    
    print(f"Running: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)  # 5 minute timeout
        
        print("\n📊 Analysis output:")
        print(result.stdout)
        
        if result.stderr:
            print("\n❌ Analysis errors:")
            print(result.stderr)
        
        if result.returncode == 0:
            print("✅ Log analysis completed - no critical issues found")
        else:
            print(f"⚠️  Log analysis found critical issues (exit code: {result.returncode})")
        
        print(f"📄 Detailed analysis report saved to: {output_file}")
        return result.returncode == 0, output_file
        
    except subprocess.TimeoutExpired:
        print("❌ Log analysis timed out")
        return False, None
    except Exception as e:
        print(f"❌ Failed to analyze logs: {e}")
        return False, None

def print_summary(tests_passed, analysis_passed, analysis_report):
    """Print final summary."""
    print("\n" + "="*60)
    print("🎯 TESTING SUMMARY")
    print("="*60)
    
    if tests_passed:
        print("✅ Adventure tests: PASSED")
    else:
        print("❌ Adventure tests: FAILED")
    
    if analysis_passed is not None:
        if analysis_passed:
            print("✅ Log analysis: CLEAN (No critical issues)")
        else:
            print("⚠️  Log analysis: ISSUES FOUND")
    else:
        print("❌ Log analysis: FAILED TO RUN")
    
    overall_status = tests_passed and (analysis_passed is not False)
    
    if overall_status:
        print("\n🎉 Overall result: SUCCESS")
        print("The adventure system is working correctly!")
    else:
        print("\n🔥 Overall result: ISSUES DETECTED")
        print("Check the logs and analysis report for details.")
    
    if analysis_report:
        print(f"\n📋 Full analysis report: {analysis_report}")
    
    print("="*60)
    
    return overall_status

async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Run adventure tests and analyze logs")
    parser.add_argument("--runs", type=int, default=1, help="Number of test runs")
    parser.add_argument("--category", type=str, help="Specific story category")
    parser.add_argument("--topic", type=str, help="Specific lesson topic")
    parser.add_argument("--port", type=int, default=8000, help="Server port")
    parser.add_argument("--host", type=str, default="localhost", help="Server host")
    parser.add_argument("--analyze-only", action="store_true", help="Only analyze existing logs")
    parser.add_argument("--no-server", action="store_true", help="Don't start/stop server (assume already running)")
    
    args = parser.parse_args()
    
    print("🧪 Adventure Testing & Analysis Suite")
    print("="*50)
    
    tests_passed = True
    analysis_passed = None
    analysis_report = None
    
    if not args.analyze_only:
        if args.no_server:
            # Run tests against existing server
            print("📡 Using existing server (no server management)")
            tests_passed = await run_adventure_tests(args, args.port)
        else:
            # Start server, run tests, stop server
            print("🏗️  Managing server lifecycle automatically")
            try:
                with ServerManager(host=args.host, port=args.port):
                    # Brief pause to ensure server is fully ready
                    time.sleep(2)
                    tests_passed = await run_adventure_tests(args, args.port)
            except Exception as e:
                print(f"❌ Failed to manage server: {e}")
                tests_passed = False
        
        # Brief pause before analysis
        time.sleep(2)
    
    # Find and analyze logs
    log_file = find_latest_log_file()
    if log_file:
        analysis_passed, analysis_report = analyze_logs(log_file)
    else:
        print("❌ Cannot analyze logs - no log files found")
    
    # Print summary
    overall_success = print_summary(tests_passed, analysis_passed, analysis_report)
    
    # Exit with appropriate code
    sys.exit(0 if overall_success else 1)

if __name__ == "__main__":
    asyncio.run(main())
