# Generated by Django 3.2.19 on 2023-05-12 14:14

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('notifications', '0002_notificationpreference'),
    ]

    operations = [
        migrations.AlterField(
            model_name='notification',
            name='app_name',
            field=models.CharField(choices=[('DISCUSSION', 'Discussion')], db_index=True, max_length=64),
        ),
    ]
