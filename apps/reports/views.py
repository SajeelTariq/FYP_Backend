from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.http import HttpResponse

from .models import Report
from .serializers import GenerateReportSerializer, ReportSerializer, ReportListSerializer
from .tasks import generate_report_task
from .pdf_generator import generate_pdf


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def generate_report(request):
    serializer = GenerateReportSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    period_start, period_end = serializer.get_period()
    competitor_ids = serializer.validated_data.get('competitor_ids', [])

    report = Report.objects.create(
        user=request.user,
        report_type=serializer.validated_data['report_type'],
        status='pending',
        period_start=period_start,
        period_end=period_end,
    )

    if competitor_ids:
        from apps.monitoring.models import Competitor
        valid_competitors = Competitor.objects.filter(
            id__in=competitor_ids,
            user=request.user,
            is_deleted=False,
        )
        report.competitors.set(valid_competitors)

    generate_report_task.delay(report.id)

    return Response(
        {
            "message": "Report generation started.",
            "report_id": report.id,
            "status": report.status,
            "period_start": period_start,
            "period_end": period_end,
        },
        status=status.HTTP_202_ACCEPTED,
    )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_reports(request):
    from datetime import timedelta
    from django.utils import timezone

    reports = Report.objects.filter(user=request.user, status='completed')

    # Filter by type
    report_type = request.query_params.get('type')
    if report_type in ('executive', 'analyst'):
        reports = reports.filter(report_type=report_type)

    # Filter by period (how many days ago the report was created)
    period = request.query_params.get('period')
    VALID_PERIODS = {'7': 7, '30': 30, '90': 90}
    if period in VALID_PERIODS:
        since = timezone.now() - timedelta(days=VALID_PERIODS[period])
        reports = reports.filter(created_at__gte=since)

    serializer = ReportListSerializer(reports, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def report_detail(request, report_id):
    try:
        report = Report.objects.get(id=report_id, user=request.user)
    except Report.DoesNotExist:
        return Response({"error": "Report not found."}, status=status.HTTP_404_NOT_FOUND)
    serializer = ReportSerializer(report)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def download_report_pdf(request, report_id):
    try:
        report = Report.objects.get(id=report_id, user=request.user)
    except Report.DoesNotExist:
        return Response({"error": "Report not found."}, status=status.HTTP_404_NOT_FOUND)

    if report.status != 'completed':
        return Response(
            {"error": f"Report is not ready yet. Current status: {report.status}"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    pdf_bytes = generate_pdf(report)
    filename = f"report_{report.report_type}_{report.period_start}_{report.period_end}.pdf"

    response = HttpResponse(pdf_bytes, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_report(request, report_id):
    try:
        report = Report.objects.get(id=report_id, user=request.user)
    except Report.DoesNotExist:
        return Response({"error": "Report not found."}, status=status.HTTP_404_NOT_FOUND)
    report.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)
