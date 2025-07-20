"""
Enhanced Log Analyzer for Adventure Test Logs

Analyzes adventure test logs using app-specific patterns and structures.
Designed specifically for the Learning Odyssey application logging format.

Usage:
    python tests/simulations/log_analyzer_new.py <log_file> [--output OUTPUT_FILE]
"""

import re
import argparse
import json as json_lib
from pathlib import Path
from typing import List, Optional
from dataclasses import dataclass
from datetime import datetime

@dataclass
class LogEntry:
    """Structured log entry for analysis."""
    timestamp: str
    level: str
    logger: str
    message: str
    raw_line: str
    line_number: int

@dataclass
class Anomaly:
    """Detected anomaly in logs."""
    category: str
    severity: str
    description: str
    log_entry: LogEntry
    context: Optional[List[str]] = None

class AdventureLogAnalyzer:
    """Enhanced log analyzer using app-specific patterns from Learning Odyssey."""
    
    # Application-specific log patterns based on actual codebase
    LOG_PATTERNS = {
        # Structured JSON logs from StructuredLogger
        'structured_json': r'\{"timestamp":\s*"[^"]+",\s*"level":\s*"([^"]+)",\s*"message":\s*"([^"]+)"[^}]*\}',
        # Basic JSON formatter from file handler
        'basic_json': r'\{"timestamp":\s*"[^"]+",\s*"level":\s*"([^"]+)",\s*"message":\s*"([^"]+)"\}',
        # Console format (plain text messages)
        'console_format': r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}) - ([\w.]+) - (\w+) - (.+)',
    }
    
    # Performance tracking patterns specific to this app
    PERFORMANCE_PATTERNS = {
        'live_streaming_issues': r'\[PERFORMANCE\] .*(?:fail|error|slow|timeout).*(?:streaming|stream)',
        'background_task_issues': r'\[PERFORMANCE\] .*(?:fail|error|timeout).*(?:background|deferred|task)',
        'slow_operations': r'duration[_\s]*[:\-]?\s*([5-9]\d{3,}|[1-9]\d{4,})\s*(ms|milliseconds)',  # >5 seconds
        'image_gen_issues': r'\[PERFORMANCE\] .*(?:fail|error|timeout).*image',
        'chapter_processing_slow': r'\[PERFORMANCE\] .*(?:slow|delay).*chapter',
    }
    
    # State management patterns (critical for adventure flow)
    STATE_PATTERNS = {
        'corruption': r'\[STATE CORRUPTION\] (.+)',
        'storage_issues': r'\[STATE STORAGE\] .*(?:fail|error|missing|corrupt)',
        'summary_issues': r'\[REVEAL SUMMARY\] .*(?:fail|error|missing|timeout)',
        'incomplete_chapters': r'chapters_completed[\"\':\s]*([0-9])\b',  # Single digit (0-9)
        'reconstruction_failure': r'State reconstruction.*(?:fail|error)',
        'chapter_validation_error': r'(?:chapter_number|chapter_type).*(?:invalid|missing|error)',
    }
    
    # WebSocket communication patterns
    WEBSOCKET_PATTERNS = {
        'connection_failures': r'(?:WebSocket|websocket).*(?:fail|error|closed|timeout|refused)',
        'message_errors': r'(?:send|recv|message).*(?:fail|error|timeout)',
        'choice_processing_errors': r'(?:Choice|choice).*(?:fail|error|invalid)',
    }
    
    # LLM interaction patterns
    LLM_PATTERNS = {
        'generation_failures': r'(?:generation|prompt|llm).*(?:fail|error|timeout)',
        'serialization_errors': r'serialization.*(?:fail|error)',
        'model_errors': r'(?:Flash|Gemini|OpenAI).*(?:fail|error|timeout)',
        'prompt_issues': r'llm_prompt.*(?:fail|error|missing)',
    }
    
    # Adventure flow patterns
    ADVENTURE_PATTERNS = {
        'incomplete_story': r'(?:story|adventure).*(?:incomplete|partial|stopped)',
        'chapter_flow_errors': r'Chapter.*(?:fail|error|skip|missing)',
        'lesson_errors': r'(?:LESSON|lesson).*(?:fail|error|invalid|missing)',
        'summary_generation_fail': r'summary.*(?:fail|error|timeout|missing)',
    }
    
    def __init__(self, log_file: Path):
        self.log_file = log_file
        self.log_entries: List[LogEntry] = []
        self.anomalies: List[Anomaly] = []
        
    def parse_log_file(self):
        """Parse the log file using app-specific patterns."""
        with open(self.log_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        for line_num, line in enumerate(lines, 1):
            line = line.strip()
            if not line:
                continue
            
            entry = self._parse_log_line(line, line_num)
            if entry:
                self.log_entries.append(entry)
            else:
                # Handle multi-line entries
                if self.log_entries:
                    self.log_entries[-1].message += f" {line}"
                    self.log_entries[-1].raw_line += f"\n{line}"
    
    def _parse_log_line(self, line: str, line_num: int) -> Optional[LogEntry]:
        """Parse a single log line using multiple patterns."""
        # Try structured JSON format first (from StructuredLogger)
        try:
            if line.startswith('{"timestamp"'):
                log_data = json_lib.loads(line)
                return LogEntry(
                    timestamp=log_data.get("timestamp", ""),
                    level=log_data.get("level", "INFO"),
                    logger="structured",
                    message=log_data.get("message", ""),
                    raw_line=line,
                    line_number=line_num
                )
        except json_lib.JSONDecodeError:
            pass
        
        # Try console format
        console_match = re.match(self.LOG_PATTERNS['console_format'], line)
        if console_match:
            timestamp, logger, level, message = console_match.groups()
            return LogEntry(
                timestamp=timestamp,
                level=level,
                logger=logger,
                message=message,
                raw_line=line,
                line_number=line_num
            )
        
        # Try basic JSON format
        json_match = re.match(self.LOG_PATTERNS['basic_json'], line)
        if json_match:
            level, message = json_match.groups()
            return LogEntry(
                timestamp="",
                level=level,
                logger="file",
                message=message,
                raw_line=line,
                line_number=line_num
            )
        
        # Treat as plain text
        return LogEntry(
            timestamp="",
            level="INFO",
            logger="unknown",
            message=line,
            raw_line=line,
            line_number=line_num
        )
    
    def detect_anomalies(self):
        """Detect anomalies using app-specific patterns."""
        for entry in self.log_entries:
            self._check_critical_errors(entry)
            self._check_performance_issues(entry)
            self._check_state_management(entry)
            self._check_websocket_issues(entry)
            self._check_llm_issues(entry)
            self._check_adventure_flow(entry)
    
    def _check_critical_errors(self, entry: LogEntry):
        """Check for critical errors and exceptions."""
        message = entry.message
        
        # Explicit ERROR/CRITICAL level logs
        if entry.level in ["ERROR", "CRITICAL"]:
            anomaly = Anomaly(
                category="CRITICAL_ERROR",
                severity="HIGH",
                description=f"{entry.level}: {message[:100]}...",
                log_entry=entry
            )
            self.anomalies.append(anomaly)
        
        # Look for exception patterns
        if re.search(r'(?:Exception|Traceback|Error:|Failed to)', message, re.IGNORECASE):
            anomaly = Anomaly(
                category="EXCEPTION",
                severity="HIGH",
                description=f"Exception detected: {message[:100]}...",
                log_entry=entry
            )
            self.anomalies.append(anomaly)
    
    def _check_performance_issues(self, entry: LogEntry):
        """Check for performance-related issues."""
        message = entry.message
        
        for pattern_name, pattern in self.PERFORMANCE_PATTERNS.items():
            if re.search(pattern, message, re.IGNORECASE):
                # Special handling for duration patterns
                if pattern_name == 'slow_operations':
                    duration_match = re.search(pattern, message)
                    if duration_match:
                        duration = duration_match.group(1)
                        description = f"Slow operation detected: {duration}ms - {message[:80]}..."
                    else:
                        description = f"Performance issue: {message[:100]}..."
                else:
                    description = f"Performance issue ({pattern_name}): {message[:100]}..."
                
                anomaly = Anomaly(
                    category="PERFORMANCE",
                    severity="MEDIUM" if "slow" in pattern_name else "HIGH",
                    description=description,
                    log_entry=entry
                )
                self.anomalies.append(anomaly)
                break
    
    def _check_state_management(self, entry: LogEntry):
        """Check for state management issues."""
        message = entry.message
        
        for pattern_name, pattern in self.STATE_PATTERNS.items():
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                if pattern_name == 'incomplete_chapters':
                    chapters = match.group(1)
                    description = f"Incomplete adventure: only {chapters} chapters completed"
                    severity = "MEDIUM"
                elif pattern_name == 'corruption':
                    description = f"State corruption detected: {match.group(1)}"
                    severity = "HIGH"
                else:
                    description = f"State issue ({pattern_name}): {message[:100]}..."
                    severity = "HIGH" if "fail" in pattern_name else "MEDIUM"
                
                anomaly = Anomaly(
                    category="STATE_MANAGEMENT",
                    severity=severity,
                    description=description,
                    log_entry=entry
                )
                self.anomalies.append(anomaly)
                break
    
    def _check_websocket_issues(self, entry: LogEntry):
        """Check for WebSocket communication issues."""
        message = entry.message
        
        for pattern_name, pattern in self.WEBSOCKET_PATTERNS.items():
            if re.search(pattern, message, re.IGNORECASE):
                anomaly = Anomaly(
                    category="WEBSOCKET",
                    severity="HIGH",
                    description=f"WebSocket issue ({pattern_name}): {message[:100]}...",
                    log_entry=entry
                )
                self.anomalies.append(anomaly)
                break
    
    def _check_llm_issues(self, entry: LogEntry):
        """Check for LLM service issues."""
        message = entry.message
        
        for pattern_name, pattern in self.LLM_PATTERNS.items():
            if re.search(pattern, message, re.IGNORECASE):
                anomaly = Anomaly(
                    category="LLM_SERVICE",
                    severity="HIGH",
                    description=f"LLM issue ({pattern_name}): {message[:100]}...",
                    log_entry=entry
                )
                self.anomalies.append(anomaly)
                break
    
    def _check_adventure_flow(self, entry: LogEntry):
        """Check for adventure flow issues."""
        message = entry.message
        
        for pattern_name, pattern in self.ADVENTURE_PATTERNS.items():
            if re.search(pattern, message, re.IGNORECASE):
                severity = "HIGH" if "fail" in pattern_name else "MEDIUM"
                anomaly = Anomaly(
                    category="ADVENTURE_FLOW",
                    severity=severity,
                    description=f"Adventure flow issue ({pattern_name}): {message[:100]}...",
                    log_entry=entry
                )
                self.anomalies.append(anomaly)
                break
    
    def get_context_lines(self, entry: LogEntry, before: int = 2, after: int = 2) -> List[str]:
        """Get context lines around a log entry."""
        context = []
        start_line = max(0, entry.line_number - before - 1)
        end_line = min(len(self.log_entries), entry.line_number + after)
        
        for i in range(start_line, end_line):
            if i < len(self.log_entries):
                prefix = ">>> " if i == entry.line_number - 1 else "    "
                context.append(f"{prefix}{self.log_entries[i].raw_line}")
        
        return context
    
    def generate_report(self, output_file: Optional[Path] = None):
        """Generate enhanced analysis report."""
        report_lines = []
        
        # Header
        report_lines.append("=" * 80)
        report_lines.append("ADVENTURE LOG ANALYSIS REPORT (Enhanced)")
        report_lines.append("=" * 80)
        report_lines.append(f"Log file: {self.log_file}")
        report_lines.append(f"Analysis time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append(f"Total log entries: {len(self.log_entries)}")
        report_lines.append(f"Anomalies detected: {len(self.anomalies)}")
        report_lines.append("")
        
        # Summary by category
        categories = {}
        for anomaly in self.anomalies:
            categories[anomaly.category] = categories.get(anomaly.category, 0) + 1
        
        if categories:
            report_lines.append("ANOMALIES BY CATEGORY:")
            report_lines.append("-" * 40)
            for category, count in sorted(categories.items()):
                report_lines.append(f"{category:20s}: {count}")
            report_lines.append("")
        
        # Summary by severity
        severities = {}
        for anomaly in self.anomalies:
            severities[anomaly.severity] = severities.get(anomaly.severity, 0) + 1
        
        if severities:
            report_lines.append("ANOMALIES BY SEVERITY:")
            report_lines.append("-" * 40)
            for severity in ["HIGH", "MEDIUM", "LOW"]:
                if severity in severities:
                    report_lines.append(f"{severity:10s}: {severities[severity]}")
            report_lines.append("")
        
        # Critical issues first
        critical_anomalies = [a for a in self.anomalies if a.severity == "HIGH"]
        if critical_anomalies:
            report_lines.append("CRITICAL ISSUES (HIGH SEVERITY):")
            report_lines.append("=" * 80)
            
            for i, anomaly in enumerate(critical_anomalies, 1):
                report_lines.append(f"\n{i}. [HIGH] {anomaly.category}")
                report_lines.append(f"   {anomaly.description}")
                report_lines.append(f"   Time: {anomaly.log_entry.timestamp}")
                report_lines.append(f"   Logger: {anomaly.log_entry.logger}")
                report_lines.append(f"   Line: {anomaly.log_entry.line_number}")
                
                # Add context for critical issues
                context = self.get_context_lines(anomaly.log_entry)
                if context:
                    report_lines.append("   Context:")
                    for line in context:
                        report_lines.append(f"   {line}")
                
                report_lines.append("-" * 80)
        
        # Medium/Low severity issues
        other_anomalies = [a for a in self.anomalies if a.severity != "HIGH"]
        if other_anomalies:
            report_lines.append("\nOTHER ISSUES:")
            report_lines.append("=" * 80)
            
            for i, anomaly in enumerate(other_anomalies, 1):
                report_lines.append(f"\n{i}. [{anomaly.severity}] {anomaly.category}")
                report_lines.append(f"   {anomaly.description}")
                report_lines.append(f"   Time: {anomaly.log_entry.timestamp}")
                report_lines.append(f"   Line: {anomaly.log_entry.line_number}")
                report_lines.append("-" * 40)
        
        if not self.anomalies:
            report_lines.append("🎉 No anomalies detected - clean run!")
            report_lines.append("")
            report_lines.append("All adventure tests completed successfully with no issues.")
        
        # Write report
        report_content = "\n".join(report_lines)
        
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(report_content)
            print(f"Enhanced analysis report saved to: {output_file}")
        else:
            print(report_content)
        
        return report_content
    
    def analyze(self, output_file: Optional[Path] = None):
        """Run complete analysis pipeline."""
        print(f"Analyzing log file with enhanced patterns: {self.log_file}")
        
        # Parse logs
        self.parse_log_file()
        print(f"Parsed {len(self.log_entries)} log entries")
        
        # Detect anomalies
        self.detect_anomalies()
        print(f"Detected {len(self.anomalies)} anomalies using app-specific patterns")
        
        # Generate report
        self.generate_report(output_file)
        
        return self.anomalies

def main():
    """Main entry point for enhanced log analysis."""
    parser = argparse.ArgumentParser(description="Enhanced adventure test log analyzer")
    parser.add_argument("log_file", type=Path, help="Log file to analyze")
    parser.add_argument("--output", type=Path, help="Output file for analysis report")
    
    args = parser.parse_args()
    
    if not args.log_file.exists():
        print(f"Error: Log file not found: {args.log_file}")
        return 1
    
    # Create analyzer and run analysis
    analyzer = AdventureLogAnalyzer(args.log_file)
    anomalies = analyzer.analyze(args.output)
    
    # Return exit code based on severity
    high_severity = sum(1 for a in anomalies if a.severity == "HIGH")
    if high_severity > 0:
        print(f"\n🚨 Found {high_severity} high-severity issues!")
        return 1
    else:
        print("\n✅ Analysis complete - no critical issues found.")
        return 0

if __name__ == "__main__":
    exit(main())
