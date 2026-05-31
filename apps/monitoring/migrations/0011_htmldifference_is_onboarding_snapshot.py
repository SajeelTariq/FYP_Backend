from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('monitoring', '0010_alter_competitor_onboarding_status_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='htmldifference',
            name='is_onboarding_snapshot',
            field=models.BooleanField(
                default=False,
                help_text='True for initial snapshots captured during competitor onboarding — excluded from the change feed',
            ),
        ),
    ]
