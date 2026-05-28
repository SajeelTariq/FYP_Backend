from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('monitoring', '0008_htmldifference_change_category'),
    ]

    operations = [
        migrations.AddField(
            model_name='competitor',
            name='onboarding_status',
            field=models.CharField(
                choices=[
                    ('pending', 'Pending'),
                    ('scraping', 'Scraping Pages'),
                    ('indexing', 'Building AI Index'),
                    ('ready', 'Ready'),
                    ('error', 'Error'),
                ],
                default='ready',
                help_text='Tracks initial data pipeline progress after competitor is added',
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='competitor',
            name='onboarding_error',
            field=models.CharField(
                blank=True,
                default='',
                help_text='Error message if onboarding_status is error',
                max_length=500,
            ),
        ),
    ]
