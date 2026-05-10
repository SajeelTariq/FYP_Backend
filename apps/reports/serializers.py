from datetime import date, timedelta
from rest_framework import serializers
from .models import Report


class ReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = Report
        fields = [
            'id', 'report_type', 'status', 'period_start', 'period_end',
            'content', 'error_message', 'created_at', 'completed_at',
        ]
        read_only_fields = ['id', 'status', 'content', 'error_message', 'created_at', 'completed_at']


class ReportListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for list view — excludes heavy content field."""
    class Meta:
        model = Report
        fields = [
            'id', 'report_type', 'status', 'period_start', 'period_end',
            'created_at', 'completed_at',
        ]


class GenerateReportSerializer(serializers.Serializer):
    report_type = serializers.ChoiceField(choices=['executive', 'analyst'])
    period_start = serializers.DateField(help_text="Start date (YYYY-MM-DD)")
    period_end = serializers.DateField(help_text="End date (YYYY-MM-DD)")
    competitor_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=True,
        allow_empty=True,
        help_text="List of competitor IDs. Pass an empty array [] to include all competitors.",
    )

    def validate(self, data):
        start = data.get('period_start')
        end = data.get('period_end')

        if start and end:
            if end < start:
                raise serializers.ValidationError("period_end must be after period_start.")
            if (end - start).days > 30:
                raise serializers.ValidationError("Date range cannot exceed 30 days.")
            if end > date.today():
                raise serializers.ValidationError("period_end cannot be in the future.")

        return data

    def get_period(self) -> tuple[date, date]:
        return self.validated_data['period_start'], self.validated_data['period_end']
