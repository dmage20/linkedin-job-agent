"""Repository pattern implementation for database operations."""

from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, asc, func
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from .models import JobModel
from .connection import get_db_session


class BaseRepository:
    """Base repository class with common CRUD operations."""

    def __init__(self, session: Session, model_class):
        self.session = session
        self.model_class = model_class

    def create(self, **kwargs) -> Any:
        """Create a new record."""
        try:
            instance = self.model_class(**kwargs)
            self.session.add(instance)
            self.session.commit()
            self.session.refresh(instance)
            return instance
        except IntegrityError as e:
            self.session.rollback()
            raise ValueError(f"Data integrity error: {str(e)}")
        except SQLAlchemyError as e:
            self.session.rollback()
            raise RuntimeError(f"Database error: {str(e)}")

    def get_by_id(self, record_id: int) -> Optional[Any]:
        """Get a record by ID."""
        try:
            return self.session.query(self.model_class).filter(
                self.model_class.id == record_id
            ).first()
        except SQLAlchemyError as e:
            raise RuntimeError(f"Database error: {str(e)}")

    def get_all(self, limit: Optional[int] = None, offset: int = 0) -> List[Any]:
        """Get all records with optional pagination."""
        try:
            query = self.session.query(self.model_class)
            if offset > 0:
                query = query.offset(offset)
            if limit:
                query = query.limit(limit)
            return query.all()
        except SQLAlchemyError as e:
            raise RuntimeError(f"Database error: {str(e)}")

    def update(self, record_id: int, **kwargs) -> Optional[Any]:
        """Update a record by ID."""
        try:
            instance = self.get_by_id(record_id)
            if not instance:
                return None

            for key, value in kwargs.items():
                if hasattr(instance, key):
                    setattr(instance, key, value)

            self.session.commit()
            self.session.refresh(instance)
            return instance
        except IntegrityError as e:
            self.session.rollback()
            raise ValueError(f"Data integrity error: {str(e)}")
        except SQLAlchemyError as e:
            self.session.rollback()
            raise RuntimeError(f"Database error: {str(e)}")

    def delete(self, record_id: int) -> bool:
        """Delete a record by ID."""
        try:
            instance = self.get_by_id(record_id)
            if not instance:
                return False

            self.session.delete(instance)
            self.session.commit()
            return True
        except SQLAlchemyError as e:
            self.session.rollback()
            raise RuntimeError(f"Database error: {str(e)}")

    def count(self) -> int:
        """Count total records."""
        try:
            return self.session.query(self.model_class).count()
        except SQLAlchemyError as e:
            raise RuntimeError(f"Database error: {str(e)}")


class JobRepository(BaseRepository):
    """Repository for job-specific database operations."""

    def __init__(self, session: Session):
        super().__init__(session, JobModel)

    def get_by_linkedin_id(self, linkedin_job_id: str) -> Optional[JobModel]:
        """Get a job by LinkedIn job ID."""
        try:
            return self.session.query(JobModel).filter(
                JobModel.linkedin_job_id == linkedin_job_id
            ).first()
        except SQLAlchemyError as e:
            raise RuntimeError(f"Database error: {str(e)}")

    def search_jobs(
        self,
        title: Optional[str] = None,
        company: Optional[str] = None,
        location: Optional[str] = None,
        employment_type: Optional[str] = None,
        experience_level: Optional[str] = None,
        is_remote: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
        order_by: str = "created_at",
        order_direction: str = "desc"
    ) -> List[JobModel]:
        """Search jobs with multiple filters."""
        try:
            query = self.session.query(JobModel)

            # Apply filters
            if title:
                query = query.filter(JobModel.title.ilike(f"%{title}%"))
            if company:
                query = query.filter(JobModel.company.ilike(f"%{company}%"))
            if location:
                query = query.filter(JobModel.location.ilike(f"%{location}%"))
            if employment_type:
                query = query.filter(JobModel.employment_type == employment_type)
            if experience_level:
                query = query.filter(JobModel.experience_level == experience_level)
            if is_remote:
                query = query.filter(JobModel.is_remote == is_remote)

            # Apply ordering
            order_column = getattr(JobModel, order_by, JobModel.created_at)
            if order_direction.lower() == "asc":
                query = query.order_by(asc(order_column))
            else:
                query = query.order_by(desc(order_column))

            # Apply pagination
            query = query.offset(offset).limit(limit)

            return query.all()
        except SQLAlchemyError as e:
            raise RuntimeError(f"Database error: {str(e)}")

    def get_jobs_by_company(self, company: str, limit: int = 50) -> List[JobModel]:
        """Get all jobs from a specific company."""
        try:
            return self.session.query(JobModel).filter(
                JobModel.company.ilike(f"%{company}%")
            ).order_by(desc(JobModel.created_at)).limit(limit).all()
        except SQLAlchemyError as e:
            raise RuntimeError(f"Database error: {str(e)}")

    def get_recent_jobs(self, days: int = 7, limit: int = 100) -> List[JobModel]:
        """Get jobs posted in the last N days."""
        try:
            from datetime import datetime, timedelta, timezone
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)

            return self.session.query(JobModel).filter(
                JobModel.created_at >= cutoff_date
            ).order_by(desc(JobModel.created_at)).limit(limit).all()
        except SQLAlchemyError as e:
            raise RuntimeError(f"Database error: {str(e)}")

    def get_jobs_stats(self) -> Dict[str, Any]:
        """Get statistical information about jobs."""
        try:
            total_jobs = self.count()

            # Count by employment type
            employment_stats = self.session.query(
                JobModel.employment_type,
                func.count(JobModel.id)
            ).group_by(JobModel.employment_type).all()

            # Count by experience level
            experience_stats = self.session.query(
                JobModel.experience_level,
                func.count(JobModel.id)
            ).group_by(JobModel.experience_level).all()

            # Count by remote status
            remote_stats = self.session.query(
                JobModel.is_remote,
                func.count(JobModel.id)
            ).group_by(JobModel.is_remote).all()

            # Top companies by job count
            top_companies = self.session.query(
                JobModel.company,
                func.count(JobModel.id)
            ).group_by(JobModel.company).order_by(
                desc(func.count(JobModel.id))
            ).limit(10).all()

            return {
                "total_jobs": total_jobs,
                "employment_type_breakdown": dict(employment_stats),
                "experience_level_breakdown": dict(experience_stats),
                "remote_status_breakdown": dict(remote_stats),
                "top_companies": dict(top_companies)
            }
        except SQLAlchemyError as e:
            raise RuntimeError(f"Database error: {str(e)}")

    def bulk_create(self, jobs_data: List[Dict[str, Any]]) -> List[JobModel]:
        """Create multiple jobs in a single transaction."""
        try:
            jobs = []
            for job_data in jobs_data:
                job = JobModel(**job_data)
                jobs.append(job)
                self.session.add(job)

            self.session.commit()

            # Refresh all instances to get IDs
            for job in jobs:
                self.session.refresh(job)

            return jobs
        except IntegrityError as e:
            self.session.rollback()
            raise ValueError(f"Data integrity error during bulk create: {str(e)}")
        except SQLAlchemyError as e:
            self.session.rollback()
            raise RuntimeError(f"Database error during bulk create: {str(e)}")

    def upsert_job(self, job_data: Dict[str, Any]) -> JobModel:
        """Create or update a job based on LinkedIn job ID."""
        try:
            linkedin_job_id = job_data.get("linkedin_job_id")
            if not linkedin_job_id:
                raise ValueError("linkedin_job_id is required for upsert operation")

            # Check if job exists
            existing_job = self.get_by_linkedin_id(linkedin_job_id)

            if existing_job:
                # Update existing job
                for key, value in job_data.items():
                    if hasattr(existing_job, key) and key != "id":
                        setattr(existing_job, key, value)

                self.session.commit()
                self.session.refresh(existing_job)
                return existing_job
            else:
                # Create new job
                return self.create(**job_data)

        except SQLAlchemyError as e:
            self.session.rollback()
            raise RuntimeError(f"Database error during upsert: {str(e)}")

    def find_jobs_by_applicant_count(
        self,
        min_applicants: Optional[int] = None,
        max_applicants: Optional[int] = None,
        order_by_competition: str = "asc"
    ) -> List[JobModel]:
        """Find jobs filtered by applicant count for competitive analysis."""
        try:
            query = self.session.query(JobModel).filter(
                JobModel.applicant_count.isnot(None)
            )

            if min_applicants is not None:
                query = query.filter(JobModel.applicant_count >= min_applicants)

            if max_applicants is not None:
                query = query.filter(JobModel.applicant_count <= max_applicants)

            # Order by competition level
            if order_by_competition == "asc":
                query = query.order_by(JobModel.applicant_count.asc())
            else:
                query = query.order_by(JobModel.applicant_count.desc())

            return query.all()
        except SQLAlchemyError as e:
            raise RuntimeError(f"Database error: {str(e)}")

    def get_low_competition_jobs(self, max_applicants: int = 10) -> List[JobModel]:
        """Find jobs with low competition (few applicants) for strategic targeting."""
        return self.find_jobs_by_applicant_count(max_applicants=max_applicants)

    def get_competition_statistics(self) -> Dict[str, Any]:
        """Get applicant count statistics for market intelligence."""
        try:
            # Jobs with applicant count data
            jobs_with_count = self.session.query(JobModel).filter(
                JobModel.applicant_count.isnot(None)
            )

            total_with_data = jobs_with_count.count()
            if total_with_data == 0:
                return {"message": "No applicant count data available"}

            # Statistics
            avg_applicants = self.session.query(
                func.avg(JobModel.applicant_count)
            ).filter(JobModel.applicant_count.isnot(None)).scalar()

            min_applicants = self.session.query(
                func.min(JobModel.applicant_count)
            ).filter(JobModel.applicant_count.isnot(None)).scalar()

            max_applicants = self.session.query(
                func.max(JobModel.applicant_count)
            ).filter(JobModel.applicant_count.isnot(None)).scalar()

            # Competition levels
            low_competition = jobs_with_count.filter(JobModel.applicant_count <= 10).count()
            medium_competition = jobs_with_count.filter(
                JobModel.applicant_count.between(11, 50)
            ).count()
            high_competition = jobs_with_count.filter(JobModel.applicant_count > 50).count()

            return {
                "total_jobs_with_data": total_with_data,
                "average_applicants": round(float(avg_applicants), 2) if avg_applicants else 0,
                "min_applicants": min_applicants,
                "max_applicants": max_applicants,
                "competition_breakdown": {
                    "low_competition_jobs": low_competition,  # ≤10 applicants
                    "medium_competition_jobs": medium_competition,  # 11-50 applicants
                    "high_competition_jobs": high_competition  # >50 applicants
                }
            }
        except SQLAlchemyError as e:
            raise RuntimeError(f"Database error: {str(e)}")


def get_job_repository(session: Optional[Session] = None) -> JobRepository:
    """Factory function to get a job repository instance."""
    if session:
        return JobRepository(session)

    # Use dependency injection for session
    with next(get_db_session()) as db_session:
        return JobRepository(db_session)