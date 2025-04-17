from django import forms
from .models import Report
from datetime import datetime, timedelta

class ReportSummaryForm(forms.ModelForm):
    class Meta:
        model = Report
        fields = ['from_date', 'to_date', 'total_sessions_conducted', 'average_duration_per_session']
        widgets = {
            'from_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'to_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'average_duration_per_session': forms.TimeInput(attrs={'type': 'time'}),
        }

    def clean(self):
        """Override the clean method to serialize datetime, time, and timedelta objects."""
        cleaned_data = super().clean()

        # Serialize datetime fields
        for field in ['from_date', 'to_date']:
            value = cleaned_data.get(field)
            if isinstance(value, datetime):
                cleaned_data[field] = value.isoformat()  # Convert to ISO 8601 string

        # Serialize time fields
        if 'average_duration_per_session' in cleaned_data:
            value = cleaned_data['average_duration_per_session']
            if isinstance(value, timedelta):
                # Convert timedelta to HH:MM:SS format
                total_seconds = int(value.total_seconds())
                hours, remainder = divmod(total_seconds, 3600)
                minutes, seconds = divmod(remainder, 60)
                cleaned_data['average_duration_per_session'] = f"{hours:02}:{minutes:02}:{seconds:02}"

        return cleaned_data

class SessionInsightForm(forms.Form):
    strengths = forms.CharField()
    weaknesses = forms.CharField()
    goals_achieved = forms.CharField()
    learning_material_prepared = forms.CharField()
    child_participation = forms.CharField(widget=forms.Textarea(attrs={'rows': 4}), required=True)

    def clean(self):
        cleaned_data = super().clean()
        many_to_many_fields = ['strengths', 'weaknesses', 'goals_achieved', 'learning_material_prepared']

        for field in many_to_many_fields:
            raw_input = cleaned_data.get(field, '')
            cleaned_data[field] = [item.strip() for item in raw_input.split(',') if item.strip()]

        return cleaned_data

class QuizAssignmentForm(forms.ModelForm):
    class Meta:
        model = Report
        fields = ['number_of_quizzes_prepared', 'average_quiz_score', 'completion_percentage', 'completion_notes']

class MockExamForm(forms.ModelForm):
    class Meta:
        model = Report
        fields = [
            'number_of_mock_exams_prepared',
            'mock_exam_result_overview',
            'mock_exam_strengths',
            'mock_exam_improvement_areas'
        ]
