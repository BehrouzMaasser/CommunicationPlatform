from django.db import migrations, models

import apps.voice.models


class Migration(migrations.Migration):

    dependencies = [
        ("voice", "0004_remove_voiceparticipation_unique_voice_participation_per_session_user"),
    ]

    operations = [
        migrations.AddField(
            model_name="voiceroom",
            name="avatar",
            field=models.ImageField(
                blank=True,
                upload_to=(
                    apps.voice.models.voice_room_avatar_upload_to
                ),
            ),
        ),
    ]
