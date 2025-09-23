#!/usr/bin/env python3
"""
Monitoring and Health Check System for Staging Environment
LinkedIn Job Agent - Database System (US-001)
"""

import os
import sys
import time
import json
import logging
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.database.connection import DatabaseManager
from src.database.repository import JobRepository


class PerformanceMonitor:
    """Monitors database performance metrics."""

    def __init__(self, log_file: str):
        self.log_file = Path(log_file)
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        self.metrics = []

    def measure_operation(self, operation_name: str, operation_func):
        """Measure the performance of a database operation."""
        start_time = time.time()
        try:
            result = operation_func()
            end_time = time.time()
            duration_ms = (end_time - start_time) * 1000

            metric = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "operation": operation_name,
                "duration_ms": round(duration_ms, 3),
                "status": "success",
                "result_count": len(result) if isinstance(result, list) else 1
            }

            self.metrics.append(metric)
            self._log_metric(metric)
            return result, metric

        except Exception as e:
            end_time = time.time()
            duration_ms = (end_time - start_time) * 1000

            metric = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "operation": operation_name,
                "duration_ms": round(duration_ms, 3),
                "status": "error",
                "error": str(e)
            }

            self.metrics.append(metric)
            self._log_metric(metric)
            raise

    def _log_metric(self, metric: Dict[str, Any]):
        """Log metric to file."""
        with open(self.log_file, 'a') as f:
            f.write(f"{json.dumps(metric)}\n")

    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary statistics."""
        if not self.metrics:
            return {"total_operations": 0}

        successful_metrics = [m for m in self.metrics if m["status"] == "success"]

        if not successful_metrics:
            return {"total_operations": len(self.metrics), "error_rate": 100.0}

        durations = [m["duration_ms"] for m in successful_metrics]

        return {
            "total_operations": len(self.metrics),
            "successful_operations": len(successful_metrics),
            "error_rate": round((len(self.metrics) - len(successful_metrics)) / len(self.metrics) * 100, 2),
            "avg_duration_ms": round(sum(durations) / len(durations), 3),
            "min_duration_ms": round(min(durations), 3),
            "max_duration_ms": round(max(durations), 3),
            "operations_under_50ms": len([d for d in durations if d < 50]),
            "operations_over_50ms": len([d for d in durations if d >= 50])
        }


class HealthChecker:
    """Health check system for database connectivity and operations."""

    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.last_check = None
        self.health_status = {"status": "unknown"}

    def check_database_connectivity(self) -> Dict[str, Any]:
        """Check basic database connectivity."""
        try:
            from sqlalchemy import text
            with self.db_manager.get_session_context() as session:
                # Simple connectivity test
                session.execute(text("SELECT 1"))
                return {"connectivity": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()}
        except Exception as e:
            return {"connectivity": "unhealthy", "error": str(e), "timestamp": datetime.now(timezone.utc).isoformat()}

    def check_database_operations(self) -> Dict[str, Any]:
        """Check core database operations."""
        try:
            with self.db_manager.get_session_context() as session:
                repository = JobRepository(session)

                # Test basic operations
                count = repository.count()
                recent_jobs = repository.get_recent_jobs(days=1, limit=1)

                return {
                    "operations": "healthy",
                    "job_count": count,
                    "recent_jobs_available": len(recent_jobs) > 0,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
        except Exception as e:
            return {"operations": "unhealthy", "error": str(e), "timestamp": datetime.now(timezone.utc).isoformat()}

    def full_health_check(self) -> Dict[str, Any]:
        """Perform comprehensive health check."""
        start_time = time.time()

        connectivity_check = self.check_database_connectivity()
        operations_check = self.check_database_operations()

        end_time = time.time()
        duration_ms = (end_time - start_time) * 1000

        overall_status = "healthy" if (
            connectivity_check.get("connectivity") == "healthy" and
            operations_check.get("operations") == "healthy"
        ) else "unhealthy"

        health_result = {
            "overall_status": overall_status,
            "check_duration_ms": round(duration_ms, 3),
            "connectivity": connectivity_check,
            "operations": operations_check,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        self.last_check = health_result
        self.health_status = health_result

        return health_result


class StagingMonitor:
    """Main monitoring system for staging environment."""

    def __init__(self):
        self.setup_logging()
        self.db_manager = None
        self.performance_monitor = None
        self.health_checker = None
        self.monitoring_active = False

    def setup_logging(self):
        """Configure logging for monitoring system."""
        log_dir = Path(__file__).parent / "logs"
        log_dir.mkdir(exist_ok=True)

        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_dir / "monitoring.log"),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger(__name__)

    def initialize(self):
        """Initialize monitoring components."""
        try:
            # Initialize database
            staging_db_path = Path(__file__).parent / "data" / "db" / "jobs_staging.db"
            database_url = f"sqlite:///{staging_db_path.absolute()}"

            self.db_manager = DatabaseManager(database_url)
            self.db_manager.initialize()

            # Initialize monitoring components
            perf_log_path = Path(__file__).parent / "logs" / "performance_staging.log"
            self.performance_monitor = PerformanceMonitor(str(perf_log_path))
            self.health_checker = HealthChecker(self.db_manager)

            self.logger.info("✅ Monitoring system initialized")
            return True

        except Exception as e:
            self.logger.error(f"❌ Failed to initialize monitoring: {e}")
            return False

    def run_performance_tests(self):
        """Run comprehensive performance tests."""
        self.logger.info("⚡ Running performance tests...")

        try:
            with self.db_manager.get_session_context() as session:
                repository = JobRepository(session)

                # Define test operations
                test_operations = [
                    ("count_all_jobs", lambda: repository.count()),
                    ("search_by_title", lambda: repository.search_jobs(title="Engineer", limit=10)),
                    ("search_by_company", lambda: repository.search_jobs(company="TechCorp", limit=10)),
                    ("get_recent_jobs", lambda: repository.get_recent_jobs(days=7, limit=20)),
                    ("get_jobs_by_company", lambda: repository.get_jobs_by_company("Staging", limit=10)),
                    ("get_job_statistics", lambda: repository.get_jobs_stats()),
                    ("search_with_filters", lambda: repository.search_jobs(
                        title="Engineer",
                        location="Remote",
                        employment_type="Full-time",
                        limit=5
                    ))
                ]

                # Run performance tests
                results = []
                for operation_name, operation_func in test_operations:
                    result, metric = self.performance_monitor.measure_operation(operation_name, operation_func)
                    results.append(metric)
                    self.logger.info(f"✅ {operation_name}: {metric['duration_ms']}ms")

                # Get performance summary
                summary = self.performance_monitor.get_performance_summary()
                self.logger.info(f"📊 Performance Summary: {summary}")

                return results, summary

        except Exception as e:
            self.logger.error(f"❌ Performance tests failed: {e}")
            return [], {}

    def run_health_checks(self):
        """Run health check monitoring."""
        self.logger.info("🏥 Running health checks...")

        try:
            health_result = self.health_checker.full_health_check()

            if health_result["overall_status"] == "healthy":
                self.logger.info(f"✅ Health check passed: {health_result['check_duration_ms']}ms")
            else:
                self.logger.error(f"❌ Health check failed: {health_result}")

            # Log detailed health information
            health_log_path = Path(__file__).parent / "logs" / "health_checks.log"
            with open(health_log_path, 'a') as f:
                f.write(f"{json.dumps(health_result)}\n")

            return health_result

        except Exception as e:
            self.logger.error(f"❌ Health check failed: {e}")
            return {"overall_status": "unhealthy", "error": str(e)}

    def generate_monitoring_report(self, performance_results, performance_summary, health_result):
        """Generate comprehensive monitoring report."""
        report = f"""
# Staging Environment Monitoring Report
## LinkedIn Job Agent - Database System (US-001)

**Monitoring Timestamp:** {datetime.now(timezone.utc).isoformat()}

## Health Check Results
- **Overall Status:** {'✅ HEALTHY' if health_result.get('overall_status') == 'healthy' else '❌ UNHEALTHY'}
- **Database Connectivity:** {'✅ HEALTHY' if health_result.get('connectivity', {}).get('connectivity') == 'healthy' else '❌ UNHEALTHY'}
- **Database Operations:** {'✅ HEALTHY' if health_result.get('operations', {}).get('operations') == 'healthy' else '❌ UNHEALTHY'}
- **Health Check Duration:** {health_result.get('check_duration_ms', 0):.2f}ms

## Performance Metrics
- **Total Operations Tested:** {performance_summary.get('total_operations', 0)}
- **Success Rate:** {100 - performance_summary.get('error_rate', 0):.1f}%
- **Average Response Time:** {performance_summary.get('avg_duration_ms', 0):.2f}ms
- **Min Response Time:** {performance_summary.get('min_duration_ms', 0):.2f}ms
- **Max Response Time:** {performance_summary.get('max_duration_ms', 0):.2f}ms
- **Operations Under 50ms:** {performance_summary.get('operations_under_50ms', 0)}/{performance_summary.get('total_operations', 0)}

## Performance Test Results
"""

        for i, result in enumerate(performance_results, 1):
            status_icon = "✅" if result.get('status') == 'success' else "❌"
            report += f"**{i}. {result.get('operation', 'Unknown')}:** {status_icon} {result.get('duration_ms', 0):.2f}ms\n"

        report += f"""
## Database Information
- **Environment:** Staging
- **Database Type:** SQLite
- **Job Count:** {health_result.get('operations', {}).get('job_count', 'Unknown')}

## Alerts and Recommendations
"""

        # Add alerts based on performance
        if performance_summary.get('max_duration_ms', 0) > 50:
            report += "⚠️ **Warning:** Some operations exceeded 50ms response time target\n"

        if performance_summary.get('error_rate', 0) > 0:
            report += "⚠️ **Warning:** Some operations failed during testing\n"

        if health_result.get('overall_status') != 'healthy':
            report += "🚨 **Critical:** Health checks indicate system issues\n"

        if performance_summary.get('error_rate', 0) == 0 and performance_summary.get('max_duration_ms', 0) <= 50:
            report += "✅ **All systems operating within acceptable parameters**\n"

        # Write report to file
        report_path = Path(__file__).parent / "logs" / "monitoring_report.md"
        with open(report_path, 'w') as f:
            f.write(report)

        self.logger.info(f"📊 Monitoring report generated: {report_path}")
        return report

    def run_full_monitoring(self):
        """Execute comprehensive monitoring suite."""
        self.logger.info("🚀 Starting comprehensive staging monitoring...")

        try:
            if not self.initialize():
                raise Exception("Failed to initialize monitoring system")

            # Run health checks
            health_result = self.run_health_checks()

            # Run performance tests
            performance_results, performance_summary = self.run_performance_tests()

            # Generate monitoring report
            report = self.generate_monitoring_report(performance_results, performance_summary, health_result)

            self.logger.info("🎉 Comprehensive monitoring completed successfully!")
            print(report)

            return True

        except Exception as e:
            self.logger.error(f"💥 Monitoring failed: {e}")
            return False

        finally:
            if self.db_manager:
                self.db_manager.close()


if __name__ == "__main__":
    monitor = StagingMonitor()
    success = monitor.run_full_monitoring()
    sys.exit(0 if success else 1)