"""Tests for PDF report card generation."""

import pytest

from app.services.results_engine import StudentReportCard, SubjectResult
from app.services.reports.pdf_report_card import generate_report_card_pdf


@pytest.fixture
def sample_report() -> StudentReportCard:
    return StudentReportCard(
        student_id="st-001",
        student_name="Barack Ochieng",
        admission_number="MSS/2026/001",
        class_name="Form 3",
        stream_name="East",
        term_name="Term 1",
        academic_year="2026",
        subjects=[
            SubjectResult(
                subject_id="s1", subject_name="Mathematics",
                total_score=78.0, max_possible=100.0, percentage=78.0,
                grade="A-", points=11, assessments=[],
            ),
            SubjectResult(
                subject_id="s2", subject_name="English",
                total_score=65.0, max_possible=100.0, percentage=65.0,
                grade="B", points=9, assessments=[],
            ),
            SubjectResult(
                subject_id="s3", subject_name="Kiswahili",
                total_score=82.0, max_possible=100.0, percentage=82.0,
                grade="A", points=12, assessments=[],
            ),
        ],
        overall_total=225.0,
        overall_mean=75.0,
        overall_grade="A-",
        overall_points=11,
        rank_in_class=3,
        total_subjects=3,
        teacher_remarks="Good performance. Continue working hard.",
        principal_remarks="Approved. Well done.",
    )


class TestPDFGenerator:
    def test_generates_valid_pdf(self, sample_report):
        pdf_bytes = generate_report_card_pdf(sample_report, "Test Academy")
        assert isinstance(pdf_bytes, bytes)
        assert len(pdf_bytes) > 1000  # PDFs are at least 1 KB
        # Check PDF header
        assert pdf_bytes[:5] == b"%PDF-"

    def test_pdf_with_empty_subjects(self):
        report = StudentReportCard(
            student_id="st-002",
            student_name="No Subjects Student",
            admission_number="MSS/000",
            class_name="Form 1",
            stream_name=None,
            term_name="Term 1",
            academic_year="2026",
            subjects=[],
            overall_total=0,
            overall_mean=0,
            overall_grade="E",
            overall_points=1,
            rank_in_class=40,
            total_subjects=0,
            teacher_remarks="Unsatisfactory.",
            principal_remarks="See the Principal.",
        )
        pdf_bytes = generate_report_card_pdf(report, "Test Academy")
        assert pdf_bytes[:5] == b"%PDF-"

    def test_pdf_size_grows_with_subjects(self, sample_report):
        small = generate_report_card_pdf(sample_report, "Test")
        # Add 10 more subjects
        for i in range(10):
            sample_report.subjects.append(
                SubjectResult(
                    subject_id=f"s{i}",
                    subject_name=f"Subject {i}",
                    total_score=70.0, max_possible=100.0,
                    percentage=70.0, grade="B+", points=10,
                    assessments=[],
                )
            )
        large = generate_report_card_pdf(sample_report, "Test")
        assert len(large) > len(small)
