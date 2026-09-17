import uuid

from django.db import migrations, models

import apps.conversations.models


class Migration(migrations.Migration):

    dependencies = [
        ("conversations", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="groupconversation",
            name="avatar",
            field=models.ImageField(
                blank=True,
                upload_to=(
                    apps.conversations.models.group_avatar_upload_to
                ),
            ),
        ),
    ]
