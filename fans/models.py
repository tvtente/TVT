from django.db import models

class Fan(models.Model):
    class ProfileType(models.TextChoices):
        GENERAL = "general", "General"
        VIP = "vip", "VIP"
        SPECIAL = "special", "Especial"

    platform = models.CharField(max_length=30, default="instagram")
    platform_user_id = models.CharField(max_length=128)
    username = models.CharField(max_length=150, blank=True)
    display_name = models.CharField(max_length=180, blank=True)
    profile_type = models.CharField(max_length=20, choices=ProfileType.choices, default=ProfileType.GENERAL)
    is_vip = models.BooleanField(default=False)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["platform", "platform_user_id"], name="unique_platform_fan")
        ]

    def __str__(self):
        return self.display_name or self.username or self.platform_user_id

class FanRule(models.Model):
    fan = models.OneToOneField(Fan, on_delete=models.CASCADE, related_name="rule")
    tone = models.CharField(max_length=255, blank=True)
    preferred_names = models.CharField(max_length=255, blank=True)
    emojis = models.CharField(max_length=255, blank=True)
    forbidden_topics = models.TextField(blank=True)
    special_context = models.TextField(blank=True)
    human_review_required = models.BooleanField(default=False)

    def __str__(self):
        return f"Reglas de {self.fan}"
