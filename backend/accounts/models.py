from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify


class Business(models.Model):
    """
    **a db table containing a user and some details.**
    user: [one-to-one] logins are provided form this user.
    label: [unique, pk] a label which is unique for each business.
    slug: [unique, auto-generate] is being used for lookup_field to view each business detail and is auto generated
    from label.
    registration_date: [auto-generated] is being set, whenever a business instance is created.
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='business')
    label = models.CharField(max_length=256, unique=True, primary_key=True)
    slug = models.SlugField(max_length=256, unique=True)
    registeration_date = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        """
        overriding save method to handle auto generate slug. (using slugify)
        """
        self.slug = slugify(self.label)
        return super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.label
