from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0002_add_alerts_permission_and_alert_preference'),
    ]

    operations = [
        migrations.AddField(
            model_name='alertpreference',
            name='notify_news_mentions',
            field=models.BooleanField(default=True),
        ),
    ]
