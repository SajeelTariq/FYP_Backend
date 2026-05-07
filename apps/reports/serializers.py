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
    days = serializers.IntegerField(min_value=1, max_value=7, help_text="1 to 7 days")
    competitor_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        allow_empty=True,
        help_text="Leave empty to include all competitors",
    )

    def get_period(self) -> tuple[date, date]:
        days = self.validated_data['days']
        end = date.today()
        start = end - timedelta(days=days - 1)
        return start, end
