from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('coursewarehistoryextended', '0001_initial'),
    ]

    operations = [
        migrations.AlterIndexTogether(
            name='studentmodulehistoryextended',
            index_together={('student_module',)},
        ),
    ]
