"""SQLite storage layer for locator repository."""

from __future__ import annotations

import inspectiq.bootstrap  # noqa: F401 — patch sqlite3 before SQLAlchemy

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text, create_engine, func
from sqlalchemy.orm import DeclarativeBase, Session, relationship, sessionmaker

from inspectiq.domain.models import LocatorCandidate, Platform, ProjectSummary, SaveElementRequest


class Base(DeclarativeBase):
    pass


class ProjectORM(Base):
    __tablename__ = "projects"
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    features = relationship("FeatureORM", back_populates="project", cascade="all, delete-orphan")


class FeatureORM(Base):
    __tablename__ = "features"
    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    name = Column(String, nullable=False)
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    project = relationship("ProjectORM", back_populates="features")
    screens = relationship("ScreenORM", back_populates="feature", cascade="all, delete-orphan")


class ScreenORM(Base):
    __tablename__ = "screens"
    id = Column(Integer, primary_key=True)
    feature_id = Column(Integer, ForeignKey("features.id"), nullable=False)
    name = Column(String, nullable=False)
    platform = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    feature = relationship("FeatureORM", back_populates="screens")
    elements = relationship("SavedElementORM", back_populates="screen", cascade="all, delete-orphan")


class SavedElementORM(Base):
    __tablename__ = "saved_elements"
    id = Column(Integer, primary_key=True)
    screen_id = Column(Integer, ForeignKey("screens.id"), nullable=False)
    name = Column(String, nullable=False)
    element_type = Column(String)
    class_name = Column(String)
    properties_json = Column(Text, default="{}")
    bounds = Column(String)
    captured_at = Column(DateTime, default=datetime.utcnow)
    screen = relationship("ScreenORM", back_populates="elements")
    locators = relationship("LocatorRecordORM", back_populates="element", cascade="all, delete-orphan")
    artifact = relationship("ArtifactORM", back_populates="element", uselist=False, cascade="all, delete-orphan")


class LocatorRecordORM(Base):
    __tablename__ = "locator_records"
    id = Column(Integer, primary_key=True)
    element_id = Column(Integer, ForeignKey("saved_elements.id"), nullable=False)
    locator_type = Column(String, nullable=False)
    locator_value = Column(Text, nullable=False)
    stability_score = Column(Float, default=0)
    uniqueness_score = Column(Float, default=0)
    maintainability_score = Column(Float, default=0)
    overall_score = Column(Float, default=0)
    recommended = Column(Integer, default=0)
    reason = Column(Text)
    is_primary = Column(Integer, default=0)
    element = relationship("SavedElementORM", back_populates="locators")


class ArtifactORM(Base):
    __tablename__ = "artifacts"
    id = Column(Integer, primary_key=True)
    element_id = Column(Integer, ForeignKey("saved_elements.id"), nullable=False)
    screenshot_path = Column(String)
    xml_path = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow)
    element = relationship("SavedElementORM", back_populates="artifact")


class StorageService:
    def __init__(self, db_path: Optional[str] = None, artifacts_dir: Optional[str] = None):
        home = Path.home() / ".droidlens"
        legacy = Path.home() / ".inspectiq"
        if not home.exists() and legacy.exists():
            home = legacy
        home.mkdir(parents=True, exist_ok=True)
        self.db_path = db_path or str(home / ("droidlens.db" if home.name == ".droidlens" else "inspectiq.db"))
        if home.name == ".droidlens" and not Path(self.db_path).exists() and (legacy / "inspectiq.db").exists():
            self.db_path = str(legacy / "inspectiq.db")
        self.artifacts_dir = Path(artifacts_dir or home / "artifacts")
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
        self.engine = create_engine(f"sqlite:///{self.db_path}")
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)

    def _session(self) -> Session:
        return self.SessionLocal()

    def list_projects(self) -> list[ProjectSummary]:
        with self._session() as session:
            projects = session.query(ProjectORM).all()
            result = []
            for p in projects:
                feat_count = len(p.features)
                elem_count = sum(len(s.elements) for f in p.features for s in f.screens)
                result.append(
                    ProjectSummary(
                        id=p.id,
                        name=p.name,
                        feature_count=feat_count,
                        element_count=elem_count,
                        created_at=p.created_at or datetime.utcnow(),
                    )
                )
            return result

    def _get_or_create_project(self, session: Session, name: str) -> ProjectORM:
        p = session.query(ProjectORM).filter_by(name=name).first()
        if not p:
            p = ProjectORM(name=name)
            session.add(p)
            session.flush()
        return p

    def _get_or_create_feature(self, session: Session, project: ProjectORM, name: str) -> FeatureORM:
        f = session.query(FeatureORM).filter_by(project_id=project.id, name=name).first()
        if not f:
            f = FeatureORM(project_id=project.id, name=name)
            session.add(f)
            session.flush()
        return f

    def _get_or_create_screen(self, session: Session, feature: FeatureORM, name: str, platform: Platform) -> ScreenORM:
        s = session.query(ScreenORM).filter_by(feature_id=feature.id, name=name).first()
        if not s:
            s = ScreenORM(feature_id=feature.id, name=name, platform=platform.value)
            session.add(s)
            session.flush()
        return s

    def save_element(self, request: SaveElementRequest) -> dict:
        import base64

        with self._session() as session:
            project = self._get_or_create_project(session, request.project_name)
            feature = self._get_or_create_feature(session, project, request.feature_name)
            screen = self._get_or_create_screen(session, feature, request.screen_name, request.platform)

            bounds_str = request.element.bounds.to_string() if request.element.bounds else None
            element = SavedElementORM(
                screen_id=screen.id,
                name=request.element_name,
                element_type=request.element.display_type(),
                class_name=request.element.class_name,
                properties_json=json.dumps(request.element.model_dump(mode="json")),
                bounds=bounds_str,
            )
            session.add(element)
            session.flush()

            for loc in request.all_locators or [request.primary_locator]:
                is_primary = loc.locator_type == request.primary_locator.locator_type and loc.value == request.primary_locator.value
                session.add(
                    LocatorRecordORM(
                        element_id=element.id,
                        locator_type=loc.locator_type.value,
                        locator_value=loc.value,
                        stability_score=loc.scores.stability,
                        uniqueness_score=loc.scores.uniqueness,
                        maintainability_score=loc.scores.maintainability,
                        overall_score=loc.scores.overall,
                        recommended=1 if loc.recommended else 0,
                        reason=loc.reason,
                        is_primary=1 if is_primary else 0,
                    )
                )

            screenshot_path = None
            xml_path = None
            elem_dir = self.artifacts_dir / request.project_name / request.feature_name / request.screen_name
            elem_dir.mkdir(parents=True, exist_ok=True)

            if request.screenshot_base64:
                screenshot_path = str(elem_dir / f"{request.element_name}.png")
                with open(screenshot_path, "wb") as f:
                    f.write(base64.b64decode(request.screenshot_base64))

            if request.xml_content:
                xml_path = str(elem_dir / f"{request.screen_name}.xml")
                with open(xml_path, "w", encoding="utf-8") as f:
                    f.write(request.xml_content)

            session.add(ArtifactORM(element_id=element.id, screenshot_path=screenshot_path, xml_path=xml_path))
            session.commit()

            return {
                "element_id": element.id,
                "project": request.project_name,
                "feature": request.feature_name,
                "screen": request.screen_name,
                "element": request.element_name,
                "screenshot_path": screenshot_path,
                "xml_path": xml_path,
            }
