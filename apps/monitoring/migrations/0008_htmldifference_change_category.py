from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('monitoring', '0007_remove_description_from_newsarticle'),
    ]

    operations = [
        migrations.AddField(
            model_name='htmldifference',
            name='change_category',
            field=models.CharField(
                choices=[('critical', 'Critical'), ('non_critical', 'Non-Critical'), ('technical', 'Technical')],
                default='non_critical',
                help_text='critical=business-impacting, non_critical=minor visible change, technical=no visible content change',
                max_length=20,
            ),
        ),
    ]
