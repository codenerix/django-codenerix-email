# Generated by Django 5.0.6 on 2024-06-04 11:05

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("codenerix_email", "0010_emailmessage_content_subtype_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="emailmessage",
            name="content_subtype",
            field=models.CharField(
                choices=[("plain", "Plain"), ("html", "HTML Web")],
                default="html",
                max_length=256,
                verbose_name="Content Subtype",
            ),
        ),
        migrations.AlterField(
            model_name="emailtemplate",
            name="content_subtype",
            field=models.CharField(
                choices=[("plain", "Plain"), ("html", "HTML Web")],
                default="html",
                max_length=256,
                verbose_name="Content Subtype",
            ),
        ),
    ]