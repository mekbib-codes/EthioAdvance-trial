from django import forms
from child.models import Status

class StatusForm(forms.ModelForm):
    class Meta:
        model = Status
        fields = [
            'sessions_summary',
            'strengths',
            'weaknesses',
            'improvement_notes',
            'mock_exam_graph',
            'attendance_rate',
        ]