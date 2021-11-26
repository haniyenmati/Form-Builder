from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify


class Business(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='business')
    label = models.CharField(max_length=256, unique=True, primary_key=True)
    slug = models.SlugField(max_length=256, unique=True)
    registeration_date = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        self.slug = slugify(self.label)
        return super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.label