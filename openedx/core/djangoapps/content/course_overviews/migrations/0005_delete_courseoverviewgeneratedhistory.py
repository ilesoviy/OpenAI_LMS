from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('course_overviews', '0004_courseoverview_org'),
    ]

    operations = [
        migrations.DeleteModel(
            name='CourseOverviewGeneratedHistory',
        ),
    ]
