import django.core.validators
import django.db.models.deletion
import django.utils.timezone
import jsonfield.fields
import model_utils.fields
from django.conf import settings
from django.db import migrations, models
from opaque_keys.edx.django.models import CourseKeyField

import openedx.core.djangoapps.credit.models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='CreditCourse',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('course_key', CourseKeyField(unique=True, max_length=255, db_index=True)),
                ('enabled', models.BooleanField(default=False)),
            ],
        ),
        migrations.CreateModel(
            name='CreditEligibility',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, verbose_name='created', editable=False)),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, verbose_name='modified', editable=False)),
                ('username', models.CharField(max_length=255, db_index=True)),
                ('deadline', models.DateTimeField(default=openedx.core.djangoapps.credit.models.default_deadline_for_credit_eligibility, help_text='Deadline for purchasing and requesting credit.')),
                ('course', models.ForeignKey(related_name='eligibilities', to='credit.CreditCourse', on_delete=models.CASCADE)),
            ],
            options={
                'verbose_name_plural': 'Credit eligibilities',
            },
        ),
        migrations.CreateModel(
            name='CreditProvider',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, verbose_name='created', editable=False)),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, verbose_name='modified', editable=False)),
                ('provider_id', models.CharField(help_text='Unique identifier for this credit provider. Only alphanumeric characters and hyphens (-) are allowed. The identifier is case-sensitive.', unique=True, max_length=255, validators=[django.core.validators.RegexValidator(regex='[a-z,A-Z,0-9,\\-]+', message='Only alphanumeric characters and hyphens (-) are allowed', code='invalid_provider_id')])),
                ('active', models.BooleanField(default=True, help_text='Whether the credit provider is currently enabled.')),
                ('display_name', models.CharField(help_text='Name of the credit provider displayed to users', max_length=255)),
                ('enable_integration', models.BooleanField(default=False, help_text='When true, automatically notify the credit provider when a user requests credit. In order for this to work, a shared secret key MUST be configured for the credit provider in secure auth settings.')),
                ('provider_url', models.URLField(default='', help_text='URL of the credit provider.  If automatic integration is enabled, this will the the end-point that we POST to to notify the provider of a credit request.  Otherwise, the user will be shown a link to this URL, so the user can request credit from the provider directly.')),
                ('provider_status_url', models.URLField(default='', help_text='URL from the credit provider where the user can check the status of his or her request for credit.  This is displayed to students *after* they have requested credit.')),
                ('provider_description', models.TextField(default='', help_text='Description for the credit provider displayed to users.')),
                ('fulfillment_instructions', models.TextField(help_text='Plain text or html content for displaying further steps on receipt page *after* paying for the credit to get credit for a credit course against a credit provider.', null=True, blank=True)),
                ('eligibility_email_message', models.TextField(default='', help_text='Plain text or html content for displaying custom message inside credit eligibility email content which is sent when user has met all credit eligibility requirements.')),
                ('receipt_email_message', models.TextField(default='', help_text='Plain text or html content for displaying custom message inside credit receipt email content which is sent *after* paying to get credit for a credit course.')),
                ('thumbnail_url', models.URLField(default='', help_text='Thumbnail image url of the credit provider.', max_length=255)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='CreditRequest',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, verbose_name='created', editable=False)),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, verbose_name='modified', editable=False)),
                ('uuid', models.CharField(unique=True, max_length=32, db_index=True)),
                ('username', models.CharField(max_length=255, db_index=True)),
                ('parameters', jsonfield.fields.JSONField()),
                ('status', models.CharField(default='pending', max_length=255, choices=[('pending', 'Pending'), ('approved', 'Approved'), ('rejected', 'Rejected')])),
                ('course', models.ForeignKey(related_name='credit_requests', to='credit.CreditCourse', on_delete=models.CASCADE)),
                ('provider', models.ForeignKey(related_name='credit_requests', to='credit.CreditProvider', on_delete=models.CASCADE)),
            ],
            options={
                'get_latest_by': 'created',
            },
        ),
        migrations.CreateModel(
            name='CreditRequirement',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, verbose_name='created', editable=False)),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, verbose_name='modified', editable=False)),
                ('namespace', models.CharField(max_length=255)),
                ('name', models.CharField(max_length=255)),
                ('display_name', models.CharField(default='', max_length=255)),
                ('order', models.PositiveIntegerField(default=0)),
                ('criteria', jsonfield.fields.JSONField()),
                ('active', models.BooleanField(default=True)),
                ('course', models.ForeignKey(related_name='credit_requirements', to='credit.CreditCourse', on_delete=models.CASCADE)),
            ],
            options={
                'ordering': ['order'],
            },
        ),
        migrations.CreateModel(
            name='CreditRequirementStatus',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, verbose_name='created', editable=False)),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, verbose_name='modified', editable=False)),
                ('username', models.CharField(max_length=255, db_index=True)),
                ('status', models.CharField(max_length=32, choices=[('satisfied', 'satisfied'), ('failed', 'failed'), ('declined', 'declined')])),
                ('reason', jsonfield.fields.JSONField(default={})),
                ('requirement', models.ForeignKey(related_name='statuses', to='credit.CreditRequirement', on_delete=models.CASCADE)),
            ],
        ),
        migrations.CreateModel(
            name='HistoricalCreditRequest',
            fields=[
                ('id', models.IntegerField(verbose_name='ID', db_index=True, auto_created=True, blank=True)),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, verbose_name='created', editable=False)),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, verbose_name='modified', editable=False)),
                ('uuid', models.CharField(max_length=32, db_index=True)),
                ('username', models.CharField(max_length=255, db_index=True)),
                ('parameters', jsonfield.fields.JSONField()),
                ('status', models.CharField(default='pending', max_length=255, choices=[('pending', 'Pending'), ('approved', 'Approved'), ('rejected', 'Rejected')])),
                ('history_id', models.AutoField(serialize=False, primary_key=True)),
                ('history_date', models.DateTimeField()),
                ('history_type', models.CharField(max_length=1, choices=[('+', 'Created'), ('~', 'Changed'), ('-', 'Deleted')])),
                ('course', models.ForeignKey(related_name='+', on_delete=django.db.models.deletion.DO_NOTHING, db_constraint=False, blank=True, to='credit.CreditCourse', null=True)),
                ('history_user', models.ForeignKey(related_name='+', on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL, null=True)),
                ('provider', models.ForeignKey(related_name='+', on_delete=django.db.models.deletion.DO_NOTHING, db_constraint=False, blank=True, to='credit.CreditProvider', null=True)),
            ],
            options={
                'ordering': ('-history_date', '-history_id'),
                'get_latest_by': 'history_date',
                'verbose_name': 'historical credit request',
            },
        ),
        migrations.CreateModel(
            name='HistoricalCreditRequirementStatus',
            fields=[
                ('id', models.IntegerField(verbose_name='ID', db_index=True, auto_created=True, blank=True)),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, verbose_name='created', editable=False)),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, verbose_name='modified', editable=False)),
                ('username', models.CharField(max_length=255, db_index=True)),
                ('status', models.CharField(max_length=32, choices=[('satisfied', 'satisfied'), ('failed', 'failed'), ('declined', 'declined')])),
                ('reason', jsonfield.fields.JSONField(default={})),
                ('history_id', models.AutoField(serialize=False, primary_key=True)),
                ('history_date', models.DateTimeField()),
                ('history_type', models.CharField(max_length=1, choices=[('+', 'Created'), ('~', 'Changed'), ('-', 'Deleted')])),
                ('history_user', models.ForeignKey(related_name='+', on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL, null=True)),
                ('requirement', models.ForeignKey(related_name='+', on_delete=django.db.models.deletion.DO_NOTHING, db_constraint=False, blank=True, to='credit.CreditRequirement', null=True)),
            ],
            options={
                'ordering': ('-history_date', '-history_id'),
                'get_latest_by': 'history_date',
                'verbose_name': 'historical credit requirement status',
            },
        ),
        migrations.AlterUniqueTogether(
            name='creditrequirementstatus',
            unique_together={('username', 'requirement')},
        ),
        migrations.AlterUniqueTogether(
            name='creditrequirement',
            unique_together={('namespace', 'name', 'course')},
        ),
        migrations.AlterUniqueTogether(
            name='creditrequest',
            unique_together={('username', 'course', 'provider')},
        ),
        migrations.AlterUniqueTogether(
            name='crediteligibility',
            unique_together={('username', 'course')},
        ),
    ]
