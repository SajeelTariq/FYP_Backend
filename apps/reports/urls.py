from django.urls import path
from . import views

urlpatterns = [
    path('generate/', views.generate_report, name='report-generate'),
    path('', views.list_reports, name='report-list'),
    path('<int:report_id>/', views.report_detail, name='report-detail'),
    path('<int:report_id>/pdf/', views.download_report_pdf, name='report-pdf'),
    path('<int:report_id>/delete/', views.delete_report, name='report-delete'),
]
