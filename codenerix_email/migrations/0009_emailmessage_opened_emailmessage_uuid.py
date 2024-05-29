# Generated by Django 5.0.4 on 2024-05-22 11:41

import uuid
from django.db import migrations, models


def create_uuid(apps, schema_editor):
    EmailMessage = apps.get_model("codenerix_email", "EmailMessage")
    for email_message in EmailMessage.objects.all():
        email_message.uuid = uuid.uuid4()
        email_message.save()


class Migration(migrations.Migration):

    dependencies = [
        ("codenerix_email", "0008_auto_20171201_0928"),
    ]

    operations = [
        migrations.AddField(
            model_name="emailmessage",
            name="opened",
            field=models.DateTimeField(
                blank=True, default=None, null=True, verbose_name="Opened"
            ),
        ),
        migrations.AddField(
            model_name="emailmessage",
            name="uuid",
            field=models.UUIDField(blank=True, null=True),
        ),
        migrations.RunPython(create_uuid),
        migrations.AlterField(
            model_name="emailmessage",
            name="uuid",
            field=models.UUIDField(
                default=uuid.uuid4,
                editable=False,
                unique=True,
                verbose_name="UUID",
            ),
        ),
    ]