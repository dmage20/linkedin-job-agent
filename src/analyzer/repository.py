"""Repository for job analysis data operations."""

from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any, Union
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy import desc, asc, func, and_, or_

from ..database.repository import BaseRepository
from .models import (
    JobAnalysisModel,
    CompetitionAnalysisModel,
    UserProfileModel,
    JobMatchModel,
    AnalysisStatus,
    AnalysisType
)


class AnalysisRepository(BaseRepository):
    """Repository for job analysis database operations."""

    def __init__(self, session: Session):
        # Initialize with JobAnalysisModel as the default model
        super().__init__(session, JobAnalysisModel)

    # Job Analysis Operations
    def create_job_analysis(self, **kwargs) -> JobAnalysisModel:
        """Create a new job analysis record."""
        try:
            analysis = JobAnalysisModel(**kwargs)
            self.session.add(analysis)
            self.session.commit()
            self.session.refresh(analysis)
            return analysis
        except IntegrityError as e:
            self.session.rollback()
            raise ValueError(f"Job analysis creation failed: {str(e)}")
        except SQLAlchemyError as e:
            self.session.rollback()
            raise RuntimeError(f"Database error during job analysis creation: {str(e)}")

    def get_job_analysis(self, analysis_id: int) -> Optional[JobAnalysisModel]:
        """Get job analysis by ID."""
        try:
            return self.session.query(JobAnalysisModel).filter(
                JobAnalysisModel.id == analysis_id
            ).first()
        except SQLAlchemyError as e:
            raise RuntimeError(f"Database error: {str(e)}")

    def get_job_analyses_for_job(
        self,
        job_id: int,
        analysis_type: Optional[AnalysisType] = None,
        status: Optional[AnalysisStatus] = None
    ) -> List[JobAnalysisModel]:
        """Get all analyses for a specific job."""
        try:
            query = self.session.query(JobAnalysisModel).filter(
                JobAnalysisModel.job_id == job_id
            )

            if analysis_type:
                query = query.filter(JobAnalysisModel.analysis_type == analysis_type)

            if status:
                query = query.filter(JobAnalysisModel.status == status)

            return query.order_by(desc(JobAnalysisModel.created_at)).all()
        except SQLAlchemyError as e:
            raise RuntimeError(f"Database error: {str(e)}")

    def update_job_analysis_status(
        self,
        analysis_id: int,
        status: AnalysisStatus,
        **update_data
    ) -> Optional[JobAnalysisModel]:
        """Update job analysis status and related data."""
        try:
            analysis = self.get_job_analysis(analysis_id)
            if not analysis:
                return None

            # Update status
            analysis.status = status

            # Update other fields if provided
            for key, value in update_data.items():
                if hasattr(analysis, key):
                    setattr(analysis, key, value)

            self.session.commit()
            self.session.refresh(analysis)
            return analysis

        except SQLAlchemyError as e:
            self.session.rollback()
            raise RuntimeError(f"Database error during analysis update: {str(e)}")

    def bulk_create_job_analyses(self, analyses_data: List[Dict[str, Any]]) -> List[JobAnalysisModel]:
        """Create multiple job analyses in a single transaction."""
        try:
            analyses = []
            for data in analyses_data:
                analysis = JobAnalysisModel(**data)
                analyses.append(analysis)
                self.session.add(analysis)

            self.session.commit()

            # Refresh all instances
            for analysis in analyses:
                self.session.refresh(analysis)

            return analyses

        except IntegrityError as e:
            self.session.rollback()
            raise ValueError(f"Bulk analysis creation failed: {str(e)}")
        except SQLAlchemyError as e:
            self.session.rollback()
            raise RuntimeError(f"Database error during bulk creation: {str(e)}")

    def find_analyses_for_retry(
        self,
        max_retries: int = 3,
        status: AnalysisStatus = AnalysisStatus.FAILED
    ) -> List[JobAnalysisModel]:
        """Find analyses that failed and can be retried."""
        try:
            return self.session.query(JobAnalysisModel).filter(
                and_(
                    JobAnalysisModel.status == status,
                    JobAnalysisModel.retry_count < max_retries
                )
            ).order_by(JobAnalysisModel.created_at).all()
        except SQLAlchemyError as e:
            raise RuntimeError(f"Database error: {str(e)}")

    # Competition Analysis Operations
    def create_competition_analysis(self, **kwargs) -> CompetitionAnalysisModel:
        """Create a new competition analysis record."""
        try:
            analysis = CompetitionAnalysisModel(**kwargs)
            self.session.add(analysis)
            self.session.commit()
            self.session.refresh(analysis)
            return analysis
        except IntegrityError as e:
            self.session.rollback()
            raise ValueError(f"Competition analysis creation failed: {str(e)}")
        except SQLAlchemyError as e:
            self.session.rollback()
            raise RuntimeError(f"Database error during competition analysis creation: {str(e)}")

    def get_competition_analysis_for_job(self, job_id: int) -> Optional[CompetitionAnalysisModel]:
        """Get competition analysis for a specific job."""
        try:
            return self.session.query(CompetitionAnalysisModel).filter(
                CompetitionAnalysisModel.job_id == job_id
            ).first()
        except SQLAlchemyError as e:
            raise RuntimeError(f"Database error: {str(e)}")

    def update_competition_analysis(
        self,
        analysis_id: int,
        **update_data
    ) -> Optional[CompetitionAnalysisModel]:
        """Update competition analysis."""
        try:
            analysis = self.session.query(CompetitionAnalysisModel).filter(
                CompetitionAnalysisModel.id == analysis_id
            ).first()

            if not analysis:
                return None

            for key, value in update_data.items():
                if hasattr(analysis, key):
                    setattr(analysis, key, value)

            self.session.commit()
            self.session.refresh(analysis)
            return analysis

        except SQLAlchemyError as e:
            self.session.rollback()
            raise RuntimeError(f"Database error during competition analysis update: {str(e)}")

    # User Profile Operations
    def create_user_profile(self, **kwargs) -> UserProfileModel:
        """Create a new user profile."""
        try:
            profile = UserProfileModel(**kwargs)
            self.session.add(profile)
            self.session.commit()
            self.session.refresh(profile)
            return profile
        except IntegrityError as e:
            self.session.rollback()
            raise ValueError(f"User profile creation failed: {str(e)}")
        except SQLAlchemyError as e:
            self.session.rollback()
            raise RuntimeError(f"Database error during profile creation: {str(e)}")

    def get_user_profile_by_user_id(self, user_id: str) -> Optional[UserProfileModel]:
        """Get user profile by user_id."""
        try:
            return self.session.query(UserProfileModel).filter(
                UserProfileModel.user_id == user_id
            ).first()
        except SQLAlchemyError as e:
            raise RuntimeError(f"Database error: {str(e)}")

    def get_user_profile(self, profile_id: int) -> Optional[UserProfileModel]:
        """Get user profile by ID."""
        try:
            return self.session.query(UserProfileModel).filter(
                UserProfileModel.id == profile_id
            ).first()
        except SQLAlchemyError as e:
            raise RuntimeError(f"Database error: {str(e)}")

    def update_user_profile(
        self,
        profile_id: int,
        **update_data
    ) -> Optional[UserProfileModel]:
        """Update user profile."""
        try:
            profile = self.get_user_profile(profile_id)
            if not profile:
                return None

            # Update last_updated timestamp
            update_data['last_updated'] = datetime.now(timezone.utc)

            for key, value in update_data.items():
                if hasattr(profile, key):
                    setattr(profile, key, value)

            self.session.commit()
            self.session.refresh(profile)
            return profile

        except SQLAlchemyError as e:
            self.session.rollback()
            raise RuntimeError(f"Database error during profile update: {str(e)}")

    def upsert_user_profile(self, user_id: str, **profile_data) -> UserProfileModel:
        """Create or update user profile based on user_id."""
        try:
            existing_profile = self.get_user_profile_by_user_id(user_id)

            if existing_profile:
                # Update existing profile
                return self.update_user_profile(existing_profile.id, **profile_data)
            else:
                # Create new profile
                profile_data['user_id'] = user_id
                return self.create_user_profile(**profile_data)

        except SQLAlchemyError as e:
            self.session.rollback()
            raise RuntimeError(f"Database error during profile upsert: {str(e)}")

    # Job Match Operations
    def create_job_match(self, **kwargs) -> JobMatchModel:
        """Create a new job match record."""
        try:
            match = JobMatchModel(**kwargs)
            self.session.add(match)
            self.session.commit()
            self.session.refresh(match)
            return match
        except IntegrityError as e:
            self.session.rollback()
            raise ValueError(f"Job match creation failed: {str(e)}")
        except SQLAlchemyError as e:
            self.session.rollback()
            raise RuntimeError(f"Database error during job match creation: {str(e)}")

    def get_job_match(
        self,
        job_id: int,
        user_profile_id: int
    ) -> Optional[JobMatchModel]:
        """Get specific job match."""
        try:
            return self.session.query(JobMatchModel).filter(
                and_(
                    JobMatchModel.job_id == job_id,
                    JobMatchModel.user_profile_id == user_profile_id
                )
            ).first()
        except SQLAlchemyError as e:
            raise RuntimeError(f"Database error: {str(e)}")

    def get_job_matches_for_profile(
        self,
        user_profile_id: int,
        recommendation: Optional[str] = None,
        min_score: Optional[int] = None,
        limit: int = 100
    ) -> List[JobMatchModel]:
        """Get job matches for a user profile."""
        try:
            query = self.session.query(JobMatchModel).filter(
                JobMatchModel.user_profile_id == user_profile_id
            )

            if recommendation:
                query = query.filter(JobMatchModel.recommendation == recommendation)

            if min_score:
                query = query.filter(JobMatchModel.match_score >= min_score)

            return query.order_by(desc(JobMatchModel.match_score)).limit(limit).all()

        except SQLAlchemyError as e:
            raise RuntimeError(f"Database error: {str(e)}")

    def get_top_matches_for_profile(
        self,
        user_profile_id: int,
        limit: int = 10
    ) -> List[JobMatchModel]:
        """Get top job matches for a user profile."""
        return self.get_job_matches_for_profile(
            user_profile_id=user_profile_id,
            min_score=70,  # Only high-quality matches
            limit=limit
        )

    def update_match_user_interaction(
        self,
        match_id: int,
        interaction_type: str,
        timestamp: Optional[datetime] = None
    ) -> Optional[JobMatchModel]:
        """Update user interaction with a job match."""
        if timestamp is None:
            timestamp = datetime.now(timezone.utc)

        try:
            match = self.session.query(JobMatchModel).filter(
                JobMatchModel.id == match_id
            ).first()

            if not match:
                return None

            interaction_field = f"user_{interaction_type}"
            if hasattr(match, interaction_field):
                setattr(match, interaction_field, timestamp)

            self.session.commit()
            self.session.refresh(match)
            return match

        except SQLAlchemyError as e:
            self.session.rollback()
            raise RuntimeError(f"Database error during interaction update: {str(e)}")

    def bulk_create_job_matches(self, matches_data: List[Dict[str, Any]]) -> List[JobMatchModel]:
        """Create multiple job matches in a single transaction."""
        try:
            matches = []
            for data in matches_data:
                match = JobMatchModel(**data)
                matches.append(match)
                self.session.add(match)

            self.session.commit()

            # Refresh all instances
            for match in matches:
                self.session.refresh(match)

            return matches

        except IntegrityError as e:
            self.session.rollback()
            raise ValueError(f"Bulk match creation failed: {str(e)}")
        except SQLAlchemyError as e:
            self.session.rollback()
            raise RuntimeError(f"Database error during bulk match creation: {str(e)}")

    # Analytics and Statistics
    def get_analysis_statistics(self) -> Dict[str, Any]:
        """Get comprehensive analysis statistics."""
        try:
            # Total analyses
            total_analyses = self.session.query(JobAnalysisModel).count()

            # Analyses by status
            status_counts = self.session.query(
                JobAnalysisModel.status,
                func.count(JobAnalysisModel.id)
            ).group_by(JobAnalysisModel.status).all()

            # Analyses by type
            type_counts = self.session.query(
                JobAnalysisModel.analysis_type,
                func.count(JobAnalysisModel.id)
            ).group_by(JobAnalysisModel.analysis_type).all()

            # Average scores
            avg_quality = self.session.query(
                func.avg(JobAnalysisModel.quality_score)
            ).filter(JobAnalysisModel.quality_score.isnot(None)).scalar()

            avg_competition = self.session.query(
                func.avg(JobAnalysisModel.competition_score)
            ).filter(JobAnalysisModel.competition_score.isnot(None)).scalar()

            avg_match = self.session.query(
                func.avg(JobAnalysisModel.match_score)
            ).filter(JobAnalysisModel.match_score.isnot(None)).scalar()

            # API costs
            total_cost = self.session.query(
                func.sum(JobAnalysisModel.api_cost)
            ).filter(JobAnalysisModel.api_cost.isnot(None)).scalar() or 0.0

            return {
                "total_analyses": total_analyses,
                "completed_analyses": sum(count for status, count in status_counts if status == AnalysisStatus.COMPLETED),
                "failed_analyses": sum(count for status, count in status_counts if status == AnalysisStatus.FAILED),
                "pending_analyses": sum(count for status, count in status_counts if status == AnalysisStatus.PENDING),
                "analysis_by_status": dict(status_counts),
                "analysis_by_type": dict(type_counts),
                "average_scores": {
                    "quality": round(float(avg_quality), 2) if avg_quality else None,
                    "competition": round(float(avg_competition), 2) if avg_competition else None,
                    "matching": round(float(avg_match), 2) if avg_match else None
                },
                "total_api_cost": round(total_cost, 4)
            }

        except SQLAlchemyError as e:
            raise RuntimeError(f"Database error: {str(e)}")

    def get_match_statistics_for_profile(self, user_profile_id: int) -> Dict[str, Any]:
        """Get matching statistics for a specific user profile."""
        try:
            matches = self.session.query(JobMatchModel).filter(
                JobMatchModel.user_profile_id == user_profile_id
            )

            total_matches = matches.count()
            if total_matches == 0:
                return {"total_matches": 0, "message": "No matches found"}

            # Average match score
            avg_score = matches.with_entities(
                func.avg(JobMatchModel.match_score)
            ).scalar()

            # Recommendation breakdown
            recommendations = matches.with_entities(
                JobMatchModel.recommendation,
                func.count(JobMatchModel.id)
            ).group_by(JobMatchModel.recommendation).all()

            # User interactions
            viewed_count = matches.filter(JobMatchModel.user_viewed.isnot(None)).count()
            applied_count = matches.filter(JobMatchModel.user_applied.isnot(None)).count()
            bookmarked_count = matches.filter(JobMatchModel.user_bookmarked.isnot(None)).count()

            return {
                "total_matches": total_matches,
                "average_match_score": round(float(avg_score), 2) if avg_score else 0,
                "recommendations": dict(recommendations),
                "user_interactions": {
                    "viewed": viewed_count,
                    "applied": applied_count,
                    "bookmarked": bookmarked_count
                }
            }

        except SQLAlchemyError as e:
            raise RuntimeError(f"Database error: {str(e)}")

    def cleanup_old_analyses(self, days_old: int = 30) -> int:
        """Clean up old analysis records."""
        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_old)

            deleted_count = self.session.query(JobAnalysisModel).filter(
                and_(
                    JobAnalysisModel.created_at < cutoff_date,
                    JobAnalysisModel.status.in_([AnalysisStatus.COMPLETED, AnalysisStatus.FAILED])
                )
            ).delete()

            self.session.commit()
            return deleted_count

        except SQLAlchemyError as e:
            self.session.rollback()
            raise RuntimeError(f"Database error during cleanup: {str(e)}")


def get_analysis_repository(session: Optional[Session] = None) -> AnalysisRepository:
    """Factory function to get an analysis repository instance."""
    if session:
        return AnalysisRepository(session)

    # Use dependency injection for session
    from ..database.connection import get_db_session
    with next(get_db_session()) as db_session:
        return AnalysisRepository(db_session)